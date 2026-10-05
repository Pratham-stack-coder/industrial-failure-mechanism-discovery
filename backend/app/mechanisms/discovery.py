"""
Candidate Mechanism Discovery
==============================
Generates candidate failure mechanism hypotheses from industrial data.

Discovery approaches (modular, each independently testable):
  1. TemporalAssociationDiscovery  — finds parameters that changed before the failure
  2. GraphTraversalDiscovery       — traverses the industrial graph for causal paths
  3. ChangePointDiscovery          — finds change-points that precede the failure
  4. EventSequenceDiscovery        — mines recurring event sequences before failures
  5. MaterialLotDiscovery          — identifies shared material lots across failures

Terminology:
  - All outputs are "candidate mechanisms" or "hypotheses" — NOT proven causal facts.
  - Temporal precedence ≠ causation. This is explicitly noted in all outputs.
  - Evidence is labeled as "supporting", "contradicting", or "missing".

Each discoverer returns a list of CandidateMechanismHypothesis objects.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from app.temporal.temporal_analysis import (
    ChangePoint,
    TemporalCorrelation,
    TemporalWindow,
    detect_change_points,
    detect_parameter_trends,
    extract_window_features,
)
from app.graph.graph_builder import IndustrialGraph


# ============================================================
# Hypothesis data structure
# ============================================================

@dataclass
class EvidenceItem:
    """A single piece of evidence for/against a mechanism hypothesis."""
    evidence_type: str
    polarity: str           # "supporting" | "contradicting" | "neutral"
    description: str
    strength: float         # 0..1
    source_table: Optional[str] = None
    source_id: Optional[str] = None
    source_timestamp: Optional[str] = None
    measured_value: Optional[float] = None
    expected_value: Optional[float] = None
    deviation: Optional[float] = None
    statistical_significance: Optional[float] = None
    lag_hours: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateMechanismHypothesis:
    """
    A candidate failure mechanism hypothesis.
    Represents one plausible explanation for the observed failure.
    """
    hypothesis_id: str
    mechanism_type: str
    name: str
    description: str
    discovery_method: str

    # Structured causal chain
    cause: Optional[str] = None
    process_condition: Optional[str] = None
    intermediate_effect: Optional[str] = None
    observable_failure: Optional[str] = None

    # Entities and variables involved
    entities_involved: List[str] = field(default_factory=list)
    variables_involved: List[str] = field(default_factory=list)
    temporal_conditions: Dict[str, Any] = field(default_factory=dict)
    expected_effects: List[str] = field(default_factory=list)

    # Evidence
    supporting_evidence: List[EvidenceItem] = field(default_factory=list)
    contradicting_evidence: List[EvidenceItem] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)

    # Scores (set by ranking module)
    overall_score: float = 0.0
    confidence: float = 0.0
    rank: Optional[int] = None
    temporal_consistency_score: float = 0.0
    evidence_strength_score: float = 0.0
    evidence_coverage_score: float = 0.0
    recurrence_score: float = 0.0
    plausibility_score: float = 0.0
    contradiction_penalty: float = 0.0


# ============================================================
# Mechanism templates (knowledge base)
# ============================================================

MECHANISM_TEMPLATES = {
    "thermal": {
        "name": "Thermal Degradation",
        "description": "Temperature-related parameter excursion causing quality failure",
        "expected_parameters": ["machining_temperature", "tool_temperature", "coolant_flow_rate", "ambient_temperature"],
        "cause_template": "Temperature parameter exceeded operating limit",
        "observable_failure": "Dimensional/surface quality failure due to thermal effects",
    },
    "wear": {
        "name": "Wear-Related Failure",
        "description": "Progressive wear causing parameter drift and quality degradation",
        "expected_parameters": ["vibration_amplitude", "surface_roughness", "tool_wear_index", "spindle_load"],
        "cause_template": "Wear accumulation beyond acceptable threshold",
        "observable_failure": "Surface quality or dimensional failure due to tool/machine wear",
    },
    "contamination": {
        "name": "Contamination Event",
        "description": "Contaminant introduction causing product quality deviation",
        "expected_parameters": ["chemical_composition_index", "surface_roughness"],
        "cause_template": "Contaminated material or process fluid introduced",
        "observable_failure": "Surface defects or chemical deviation in product",
    },
    "process_drift": {
        "name": "Process Parameter Drift",
        "description": "Process parameters drifting from nominal causing quality failure",
        "expected_parameters": ["feed_rate", "cutting_speed", "spindle_speed"],
        "cause_template": "Process parameters drifted from nominal specification",
        "observable_failure": "Machining quality failure due to parameter deviation",
    },
    "mechanical": {
        "name": "Mechanical Anomaly",
        "description": "Mechanical issue detected via vibration or load anomaly",
        "expected_parameters": ["vibration_amplitude", "spindle_load", "spindle_speed"],
        "cause_template": "Mechanical component anomaly or structural issue",
        "observable_failure": "Machine or product failure from mechanical cause",
    },
}


# ============================================================
# Discovery 1: Temporal Association Discovery
# ============================================================

class TemporalAssociationDiscovery:
    """
    Discovers mechanism hypotheses by finding parameters that changed
    significantly BEFORE the failure event.

    Logic:
    1. For each parameter, run change-point detection in the lookback window
    2. If a change-point occurs before failure with sufficient magnitude, record it
    3. Map parameter → mechanism type using MECHANISM_TEMPLATES
    4. Create a hypothesis per mechanism type
    5. Collect supporting evidence from all parameters of that type
    """

    def __init__(
        self,
        lookback_hours: float = 72.0,
        min_association_threshold: float = 0.15,
        changepoint_model: str = "rbf",
        changepoint_penalty: float = 3.0,
    ):
        self.lookback_hours = lookback_hours
        self.min_threshold = min_association_threshold
        self.cp_model = changepoint_model
        self.cp_penalty = changepoint_penalty

    def discover(
        self,
        failure_time: datetime,
        measurements_df: pd.DataFrame,
        param_defs_df: pd.DataFrame,
        failure_id: str,
    ) -> List[CandidateMechanismHypothesis]:
        """
        Args:
            failure_time:    timestamp of the failure event
            measurements_df: parameter measurements with columns
                             [timestamp, parameter_code, value, machine_id]
            param_defs_df:   parameter definitions
            failure_id:      failure event ID for traceability

        Returns:
            List of CandidateMechanismHypothesis objects
        """
        if failure_time.tzinfo is None:
            failure_time = failure_time.replace(tzinfo=timezone.utc)

        cutoff = failure_time - timedelta(hours=self.lookback_hours)

        # Filter measurements to lookback window
        m_df = measurements_df.copy()
        m_df["timestamp"] = pd.to_datetime(m_df["timestamp"], utc=True)
        window_mask = (m_df["timestamp"] >= cutoff) & (m_df["timestamp"] <= failure_time)
        m_window = m_df[window_mask]

        if m_window.empty:
            return []

        # Detect change-points per parameter
        param_changepoints: Dict[str, List[ChangePoint]] = {}
        param_trends: Dict[str, Dict] = {}

        for param_code in m_window["parameter_code"].unique():
            param_data = m_window[m_window["parameter_code"] == param_code].sort_values("timestamp")
            if len(param_data) < 10:
                continue

            cps = detect_change_points(
                series=param_data["value"],
                timestamps=param_data["timestamp"],
                param_code=str(param_code),
                model=self.cp_model,
                penalty=self.cp_penalty,
            )
            # Only keep change-points with meaningful magnitude
            significant_cps = [
                cp for cp in cps
                if abs(cp.relative_change) >= self.min_threshold
            ]
            if significant_cps:
                param_changepoints[str(param_code)] = significant_cps

            trend = detect_parameter_trends(
                series=param_data["value"],
                timestamps=param_data["timestamp"],
            )
            param_trends[str(param_code)] = trend

        # Map parameters to mechanism types
        param_to_mechanism: Dict[str, List[str]] = {}
        for mtype, template in MECHANISM_TEMPLATES.items():
            for expected_param in template["expected_parameters"]:
                if expected_param not in param_to_mechanism:
                    param_to_mechanism[expected_param] = []
                param_to_mechanism[expected_param].append(mtype)

        # Build mechanism hypotheses
        mechanism_evidence: Dict[str, List[EvidenceItem]] = {mtype: [] for mtype in MECHANISM_TEMPLATES}

        for param_code, cps in param_changepoints.items():
            mechansim_types = param_to_mechanism.get(param_code, ["mechanical"])
            for cp in cps:
                lag = (failure_time - cp.timestamp).total_seconds() / 3600.0
                ev = EvidenceItem(
                    evidence_type="changepoint",
                    polarity="supporting",
                    description=(
                        f"Parameter '{param_code}' shows change-point at "
                        f"{cp.timestamp.isoformat()}: "
                        f"{cp.pre_mean:.3f} → {cp.post_mean:.3f} "
                        f"({cp.direction}, {cp.relative_change*100:.1f}% change)"
                    ),
                    strength=min(1.0, abs(cp.relative_change) / 0.5 * cp.confidence),
                    source_table="parameter_measurements",
                    source_timestamp=cp.timestamp.isoformat(),
                    measured_value=cp.post_mean,
                    expected_value=cp.pre_mean,
                    deviation=cp.magnitude,
                    statistical_significance=cp.confidence,
                    lag_hours=round(lag, 2),
                    metadata={"direction": cp.direction, "parameter": param_code},
                )
                for mtype in mechansim_types:
                    mechanism_evidence[mtype].append(ev)

        # Add trend evidence
        for param_code, trend in param_trends.items():
            if trend.get("trend") in ("increasing", "decreasing"):
                mech_types = param_to_mechanism.get(param_code, ["mechanical"])
                lag_h = self.lookback_hours / 2  # approximate mid-window
                slope = trend.get("slope_per_hour", 0.0)
                strength = min(1.0, abs(slope) * self.lookback_hours / 10.0)
                ev = EvidenceItem(
                    evidence_type="parameter_change",
                    polarity="supporting",
                    description=(
                        f"Parameter '{param_code}' shows {trend['trend']} trend "
                        f"(slope={slope:.4f}/h, p={trend.get('p_value',1.0):.4f})"
                    ),
                    strength=strength,
                    lag_hours=lag_h,
                    metadata={"trend": trend["trend"], "parameter": param_code},
                )
                for mtype in mech_types:
                    mechanism_evidence[mtype].append(ev)

        # Construct hypothesis objects for mechanism types with evidence
        hypotheses: List[CandidateMechanismHypothesis] = []
        import uuid

        for mtype, evidence_list in mechanism_evidence.items():
            if not evidence_list:
                continue
            template = MECHANISM_TEMPLATES[mtype]
            affected_params = [
                ev.metadata.get("parameter", "")
                for ev in evidence_list
                if ev.metadata.get("parameter")
            ]

            hypothesis = CandidateMechanismHypothesis(
                hypothesis_id=str(uuid.uuid4()),
                mechanism_type=mtype,
                name=template["name"],
                description=template["description"],
                discovery_method="temporal_association",
                cause=template["cause_template"],
                observable_failure=template["observable_failure"],
                variables_involved=list(set(affected_params)),
                supporting_evidence=evidence_list,
                missing_evidence=self._identify_missing_evidence(mtype, affected_params),
                temporal_conditions={
                    "lookback_hours": self.lookback_hours,
                    "failure_time": failure_time.isoformat(),
                    "n_changepoints_detected": sum(
                        len(v) for k, v in param_changepoints.items()
                        if k in template["expected_parameters"]
                    ),
                },
            )
            hypotheses.append(hypothesis)

        return hypotheses

    def _identify_missing_evidence(
        self, mtype: str, found_params: List[str]
    ) -> List[str]:
        """Identify expected parameters that were NOT found with anomalies."""
        template = MECHANISM_TEMPLATES[mtype]
        expected = set(template["expected_parameters"])
        found = set(found_params)
        missing = expected - found
        return [f"Expected parameter anomaly in '{p}' not detected" for p in missing]


# ============================================================
# Discovery 2: Graph Traversal Discovery
# ============================================================

class GraphTraversalDiscovery:
    """
    Discovers mechanism hypotheses by traversing the industrial graph.

    Logic:
    1. Find all failure nodes in the graph
    2. For each failure node, find all PRECEDES paths
    3. Path patterns (maintenance → failure, process_change → failure, etc.)
       are mapped to mechanism types
    4. Evidence strength is proportional to lag_hours proximity
    """

    def discover(
        self,
        graph: IndustrialGraph,
        failure_id: str,
        failure_time: datetime,
    ) -> List[CandidateMechanismHypothesis]:
        import uuid

        failure_node = f"failure:{failure_id}"
        if not graph.G.has_node(failure_node):
            return []

        hypotheses = []

        # Get all predecessors with PRECEDES edges
        predecessors = graph.get_predecessors_within_lag(failure_node, max_lag_hours=96.0)

        # Group predecessors by type
        maint_preds = [(n, d, lag) for n, d, lag in predecessors if d.get("node_type") == "maintenance"]
        pc_preds = [(n, d, lag) for n, d, lag in predecessors if d.get("node_type") == "process_change"]

        # Maintenance preceding failure → thermal / wear hypotheses
        if maint_preds:
            evidence = []
            for node_id, attrs, lag in maint_preds:
                evidence.append(EvidenceItem(
                    evidence_type="maintenance_record",
                    polarity="supporting",
                    description=(
                        f"Maintenance event (type={attrs.get('maintenance_type','')}) "
                        f"occurred {lag:.1f}h before failure: {attrs.get('description','')}"
                    ),
                    strength=min(1.0, 2.0 / max(0.1, lag)),  # closer lag = stronger
                    source_table="maintenance_events",
                    source_id=node_id.replace("maintenance:", ""),
                    source_timestamp=attrs.get("timestamp"),
                    lag_hours=lag,
                ))

            hyp = CandidateMechanismHypothesis(
                hypothesis_id=str(uuid.uuid4()),
                mechanism_type="thermal",
                name="Post-Maintenance Thermal/Process Anomaly",
                description=(
                    "Graph traversal identified maintenance event(s) preceding the failure, "
                    "suggesting maintenance-induced parameter disruption as a candidate mechanism."
                ),
                discovery_method="graph_traversal",
                cause="Maintenance activity may have disrupted process equilibrium",
                process_condition="Post-maintenance parameter recovery failure",
                observable_failure="Quality or process failure following maintenance",
                supporting_evidence=evidence,
                temporal_conditions={"n_maintenance_events": len(maint_preds)},
            )
            hypotheses.append(hyp)

        # Process change preceding failure → process_drift hypothesis
        if pc_preds:
            evidence = []
            for node_id, attrs, lag in pc_preds:
                evidence.append(EvidenceItem(
                    evidence_type="event_sequence",
                    polarity="supporting",
                    description=(
                        f"Process change (type={attrs.get('change_type','')}, "
                        f"param={attrs.get('parameter_name','')}) occurred "
                        f"{lag:.1f}h before failure"
                    ),
                    strength=min(1.0, 1.5 / max(0.1, lag / 24.0)),
                    source_table="process_changes",
                    source_id=node_id.replace("process_change:", ""),
                    source_timestamp=attrs.get("timestamp"),
                    lag_hours=lag,
                ))

            hyp = CandidateMechanismHypothesis(
                hypothesis_id=str(uuid.uuid4()),
                mechanism_type="process_drift",
                name="Process Change-Induced Drift",
                description=(
                    "Graph traversal found process change(s) preceding the failure, "
                    "suggesting a parameter drift or instability induced by the change."
                ),
                discovery_method="graph_traversal",
                cause="Process recipe or parameter change",
                process_condition="Parameter instability after change",
                observable_failure="Quality failure following process change",
                supporting_evidence=evidence,
                temporal_conditions={"n_process_changes": len(pc_preds)},
            )
            hypotheses.append(hyp)

        return hypotheses


# ============================================================
# Discovery 3: Material Lot Discovery
# ============================================================

class MaterialLotDiscovery:
    """
    Identifies shared material lots across multiple failing batches.

    Logic:
    1. Find all failing batches in the investigation context
    2. For each failing batch, get its material lots
    3. If a lot appears in multiple failing batches → contamination hypothesis
    4. Compute Jaccard similarity between lot sets of failing vs passing batches
    """

    def discover(
        self,
        failing_batch_ids: List[str],
        all_batch_ids: List[str],
        batch_lots_df: pd.DataFrame,
        material_lots_df: pd.DataFrame,
    ) -> List[CandidateMechanismHypothesis]:
        import uuid

        if batch_lots_df.empty or not failing_batch_ids:
            return []

        # Get lots used in failing batches
        failing_lots = batch_lots_df[
            batch_lots_df["batch_id"].isin(failing_batch_ids)
        ]["material_lot_id"].value_counts()

        # Get lots used in passing batches
        passing_batch_ids = [bid for bid in all_batch_ids if bid not in failing_batch_ids]
        passing_lots = batch_lots_df[
            batch_lots_df["batch_id"].isin(passing_batch_ids)
        ]["material_lot_id"].value_counts()

        hypotheses = []

        # Lots that appear in failing batches but rarely in passing batches
        for lot_id, fail_count in failing_lots.items():
            pass_count = passing_lots.get(lot_id, 0)
            n_failing = len(failing_batch_ids)
            n_passing = max(1, len(passing_batch_ids))

            # Fisher-exact-like enrichment check
            fail_rate = fail_count / n_failing
            pass_rate = pass_count / n_passing

            if fail_rate > 0.3 and fail_rate > pass_rate * 2:
                # Get lot details
                lot_info = material_lots_df[
                    material_lots_df["id"] == lot_id
                ]
                lot_number = lot_info["lot_number"].iloc[0] if not lot_info.empty else str(lot_id)

                strength = min(1.0, fail_rate / max(0.01, pass_rate) / 10.0)
                ev = EvidenceItem(
                    evidence_type="material_batch",
                    polarity="supporting",
                    description=(
                        f"Material lot '{lot_number}' present in "
                        f"{fail_count}/{n_failing} failing batches "
                        f"vs {pass_count}/{n_passing} passing batches "
                        f"(enrichment ratio: {fail_rate/max(0.001, pass_rate):.1f}x)"
                    ),
                    strength=strength,
                    source_table="material_lots",
                    source_id=str(lot_id),
                    metadata={
                        "lot_id": str(lot_id),
                        "lot_number": lot_number,
                        "fail_count": fail_count,
                        "pass_count": pass_count,
                        "enrichment": fail_rate / max(0.001, pass_rate),
                    },
                )

                # Contradicting evidence: some failing batches don't use this lot
                contra_evidence = []
                if fail_count < n_failing:
                    contra_evidence.append(EvidenceItem(
                        evidence_type="material_batch",
                        polarity="contradicting",
                        description=(
                            f"{n_failing - fail_count} failing batches do NOT use lot '{lot_number}', "
                            "which partially contradicts lot contamination as the sole cause"
                        ),
                        strength=0.4 * (n_failing - fail_count) / n_failing,
                    ))

                hyp = CandidateMechanismHypothesis(
                    hypothesis_id=str(uuid.uuid4()),
                    mechanism_type="contamination",
                    name=f"Material Lot Contamination (Lot: {lot_number})",
                    description=(
                        f"Material lot '{lot_number}' is disproportionately present "
                        "in failing batches, suggesting lot-level contamination as a "
                        "candidate failure mechanism."
                    ),
                    discovery_method="material_lot_analysis",
                    cause=f"Contaminated or out-of-spec material lot {lot_number}",
                    observable_failure="Quality failures correlated with lot usage",
                    supporting_evidence=[ev],
                    contradicting_evidence=contra_evidence,
                    missing_evidence=[
                        "Contamination test result for this lot not available",
                        "Chemical analysis of affected parts not available",
                    ],
                )
                hypotheses.append(hyp)

        return hypotheses


# ============================================================
# Orchestrator
# ============================================================

class MechanismDiscoveryOrchestrator:
    """
    Runs all discovery methods and aggregates results.
    Deduplicates overlapping hypotheses by mechanism type.
    """

    def __init__(
        self,
        lookback_hours: float = 72.0,
        min_association_threshold: float = 0.15,
        max_candidates: int = 20,
    ):
        self.lookback_hours = lookback_hours
        self.min_threshold = min_association_threshold
        self.max_candidates = max_candidates

        self.temporal_discoverer = TemporalAssociationDiscovery(
            lookback_hours=lookback_hours,
            min_association_threshold=min_association_threshold,
        )
        self.graph_discoverer = GraphTraversalDiscovery()
        self.lot_discoverer = MaterialLotDiscovery()

    def discover_all(
        self,
        failure_event: Dict[str, Any],
        measurements_df: pd.DataFrame,
        param_defs_df: pd.DataFrame,
        maintenance_df: pd.DataFrame,
        process_changes_df: pd.DataFrame,
        batch_lots_df: pd.DataFrame,
        material_lots_df: pd.DataFrame,
        batches_df: pd.DataFrame,
        graph: Optional[IndustrialGraph] = None,
    ) -> List[CandidateMechanismHypothesis]:
        """Run all discoverers and return merged, deduplicated hypotheses."""

        failure_id = str(failure_event["id"])
        failure_time_raw = failure_event.get("event_time") or failure_event.get("timestamp")
        if isinstance(failure_time_raw, str):
            failure_time = pd.to_datetime(failure_time_raw, utc=True).to_pydatetime()
        else:
            failure_time = failure_time_raw
        if failure_time.tzinfo is None:
            failure_time = failure_time.replace(tzinfo=timezone.utc)

        all_hypotheses: List[CandidateMechanismHypothesis] = []

        # 1. Temporal association
        logger.info("Running temporal association discovery...")
        try:
            ta_hyps = self.temporal_discoverer.discover(
                failure_time=failure_time,
                measurements_df=measurements_df,
                param_defs_df=param_defs_df,
                failure_id=failure_id,
            )
            all_hypotheses.extend(ta_hyps)
            logger.info(f"Temporal association: {len(ta_hyps)} hypotheses")
        except Exception as e:
            logger.warning(f"Temporal association discovery failed: {e}")

        # 2. Graph traversal
        if graph is not None:
            logger.info("Running graph traversal discovery...")
            try:
                gt_hyps = self.graph_discoverer.discover(
                    graph=graph,
                    failure_id=failure_id,
                    failure_time=failure_time,
                )
                all_hypotheses.extend(gt_hyps)
                logger.info(f"Graph traversal: {len(gt_hyps)} hypotheses")
            except Exception as e:
                logger.warning(f"Graph traversal discovery failed: {e}")

        # 3. Material lot analysis
        logger.info("Running material lot discovery...")
        try:
            failing_batch_ids = []
            if "batch_id" in failure_event and failure_event["batch_id"]:
                failing_batch_ids.append(str(failure_event["batch_id"]))
            # Also find nearby defective batches
            if not batches_df.empty and "is_defective" in batches_df.columns:
                near_defective = batches_df[batches_df["is_defective"] == True]["id"].tolist()
                failing_batch_ids.extend([str(bid) for bid in near_defective])
            failing_batch_ids = list(set(failing_batch_ids))
            all_batch_ids = batches_df["id"].astype(str).tolist() if not batches_df.empty else []

            lot_hyps = self.lot_discoverer.discover(
                failing_batch_ids=failing_batch_ids,
                all_batch_ids=all_batch_ids,
                batch_lots_df=batch_lots_df,
                material_lots_df=material_lots_df,
            )
            all_hypotheses.extend(lot_hyps)
            logger.info(f"Material lot: {len(lot_hyps)} hypotheses")
        except Exception as e:
            logger.warning(f"Material lot discovery failed: {e}")

        # Merge hypotheses of same mechanism_type (keep richest evidence)
        merged = self._merge_by_type(all_hypotheses)

        # Limit to max candidates
        return merged[: self.max_candidates]

    def _merge_by_type(
        self, hypotheses: List[CandidateMechanismHypothesis]
    ) -> List[CandidateMechanismHypothesis]:
        """Merge hypotheses of the same mechanism_type, combining evidence."""
        type_groups: Dict[str, List[CandidateMechanismHypothesis]] = {}
        for hyp in hypotheses:
            key = f"{hyp.mechanism_type}:{hyp.discovery_method}"
            if key not in type_groups:
                type_groups[key] = []
            type_groups[key].append(hyp)

        merged = []
        for key, group in type_groups.items():
            if len(group) == 1:
                merged.append(group[0])
            else:
                # Use the one with most supporting evidence as base
                base = max(group, key=lambda h: len(h.supporting_evidence))
                for other in group:
                    if other is base:
                        continue
                    base.supporting_evidence.extend(other.supporting_evidence)
                    base.contradicting_evidence.extend(other.contradicting_evidence)
                    base.missing_evidence.extend(
                        e for e in other.missing_evidence
                        if e not in base.missing_evidence
                    )
                    base.variables_involved = list(
                        set(base.variables_involved + other.variables_involved)
                    )
                merged.append(base)

        return merged
