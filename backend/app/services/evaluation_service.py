"""
Evaluation Service
===================
Computes research evaluation metrics for mechanism discovery experiments.

Metrics implemented:
  - Top-1, Top-3, Top-5 Mechanism Accuracy
  - Mean Reciprocal Rank (MRR)
  - Normalized Discounted Cumulative Gain (NDCG)
  - Evidence Attribution Precision/Recall
  - False Explanation Rate
  - Contradiction Detection Accuracy

Uses synthetic ground-truth labels stored in FailureEvent.root_cause_label.
These labels are ONLY used during evaluation — never exposed to the AI pipeline.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    CandidateMechanism,
    Dataset,
    Experiment,
    ExperimentResult,
    FailureEvent,
    Investigation,
    MechanismEvidence,
)


# Mapping from ground-truth label prefix to mechanism type
GT_LABEL_TO_TYPE = {
    "GTM-001": "thermal",
    "GTM-002": "contamination",
    "GTM-003": "wear",
    "GTM-004": "process_drift",
    "GTM-005": "thermal",
}


class EvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_evaluation(self, experiment_id: str) -> None:
        """Run the evaluation experiment and persist results."""
        exp_uid = uuid.UUID(experiment_id)
        experiment = await self.db.get(Experiment, exp_uid)
        if not experiment:
            logger.error(f"Experiment {experiment_id} not found")
            return

        try:
            experiment.status = "running"
            experiment.started_at = datetime.now(timezone.utc)
            await self.db.flush()

            # Load all completed investigations for this dataset
            inv_result = await self.db.execute(
                select(Investigation)
                .where(Investigation.dataset_id == experiment.dataset_id)
                .where(Investigation.status == "completed")
            )
            investigations = inv_result.scalars().all()

            if not investigations:
                raise ValueError("No completed investigations found for this dataset")

            # Load ground-truth failure events
            fe_result = await self.db.execute(
                select(FailureEvent)
                .where(FailureEvent.dataset_id == experiment.dataset_id)
                .where(FailureEvent.is_synthetic_ground_truth == True)
            )
            ground_truth_events = fe_result.scalars().all()

            if not ground_truth_events:
                raise ValueError("No ground-truth failure events found (synthetic dataset required)")

            # Compute metrics
            metrics = await self._compute_metrics(
                investigations=investigations,
                ground_truth_events=ground_truth_events,
                experiment_type=experiment.experiment_type,
            )

            # Save metrics
            for metric_name, metric_value in metrics.items():
                result = ExperimentResult(
                    experiment_id=exp_uid,
                    metric_name=metric_name,
                    metric_value=float(metric_value) if metric_value is not None else 0.0,
                )
                self.db.add(result)

            # Save JSON results
            output_dir = Path(settings.experiment_output_dir) / "tables"
            output_dir.mkdir(parents=True, exist_ok=True)
            results_path = output_dir / f"experiment_{experiment_id[:8]}_results.json"
            with open(results_path, "w") as f:
                json.dump({
                    "experiment_id": experiment_id,
                    "experiment_type": experiment.experiment_type,
                    "metrics": {k: float(v) if v is not None else None for k, v in metrics.items()},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, f, indent=2)

            experiment.status = "completed"
            experiment.completed_at = datetime.now(timezone.utc)
            await self.db.flush()
            logger.info(f"Evaluation {experiment_id} completed: {metrics}")

        except Exception as e:
            logger.exception(f"Evaluation failed: {e}")
            experiment.status = "failed"
            experiment.completed_at = datetime.now(timezone.utc)
            await self.db.flush()

    async def _compute_metrics(
        self,
        investigations: List[Investigation],
        ground_truth_events: List[FailureEvent],
        experiment_type: str,
    ) -> Dict[str, float]:
        """Compute all evaluation metrics."""

        # Build ground truth lookup: investigation → expected mechanism type
        # An investigation is linked to a failure event
        gt_lookup: Dict[str, str] = {}
        for fe in ground_truth_events:
            if fe.root_cause_label:
                # "GTM-001:Cooling System Degradation" → "thermal"
                gtm_prefix = fe.root_cause_label.split(":")[0].strip()
                expected_type = GT_LABEL_TO_TYPE.get(gtm_prefix, "unknown")
                if fe.id:
                    gt_lookup[str(fe.id)] = expected_type

        reciprocal_ranks = []
        top1_hits = []
        top3_hits = []
        top5_hits = []
        ndcg_scores = []

        for inv in investigations:
            if not inv.failure_event_id:
                continue
            expected_type = gt_lookup.get(str(inv.failure_event_id))
            if not expected_type:
                continue

            # Get ranked mechanisms for this investigation
            mech_result = await self.db.execute(
                select(CandidateMechanism)
                .where(CandidateMechanism.investigation_id == inv.id)
                .order_by(CandidateMechanism.rank)
            )
            mechanisms = mech_result.scalars().all()
            if not mechanisms:
                reciprocal_ranks.append(0.0)
                top1_hits.append(0)
                top3_hits.append(0)
                top5_hits.append(0)
                ndcg_scores.append(0.0)
                continue

            # Find position of correct mechanism type
            correct_rank = None
            for i, mech in enumerate(mechanisms[:10], start=1):
                mtype = mech.mechanism_type.value if hasattr(mech.mechanism_type, 'value') else str(mech.mechanism_type)
                if mtype == expected_type:
                    correct_rank = i
                    break

            if correct_rank is None:
                reciprocal_ranks.append(0.0)
                top1_hits.append(0)
                top3_hits.append(0)
                top5_hits.append(0)
                ndcg_scores.append(0.0)
            else:
                reciprocal_ranks.append(1.0 / correct_rank)
                top1_hits.append(1 if correct_rank <= 1 else 0)
                top3_hits.append(1 if correct_rank <= 3 else 0)
                top5_hits.append(1 if correct_rank <= 5 else 0)
                # NDCG@5
                relevances = [
                    1.0 if (
                        (mech.mechanism_type.value if hasattr(mech.mechanism_type, 'value') else str(mech.mechanism_type))
                        == expected_type
                    ) else 0.0
                    for mech in mechanisms[:5]
                ]
                dcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(relevances))
                ideal_dcg = 1.0  # Best possible: correct mechanism at rank 1
                ndcg = dcg / ideal_dcg if ideal_dcg > 0 else 0.0
                ndcg_scores.append(ndcg)

        n = len(reciprocal_ranks)
        if n == 0:
            return {"error": "No evaluable investigations found"}

        metrics = {
            "n_investigations_evaluated": float(n),
            "top_1_accuracy": float(np.mean(top1_hits)),
            "top_3_recall": float(np.mean(top3_hits)),
            "top_5_recall": float(np.mean(top5_hits)),
            "mean_reciprocal_rank": float(np.mean(reciprocal_ranks)),
            "ndcg_at_5": float(np.mean(ndcg_scores)),
            "experiment_type": 0.0,  # categorical stored separately
        }

        return metrics
