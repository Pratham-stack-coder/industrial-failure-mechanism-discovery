"""
SQLAlchemy ORM models for the Industrial Failure Mechanism Discovery system.

Schema overview:
  Industrial entities: Machine, Product, Material, MaterialLot, Operator,
                       Process, Batch, EnvironmentalCondition
  Measurements:        ParameterDefinition, ParameterMeasurement
  Events:              MaintenanceEvent, ProcessChange, QualityInspection,
                       FailureEvent
  Investigations:      Investigation, CandidateMechanism, MechanismEvidence,
                       MechanismScore
  Research:            Dataset, Experiment, ExperimentResult
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ============================================================
# Enumerations
# ============================================================

class MachineStatus(str, enum.Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    UNDER_MAINTENANCE = "under_maintenance"
    FAILED = "failed"
    DECOMMISSIONED = "decommissioned"


class InvestigationStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MechanismType(str, enum.Enum):
    WEAR = "wear"
    CONTAMINATION = "contamination"
    THERMAL = "thermal"
    MECHANICAL = "mechanical"
    CHEMICAL = "chemical"
    ELECTRICAL = "electrical"
    PROCESS_DRIFT = "process_drift"
    MATERIAL_DEFECT = "material_defect"
    OPERATOR_ERROR = "operator_error"
    ENVIRONMENTAL = "environmental"
    COMPOSITE = "composite"
    UNKNOWN = "unknown"


class EvidenceType(str, enum.Enum):
    PARAMETER_CHANGE = "parameter_change"
    TEMPORAL_CORRELATION = "temporal_correlation"
    EVENT_SEQUENCE = "event_sequence"
    MATERIAL_BATCH = "material_batch"
    HISTORICAL_PATTERN = "historical_pattern"
    CHANGEPOINT = "changepoint"
    STATISTICAL_ANOMALY = "statistical_anomaly"
    MAINTENANCE_RECORD = "maintenance_record"
    QUALITY_DEGRADATION = "quality_degradation"
    OPERATOR_CHANGE = "operator_change"
    ENVIRONMENTAL_CONDITION = "environmental_condition"


class EvidencePolarity(str, enum.Enum):
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    NEUTRAL = "neutral"


class FailureSeverity(str, enum.Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class MaintenanceType(str, enum.Enum):
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    PREDICTIVE = "predictive"
    EMERGENCY = "emergency"
    CALIBRATION = "calibration"
    INSPECTION = "inspection"


class InspectionResult(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    MARGINAL = "marginal"
    PENDING = "pending"


# ============================================================
# Mixins
# ============================================================

class TimestampMixin:
    """Adds created_at / updated_at to any model."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPKMixin:
    """UUID primary key."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


# ============================================================
# Industrial Entity Models
# ============================================================

class Machine(Base, UUIDPKMixin, TimestampMixin):
    """Physical machine or equipment unit."""
    __tablename__ = "machines"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    machine_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    machine_type: Mapped[str] = mapped_column(String(100), nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(200))
    model_number: Mapped[Optional[str]] = mapped_column(String(100))
    installation_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[MachineStatus] = mapped_column(
        Enum(MachineStatus), default=MachineStatus.OPERATIONAL, nullable=False
    )
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON)

    # Relationships
    batches: Mapped[List["Batch"]] = relationship(back_populates="machine")
    parameter_measurements: Mapped[List["ParameterMeasurement"]] = relationship(
        back_populates="machine"
    )
    maintenance_events: Mapped[List["MaintenanceEvent"]] = relationship(
        back_populates="machine"
    )
    failure_events: Mapped[List["FailureEvent"]] = relationship(
        back_populates="machine"
    )

    __table_args__ = (
        Index("ix_machines_machine_code", "machine_code"),
        Index("ix_machines_status", "status"),
    )


class Product(Base, UUIDPKMixin, TimestampMixin):
    """Product specification / type."""
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    product_family: Mapped[Optional[str]] = mapped_column(String(100))
    specifications: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    quality_limits: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    batches: Mapped[List["Batch"]] = relationship(back_populates="product")

    __table_args__ = (Index("ix_products_product_code", "product_code"),)


class Material(Base, UUIDPKMixin, TimestampMixin):
    """Raw material or input material specification."""
    __tablename__ = "materials"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    material_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    material_type: Mapped[str] = mapped_column(String(100), nullable=False)
    supplier: Mapped[Optional[str]] = mapped_column(String(200))
    specifications: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    lots: Mapped[List["MaterialLot"]] = relationship(back_populates="material")

    __table_args__ = (Index("ix_materials_material_code", "material_code"),)


class MaterialLot(Base, UUIDPKMixin, TimestampMixin):
    """A specific lot/batch of raw material."""
    __tablename__ = "material_lots"

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False
    )
    lot_number: Mapped[str] = mapped_column(String(100), nullable=False)
    received_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String(20))
    supplier_lot_number: Mapped[Optional[str]] = mapped_column(String(100))
    quality_certificate: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    material: Mapped["Material"] = relationship(back_populates="lots")
    batch_lots: Mapped[List["BatchMaterialLot"]] = relationship(
        back_populates="material_lot"
    )

    __table_args__ = (
        UniqueConstraint("material_id", "lot_number", name="uq_material_lot"),
        Index("ix_material_lots_lot_number", "lot_number"),
    )


class Operator(Base, UUIDPKMixin, TimestampMixin):
    """Machine operator / process technician."""
    __tablename__ = "operators"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    operator_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    shift: Mapped[Optional[str]] = mapped_column(String(20))
    certification_level: Mapped[Optional[str]] = mapped_column(String(50))
    department: Mapped[Optional[str]] = mapped_column(String(100))

    batches: Mapped[List["Batch"]] = relationship(back_populates="operator")

    __table_args__ = (Index("ix_operators_operator_code", "operator_code"),)


class Process(Base, UUIDPKMixin, TimestampMixin):
    """Manufacturing process / recipe."""
    __tablename__ = "processes"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    process_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    process_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    nominal_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    version: Mapped[str] = mapped_column(String(20), default="1.0")

    batches: Mapped[List["Batch"]] = relationship(back_populates="process")
    process_changes: Mapped[List["ProcessChange"]] = relationship(
        back_populates="process"
    )
    parameter_measurements: Mapped[List["ParameterMeasurement"]] = relationship(
        back_populates="process"
    )

    __table_args__ = (Index("ix_processes_process_code", "process_code"),)


class Batch(Base, UUIDPKMixin, TimestampMixin):
    """Production batch - central entity linking machine, product, process, operator."""
    __tablename__ = "batches"

    batch_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processes.id"), nullable=False
    )
    operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operators.id")
    )
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id")
    )

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    planned_quantity: Mapped[Optional[float]] = mapped_column(Float)
    actual_quantity: Mapped[Optional[float]] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String(20))
    is_defective: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    defect_rate: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    machine: Mapped["Machine"] = relationship(back_populates="batches")
    product: Mapped["Product"] = relationship(back_populates="batches")
    process: Mapped["Process"] = relationship(back_populates="batches")
    operator: Mapped[Optional["Operator"]] = relationship(back_populates="batches")
    dataset: Mapped[Optional["Dataset"]] = relationship(back_populates="batches")
    material_lots: Mapped[List["BatchMaterialLot"]] = relationship(
        back_populates="batch"
    )
    quality_inspections: Mapped[List["QualityInspection"]] = relationship(
        back_populates="batch"
    )
    failure_events: Mapped[List["FailureEvent"]] = relationship(
        back_populates="batch"
    )

    __table_args__ = (
        Index("ix_batches_batch_number", "batch_number"),
        Index("ix_batches_machine_start", "machine_id", "start_time"),
        Index("ix_batches_start_time", "start_time"),
        Index("ix_batches_is_defective", "is_defective"),
    )


class BatchMaterialLot(Base, TimestampMixin):
    """Association between batches and material lots (many-to-many)."""
    __tablename__ = "batch_material_lots"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.id"), primary_key=True
    )
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_lots.id"), primary_key=True
    )
    quantity_used: Mapped[Optional[float]] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String(20))

    batch: Mapped["Batch"] = relationship(back_populates="material_lots")
    material_lot: Mapped["MaterialLot"] = relationship(back_populates="batch_lots")


class EnvironmentalCondition(Base, UUIDPKMixin, TimestampMixin):
    """Environmental sensor readings (temperature, humidity, etc.)."""
    __tablename__ = "environmental_conditions"

    machine_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id")
    )
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id")
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ambient_temperature: Mapped[Optional[float]] = mapped_column(Float)
    ambient_humidity: Mapped[Optional[float]] = mapped_column(Float)
    ambient_pressure: Mapped[Optional[float]] = mapped_column(Float)
    vibration_level: Mapped[Optional[float]] = mapped_column(Float)
    additional_readings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_env_machine_time", "machine_id", "timestamp"),
        Index("ix_env_timestamp", "timestamp"),
    )


# ============================================================
# Measurement Models
# ============================================================

class ParameterDefinition(Base, UUIDPKMixin, TimestampMixin):
    """Definition of a measurable process or machine parameter."""
    __tablename__ = "parameter_definitions"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parameter_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    nominal_value: Mapped[Optional[float]] = mapped_column(Float)
    lower_limit: Mapped[Optional[float]] = mapped_column(Float)
    upper_limit: Mapped[Optional[float]] = mapped_column(Float)
    critical_lower_limit: Mapped[Optional[float]] = mapped_column(Float)
    critical_upper_limit: Mapped[Optional[float]] = mapped_column(Float)
    parameter_type: Mapped[str] = mapped_column(String(50), default="continuous")
    # continuous | discrete | categorical | event

    measurements: Mapped[List["ParameterMeasurement"]] = relationship(
        back_populates="parameter_definition"
    )

    __table_args__ = (Index("ix_param_def_code", "parameter_code"),)


class ParameterMeasurement(Base, UUIDPKMixin):
    """A single measurement of a process/machine parameter at a specific time."""
    __tablename__ = "parameter_measurements"

    parameter_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parameter_definitions.id"), nullable=False
    )
    machine_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id")
    )
    process_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processes.id")
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.id")
    )
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id")
    )

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    is_out_of_spec: Mapped[bool] = mapped_column(Boolean, default=False)
    is_anomalous: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_flag: Mapped[Optional[str]] = mapped_column(String(20))
    # good | suspect | bad | missing_interpolated

    parameter_definition: Mapped["ParameterDefinition"] = relationship(
        back_populates="measurements"
    )
    machine: Mapped[Optional["Machine"]] = relationship(
        back_populates="parameter_measurements"
    )
    process: Mapped[Optional["Process"]] = relationship(
        back_populates="parameter_measurements"
    )

    __table_args__ = (
        Index("ix_pm_param_time", "parameter_definition_id", "timestamp"),
        Index("ix_pm_machine_time", "machine_id", "timestamp"),
        Index("ix_pm_batch", "batch_id"),
        Index("ix_pm_timestamp", "timestamp"),
    )


# ============================================================
# Event Models
# ============================================================

class MaintenanceEvent(Base, UUIDPKMixin, TimestampMixin):
    """Maintenance activity on a machine."""
    __tablename__ = "maintenance_events"

    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id"), nullable=False
    )
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id")
    )
    maintenance_type: Mapped[MaintenanceType] = mapped_column(
        Enum(MaintenanceType), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_hours: Mapped[Optional[float]] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(Text)
    technician: Mapped[Optional[str]] = mapped_column(String(200))
    components_replaced: Mapped[Optional[List[str]]] = mapped_column(JSON)
    work_order: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    machine: Mapped["Machine"] = relationship(back_populates="maintenance_events")

    __table_args__ = (
        Index("ix_me_machine_time", "machine_id", "start_time"),
        Index("ix_me_type", "maintenance_type"),
    )


class ProcessChange(Base, UUIDPKMixin, TimestampMixin):
    """A change to a process recipe, parameters, or procedure."""
    __tablename__ = "process_changes"

    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processes.id"), nullable=False
    )
    machine_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id")
    )
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id")
    )
    change_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    change_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # parameter_adjustment | recipe_change | equipment_swap | procedure_update
    parameter_name: Mapped[Optional[str]] = mapped_column(String(200))
    old_value: Mapped[Optional[str]] = mapped_column(String(500))
    new_value: Mapped[Optional[str]] = mapped_column(String(500))
    changed_by: Mapped[Optional[str]] = mapped_column(String(200))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    approved_by: Mapped[Optional[str]] = mapped_column(String(200))

    process: Mapped["Process"] = relationship(back_populates="process_changes")

    __table_args__ = (Index("ix_pc_process_time", "process_id", "change_time"),)


class QualityInspection(Base, UUIDPKMixin, TimestampMixin):
    """Quality inspection result for a batch."""
    __tablename__ = "quality_inspections"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False
    )
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id")
    )
    inspection_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    inspector: Mapped[Optional[str]] = mapped_column(String(200))
    result: Mapped[InspectionResult] = mapped_column(
        Enum(InspectionResult), nullable=False
    )
    defect_count: Mapped[Optional[int]] = mapped_column(Integer)
    defect_rate: Mapped[Optional[float]] = mapped_column(Float)
    defect_types: Mapped[Optional[List[str]]] = mapped_column(JSON)
    measurements: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    # key: measurement_name → value
    notes: Mapped[Optional[str]] = mapped_column(Text)

    batch: Mapped["Batch"] = relationship(back_populates="quality_inspections")

    __table_args__ = (
        Index("ix_qi_batch", "batch_id"),
        Index("ix_qi_result", "result"),
        Index("ix_qi_time", "inspection_time"),
    )


class FailureEvent(Base, UUIDPKMixin, TimestampMixin):
    """A detected failure or significant quality/operational event."""
    __tablename__ = "failure_events"

    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.id")
    )
    machine_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id")
    )
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id")
    )
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # quality_failure | machine_failure | process_deviation | yield_loss
    severity: Mapped[FailureSeverity] = mapped_column(
        Enum(FailureSeverity), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_quantity: Mapped[Optional[float]] = mapped_column(Float)
    downtime_hours: Mapped[Optional[float]] = mapped_column(Float)
    detected_by: Mapped[Optional[str]] = mapped_column(String(200))
    root_cause_label: Mapped[Optional[str]] = mapped_column(String(500))
    # Ground-truth label for evaluation (only in synthetic datasets)
    is_synthetic_ground_truth: Mapped[bool] = mapped_column(Boolean, default=False)

    batch: Mapped[Optional["Batch"]] = relationship(back_populates="failure_events")
    machine: Mapped[Optional["Machine"]] = relationship(back_populates="failure_events")
    investigations: Mapped[List["Investigation"]] = relationship(
        back_populates="failure_event"
    )

    __table_args__ = (
        Index("ix_fe_machine_time", "machine_id", "event_time"),
        Index("ix_fe_event_time", "event_time"),
        Index("ix_fe_severity", "severity"),
    )


# ============================================================
# Investigation Models
# ============================================================

class Dataset(Base, UUIDPKMixin, TimestampMixin):
    """Uploaded or generated dataset."""
    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # upload | synthetic | public
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    record_count: Mapped[Optional[int]] = mapped_column(Integer)
    time_range_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    time_range_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    schema_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    quality_report: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False)

    batches: Mapped[List["Batch"]] = relationship(back_populates="dataset")
    investigations: Mapped[List["Investigation"]] = relationship(
        back_populates="dataset"
    )


class Investigation(Base, UUIDPKMixin, TimestampMixin):
    """A failure investigation instance."""
    __tablename__ = "investigations"

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False
    )
    failure_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("failure_events.id")
    )
    machine_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id")
    )

    # Time window for the investigation
    analysis_start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    analysis_end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus), default=InvestigationStatus.PENDING, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Configuration used for this run
    config_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    # Summary from LLM (generated last)
    llm_summary: Mapped[Optional[str]] = mapped_column(Text)

    dataset: Mapped["Dataset"] = relationship(back_populates="investigations")
    failure_event: Mapped[Optional["FailureEvent"]] = relationship(
        back_populates="investigations"
    )
    candidate_mechanisms: Mapped[List["CandidateMechanism"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_inv_dataset", "dataset_id"),
        Index("ix_inv_status", "status"),
    )


class CandidateMechanism(Base, UUIDPKMixin, TimestampMixin):
    """A discovered candidate failure mechanism for an investigation."""
    __tablename__ = "candidate_mechanisms"

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investigations.id"), nullable=False
    )
    mechanism_type: Mapped[MechanismType] = mapped_column(
        Enum(MechanismType), nullable=False
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Structured mechanism representation
    cause: Mapped[Optional[str]] = mapped_column(String(500))
    process_condition: Mapped[Optional[str]] = mapped_column(String(500))
    intermediate_effect: Mapped[Optional[str]] = mapped_column(String(500))
    observable_failure: Mapped[Optional[str]] = mapped_column(String(500))
    entities_involved: Mapped[Optional[List[str]]] = mapped_column(JSON)
    variables_involved: Mapped[Optional[List[str]]] = mapped_column(JSON)
    temporal_conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    expected_effects: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # Discovery metadata
    discovery_method: Mapped[Optional[str]] = mapped_column(String(100))
    # temporal_association | graph_traversal | changepoint | event_sequence

    # Scoring
    rank: Mapped[Optional[int]] = mapped_column(Integer)
    overall_score: Mapped[Optional[float]] = mapped_column(Float)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    temporal_consistency_score: Mapped[Optional[float]] = mapped_column(Float)
    evidence_strength_score: Mapped[Optional[float]] = mapped_column(Float)
    evidence_coverage_score: Mapped[Optional[float]] = mapped_column(Float)
    recurrence_score: Mapped[Optional[float]] = mapped_column(Float)
    plausibility_score: Mapped[Optional[float]] = mapped_column(Float)
    contradiction_penalty: Mapped[Optional[float]] = mapped_column(Float)

    # Evidence summary (denormalized for display)
    supporting_evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    contradicting_evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_evidence_count: Mapped[int] = mapped_column(Integer, default=0)

    # LLM-generated explanation
    llm_explanation: Mapped[Optional[str]] = mapped_column(Text)

    investigation: Mapped["Investigation"] = relationship(
        back_populates="candidate_mechanisms"
    )
    evidence_items: Mapped[List["MechanismEvidence"]] = relationship(
        back_populates="mechanism", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_cm_investigation", "investigation_id"),
        Index("ix_cm_rank", "investigation_id", "rank"),
    )


class MechanismEvidence(Base, UUIDPKMixin, TimestampMixin):
    """A specific piece of evidence (supporting or contradicting) for a mechanism."""
    __tablename__ = "mechanism_evidence"

    mechanism_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_mechanisms.id"), nullable=False
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType), nullable=False
    )
    polarity: Mapped[EvidencePolarity] = mapped_column(
        Enum(EvidencePolarity), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    # 0.0 to 1.0

    # Traceable source references
    source_table: Mapped[Optional[str]] = mapped_column(String(100))
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    source_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Quantitative details
    measured_value: Mapped[Optional[float]] = mapped_column(Float)
    expected_value: Mapped[Optional[float]] = mapped_column(Float)
    deviation: Mapped[Optional[float]] = mapped_column(Float)
    statistical_significance: Mapped[Optional[float]] = mapped_column(Float)

    # Temporal info
    event_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lag_hours: Mapped[Optional[float]] = mapped_column(Float)
    # hours before the failure event

    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON)

    mechanism: Mapped["CandidateMechanism"] = relationship(
        back_populates="evidence_items"
    )

    __table_args__ = (
        Index("ix_me_mechanism", "mechanism_id"),
        Index("ix_me_polarity", "polarity"),
        Index("ix_me_type", "evidence_type"),
    )


# ============================================================
# Research / Experiment Models
# ============================================================

class Experiment(Base, UUIDPKMixin, TimestampMixin):
    """A research experiment (baseline comparison, ablation, robustness test)."""
    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    experiment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # baseline | ablation | robustness | full_system
    description: Mapped[Optional[str]] = mapped_column(Text)
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id")
    )
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    random_seed: Mapped[int] = mapped_column(Integer, default=42)

    results: Mapped[List["ExperimentResult"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )


class ExperimentResult(Base, UUIDPKMixin, TimestampMixin):
    """Metric results from a single experiment run."""
    __tablename__ = "experiment_results"

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    experiment: Mapped["Experiment"] = relationship(back_populates="results")

    __table_args__ = (Index("ix_er_experiment", "experiment_id"),)
