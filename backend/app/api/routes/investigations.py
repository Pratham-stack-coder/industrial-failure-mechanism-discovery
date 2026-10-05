"""
Investigation routes.
POST /api/investigations              — create investigation
GET  /api/investigations              — list investigations  
GET  /api/investigations/{id}         — get investigation
POST /api/investigations/{id}/run     — run investigation pipeline
GET  /api/investigations/{id}/mechanisms — get mechanisms for investigation
GET  /api/investigations/{id}/timeline   — get event timeline
GET  /api/investigations/{id}/graph      — get relationship graph
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.models import (
    Investigation,
    InvestigationStatus,
    CandidateMechanism,
    MechanismEvidence,
    Dataset,
    FailureEvent,
    Machine,
)
from app.services.investigation_service import InvestigationService

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class InvestigationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    dataset_id: str
    failure_event_id: Optional[str] = None
    machine_id: Optional[str] = None
    analysis_start_time: datetime
    analysis_end_time: datetime


class InvestigationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    dataset_id: str
    failure_event_id: Optional[str]
    machine_id: Optional[str]
    analysis_start_time: datetime
    analysis_end_time: datetime
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    mechanism_count: Optional[int] = 0
    created_at: datetime

    class Config:
        from_attributes = True


class InvestigationList(BaseModel):
    investigations: List[InvestigationResponse]
    total: int


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=InvestigationResponse, status_code=201)
async def create_investigation(
    payload: InvestigationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new failure investigation."""
    # Validate dataset exists
    dataset = await db.get(Dataset, uuid.UUID(payload.dataset_id))
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {payload.dataset_id} not found")

    if payload.analysis_start_time >= payload.analysis_end_time:
        raise HTTPException(
            status_code=422,
            detail="analysis_start_time must be before analysis_end_time",
        )

    investigation = Investigation(
        name=payload.name,
        description=payload.description,
        dataset_id=uuid.UUID(payload.dataset_id),
        failure_event_id=(
            uuid.UUID(payload.failure_event_id) if payload.failure_event_id else None
        ),
        machine_id=(
            uuid.UUID(payload.machine_id) if payload.machine_id else None
        ),
        analysis_start_time=payload.analysis_start_time,
        analysis_end_time=payload.analysis_end_time,
        status=InvestigationStatus.PENDING,
        config_snapshot={
            "lookback_hours": settings.temporal_lookback_hours,
            "min_association_threshold": settings.min_association_threshold,
            "max_candidate_mechanisms": settings.max_candidate_mechanisms,
        },
    )
    db.add(investigation)
    await db.flush()
    await db.refresh(investigation)

    logger.info(f"Created investigation {investigation.id}")
    return _to_response(investigation, mechanism_count=0)


