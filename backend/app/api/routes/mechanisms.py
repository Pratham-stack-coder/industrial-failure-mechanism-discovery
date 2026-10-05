"""Mechanism detail routes."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import CandidateMechanism, MechanismEvidence
from app.ranking.ranker import get_scoring_breakdown

router = APIRouter()


@router.get("/{mechanism_id}")
async def get_mechanism(
    mechanism_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get mechanism details."""
    try:
        uid = uuid.UUID(mechanism_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID")

    mech = await db.get(CandidateMechanism, uid)
    if not mech:
        raise HTTPException(status_code=404, detail="Mechanism not found")

    return {
        "id": str(mech.id),
        "investigation_id": str(mech.investigation_id),
        "mechanism_type": mech.mechanism_type.value if hasattr(mech.mechanism_type, 'value') else str(mech.mechanism_type),
        "name": mech.name,
        "description": mech.description,
        "rank": mech.rank,
        "overall_score": mech.overall_score,
        "confidence": mech.confidence,
        "cause": mech.cause,
        "process_condition": mech.process_condition,
        "intermediate_effect": mech.intermediate_effect,
        "observable_failure": mech.observable_failure,
        "variables_involved": mech.variables_involved or [],
        "entities_involved": mech.entities_involved or [],
        "temporal_conditions": mech.temporal_conditions or {},
        "expected_effects": mech.expected_effects or [],
        "discovery_method": mech.discovery_method,
        "temporal_consistency_score": mech.temporal_consistency_score,
        "evidence_strength_score": mech.evidence_strength_score,
        "evidence_coverage_score": mech.evidence_coverage_score,
        "recurrence_score": mech.recurrence_score,
        "plausibility_score": mech.plausibility_score,
        "contradiction_penalty": mech.contradiction_penalty,
        "supporting_evidence_count": mech.supporting_evidence_count,
        "contradicting_evidence_count": mech.contradicting_evidence_count,
        "missing_evidence_count": mech.missing_evidence_count,
        "llm_explanation": mech.llm_explanation,
    }


@router.get("/{mechanism_id}/evidence")
async def get_mechanism_evidence(
    mechanism_id: str,
    polarity: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all evidence items for a mechanism."""
    try:
        uid = uuid.UUID(mechanism_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID")

    stmt = select(MechanismEvidence).where(MechanismEvidence.mechanism_id == uid)
    if polarity:
        from app.models import EvidencePolarity
        try:
            stmt = stmt.where(MechanismEvidence.polarity == EvidencePolarity(polarity))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid polarity: {polarity}")
    stmt = stmt.order_by(MechanismEvidence.strength.desc())

    result = await db.execute(stmt)
    evidence_items = result.scalars().all()

    return {
        "mechanism_id": mechanism_id,
        "evidence": [
            {
                "id": str(ev.id),
                "evidence_type": ev.evidence_type.value if hasattr(ev.evidence_type, 'value') else str(ev.evidence_type),
                "polarity": ev.polarity.value if hasattr(ev.polarity, 'value') else str(ev.polarity),
                "description": ev.description,
                "strength": ev.strength,
                "source_table": ev.source_table,
                "source_id": str(ev.source_id) if ev.source_id else None,
                "source_timestamp": ev.source_timestamp.isoformat() if ev.source_timestamp else None,
                "measured_value": ev.measured_value,
                "expected_value": ev.expected_value,
                "deviation": ev.deviation,
                "statistical_significance": ev.statistical_significance,
                "lag_hours": ev.lag_hours,
                "event_time": ev.event_time.isoformat() if ev.event_time else None,
            }
            for ev in evidence_items
        ],
    }
