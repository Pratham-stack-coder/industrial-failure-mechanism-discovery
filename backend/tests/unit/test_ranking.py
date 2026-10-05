"""
Unit tests for Mechanism Ranking and Multi-Factor Scoring
"""

import pytest
from app.mechanisms.discovery import CandidateMechanismHypothesis, EvidenceItem
from app.ranking.ranker import (
    score_temporal_consistency,
    score_evidence_strength,
    score_evidence_coverage,
    compute_contradiction_penalty,
    rank_mechanisms,
)


def make_sample_hypothesis(name="test_mech", mech_type="thermal"):
    return CandidateMechanismHypothesis(
        hypothesis_id="hyp-test-1",
        discovery_method="temporal_association",
        name=name,
        description="Test hypothesis description",
        mechanism_type=mech_type,
        cause="Coolant flow drop",
        process_condition="High feed rate",
        intermediate_effect="Spindle temperature rise",
        observable_failure="Thermal expansion out of spec",
        variables_involved=["coolant_flow", "spindle_temp"],
        entities_involved=["machine_1"],
        temporal_conditions={"min_lag_hours": 1.0, "max_lag_hours": 12.0},
        expected_effects=["tolerance excursion"],
        supporting_evidence=[
            EvidenceItem(
                evidence_type="telemetry_anomaly",
                polarity="supporting",
                description="Coolant flow dropped below 30 L/min",
                strength=0.9,
                source_table="telemetry",
                lag_hours=4.0,
            ),
            EvidenceItem(
                evidence_type="telemetry_anomaly",
                polarity="supporting",
                description="Spindle temp exceeded 65 C",
                strength=0.85,
                source_table="telemetry",
                lag_hours=1.5,
            ),
        ],
        contradicting_evidence=[],
        missing_evidence=[],
    )


def test_score_temporal_consistency_positive_lags():
    hyp = make_sample_hypothesis()
    score = score_temporal_consistency(hyp)
    assert 0.0 <= score <= 1.0
    assert score > 0.6  # Valid precursor ordering should score high


def test_score_evidence_strength():
    hyp = make_sample_hypothesis()
    score = score_evidence_strength(hyp)
    assert 0.0 <= score <= 1.0
    assert score > 0.5


def test_contradiction_penalty():
    hyp = make_sample_hypothesis()
    assert compute_contradiction_penalty(hyp) == 0.0

    # Add contradicting evidence
    hyp.contradicting_evidence.append(
        EvidenceItem(
            evidence_type="inspection_normal",
            polarity="contradicting",
            description="Intermediate inspection showed normal tolerance",
            strength=0.8,
            source_table="quality_inspections",
        )
    )
    penalty = compute_contradiction_penalty(hyp)
    assert penalty > 0.0
    assert penalty <= 0.5


def test_rank_mechanisms_ordering():
    hyp1 = make_sample_hypothesis(name="Strong Hypothesis", mech_type="thermal")
    hyp2 = make_sample_hypothesis(name="Contradicted Hypothesis", mech_type="contamination")
    # Add heavy contradiction to hyp2
    hyp2.contradicting_evidence.append(
        EvidenceItem(
            evidence_type="test",
            polarity="contradicting",
            description="Contradiction",
            strength=1.0,
            source_table="test",
        )
    )

    ranked = rank_mechanisms([hyp2, hyp1])
    assert len(ranked) == 2
    assert ranked[0].name == "Strong Hypothesis"
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    assert ranked[0].overall_score >= ranked[1].overall_score
