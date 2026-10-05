"""
Synthetic Industrial Dataset Generator
=======================================
Generates realistic industrial datasets with HIDDEN ground-truth failure mechanisms.

Design principles:
  1. Mechanisms are injected as latent causes — not directly exposed to the AI pipeline.
  2. Temporal dependencies are realistic: maintenance → parameter drift → failure.
  3. Noise, missing values, and conflicting evidence are deliberately introduced.
  4. Ground-truth labels are stored ONLY in FailureEvent.root_cause_label and
     FailureEvent.is_synthetic_ground_truth — accessible only during evaluation.

Hidden mechanisms implemented:
  A. CoolingDegradation — coolant flow reduction after maintenance causes thermal drift
  B. MaterialContamination — contaminated lot causes quality degradation
  C. WearAcceleration — cumulative wear after high-load operation
  D. ProcessDrift — gradual parameter drift after recipe change
  E. ThermalExpansion — ambient temperature excursion causes dimensional failure
"""

import json
import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


# ============================================================
# Mechanism definitions (hidden ground-truth)
# ============================================================

@dataclass
class GroundTruthMechanism:
    """Represents a hidden failure mechanism with its observable signature."""
    mechanism_id: str
    name: str
    description: str
    mechanism_type: str
    # Sequence of observable effects relative to failure_time (hours before)
    temporal_signature: List[Dict[str, Any]]
    # Which parameters show anomalies
    affected_parameters: List[str]
    # Expected evidence items (used for evaluation scoring)
    expected_evidence: List[str]


GROUND_TRUTH_MECHANISMS: List[GroundTruthMechanism] = [
    GroundTruthMechanism(
        mechanism_id="GTM-001",
        name="Cooling System Degradation",
        description=(
            "Coolant flow reduction after maintenance causes progressive thermal drift "
            "in the machining zone, leading to dimensional failures and surface defects."
        ),
        mechanism_type="thermal",
        temporal_signature=[
            {"event": "maintenance", "lag_hours": -24, "description": "Corrective maintenance on cooling circuit"},
            {"event": "coolant_flow_drop", "lag_hours": -18, "description": "Coolant flow falls 15-30%"},
            {"event": "temperature_rise", "lag_hours": -12, "description": "Machining temperature rises 8-15°C"},
            {"event": "dimensional_drift", "lag_hours": -6, "description": "Part dimensions start drifting"},
            {"event": "quality_failure", "lag_hours": 0, "description": "Batch fails quality inspection"},
        ],
        affected_parameters=["coolant_flow_rate", "machining_temperature", "tool_temperature"],
        expected_evidence=[
            "coolant_flow_rate declined before failure",
            "maintenance event preceded failure",
            "temperature drift observed",
            "dimensional measurement out of spec",
        ],
    ),
    GroundTruthMechanism(
        mechanism_id="GTM-002",
        name="Raw Material Contamination",
        description=(
            "A contaminated material lot introduces impurities that cause surface "
            "defects and chemical property deviations in finished products."
        ),
        mechanism_type="contamination",
        temporal_signature=[
            {"event": "new_lot_introduced", "lag_hours": -48, "description": "New material lot received"},
            {"event": "first_usage", "lag_hours": -36, "description": "Contaminated lot first used in production"},
            {"event": "surface_defects", "lag_hours": -12, "description": "Surface defects appear on parts"},
            {"event": "quality_failure", "lag_hours": 0, "description": "Batch fails inspection"},
        ],
        affected_parameters=["surface_roughness", "chemical_composition_index"],
        expected_evidence=[
            "same material lot in all affected batches",
            "defect rate increase correlated with lot introduction",
            "surface defect type matches contamination signature",
        ],
    ),
    GroundTruthMechanism(
        mechanism_id="GTM-003",
        name="Accelerated Tool Wear",
        description=(
            "High spindle load operation exceeding rated limits accelerates tool wear, "
            "causing progressive degradation of surface finish and dimensional accuracy."
        ),
        mechanism_type="wear",
        temporal_signature=[
            {"event": "high_load_operation", "lag_hours": -72, "description": "Spindle load consistently >90% rated"},
            {"event": "vibration_increase", "lag_hours": -48, "description": "Vibration signature increases"},
            {"event": "surface_roughness_drift", "lag_hours": -24, "description": "Ra value drifts upward"},
            {"event": "dimensional_failure", "lag_hours": 0, "description": "Part dimensions out of tolerance"},
        ],
        affected_parameters=["spindle_load", "vibration_amplitude", "surface_roughness", "tool_wear_index"],
        expected_evidence=[
            "spindle load exceeded limit before failure",
            "vibration amplitude increased gradually",
            "surface roughness trend increasing",
            "no recent tool change in maintenance records",
        ],
    ),
    GroundTruthMechanism(
        mechanism_id="GTM-004",
        name="Process Parameter Drift",
        description=(
            "A process recipe change introduces a parameter set that gradually drifts "
            "outside nominal bounds due to feedback control instability."
        ),
        mechanism_type="process_drift",
        temporal_signature=[
            {"event": "recipe_change", "lag_hours": -96, "description": "Process recipe updated"},
            {"event": "parameter_oscillation", "lag_hours": -72, "description": "Feed rate begins oscillating"},
            {"event": "gradual_drift", "lag_hours": -48, "description": "Cutting speed drifts below nominal"},
            {"event": "yield_degradation", "lag_hours": -24, "description": "Yield starts declining"},
            {"event": "quality_failure", "lag_hours": 0, "description": "Batch fails inspection"},
        ],
        affected_parameters=["feed_rate", "cutting_speed", "spindle_speed"],
        expected_evidence=[
            "process change record before failure",
            "parameter oscillation pattern detected",
            "cutting parameters drifted from nominal",
        ],
    ),
    GroundTruthMechanism(
        mechanism_id="GTM-005",
        name="Thermal Expansion from Environmental Excursion",
        description=(
            "Ambient temperature spike in the factory causes thermal expansion "
            "of the machine structure, leading to positioning errors and dimensional failures."
        ),
        mechanism_type="thermal",
        temporal_signature=[
            {"event": "ambient_temp_spike", "lag_hours": -8, "description": "Ambient temperature exceeds 35°C"},
            {"event": "machine_thermal_drift", "lag_hours": -4, "description": "Machine geometric accuracy degrades"},
            {"event": "positioning_error", "lag_hours": -2, "description": "CNC positioning error increases"},
            {"event": "quality_failure", "lag_hours": 0, "description": "Dimensional failures detected"},
        ],
        affected_parameters=["ambient_temperature", "spindle_thermal_growth"],
        expected_evidence=[
            "ambient temperature elevated before failure",
            "thermal growth sensor showed excursion",
            "no other changes coincided",
        ],
    ),
]


