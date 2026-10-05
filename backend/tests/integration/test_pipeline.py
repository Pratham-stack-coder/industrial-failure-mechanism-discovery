"""
Integration test for End-to-End Pipeline
========================================
Validates that synthetic data generation, feature extraction, candidate mechanism
discovery, ranking, and evaluation execute cohesively without failure.
"""

import pytest
import pandas as pd
import numpy as np
from app.services.synthetic_generator import SyntheticDataGenerator, GeneratorConfig
from app.ml.features.extractor import FeatureExtractor
from app.mechanisms.discovery import CandidateMechanismHypothesis, EvidenceItem
from app.ranking.ranker import rank_mechanisms
from research.evaluation.benchmark import ResearchBenchmarkEvaluator


def test_full_pipeline_flow():
    # 1. Generate small synthetic dataset
    config = GeneratorConfig(n_batches=50, random_seed=123)
    gen = SyntheticDataGenerator(config=config)
    tables = gen.generate()

    assert "batches" in tables
    assert "parameter_measurements" in tables
    assert "failure_events" in tables
    assert len(tables["batches"]) >= 50

    # 2. Extract features from telemetry
    t_df = tables["parameter_measurements"]
    extractor = FeatureExtractor(window_sizes=[5, 15])
    numeric_cols = [c for c in ["spindle_temp", "coolant_flow", "vibration_rms"] if c in t_df.columns]

    if numeric_cols:
        feat_df = extractor.extract_time_series_features(t_df, numeric_cols)
        assert len(feat_df) == len(t_df)
        assert f"{numeric_cols[0]}_mean_w5" in feat_df.columns

    # 3. Simulate candidate mechanism hypotheses from evidence
    hyp1 = CandidateMechanismHypothesis(
        hypothesis_id="hyp-pipe-1",
        discovery_method="temporal_association",
        name="Cooling Degradation Mechanism",
        description="Coolant flow drop caused spindle overheating leading to dimensional defect",
        mechanism_type="thermal",
        cause="Coolant flow reduction",
        process_condition="High load",
        intermediate_effect="Spindle temperature rise",
        observable_failure="Dimensional defect",
        variables_involved=["coolant_flow", "spindle_temp"],
        entities_involved=["m1"],
        temporal_conditions={"min_lag_hours": 1.0},
        expected_effects=["thermal expansion"],
        supporting_evidence=[
            EvidenceItem(
                evidence_type="telemetry_anomaly",
                polarity="supporting",
                description="Coolant flow low",
                strength=0.9,
                source_table="telemetry",
                lag_hours=3.0,
            )
        ],
        contradicting_evidence=[],
        missing_evidence=[],
    )

    hyp2 = CandidateMechanismHypothesis(
        hypothesis_id="hyp-pipe-2",
        discovery_method="operator_log",
        name="Operator Deviation Hypothesis",
        description="Incorrect speed setting",
        mechanism_type="operator_error",
        cause="Speed setting",
        process_condition="Normal",
        intermediate_effect="None",
        observable_failure="Dimensional defect",
        variables_involved=["spindle_speed"],
        entities_involved=["m1"],
        temporal_conditions={},
        expected_effects=[],
        supporting_evidence=[
            EvidenceItem(
                evidence_type="operator_log",
                polarity="supporting",
                description="Operator shift change",
                strength=0.4,
                source_table="operator_logs",
                lag_hours=1.0,
            )
        ],
        contradicting_evidence=[
            EvidenceItem(
                evidence_type="telemetry_normal",
                polarity="contradicting",
                description="Speed was nominal",
                strength=0.8,
                source_table="telemetry",
            )
        ],
        missing_evidence=[],
    )

    # 4. Rank mechanisms
    ranked = rank_mechanisms([hyp2, hyp1])
    assert len(ranked) == 2
    assert ranked[0].name == "Cooling Degradation Mechanism"
    assert ranked[0].overall_score > ranked[1].overall_score

    # 5. Evaluate benchmark metrics
    evaluator = ResearchBenchmarkEvaluator()
    eval_res = evaluator.evaluate_ranking(
        ranked_ids=[m.name for m in ranked],
        ground_truth_primary="Cooling Degradation Mechanism",
    )
    assert eval_res["ndcg@5"] == 1.0
    assert eval_res["mrr"] == 1.0
    assert eval_res["precision@1"] == 1.0
