"""Dataset management routes."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Dataset, Batch, FailureEvent, Machine

router = APIRouter()


class DatasetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    source_type: str
    record_count: Optional[int]
    time_range_start: Optional[str]
    time_range_end: Optional[str]
    is_validated: bool
    created_at: str


@router.get("/datasets", response_model=List[DatasetResponse])
async def list_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all datasets."""
    result = await db.execute(
        select(Dataset).order_by(Dataset.created_at.desc()).offset(skip).limit(limit)
    )
    datasets = result.scalars().all()
    return [
        DatasetResponse(
            id=str(d.id),
            name=d.name,
            description=d.description,
            source_type=d.source_type,
            record_count=d.record_count,
            time_range_start=d.time_range_start.isoformat() if d.time_range_start else None,
            time_range_end=d.time_range_end.isoformat() if d.time_range_end else None,
            is_validated=d.is_validated,
            created_at=d.created_at.isoformat(),
        )
        for d in datasets
    ]


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get dataset details including statistics."""
    try:
        uid = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID")

    dataset = await db.get(Dataset, uid)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get counts
    batches_result = await db.execute(
        select(Batch).where(Batch.dataset_id == uid)
    )
    n_batches = len(batches_result.scalars().all())

    failures_result = await db.execute(
        select(FailureEvent).where(FailureEvent.dataset_id == uid)
    )
    failure_events = failures_result.scalars().all()

    return {
        "id": str(dataset.id),
        "name": dataset.name,
        "description": dataset.description,
        "source_type": dataset.source_type,
        "record_count": dataset.record_count,
        "time_range_start": dataset.time_range_start.isoformat() if dataset.time_range_start else None,
        "time_range_end": dataset.time_range_end.isoformat() if dataset.time_range_end else None,
        "is_validated": dataset.is_validated,
        "quality_report": dataset.quality_report,
        "schema_info": dataset.schema_info,
        "created_at": dataset.created_at.isoformat(),
        "statistics": {
            "n_batches": n_batches,
            "n_failure_events": len(failure_events),
            "n_major_failures": sum(1 for f in failure_events if f.severity.value in ("major", "critical")),
        },
    }


@router.get("/datasets/{dataset_id}/failure-events")
async def list_failure_events(
    dataset_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List failure events for a dataset."""
    try:
        uid = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID")

    result = await db.execute(
        select(FailureEvent)
        .where(FailureEvent.dataset_id == uid)
        .order_by(FailureEvent.event_time.desc())
        .offset(skip)
        .limit(limit)
    )
    events = result.scalars().all()

    return {
        "failure_events": [
            {
                "id": str(fe.id),
                "batch_id": str(fe.batch_id) if fe.batch_id else None,
                "machine_id": str(fe.machine_id) if fe.machine_id else None,
                "event_time": fe.event_time.isoformat(),
                "event_type": fe.event_type,
                "severity": fe.severity.value,
                "description": fe.description,
                "affected_quantity": fe.affected_quantity,
                "downtime_hours": fe.downtime_hours,
            }
            for fe in events
        ]
    }
