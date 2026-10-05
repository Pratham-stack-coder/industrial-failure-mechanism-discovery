"""
Research Baseline Runner
========================
Executes Isolation Forest, Random Forest Classifier, and Correlation RCA baselines
over industrial dataset and logs formal comparative metrics.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import pandas as pd

# Add backend to pythonpath
backend_path = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(backend_path))

from app.ml.baselines.isolation_forest import IsolationForestBaseline
from app.ml.baselines.random_forest import RandomForestBaseline
from app.ml.baselines.correlation_rca import CorrelationRCABaseline
from research.evaluation.benchmark import ResearchBenchmarkEvaluator


def evaluate_baselines_on_data(
    sensor_df: pd.DataFrame,
    failure_target: pd.Series,
    ground_truth_cause_variable: str,
) -> Dict[str, Dict[str, float]]:
    """
    Run all three baselines and evaluate their ranking accuracy for finding the root cause.
    """
    results = {}
    evaluator = ResearchBenchmarkEvaluator()

    # 1. Isolation Forest Anomaly Detection
    iso = IsolationForestBaseline()
    iso.fit(sensor_df)
    iso_ranking = iso.rank_anomalous_sensors(sensor_df)
    ranked_sensors_iso = [item["sensor"] for item in iso_ranking]

    results["baseline_isolation_forest"] = evaluator.evaluate_ranking(
        ranked_ids=ranked_sensors_iso,
        ground_truth_primary=ground_truth_cause_variable,
    )

    # 2. Supervised Random Forest Classifier
    rf = RandomForestBaseline()
    rf.fit(sensor_df, failure_target)
    rf_ranking = rf.rank_features()
    ranked_sensors_rf = [item["feature"] for item in rf_ranking]

    results["baseline_random_forest"] = evaluator.evaluate_ranking(
        ranked_ids=ranked_sensors_rf,
        ground_truth_primary=ground_truth_cause_variable,
    )

    # 3. Correlation RCA (Spearman)
    corr = CorrelationRCABaseline(method="spearman")
    corr_ranking = corr.rank_variables(sensor_df, failure_target)
    ranked_sensors_corr = [item["variable"] for item in corr_ranking]

    results["baseline_correlation_rca"] = evaluator.evaluate_ranking(
        ranked_ids=ranked_sensors_corr,
        ground_truth_primary=ground_truth_cause_variable,
    )

    return results


if __name__ == "__main__":
    print("Testing research baselines with sample synthetic distribution...")
    np.random.seed(42)
    n_samples = 1000

    # True root cause
    coolant_flow = np.random.normal(50, 5, n_samples)
    coolant_flow[800:] -= 18  # drop in flow causes failure downstream

    # Intermediate effect
    spindle_temp = 40 + (60 - coolant_flow) * 1.5 + np.random.normal(0, 2, n_samples)

    # Downstream symptom (vibration)
    vibration = 1.0 + (spindle_temp / 40.0) ** 2 + np.random.normal(0, 0.5, n_samples)

    # Confounder (ambient noise)
    ambient_temp = np.random.normal(25, 3, n_samples)

    df = pd.DataFrame({
        "coolant_flow": coolant_flow,
        "spindle_temp": spindle_temp,
        "vibration_rms": vibration,
        "ambient_temp": ambient_temp,
    })

    # Ground truth failure target
    target = pd.Series((vibration > 4.5).astype(int))

    metrics = evaluate_baselines_on_data(
        sensor_df=df,
        failure_target=target,
        ground_truth_cause_variable="coolant_flow",
    )

    for b_name, m_dict in metrics.items():
        print(f"\n{b_name}:")
        for k, v in m_dict.items():
            print(f"  {k}: {v:.4f}")
