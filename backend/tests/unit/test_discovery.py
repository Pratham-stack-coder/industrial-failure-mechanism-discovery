"""
Unit tests for Candidate Mechanism Discovery
"""

import pytest
from datetime import datetime, timezone
import pandas as pd
from app.mechanisms.discovery import (
    MechanismDiscoveryOrchestrator,
    TemporalAssociationDiscovery,
    MECHANISM_TEMPLATES,
    CandidateMechanismHypothesis,
    EvidenceItem,
)


def test_discovery_templates():
    assert len(MECHANISM_TEMPLATES) >= 5
    assert "thermal" in MECHANISM_TEMPLATES
    assert "wear" in MECHANISM_TEMPLATES
    assert "contamination" in MECHANISM_TEMPLATES
    assert "process_drift" in MECHANISM_TEMPLATES


def test_discovery_orchestrator_initialization():
    orchestrator = MechanismDiscoveryOrchestrator(
        lookback_hours=72.0,
        min_association_threshold=0.15,
        max_candidates=10,
    )
    assert orchestrator.lookback_hours == 72.0
    assert orchestrator.max_candidates == 10
    assert orchestrator.temporal_discoverer is not None
    assert orchestrator.graph_discoverer is not None
    assert orchestrator.lot_discoverer is not None


def test_candidate_hypothesis_structure():
    hyp = CandidateMechanismHypothesis(
        hypothesis_id="test-hyp-1",
        mechanism_type="thermal",
        name="Thermal Degradation",
        description="Coolant flow drop caused spindle overheat",
        discovery_method="temporal_association",
        cause="Coolant flow drop",
        process_condition="High feed load",
        intermediate_effect="Spindle temperature elevation",
        observable_failure="Dimensional tolerance excursion",
        variables_involved=["coolant_flow_rate", "spindle_temperature"],
        supporting_evidence=[
            EvidenceItem(
                evidence_type="telemetry_anomaly",
                polarity="supporting",
                description="Coolant flow dropped below 30 L/min",
                strength=0.88,
                lag_hours=4.0,
            )
        ],
    )

    assert hyp.hypothesis_id == "test-hyp-1"
    assert hyp.mechanism_type == "thermal"
    assert len(hyp.supporting_evidence) == 1
    assert hyp.supporting_evidence[0].lag_hours == 4.0