@router.get("", response_model=InvestigationList)
async def list_investigations(
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    dataset_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List investigations with optional filtering."""
    stmt = select(Investigation).order_by(Investigation.created_at.desc())

    if dataset_id:
        stmt = stmt.where(Investigation.dataset_id == uuid.UUID(dataset_id))
    if status:
        try:
            stmt = stmt.where(Investigation.status == InvestigationStatus(status))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: {status}")

    total_stmt = stmt
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    investigations = result.scalars().all()

    # Count mechanisms per investigation
    responses = []
    for inv in investigations:
        mech_result = await db.execute(
            select(CandidateMechanism).where(
                CandidateMechanism.investigation_id == inv.id
            )
        )
        mech_count = len(mech_result.scalars().all())
        responses.append(_to_response(inv, mechanism_count=mech_count))

    return InvestigationList(investigations=responses, total=len(responses))


@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific investigation by ID."""
    inv = await _get_or_404(db, investigation_id)
    mech_result = await db.execute(
        select(CandidateMechanism).where(
            CandidateMechanism.investigation_id == inv.id
        )
    )
    mech_count = len(mech_result.scalars().all())
    return _to_response(inv, mechanism_count=mech_count)


@router.post("/{investigation_id}/run", status_code=202)
async def run_investigation(
    investigation_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the investigation pipeline asynchronously.
    The pipeline runs in the background and updates the investigation status.
    """
    inv = await _get_or_404(db, investigation_id)

    if inv.status == InvestigationStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Investigation is already running")
    if inv.status == InvestigationStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail="Investigation already completed. Create a new one to re-run.",
        )

    # Mark as running
    inv.status = InvestigationStatus.RUNNING
    inv.started_at = datetime.now(timezone.utc)
    await db.flush()

    background_tasks.add_task(
        _run_pipeline_task,
        investigation_id=investigation_id,
    )

    return {
        "message": "Investigation pipeline started",
        "investigation_id": investigation_id,
        "status": "running",
    }


@router.get("/{investigation_id}/mechanisms")
async def get_investigation_mechanisms(
    investigation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all candidate mechanisms for an investigation, ordered by rank."""
    inv = await _get_or_404(db, investigation_id)

    result = await db.execute(
        select(CandidateMechanism)
        .where(CandidateMechanism.investigation_id == inv.id)
        .order_by(CandidateMechanism.rank)
    )
    mechanisms = result.scalars().all()

    return {
        "investigation_id": investigation_id,
        "investigation_name": inv.name,
        "status": inv.status,
        "mechanisms": [_mechanism_to_dict(m) for m in mechanisms],
    }


@router.get("/{investigation_id}/timeline")
async def get_investigation_timeline(
    investigation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the event timeline for an investigation."""
    inv = await _get_or_404(db, investigation_id)
    service = InvestigationService(db)
    timeline = await service.get_timeline(inv)
    return {"investigation_id": investigation_id, "timeline": timeline}


@router.get("/{investigation_id}/graph")
async def get_investigation_graph(
    investigation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the relationship graph for visualization."""
    inv = await _get_or_404(db, investigation_id)
    service = InvestigationService(db)
    graph_data = await service.get_graph(inv)
    return {"investigation_id": investigation_id, "graph": graph_data}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, investigation_id: str) -> Investigation:
    try:
        uid = uuid.UUID(investigation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format")
    inv = await db.get(Investigation, uid)
    if not inv:
        raise HTTPException(status_code=404, detail=f"Investigation {investigation_id} not found")
    return inv


def _to_response(inv: Investigation, mechanism_count: int = 0) -> InvestigationResponse:
    return InvestigationResponse(
        id=str(inv.id),
        name=inv.name,
        description=inv.description,
        dataset_id=str(inv.dataset_id),
        failure_event_id=str(inv.failure_event_id) if inv.failure_event_id else None,
        machine_id=str(inv.machine_id) if inv.machine_id else None,
        analysis_start_time=inv.analysis_start_time,
        analysis_end_time=inv.analysis_end_time,
        status=inv.status.value,
        started_at=inv.started_at,
        completed_at=inv.completed_at,
        error_message=inv.error_message,
        mechanism_count=mechanism_count,
        created_at=inv.created_at,
    )


def _mechanism_to_dict(m: CandidateMechanism) -> dict:
    return {
        "id": str(m.id),
        "investigation_id": str(m.investigation_id),
        "mechanism_type": m.mechanism_type.value if hasattr(m.mechanism_type, 'value') else str(m.mechanism_type),
        "name": m.name,
        "description": m.description,
        "rank": m.rank,
        "overall_score": m.overall_score,
        "confidence": m.confidence,
        "cause": m.cause,
        "process_condition": m.process_condition,
        "intermediate_effect": m.intermediate_effect,
        "observable_failure": m.observable_failure,
        "variables_involved": m.variables_involved or [],
        "entities_involved": m.entities_involved or [],
        "discovery_method": m.discovery_method,
        "temporal_consistency_score": m.temporal_consistency_score,
        "evidence_strength_score": m.evidence_strength_score,
        "evidence_coverage_score": m.evidence_coverage_score,
        "recurrence_score": m.recurrence_score,
        "plausibility_score": m.plausibility_score,
        "contradiction_penalty": m.contradiction_penalty,
        "supporting_evidence_count": m.supporting_evidence_count,
        "contradicting_evidence_count": m.contradicting_evidence_count,
        "missing_evidence_count": m.missing_evidence_count,
        "llm_explanation": m.llm_explanation,
        "created_at": m.created_at.isoformat(),
    }


async def _run_pipeline_task(investigation_id: str) -> None:
    """Background task that runs the full investigation pipeline."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        service = InvestigationService(db)
        await service.run_pipeline(investigation_id)
