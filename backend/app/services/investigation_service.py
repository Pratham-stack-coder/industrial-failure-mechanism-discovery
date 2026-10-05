"""
Investigation Pipeline Service
================================
Orchestrates the full investigation pipeline:
  1. Load data for the investigation window
  2. Build temporal features and change-points
  3. Build the industrial graph
  4. Run mechanism discovery
  5. Rank mechanisms
  6. Persist results to database
  7. Optionally generate LLM explanation
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    Batch,
    BatchMaterialLot,
    CandidateMechanism,
    Dataset,
    EnvironmentalCondition,
    EvidencePolarity,
    EvidenceType,
    FailureEvent,
    Investigation,
    InvestigationStatus,
    Machine,
    MaintenanceEvent,
    MaterialLot,
    MechanismEvidence,
    MechanismType,
    ParameterDefinition,
    ParameterMeasurement,
    ProcessChange,
    QualityInspection,
)
from app.mechanisms.discovery import MechanismDiscoveryOrchestrator, CandidateMechanismHypothesis
from app.ranking.ranker import rank_mechanisms
from app.graph.graph_builder import IndustrialGraph
from app.temporal.temporal_analysis import extract_event_sequence


class InvestigationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_pipeline(self, investigation_id: str) -> None:
        """Full investigation pipeline — called from background task."""
        inv_uid = uuid.UUID(investigation_id)
        investigation = await self.db.get(Investigation, inv_uid)

        if not investigation:
            logger.error(f"Investigation {investigation_id} not found")
            return

        try:
            logger.info(f"Starting pipeline for investigation {investigation_id}")

            # ── 1. Load context data ──────────────────────────────────────
            data = await self._load_investigation_data(investigation)
            logger.info(
                f"Loaded data: "
                f"{len(data['measurements'])} measurements, "
                f"{len(data['maintenance'])} maintenance events, "
                f"{len(data['failure_events'])} failure events"
            )

            # ── 2. Determine failure event ────────────────────────────────
            failure_event = None
            if investigation.failure_event_id:
                fe = await self.db.get(FailureEvent, investigation.failure_event_id)
                if fe:
                    failure_event = {
                        "id": str(fe.id),
                        "event_time": fe.event_time.isoformat(),
                        "batch_id": str(fe.batch_id) if fe.batch_id else None,
                        "machine_id": str(fe.machine_id) if fe.machine_id else None,
                        "event_type": fe.event_type,
                        "severity": fe.severity.value,
                    }
            if not failure_event and not data["failure_events"].empty:
                # Use the most severe failure in the window
                fe_df = data["failure_events"].sort_values("event_time", ascending=False)
                row = fe_df.iloc[0]
                failure_event = row.to_dict()

            if not failure_event:
                raise ValueError("No failure event found in investigation window")

            # ── 3. Build graph ────────────────────────────────────────────
            graph = IndustrialGraph()
            failure_time = pd.to_datetime(failure_event["event_time"], utc=True).to_pydatetime()

            graph.build_from_dataframes(
                machines_df=data["machines"],
                batches_df=data["batches"],
                material_lots_df=data["material_lots"],
                batch_lots_df=data["batch_lots"],
                param_defs_df=data["param_defs"],
                maintenance_df=data["maintenance"],
                process_changes_df=data["process_changes"],
                quality_df=data["quality"],
                failure_events_df=data["failure_events"],
                failure_time=failure_time,
                lookback_hours=settings.temporal_lookback_hours,
            )
            logger.info(f"Graph built: {graph.compute_graph_metrics()}")

            # ── 4. Discover mechanisms ────────────────────────────────────
            orchestrator = MechanismDiscoveryOrchestrator(
                lookback_hours=settings.temporal_lookback_hours,
                min_association_threshold=settings.min_association_threshold,
                max_candidates=settings.max_candidate_mechanisms,
            )

            hypotheses = orchestrator.discover_all(
                failure_event=failure_event,
                measurements_df=data["measurements"],
                param_defs_df=data["param_defs"],
                maintenance_df=data["maintenance"],
                process_changes_df=data["process_changes"],
                batch_lots_df=data["batch_lots"],
                material_lots_df=data["material_lots"],
                batches_df=data["batches"],
                graph=graph,
            )
            logger.info(f"Discovered {len(hypotheses)} candidate mechanisms")

            # ── 5. Rank mechanisms ────────────────────────────────────────
            ranked = rank_mechanisms(hypotheses)
            logger.info(f"Ranked {len(ranked)} mechanisms")

            # ── 6. Persist results ────────────────────────────────────────
            graph_json = graph.to_json()
            await self._persist_mechanisms(investigation, ranked)

            # ── 7. Save graph to investigation config ─────────────────────
            investigation.config_snapshot = {
                **(investigation.config_snapshot or {}),
                "graph_metrics": graph.compute_graph_metrics(),
                "n_mechanisms_discovered": len(ranked),
                "failure_event_id": failure_event.get("id"),
            }

            # ── 8. Optional LLM summary ───────────────────────────────────
            if settings.llm_provider != "none" and ranked:
                try:
                    from app.explainability.llm_explainer import LLMExplainer
                    explainer = LLMExplainer()
                    summary = await explainer.generate_investigation_summary(
                        investigation=investigation,
                        top_mechanisms=ranked[:3],
                        failure_event=failure_event,
                    )
                    investigation.llm_summary = summary
                except Exception as e:
                    logger.warning(f"LLM explanation failed (non-critical): {e}")

            investigation.status = InvestigationStatus.COMPLETED
            investigation.completed_at = datetime.now(timezone.utc)
            await self.db.flush()
            logger.info(f"Investigation {investigation_id} completed successfully")

        except Exception as e:
            logger.exception(f"Investigation pipeline failed: {e}")
            investigation.status = InvestigationStatus.FAILED
            investigation.error_message = str(e)
            investigation.completed_at = datetime.now(timezone.utc)
            await self.db.flush()

    async def _load_investigation_data(
        self, investigation: Investigation
    ) -> Dict[str, pd.DataFrame]:
        """Load all relevant data for the investigation time window."""
        dataset_id = investigation.dataset_id
        start = investigation.analysis_start_time
        end = investigation.analysis_end_time

        # Make timezone-aware if needed
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        machine_filter = investigation.machine_id

        async def df_from_query(stmt) -> pd.DataFrame:
            result = await self.db.execute(stmt)
            rows = result.fetchall()
            if not rows:
                return pd.DataFrame()
            return pd.DataFrame([dict(row._mapping) for row in rows])

        # Machines
        machines_stmt = select(Machine)
        if machine_filter:
            machines_stmt = machines_stmt.where(Machine.id == machine_filter)
        machines_df = await df_from_query(machines_stmt)

        # Failure events in window
        fe_stmt = (
            select(FailureEvent)
            .where(FailureEvent.dataset_id == dataset_id)
            .where(FailureEvent.event_time >= start)
            .where(FailureEvent.event_time <= end)
        )
        failure_events_df = await df_from_query(fe_stmt)

        # Batches
        batch_stmt = (
            select(Batch)
            .where(Batch.dataset_id == dataset_id)
            .where(Batch.start_time >= start)
            .where(Batch.start_time <= end)
        )
        if machine_filter:
            batch_stmt = batch_stmt.where(Batch.machine_id == machine_filter)
        batches_df = await df_from_query(batch_stmt)

        # Batch material lots
        batch_lot_df = pd.DataFrame()
        if not batches_df.empty:
            batch_ids = batches_df["id"].tolist()
            bl_stmt = select(BatchMaterialLot).where(
                BatchMaterialLot.batch_id.in_(batch_ids)
            )
            batch_lot_df = await df_from_query(bl_stmt)

        # Material lots
        lots_df = pd.DataFrame()
        if not batch_lot_df.empty:
            lot_ids = batch_lot_df["material_lot_id"].tolist()
            lot_stmt = select(MaterialLot).where(MaterialLot.id.in_(lot_ids))
            lots_df = await df_from_query(lot_stmt)

        # Parameter definitions
        param_stmt = select(ParameterDefinition)
        param_defs_df = await df_from_query(param_stmt)

        # Parameter measurements in window
        meas_stmt = (
            select(
                ParameterMeasurement.id,
                ParameterMeasurement.timestamp,
                ParameterMeasurement.value,
                ParameterMeasurement.is_out_of_spec,
                ParameterMeasurement.is_anomalous,
                ParameterMeasurement.quality_flag,
                ParameterMeasurement.machine_id,
                ParameterMeasurement.batch_id,
                ParameterDefinition.parameter_code,
            )
            .join(ParameterDefinition)
            .where(ParameterMeasurement.dataset_id == dataset_id)
            .where(ParameterMeasurement.timestamp >= start)
            .where(ParameterMeasurement.timestamp <= end)
        )
        if machine_filter:
            meas_stmt = meas_stmt.where(ParameterMeasurement.machine_id == machine_filter)
        measurements_df = await df_from_query(meas_stmt)

        # Maintenance events
        maint_stmt = (
            select(MaintenanceEvent)
            .where(MaintenanceEvent.dataset_id == dataset_id)
            .where(MaintenanceEvent.start_time >= start)
            .where(MaintenanceEvent.start_time <= end)
        )
        if machine_filter:
            maint_stmt = maint_stmt.where(MaintenanceEvent.machine_id == machine_filter)
        maintenance_df = await df_from_query(maint_stmt)

        # Process changes
        pc_stmt = (
            select(ProcessChange)
            .where(ProcessChange.dataset_id == dataset_id)
            .where(ProcessChange.change_time >= start)
            .where(ProcessChange.change_time <= end)
        )
        process_changes_df = await df_from_query(pc_stmt)

        # Quality inspections
        qi_stmt = (
            select(QualityInspection)
            .where(QualityInspection.dataset_id == dataset_id)
            .where(QualityInspection.inspection_time >= start)
            .where(QualityInspection.inspection_time <= end)
        )
        quality_df = await df_from_query(qi_stmt)

        return {
            "machines": machines_df,
            "batches": batches_df,
            "batch_lots": batch_lot_df,
            "material_lots": lots_df,
            "param_defs": param_defs_df,
            "measurements": measurements_df,
            "maintenance": maintenance_df,
            "process_changes": process_changes_df,
            "quality": quality_df,
            "failure_events": failure_events_df,
        }

    async def _persist_mechanisms(
        self,
        investigation: Investigation,
        ranked: List[CandidateMechanismHypothesis],
    ) -> None:
        """Persist ranked mechanisms and their evidence to the database."""
        # Delete existing mechanisms for this investigation
        existing = await self.db.execute(
            select(CandidateMechanism).where(
                CandidateMechanism.investigation_id == investigation.id
            )
        )
        for mech in existing.scalars().all():
            await self.db.delete(mech)
        await self.db.flush()

        for hyp in ranked:
            # Map mechanism type string to enum
            try:
                mtype = MechanismType(hyp.mechanism_type)
            except ValueError:
                mtype = MechanismType.UNKNOWN

            mech = CandidateMechanism(
                investigation_id=investigation.id,
                mechanism_type=mtype,
                name=hyp.name,
                description=hyp.description,
                discovery_method=hyp.discovery_method,
                cause=hyp.cause,
                process_condition=hyp.process_condition,
                intermediate_effect=hyp.intermediate_effect,
                observable_failure=hyp.observable_failure,
                entities_involved=hyp.entities_involved,
                variables_involved=hyp.variables_involved,
                temporal_conditions=hyp.temporal_conditions,
                expected_effects=hyp.expected_effects,
                rank=hyp.rank,
                overall_score=hyp.overall_score,
                confidence=hyp.confidence,
                temporal_consistency_score=hyp.temporal_consistency_score,
                evidence_strength_score=hyp.evidence_strength_score,
                evidence_coverage_score=hyp.evidence_coverage_score,
                recurrence_score=hyp.recurrence_score,
                plausibility_score=hyp.plausibility_score,
                contradiction_penalty=hyp.contradiction_penalty,
                supporting_evidence_count=len(hyp.supporting_evidence),
                contradicting_evidence_count=len(hyp.contradicting_evidence),
                missing_evidence_count=len(hyp.missing_evidence),
            )
            self.db.add(mech)
            await self.db.flush()
            await self.db.refresh(mech)

            # Persist evidence items
            all_evidence = [
                (ev, EvidencePolarity.SUPPORTING) for ev in hyp.supporting_evidence
            ] + [
                (ev, EvidencePolarity.CONTRADICTING) for ev in hyp.contradicting_evidence
            ]

            for ev_item, polarity in all_evidence:
                try:
                    ev_type = EvidenceType(ev_item.evidence_type)
                except ValueError:
                    ev_type = EvidenceType.STATISTICAL_ANOMALY

                evidence = MechanismEvidence(
                    mechanism_id=mech.id,
                    evidence_type=ev_type,
                    polarity=polarity,
                    description=ev_item.description,
                    strength=ev_item.strength,
                    source_table=ev_item.source_table,
                    source_id=(
                        uuid.UUID(ev_item.source_id)
                        if ev_item.source_id and len(ev_item.source_id) == 36
                        else None
                    ),
                    source_timestamp=(
                        pd.to_datetime(ev_item.source_timestamp, utc=True).to_pydatetime()
                        if ev_item.source_timestamp
                        else None
                    ),
                    measured_value=ev_item.measured_value,
                    expected_value=ev_item.expected_value,
                    deviation=ev_item.deviation,
                    statistical_significance=ev_item.statistical_significance,
                    lag_hours=ev_item.lag_hours,
                    metadata_=ev_item.metadata,
                )
                self.db.add(evidence)

        await self.db.flush()
        logger.info(f"Persisted {len(ranked)} mechanisms with evidence")

    async def get_timeline(self, investigation: Investigation) -> List[Dict]:
        """Get chronological event timeline for the investigation."""
        start = investigation.analysis_start_time
        end = investigation.analysis_end_time
        dataset_id = investigation.dataset_id

        events = []

        # Maintenance events
        maint_result = await self.db.execute(
            select(MaintenanceEvent)
            .where(MaintenanceEvent.dataset_id == dataset_id)
            .where(MaintenanceEvent.start_time >= start)
            .where(MaintenanceEvent.start_time <= end)
            .order_by(MaintenanceEvent.start_time)
        )
        for me in maint_result.scalars().all():
            events.append({
                "type": "maintenance",
                "timestamp": me.start_time.isoformat(),
                "label": f"Maintenance: {me.maintenance_type.value}",
                "description": me.description,
                "entity_id": str(me.machine_id),
                "severity": "medium",
            })

        # Process changes
        pc_result = await self.db.execute(
            select(ProcessChange)
            .where(ProcessChange.dataset_id == dataset_id)
            .where(ProcessChange.change_time >= start)
            .where(ProcessChange.change_time <= end)
            .order_by(ProcessChange.change_time)
        )
        for pc in pc_result.scalars().all():
            events.append({
                "type": "process_change",
                "timestamp": pc.change_time.isoformat(),
                "label": f"Process Change: {pc.change_type}",
                "description": f"{pc.parameter_name}: {pc.old_value} → {pc.new_value}",
                "entity_id": str(pc.process_id),
                "severity": "low",
            })

        # Quality failures
        qi_result = await self.db.execute(
            select(QualityInspection)
            .where(QualityInspection.dataset_id == dataset_id)
            .where(QualityInspection.inspection_time >= start)
            .where(QualityInspection.inspection_time <= end)
            .where(QualityInspection.result == "fail")
            .order_by(QualityInspection.inspection_time)
        )
        for qi in qi_result.scalars().all():
            events.append({
                "type": "quality_failure",
                "timestamp": qi.inspection_time.isoformat(),
                "label": f"Quality FAIL (DR={qi.defect_rate:.2%})",
                "description": qi.notes or "",
                "entity_id": str(qi.batch_id),
                "severity": "high",
            })

        # Failure events
        fe_result = await self.db.execute(
            select(FailureEvent)
            .where(FailureEvent.dataset_id == dataset_id)
            .where(FailureEvent.event_time >= start)
            .where(FailureEvent.event_time <= end)
            .order_by(FailureEvent.event_time)
        )
        for fe in fe_result.scalars().all():
            events.append({
                "type": "failure_event",
                "timestamp": fe.event_time.isoformat(),
                "label": f"FAILURE: {fe.event_type}",
                "description": fe.description,
                "entity_id": str(fe.machine_id) if fe.machine_id else str(fe.batch_id),
                "severity": fe.severity.value,
            })

        events.sort(key=lambda e: e["timestamp"])
        return events

    async def get_graph(self, investigation: Investigation) -> Dict:
        """Build and return the graph for the investigation window."""
        data = await self._load_investigation_data(investigation)

        failure_time = investigation.analysis_end_time
        if failure_time.tzinfo is None:
            failure_time = failure_time.replace(tzinfo=timezone.utc)

        graph = IndustrialGraph()
        graph.build_from_dataframes(
            machines_df=data["machines"],
            batches_df=data["batches"],
            material_lots_df=data["material_lots"],
            batch_lots_df=data["batch_lots"],
            param_defs_df=data["param_defs"],
            maintenance_df=data["maintenance"],
            process_changes_df=data["process_changes"],
            quality_df=data["quality"],
            failure_events_df=data["failure_events"],
            failure_time=failure_time,
            lookback_hours=settings.temporal_lookback_hours,
        )

        return graph.to_json()