# ============================================================
# Generator configuration
# ============================================================

@dataclass
class GeneratorConfig:
    n_machines: int = 5
    n_products: int = 3
    n_processes: int = 4
    n_operators: int = 8
    n_materials: int = 6
    n_material_lots: int = 20
    n_batches: int = 500
    n_failure_events: int = 40
    # How many of each mechanism type to inject
    mechanism_counts: Dict[str, int] = field(
        default_factory=lambda: {
            "GTM-001": 8,
            "GTM-002": 8,
            "GTM-003": 8,
            "GTM-004": 8,
            "GTM-005": 8,
        }
    )
    simulation_start: datetime = field(
        default_factory=lambda: datetime(2024, 1, 1, tzinfo=timezone.utc)
    )
    simulation_end: datetime = field(
        default_factory=lambda: datetime(2024, 9, 30, tzinfo=timezone.utc)
    )
    # Measurement frequency (minutes)
    measurement_interval_minutes: int = 15
    # Fraction of measurements with missing values
    missing_value_rate: float = 0.03
    # Std dev of Gaussian noise relative to signal range
    noise_level: float = 0.05
    random_seed: int = 42


# ============================================================
# Parameter specifications
# ============================================================

PARAMETER_SPECS = {
    "coolant_flow_rate": {
        "unit": "L/min", "nominal": 15.0, "lower": 10.0, "upper": 20.0,
        "critical_lower": 8.0, "noise_std": 0.3
    },
    "machining_temperature": {
        "unit": "°C", "nominal": 45.0, "lower": 35.0, "upper": 60.0,
        "critical_upper": 70.0, "noise_std": 0.8
    },
    "tool_temperature": {
        "unit": "°C", "nominal": 55.0, "lower": 40.0, "upper": 75.0,
        "critical_upper": 85.0, "noise_std": 1.2
    },
    "spindle_load": {
        "unit": "%", "nominal": 65.0, "lower": 30.0, "upper": 90.0,
        "critical_upper": 95.0, "noise_std": 3.0
    },
    "spindle_speed": {
        "unit": "RPM", "nominal": 2500.0, "lower": 1800.0, "upper": 3200.0,
        "noise_std": 25.0
    },
    "feed_rate": {
        "unit": "mm/min", "nominal": 180.0, "lower": 120.0, "upper": 240.0,
        "noise_std": 5.0
    },
    "cutting_speed": {
        "unit": "m/min", "nominal": 120.0, "lower": 90.0, "upper": 150.0,
        "noise_std": 3.0
    },
    "vibration_amplitude": {
        "unit": "mm/s", "nominal": 1.5, "lower": 0.5, "upper": 3.0,
        "critical_upper": 5.0, "noise_std": 0.1
    },
    "surface_roughness": {
        "unit": "μm Ra", "nominal": 0.8, "lower": 0.4, "upper": 1.6,
        "critical_upper": 2.5, "noise_std": 0.05
    },
    "tool_wear_index": {
        "unit": "index", "nominal": 0.2, "lower": 0.0, "upper": 0.6,
        "critical_upper": 0.8, "noise_std": 0.01
    },
    "chemical_composition_index": {
        "unit": "index", "nominal": 1.0, "lower": 0.95, "upper": 1.05,
        "critical_lower": 0.90, "critical_upper": 1.10, "noise_std": 0.01
    },
    "ambient_temperature": {
        "unit": "°C", "nominal": 22.0, "lower": 18.0, "upper": 28.0,
        "critical_upper": 35.0, "noise_std": 1.0
    },
    "spindle_thermal_growth": {
        "unit": "μm", "nominal": 5.0, "lower": 0.0, "upper": 15.0,
        "critical_upper": 25.0, "noise_std": 0.5
    },
}


# ============================================================
# Main generator class
# ============================================================

