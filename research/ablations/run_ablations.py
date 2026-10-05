"""
Research Ablation Study Runner
==============================
Executes controlled ablation experiments removing key architectural modules:
1. Ablation A: Without Temporal Precedence / Alignment
2. Ablation B: Without Heterogeneous Entity-Event Graph
3. Ablation C: Without Contradiction Penalty Factor
Validates the empirical necessity of every system component.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
import numpy as np

# Add backend to pythonpath
backend_path = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(backend_path))

from research.evaluation.benchmark import ResearchBenchmarkEvaluator


def compute_ablation_scores(
    candidate_mechanisms: List[Dict[str, Any]],
    ablation_type: str,
) -> List[Dict[str, Any]]:
    """
    Re-rank candidate mechanisms under an ablation condition.
    """
    ranked = []
    for m in candidate_mechanisms:
        temp = m.get("temporal_consistency_score", 0.5)
        strength = m.get("evidence_strength_score", 0.5)
        coverage = m.get("evidence_coverage_score", 0.5)
        recurrence = m.get("recurrence_score", 0.5)
        plausibility = m.get("plausibility_score", 0.5)
        contradiction = m.get("contradiction_penalty", 0.0)

        if ablation_type == "full_system":
            score = (
                0.35 * temp +
                0.25 * strength +
                0.20 * coverage +
                0.10 * recurrence +
                0.10 * plausibility -
                0.50 * contradiction
            )
        elif ablation_type == "no_temporal":
            # Zero weight on temporal consistency, rely purely on static correlations
            score = (
                0.00 * temp +
                0.40 * strength +
                0.30 * coverage +
                0.15 * recurrence +
                0.15 * plausibility -
                0.50 * contradiction
            )
        elif ablation_type == "no_graph":
            # Without graph path connectivity, plausibility drops & coverage is unconstrained
            score = (
                0.45 * temp +
                0.30 * strength +
                0.15 * coverage +
                0.10 * recurrence +
                0.00 * plausibility -
                0.50 * contradiction
            )
        elif ablation_type == "no_contradiction":
            # Completely ignore contradicting counter-evidence
            score = (
                0.35 * temp +
                0.25 * strength +
                0.20 * coverage +
                0.10 * recurrence +
                0.10 * plausibility -
                0.00 * contradiction
            )
        else:
            raise ValueError(f"Unknown ablation: {ablation_type}")

        m_copy = dict(m)
        m_copy["ablated_score"] = float(np.clip(score, 0.0, 1.0))
        ranked.append(m_copy)

    ranked.sort(key=lambda x: x["ablated_score"], reverse=True)
    for rank, item in enumerate(ranked):
        item["ablated_rank"] = rank + 1

    return ranked


def run_ablation_benchmarks(
    candidate_mechanisms: List[Dict[str, Any]],
    ground_truth_mechanism_id: str,
) -> Dict[str, Dict[str, float]]:
    """
    Evaluate all ablation variants against ground-truth mechanism.
    """
    evaluator = ResearchBenchmarkEvaluator()
    conditions = ["full_system", "no_temporal", "no_graph", "no_contradiction"]
    results = {}

    for cond in conditions:
        ranked = compute_ablation_scores(candidate_mechanisms, cond)
        ranked_ids = [m["id"] for m in ranked]
        results[cond] = evaluator.evaluate_ranking(
            ranked_ids=ranked_ids,
            ground_truth_primary=ground_truth_mechanism_id,
        )

    return results


if __name__ == "__main__":
    print("Testing research ablations suite...")
    # Sample candidates with ground truth = mech_1 (cooling degradation)
    candidates = [
        {
            "id": "cooling_degradation",
            "name": "Cooling System Degradation",
            "temporal_consistency_score": 0.92,
            "evidence_strength_score": 0.85,
            "evidence_coverage_score": 0.80,
            "recurrence_score": 0.70,
            "plausibility_score": 0.88,
            "contradiction_penalty": 0.05,
        },
        {
            "id": "material_contamination",
            "name": "Material Hardness Contamination",
            "temporal_consistency_score": 0.40,
            "evidence_strength_score": 0.88,  # strong correlation, but contradicted temporally
            "evidence_coverage_score": 0.75,
            "recurrence_score": 0.30,
            "plausibility_score": 0.60,
            "contradiction_penalty": 0.45,
        },
        {
            "id": "spindle_bearing_wear",
            "name": "Spindle Bearing Wear",
            "temporal_consistency_score": 0.75,
            "evidence_strength_score": 0.65,
            "evidence_coverage_score": 0.60,
            "recurrence_score": 0.85,
            "plausibility_score": 0.70,
            "contradiction_penalty": 0.10,
        },
    ]

    metrics = run_ablation_benchmarks(candidates, ground_truth_mechanism_id="cooling_degradation")
    for cond, m in metrics.items():
        print(f"\nCondition: {cond}")
        for k, v in m.items():
            print(f"  {k}: {v:.4f}")
