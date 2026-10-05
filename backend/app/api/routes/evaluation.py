"""
Evaluation and research experiment routes.
POST /api/evaluate           — run evaluation against ground truth
GET  /api/evaluation/results — get evaluation results
"""
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Dataset, Experiment, ExperimentResult

router = APIRouter()


class EvaluationRequest(BaseModel):
    dataset_id: str
    experiment_type: str = "full_system"
    # full_system | baseline_correlation | baseline_anomaly | baseline_ml
    # ablation_no_temporal | ablation_no_graph | ablation_no_contradiction
    description: Optional[str] = None
    config: Optional[dict] = None


@router.post("/evaluate", status_code=202)
async def create_evaluation(
    payload: EvaluationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create and run an evaluation experiment."""
    # Validate dataset
    try:
        ds_uid = uuid.UUID(payload.dataset_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid dataset_id UUID")

    dataset = await db.get(Dataset, ds_uid)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    experiment = Experiment(
        name=f"{payload.experiment_type} evaluation on {dataset.name}",
        experiment_type=payload.experiment_type,
        description=payload.description,
        dataset_id=ds_uid,
        config=payload.config or {},
        status="pending",
    )
    db.add(experiment)
    await db.flush()
    await db.refresh(experiment)

    background_tasks.add_task(_run_evaluation_task, str(experiment.id))

    return {
        "experiment_id": str(experiment.id),
        "experiment_type": payload.experiment_type,
        "status": "pending",
        "message": "Evaluation started in background",
    }


@router.get("/results")
async def get_evaluation_results(
    experiment_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all evaluation results."""
    stmt = select(Experiment).order_by(Experiment.created_at.desc())
    if experiment_type:
        stmt = stmt.where(Experiment.experiment_type == experiment_type)

    result = await db.execute(stmt)
    experiments = result.scalars().all()

    output = []
    for exp in experiments:
        results_stmt = select(ExperimentResult).where(
            ExperimentResult.experiment_id == exp.id
        )
        results_result = await db.execute(results_stmt)
        results = results_result.scalars().all()

        output.append({
            "experiment_id": str(exp.id),
            "name": exp.name,
            "experiment_type": exp.experiment_type,
            "status": exp.status,
            "started_at": exp.started_at.isoformat() if exp.started_at else None,
            "completed_at": exp.completed_at.isoformat() if exp.completed_at else None,
            "metrics": {
                r.metric_name: r.metric_value for r in results
            },
        })

    return {"experiments": output, "total": len(output)}


async def _run_evaluation_task(experiment_id: str) -> None:
    """Background evaluation task."""
    from app.core.database import AsyncSessionLocal
    from app.services.evaluation_service import EvaluationService

    async with AsyncSessionLocal() as db:
        service = EvaluationService(db)
        await service.run_evaluation(experiment_id)