class SyntheticDataGenerator:
    """
    Generates realistic industrial datasets with hidden failure mechanisms.

    Output:
      - machines.csv
      - products.csv
      - materials.csv
      - material_lots.csv
      - operators.csv
      - processes.csv
      - batches.csv
      - batch_material_lots.csv
      - parameter_definitions.csv
      - parameter_measurements.csv
      - maintenance_events.csv
      - process_changes.csv
      - quality_inspections.csv
      - failure_events.csv          ← contains root_cause_label (for evaluation only)
      - ground_truth_mechanisms.json ← full mechanism definitions (for evaluation only)
    """

    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        np.random.seed(self.config.random_seed)
        random.seed(self.config.random_seed)
        self.rng = np.random.default_rng(self.config.random_seed)

        # Containers
        self.machines: List[Dict] = []
        self.products: List[Dict] = []
        self.materials: List[Dict] = []
        self.material_lots: List[Dict] = []
        self.operators: List[Dict] = []
        self.processes: List[Dict] = []
        self.batches: List[Dict] = []
        self.batch_material_lots: List[Dict] = []
        self.parameter_definitions: List[Dict] = []
        self.parameter_measurements: List[Dict] = []
        self.maintenance_events: List[Dict] = []
        self.process_changes: List[Dict] = []
        self.quality_inspections: List[Dict] = []
        self.failure_events: List[Dict] = []
        self.environmental_conditions: List[Dict] = []

        # State tracking
        self._machine_ids: List[str] = []
        self._product_ids: List[str] = []
        self._material_ids: List[str] = []
        self._lot_ids: List[str] = []
        self._operator_ids: List[str] = []
        self._process_ids: List[str] = []
        self._batch_ids: List[str] = []
        self._param_def_ids: Dict[str, str] = {}  # param_code → id

        # Injection state (tracks where in simulation time we are)
        self._injected_scenarios: List[Dict] = []

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _uid(self) -> str:
        return str(uuid.uuid4())

    def _ts(self, dt: datetime) -> str:
        return dt.isoformat()

    def _rand_time(self, start: datetime, end: datetime) -> datetime:
        delta = (end - start).total_seconds()
        return start + timedelta(seconds=self.rng.uniform(0, delta))

    def _add_noise(self, value: float, std: float) -> float:
        return float(value + self.rng.normal(0, std))

    def _missing(self) -> bool:
        return self.rng.random() < self.config.missing_value_rate

    # ── Entity generation ────────────────────────────────────────────────────

    def _generate_machines(self) -> None:
        machine_types = ["CNC_Lathe", "CNC_Mill", "Grinding_Center", "Assembly_Station", "Inspection_Station"]
        for i in range(self.config.n_machines):
            mid = self._uid()
            self._machine_ids.append(mid)
            self.machines.append({
                "id": mid,
                "name": f"Machine-{i+1:02d}",
                "machine_code": f"MCH-{i+1:03d}",
                "machine_type": machine_types[i % len(machine_types)],
                "manufacturer": random.choice(["Haas", "Mazak", "DMG Mori", "Fanuc", "Okuma"]),
                "model_number": f"MODEL-{random.randint(1000, 9999)}",
                "installation_date": self._ts(
                    self.config.simulation_start - timedelta(days=random.randint(365, 2000))
                ),
                "location": f"Hall-{chr(65 + i % 3)}/Bay-{i % 4 + 1}",
                "status": "operational",
                "created_at": self._ts(self.config.simulation_start),
                "updated_at": self._ts(self.config.simulation_start),
            })

    def _generate_products(self) -> None:
        product_names = ["Shaft-Assembly", "Gear-Component", "Housing-Part"]
        for i, pname in enumerate(product_names[:self.config.n_products]):
            pid = self._uid()
            self._product_ids.append(pid)
            self.products.append({
                "id": pid,
                "name": pname,
                "product_code": f"PRD-{i+1:03d}",
                "product_family": f"Family-{chr(65 + i)}",
                "created_at": self._ts(self.config.simulation_start),
                "updated_at": self._ts(self.config.simulation_start),
            })

    def _generate_materials(self) -> None:
        material_specs = [
            ("Steel-4140", "alloy_steel"),
            ("Aluminum-6061", "aluminum"),
            ("Coolant-Fluid", "coolant"),
            ("Cutting-Oil", "lubricant"),
            ("Abrasive-Compound", "abrasive"),
            ("Coating-Material", "coating"),
        ]
        for i, (name, mtype) in enumerate(material_specs[:self.config.n_materials]):
            mid = self._uid()
            self._material_ids.append(mid)
            self.materials.append({
                "id": mid,
                "name": name,
                "material_code": f"MAT-{i+1:03d}",
                "material_type": mtype,
                "supplier": random.choice(["SupplierA", "SupplierB", "SupplierC"]),
                "created_at": self._ts(self.config.simulation_start),
                "updated_at": self._ts(self.config.simulation_start),
            })

    def _generate_material_lots(self) -> None:
        for i in range(self.config.n_material_lots):
            lid = self._uid()
            self._lot_ids.append(lid)
            material_id = random.choice(self._material_ids)
            received = self._rand_time(
                self.config.simulation_start,
                self.config.simulation_end - timedelta(days=30),
            )
            # Lot 7 will be the "contaminated" lot (GTM-002)
            is_contaminated = (i == 6)
            self.material_lots.append({
                "id": lid,
                "material_id": material_id,
                "lot_number": f"LOT-{i+1:04d}",
                "received_date": self._ts(received),
                "expiry_date": self._ts(received + timedelta(days=180)),
                "quantity": round(self.rng.uniform(100, 2000), 1),
                "unit": "kg",
                "supplier_lot_number": f"SUP-LOT-{random.randint(10000, 99999)}",
                # NOTE: is_contaminated not exposed to AI pipeline
                "_ground_truth_contaminated": is_contaminated,
                "created_at": self._ts(received),
                "updated_at": self._ts(received),
            })

    def _generate_operators(self) -> None:
        for i in range(self.config.n_operators):
            oid = self._uid()
            self._operator_ids.append(oid)
            self.operators.append({
                "id": oid,
                "name": f"Operator-{i+1:02d}",
                "operator_code": f"OPR-{i+1:03d}",
                "shift": random.choice(["A", "B", "C"]),
                "certification_level": random.choice(["L1", "L2", "L3"]),
                "department": random.choice(["Machining", "Assembly", "QC"]),
                "created_at": self._ts(self.config.simulation_start),
                "updated_at": self._ts(self.config.simulation_start),
            })

    def _generate_processes(self) -> None:
        process_specs = [
            ("Rough_Turning", "turning"),
            ("Finish_Grinding", "grinding"),
            ("Boring_Op", "boring"),
            ("Surface_Milling", "milling"),
        ]
        for i, (pname, ptype) in enumerate(process_specs[:self.config.n_processes]):
            pid = self._uid()
            self._process_ids.append(pid)
            self.processes.append({
                "id": pid,
                "name": pname,
                "process_code": f"PRC-{i+1:03d}",
                "process_type": ptype,
                "description": f"{pname} manufacturing process",
                "version": "1.0",
                "nominal_parameters": {
                    "spindle_speed_rpm": 2500,
                    "feed_rate_mm_min": 180,
                    "cutting_depth_mm": 2.0,
                },
                "created_at": self._ts(self.config.simulation_start),
                "updated_at": self._ts(self.config.simulation_start),
            })

    def _generate_parameter_definitions(self) -> None:
        for code, spec in PARAMETER_SPECS.items():
            pid = self._uid()
            self._param_def_ids[code] = pid
            self.parameter_definitions.append({
                "id": pid,
                "name": code.replace("_", " ").title(),
                "parameter_code": code,
                "unit": spec["unit"],
                "nominal_value": spec["nominal"],
                "lower_limit": spec.get("lower"),
                "upper_limit": spec.get("upper"),
                "critical_lower_limit": spec.get("critical_lower"),
                "critical_upper_limit": spec.get("critical_upper"),
                "parameter_type": "continuous",
                "created_at": self._ts(self.config.simulation_start),
                "updated_at": self._ts(self.config.simulation_start),
            })

    # ── Batch & measurement generation ───────────────────────────────────────

    def _generate_baseline_measurements(
        self,
        machine_id: str,
        batch_id: str,
        start: datetime,
        end: datetime,
        param_overrides: Optional[Dict[str, Dict]] = None,
    ) -> List[Dict]:
        """Generate baseline time-series measurements for a batch period."""
        measurements = []
        current = start
        interval = timedelta(minutes=self.config.measurement_interval_minutes)

        overrides = param_overrides or {}

        while current <= end:
            for param_code, spec in PARAMETER_SPECS.items():
                if self._missing():
                    current += interval
                    continue

                nominal = spec["nominal"]
                noise_std = spec["noise_std"]

                # Apply overrides (used during failure mechanism injection)
                ov = overrides.get(param_code, {})
                override_value = ov.get("value", nominal)
                override_trend = ov.get("trend", 0.0)
                # trend: drift per hour
                elapsed_h = (current - start).total_seconds() / 3600.0
                value = self._add_noise(override_value + override_trend * elapsed_h, noise_std)

                lower = spec.get("lower", -np.inf)
                upper = spec.get("upper", np.inf)
                crit_lower = spec.get("critical_lower", -np.inf)
                crit_upper = spec.get("critical_upper", np.inf)
                is_oos = value < lower or value > upper
                is_anomalous = value < crit_lower or value > crit_upper

                measurements.append({
                    "id": self._uid(),
                    "parameter_definition_id": self._param_def_ids[param_code],
                    "machine_id": machine_id,
                    "batch_id": batch_id,
                    "timestamp": self._ts(current),
                    "value": round(value, 4),
                    "is_out_of_spec": is_oos,
                    "is_anomalous": is_anomalous,
                    "quality_flag": "bad" if is_anomalous else ("suspect" if is_oos else "good"),
                })
            current += interval

        return measurements

    def _generate_batches_and_measurements(self) -> None:
        """Generate all batches, assigning material lots and baseline measurements."""
        sim_start = self.config.simulation_start
        sim_end = self.config.simulation_end
        batch_duration_hours = 4.0  # average batch duration

        current_time = sim_start
        batch_count = 0

        while batch_count < self.config.n_batches and current_time < sim_end:
            bid = self._uid()
            self._batch_ids.append(bid)

            machine_id = random.choice(self._machine_ids)
            product_id = random.choice(self._product_ids)
            process_id = random.choice(self._process_ids)
            operator_id = random.choice(self._operator_ids)

            jitter = timedelta(minutes=random.randint(-30, 30))
            batch_start = current_time + jitter
            batch_end = batch_start + timedelta(hours=batch_duration_hours)

            # Assign 1-2 material lots
            n_lots = random.randint(1, 2)
            lot_ids = random.sample(self._lot_ids, n_lots)

            batch = {
                "id": bid,
                "batch_number": f"BTH-{batch_count+1:05d}",
                "machine_id": machine_id,
                "product_id": product_id,
                "process_id": process_id,
                "operator_id": operator_id,
                "dataset_id": None,  # filled during DB import
                "start_time": self._ts(batch_start),
                "end_time": self._ts(batch_end),
                "planned_quantity": float(random.randint(100, 500)),
                "actual_quantity": None,
                "unit": "pieces",
                "is_defective": False,
                "defect_rate": None,
                "_lot_ids": lot_ids,  # internal, for batch_material_lots
            }
            self.batches.append(batch)

            for lot_id in lot_ids:
                self.batch_material_lots.append({
                    "batch_id": bid,
                    "material_lot_id": lot_id,
                    "quantity_used": round(self.rng.uniform(5, 50), 2),
                    "unit": "kg",
                })

            # Baseline measurements (no anomalies for most batches)
            measurements = self._generate_baseline_measurements(
                machine_id=machine_id,
                batch_id=bid,
                start=batch_start,
                end=batch_end,
            )
            self.parameter_measurements.extend(measurements)

            # Quality inspection (most batches pass)
            defect_rate = max(0.0, self._add_noise(0.02, 0.01))
            result = "pass" if defect_rate < 0.05 else "fail"
            self.quality_inspections.append({
                "id": self._uid(),
                "batch_id": bid,
                "dataset_id": None,
                "inspection_time": self._ts(batch_end + timedelta(hours=0.5)),
                "inspector": f"QC-{random.randint(1, 5):02d}",
                "result": result,
                "defect_count": int(defect_rate * batch["planned_quantity"]),
                "defect_rate": round(defect_rate, 4),
                "defect_types": [],
                "notes": "",
            })

            batch_count += 1
            current_time = batch_end + timedelta(hours=self.rng.uniform(0.5, 2.0))

    def _generate_maintenance_events(self) -> None:
        """Generate routine maintenance events for each machine."""
        for machine_id in self._machine_ids:
            # Preventive maintenance every 30 days
            current = self.config.simulation_start + timedelta(days=random.randint(5, 15))
            while current < self.config.simulation_end:
                mtype = random.choices(
                    ["preventive", "calibration", "inspection"],
                    weights=[0.5, 0.3, 0.2]
                )[0]
                duration = self.rng.uniform(2, 8)
                self.maintenance_events.append({
                    "id": self._uid(),
                    "machine_id": machine_id,
                    "dataset_id": None,
                    "maintenance_type": mtype,
                    "start_time": self._ts(current),
                    "end_time": self._ts(current + timedelta(hours=duration)),
                    "duration_hours": round(duration, 2),
                    "description": f"Scheduled {mtype} maintenance",
                    "technician": f"Tech-{random.randint(1, 5):02d}",
                    "components_replaced": [],
                    "work_order": f"WO-{random.randint(10000, 99999)}",
                    "notes": "",
                })
                current += timedelta(days=random.randint(25, 35))

    def _generate_process_changes(self) -> None:
        """Generate occasional process recipe updates."""
        for process_id in self._process_ids:
            current = self.config.simulation_start + timedelta(days=random.randint(20, 40))
            while current < self.config.simulation_end:
                self.process_changes.append({
                    "id": self._uid(),
                    "process_id": process_id,
                    "machine_id": random.choice(self._machine_ids),
                    "dataset_id": None,
                    "change_time": self._ts(current),
                    "change_type": random.choice(["parameter_adjustment", "recipe_change"]),
                    "parameter_name": random.choice(list(PARAMETER_SPECS.keys())[:6]),
                    "old_value": str(round(self.rng.uniform(100, 200), 1)),
                    "new_value": str(round(self.rng.uniform(100, 200), 1)),
                    "changed_by": f"Engineer-{random.randint(1, 4):02d}",
                    "reason": "Optimization",
                    "approved_by": "QA-Manager",
                })
                current += timedelta(days=random.randint(30, 60))

    # ── Failure mechanism injection ───────────────────────────────────────────

    def _inject_cooling_degradation(self, failure_time: datetime, machine_id: str) -> Tuple[str, str]:
        """Inject GTM-001: Cooling Degradation scenario."""
        batch_id = self._uid()
        self._batch_ids.append(batch_id)

        batch_start = failure_time - timedelta(hours=6)
        batch_end = failure_time

        batch = {
            "id": batch_id,
            "batch_number": f"BTH-F{len(self.failure_events)+1:04d}",
            "machine_id": machine_id,
            "product_id": random.choice(self._product_ids),
            "process_id": random.choice(self._process_ids),
            "operator_id": random.choice(self._operator_ids),
            "dataset_id": None,
            "start_time": self._ts(batch_start),
            "end_time": self._ts(batch_end),
            "planned_quantity": 200.0,
            "actual_quantity": 180.0,
            "unit": "pieces",
            "is_defective": True,
            "defect_rate": round(self.rng.uniform(0.12, 0.25), 4),
            "_lot_ids": [random.choice(self._lot_ids)],
        }
        self.batches.append(batch)
        self.batch_material_lots.append({
            "batch_id": batch_id,
            "material_lot_id": batch["_lot_ids"][0],
            "quantity_used": 20.0,
            "unit": "kg",
        })

        # Inject parameter anomalies: coolant flow drops, temperature rises
        maint_time = failure_time - timedelta(hours=24)
        self.maintenance_events.append({
            "id": self._uid(),
            "machine_id": machine_id,
            "dataset_id": None,
            "maintenance_type": "corrective",
            "start_time": self._ts(maint_time),
            "end_time": self._ts(maint_time + timedelta(hours=3)),
            "duration_hours": 3.0,
            "description": "Corrective maintenance on cooling circuit — flow regulator replaced",
            "technician": "Tech-01",
            "components_replaced": ["flow_regulator"],
            "work_order": f"WO-COOL-{random.randint(10000, 99999)}",
            "notes": "Post-maintenance flow calibration may be required",
        })

        # Measurement anomalies starting 18h before failure
        param_overrides = {
            # coolant flow drops from nominal ~15 to ~10 (below lower limit)
            "coolant_flow_rate": {
                "value": 15.0,
                "trend": -(5.0 / 18.0),  # drops 5 L/min over 18 hours
            },
            # temperature rises
            "machining_temperature": {
                "value": 45.0,
                "trend": (12.0 / 12.0),  # rises 12°C over 12 hours
            },
            "tool_temperature": {
                "value": 55.0,
                "trend": (15.0 / 12.0),
            },
        }
        anomaly_start = failure_time - timedelta(hours=18)
        measurements = self._generate_baseline_measurements(
            machine_id=machine_id,
            batch_id=batch_id,
            start=anomaly_start,
            end=batch_end,
            param_overrides=param_overrides,
        )
        self.parameter_measurements.extend(measurements)

        # Quality inspection: FAIL
        self.quality_inspections.append({
            "id": self._uid(),
            "batch_id": batch_id,
            "dataset_id": None,
            "inspection_time": self._ts(batch_end + timedelta(hours=0.5)),
            "inspector": "QC-01",
            "result": "fail",
            "defect_count": int(batch["defect_rate"] * batch["planned_quantity"]),
            "defect_rate": batch["defect_rate"],
            "defect_types": ["dimensional_failure", "surface_defect"],
            "notes": "Thermal-related dimensional failures",
        })

        failure_id = self._uid()
        self.failure_events.append({
            "id": failure_id,
            "batch_id": batch_id,
            "machine_id": machine_id,
            "dataset_id": None,
            "event_time": self._ts(failure_time),
            "event_type": "quality_failure",
            "severity": "major",
            "description": "Batch failed quality inspection — dimensional failures and surface defects",
            "affected_quantity": batch["defect_rate"] * batch["planned_quantity"],
            "downtime_hours": None,
            "detected_by": "QC-01",
            "root_cause_label": "GTM-001:Cooling System Degradation",
            "is_synthetic_ground_truth": True,
        })
        return failure_id, batch_id

    def _inject_material_contamination(self, failure_time: datetime, machine_id: str) -> Tuple[str, str]:
        """Inject GTM-002: Material Contamination scenario."""
        # Find the "contaminated" lot
        contaminated_lot = next(
            (lot for lot in self.material_lots if lot.get("_ground_truth_contaminated")),
            self.material_lots[6] if len(self.material_lots) > 6 else self.material_lots[0],
        )

        batch_id = self._uid()
        self._batch_ids.append(batch_id)
        batch_start = failure_time - timedelta(hours=6)
        batch_end = failure_time

        batch = {
            "id": batch_id,
            "batch_number": f"BTH-F{len(self.failure_events)+1:04d}",
            "machine_id": machine_id,
            "product_id": random.choice(self._product_ids),
            "process_id": random.choice(self._process_ids),
            "operator_id": random.choice(self._operator_ids),
            "dataset_id": None,
            "start_time": self._ts(batch_start),
            "end_time": self._ts(batch_end),
            "planned_quantity": 300.0,
            "actual_quantity": 290.0,
            "unit": "pieces",
            "is_defective": True,
            "defect_rate": round(self.rng.uniform(0.10, 0.20), 4),
            "_lot_ids": [contaminated_lot["id"]],
        }
        self.batches.append(batch)
        self.batch_material_lots.append({
            "batch_id": batch_id,
            "material_lot_id": contaminated_lot["id"],
            "quantity_used": 30.0,
            "unit": "kg",
        })

        # Chemical composition shows deviation
        param_overrides = {
            "chemical_composition_index": {
                "value": 0.88,  # below critical_lower (0.90)
                "trend": 0.0,
            },
            "surface_roughness": {
                "value": 1.8,  # above upper limit (1.6)
                "trend": 0.0,
            },
        }
        measurements = self._generate_baseline_measurements(
            machine_id=machine_id,
            batch_id=batch_id,
            start=batch_start,
            end=batch_end,
            param_overrides=param_overrides,
        )
        self.parameter_measurements.extend(measurements)

        self.quality_inspections.append({
            "id": self._uid(),
            "batch_id": batch_id,
            "dataset_id": None,
            "inspection_time": self._ts(batch_end + timedelta(hours=0.5)),
            "inspector": "QC-02",
            "result": "fail",
            "defect_count": int(batch["defect_rate"] * batch["planned_quantity"]),
            "defect_rate": batch["defect_rate"],
            "defect_types": ["surface_contamination", "chemical_deviation"],
            "notes": f"Material from lot {contaminated_lot['lot_number']} suspected",
        })

        failure_id = self._uid()
        self.failure_events.append({
            "id": failure_id,
            "batch_id": batch_id,
            "machine_id": machine_id,
            "dataset_id": None,
            "event_time": self._ts(failure_time),
            "event_type": "quality_failure",
            "severity": "major",
            "description": "Surface contamination and chemical deviation in batch",
            "affected_quantity": batch["defect_rate"] * batch["planned_quantity"],
            "downtime_hours": None,
            "detected_by": "QC-02",
            "root_cause_label": "GTM-002:Raw Material Contamination",
            "is_synthetic_ground_truth": True,
        })
        return failure_id, batch_id

    def _inject_wear_acceleration(self, failure_time: datetime, machine_id: str) -> Tuple[str, str]:
        """Inject GTM-003: Accelerated Tool Wear scenario."""
        batch_id = self._uid()
        self._batch_ids.append(batch_id)
        batch_start = failure_time - timedelta(hours=8)
        batch_end = failure_time

        batch = {
            "id": batch_id,
            "batch_number": f"BTH-F{len(self.failure_events)+1:04d}",
            "machine_id": machine_id,
            "product_id": random.choice(self._product_ids),
            "process_id": random.choice(self._process_ids),
            "operator_id": random.choice(self._operator_ids),
            "dataset_id": None,
            "start_time": self._ts(batch_start),
            "end_time": self._ts(batch_end),
            "planned_quantity": 250.0,
            "actual_quantity": 240.0,
            "unit": "pieces",
            "is_defective": True,
            "defect_rate": round(self.rng.uniform(0.08, 0.18), 4),
            "_lot_ids": [random.choice(self._lot_ids)],
        }
        self.batches.append(batch)
        self.batch_material_lots.append({
            "batch_id": batch_id,
            "material_lot_id": batch["_lot_ids"][0],
            "quantity_used": 15.0,
            "unit": "kg",
        })

        # Gradual wear signature over 72 hours
        param_overrides = {
            "spindle_load": {"value": 88.0, "trend": 0.1},   # high and rising
            "vibration_amplitude": {"value": 2.5, "trend": 0.03},
            "surface_roughness": {"value": 1.2, "trend": 0.02},
            "tool_wear_index": {"value": 0.5, "trend": 0.005},
        }
        # Show pre-failure trend over 72h window
        pre_batch_start = failure_time - timedelta(hours=72)
        measurements = self._generate_baseline_measurements(
            machine_id=machine_id,
            batch_id=batch_id,
            start=pre_batch_start,
            end=batch_end,
            param_overrides=param_overrides,
        )
        self.parameter_measurements.extend(measurements)

        self.quality_inspections.append({
            "id": self._uid(),
            "batch_id": batch_id,
            "dataset_id": None,
            "inspection_time": self._ts(batch_end + timedelta(hours=0.5)),
            "inspector": "QC-03",
            "result": "fail",
            "defect_count": int(batch["defect_rate"] * batch["planned_quantity"]),
            "defect_rate": batch["defect_rate"],
            "defect_types": ["dimensional_failure", "surface_roughness_exceeded"],
            "notes": "Progressive surface quality degradation detected",
        })

        failure_id = self._uid()
        self.failure_events.append({
            "id": failure_id,
            "batch_id": batch_id,
            "machine_id": machine_id,
            "dataset_id": None,
            "event_time": self._ts(failure_time),
            "event_type": "quality_failure",
            "severity": "major",
            "description": "Dimensional failures due to excessive tool wear",
            "affected_quantity": batch["defect_rate"] * batch["planned_quantity"],
            "downtime_hours": None,
            "detected_by": "QC-03",
            "root_cause_label": "GTM-003:Accelerated Tool Wear",
            "is_synthetic_ground_truth": True,
        })
        return failure_id, batch_id

    def _inject_process_drift(self, failure_time: datetime, machine_id: str) -> Tuple[str, str]:
        """Inject GTM-004: Process Parameter Drift scenario."""
        process_id = random.choice(self._process_ids)
        # Add a process change event ~96h before failure
        change_time = failure_time - timedelta(hours=96)
        self.process_changes.append({
            "id": self._uid(),
            "process_id": process_id,
            "machine_id": machine_id,
            "dataset_id": None,
            "change_time": self._ts(change_time),
            "change_type": "recipe_change",
            "parameter_name": "feed_rate",
            "old_value": "180",
            "new_value": "210",
            "changed_by": "Process-Engineer-02",
            "reason": "Cycle time reduction experiment",
            "approved_by": "QA-Manager",
        })

        batch_id = self._uid()
        self._batch_ids.append(batch_id)
        batch_start = failure_time - timedelta(hours=6)
        batch_end = failure_time

        batch = {
            "id": batch_id,
            "batch_number": f"BTH-F{len(self.failure_events)+1:04d}",
            "machine_id": machine_id,
            "product_id": random.choice(self._product_ids),
            "process_id": process_id,
            "operator_id": random.choice(self._operator_ids),
            "dataset_id": None,
            "start_time": self._ts(batch_start),
            "end_time": self._ts(batch_end),
            "planned_quantity": 400.0,
            "actual_quantity": 380.0,
            "unit": "pieces",
            "is_defective": True,
            "defect_rate": round(self.rng.uniform(0.07, 0.15), 4),
            "_lot_ids": [random.choice(self._lot_ids)],
        }
        self.batches.append(batch)
        self.batch_material_lots.append({
            "batch_id": batch_id,
            "material_lot_id": batch["_lot_ids"][0],
            "quantity_used": 25.0,
            "unit": "kg",
        })

        # Parameter drift
        param_overrides = {
            "feed_rate": {"value": 210.0, "trend": -2.0},   # drifts down
            "cutting_speed": {"value": 120.0, "trend": -1.5},
            "spindle_speed": {"value": 2500.0, "trend": -20.0},
        }
        drift_start = failure_time - timedelta(hours=72)
        measurements = self._generate_baseline_measurements(
            machine_id=machine_id,
            batch_id=batch_id,
            start=drift_start,
            end=batch_end,
            param_overrides=param_overrides,
        )
        self.parameter_measurements.extend(measurements)

        self.quality_inspections.append({
            "id": self._uid(),
            "batch_id": batch_id,
            "dataset_id": None,
            "inspection_time": self._ts(batch_end + timedelta(hours=0.5)),
            "inspector": "QC-04",
            "result": "fail",
            "defect_count": int(batch["defect_rate"] * batch["planned_quantity"]),
            "defect_rate": batch["defect_rate"],
            "defect_types": ["dimensional_failure", "machining_marks"],
            "notes": "Process parameter drift suspected",
        })

        failure_id = self._uid()
        self.failure_events.append({
            "id": failure_id,
            "batch_id": batch_id,
            "machine_id": machine_id,
            "dataset_id": None,
            "event_time": self._ts(failure_time),
            "event_type": "quality_failure",
            "severity": "moderate",
            "description": "Process parameter drift following recipe change",
            "affected_quantity": batch["defect_rate"] * batch["planned_quantity"],
            "downtime_hours": None,
            "detected_by": "QC-04",
            "root_cause_label": "GTM-004:Process Parameter Drift",
            "is_synthetic_ground_truth": True,
        })
        return failure_id, batch_id

    def _inject_thermal_expansion(self, failure_time: datetime, machine_id: str) -> Tuple[str, str]:
        """Inject GTM-005: Thermal Expansion from Environmental Excursion."""
        # Inject ambient temperature spike in environmental conditions
        spike_start = failure_time - timedelta(hours=8)
        for i in range(0, 8 * 4):  # 15-min intervals for 8 hours
            t = spike_start + timedelta(minutes=i * 15)
            # Temperature peaks ~4h before failure
            hours_into_spike = (t - spike_start).total_seconds() / 3600
            temp = 22.0 + max(0, 15.0 * np.sin(np.pi * hours_into_spike / 8))
            self.environmental_conditions.append({
                "id": self._uid(),
                "machine_id": machine_id,
                "dataset_id": None,
                "timestamp": self._ts(t),
                "ambient_temperature": round(temp + self._add_noise(0, 0.5), 2),
                "ambient_humidity": round(self._add_noise(55, 5), 1),
                "ambient_pressure": round(self._add_noise(101.3, 0.2), 2),
                "vibration_level": None,
            })

        batch_id = self._uid()
        self._batch_ids.append(batch_id)
        batch_start = failure_time - timedelta(hours=4)
        batch_end = failure_time

        batch = {
            "id": batch_id,
            "batch_number": f"BTH-F{len(self.failure_events)+1:04d}",
            "machine_id": machine_id,
            "product_id": random.choice(self._product_ids),
            "process_id": random.choice(self._process_ids),
            "operator_id": random.choice(self._operator_ids),
            "dataset_id": None,
            "start_time": self._ts(batch_start),
            "end_time": self._ts(batch_end),
            "planned_quantity": 150.0,
            "actual_quantity": 140.0,
            "unit": "pieces",
            "is_defective": True,
            "defect_rate": round(self.rng.uniform(0.06, 0.14), 4),
            "_lot_ids": [random.choice(self._lot_ids)],
        }
        self.batches.append(batch)
        self.batch_material_lots.append({
            "batch_id": batch_id,
            "material_lot_id": batch["_lot_ids"][0],
            "quantity_used": 10.0,
            "unit": "kg",
        })

        param_overrides = {
            "ambient_temperature": {"value": 36.0, "trend": 0.0},
            "spindle_thermal_growth": {"value": 18.0, "trend": 0.5},
            "machining_temperature": {"value": 55.0, "trend": 1.0},
        }
        measurements = self._generate_baseline_measurements(
            machine_id=machine_id,
            batch_id=batch_id,
            start=batch_start,
            end=batch_end,
            param_overrides=param_overrides,
        )
        self.parameter_measurements.extend(measurements)

        self.quality_inspections.append({
            "id": self._uid(),
            "batch_id": batch_id,
            "dataset_id": None,
            "inspection_time": self._ts(batch_end + timedelta(hours=0.5)),
            "inspector": "QC-05",
            "result": "fail",
            "defect_count": int(batch["defect_rate"] * batch["planned_quantity"]),
            "defect_rate": batch["defect_rate"],
            "defect_types": ["dimensional_failure"],
            "notes": "Dimensional failures suspected thermal expansion",
        })

        failure_id = self._uid()
        self.failure_events.append({
            "id": failure_id,
            "batch_id": batch_id,
            "machine_id": machine_id,
            "dataset_id": None,
            "event_time": self._ts(failure_time),
            "event_type": "quality_failure",
            "severity": "moderate",
            "description": "Dimensional failures caused by thermal expansion during ambient temp excursion",
            "affected_quantity": batch["defect_rate"] * batch["planned_quantity"],
            "downtime_hours": None,
            "detected_by": "QC-05",
            "root_cause_label": "GTM-005:Thermal Expansion from Environmental Excursion",
            "is_synthetic_ground_truth": True,
        })
        return failure_id, batch_id

    def _inject_all_mechanisms(self) -> None:
        """Inject failure mechanisms at distributed time points."""
        injectors = {
            "GTM-001": self._inject_cooling_degradation,
            "GTM-002": self._inject_material_contamination,
            "GTM-003": self._inject_wear_acceleration,
            "GTM-004": self._inject_process_drift,
            "GTM-005": self._inject_thermal_expansion,
        }

        sim_duration = (self.config.simulation_end - self.config.simulation_start).total_seconds()

        for gtm_id, injector in injectors.items():
            count = self.config.mechanism_counts.get(gtm_id, 5)
            for _ in range(count):
                # Distribute failures across simulation period
                offset = self.rng.uniform(0.1, 0.9) * sim_duration
                failure_time = self.config.simulation_start + timedelta(seconds=offset)
                machine_id = random.choice(self._machine_ids)
                try:
                    injector(failure_time, machine_id)
                except Exception as e:
                    logger.warning(f"Failed to inject {gtm_id}: {e}")

    # ── Output ───────────────────────────────────────────────────────────────

    def generate(self) -> Dict[str, pd.DataFrame]:
        """Run the full generation pipeline."""
        logger.info("Starting synthetic data generation...")

        logger.info("Generating entities...")
        self._generate_machines()
        self._generate_products()
        self._generate_materials()
        self._generate_material_lots()
        self._generate_operators()
        self._generate_processes()
        self._generate_parameter_definitions()

        logger.info("Generating baseline production data...")
        self._generate_batches_and_measurements()
        self._generate_maintenance_events()
        self._generate_process_changes()

        logger.info("Injecting failure mechanisms...")
        self._inject_all_mechanisms()

        logger.info(
            f"Generation complete: "
            f"{len(self.batches)} batches, "
            f"{len(self.parameter_measurements)} measurements, "
            f"{len(self.failure_events)} failure events"
        )

        # Convert to DataFrames (strip internal _* fields)
        def clean(rows: List[Dict]) -> List[Dict]:
            return [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows]

        return {
            "machines": pd.DataFrame(clean(self.machines)),
            "products": pd.DataFrame(clean(self.products)),
            "materials": pd.DataFrame(clean(self.materials)),
            "material_lots": pd.DataFrame(clean(self.material_lots)),
            "operators": pd.DataFrame(clean(self.operators)),
            "processes": pd.DataFrame(clean(self.processes)),
            "batches": pd.DataFrame(clean(self.batches)),
            "batch_material_lots": pd.DataFrame(self.batch_material_lots),
            "parameter_definitions": pd.DataFrame(self.parameter_definitions),
            "parameter_measurements": pd.DataFrame(self.parameter_measurements),
            "maintenance_events": pd.DataFrame(clean(self.maintenance_events)),
            "process_changes": pd.DataFrame(self.process_changes),
            "quality_inspections": pd.DataFrame(clean(self.quality_inspections)),
            "failure_events": pd.DataFrame(clean(self.failure_events)),
            "environmental_conditions": pd.DataFrame(clean(self.environmental_conditions)),
        }

    def save(self, output_dir: str = "./data/synthetic") -> None:
        """Save all generated tables as CSV files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        tables = self.generate()
        for table_name, df in tables.items():
            if df.empty:
                logger.warning(f"Skipping empty table: {table_name}")
                continue
            filepath = output_path / f"{table_name}.csv"
            df.to_csv(filepath, index=False)
            logger.info(f"Saved {table_name}: {len(df)} rows → {filepath}")

        # Save ground truth mechanisms (evaluation only — do NOT feed to AI pipeline)
        gt_path = output_path / "ground_truth_mechanisms.json"
        gt_data = [
            {
                "mechanism_id": m.mechanism_id,
                "name": m.name,
                "description": m.description,
                "mechanism_type": m.mechanism_type,
                "temporal_signature": m.temporal_signature,
                "affected_parameters": m.affected_parameters,
                "expected_evidence": m.expected_evidence,
            }
            for m in GROUND_TRUTH_MECHANISMS
        ]
        with open(gt_path, "w") as f:
            json.dump(gt_data, f, indent=2)
        logger.info(f"Saved ground truth mechanisms → {gt_path}")

        # Summary stats
        tables["failure_events"].groupby("root_cause_label").size().to_csv(
            output_path / "_failure_distribution.csv"
        )
        logger.info(f"Synthetic dataset saved to {output_dir}")


def main():
    """CLI entry point for data generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic industrial dataset")
    parser.add_argument("--output-dir", default="./data/synthetic", help="Output directory")
    parser.add_argument("--batches", type=int, default=500, help="Number of normal batches")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    config = GeneratorConfig(
        n_batches=args.batches,
        random_seed=args.seed,
    )
    gen = SyntheticDataGenerator(config=config)
    gen.save(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
