"""
Data Ingestion Service
=======================
Reads generated CSV files and persists them to the database.
Used after synthetic generation or CSV upload.
"""

import uuid
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Batch,
    BatchMaterialLot,
    EnvironmentalCondition,
    FailureEvent,
    FailureSeverity,
    InspectionResult,
    Machine,
    MachineStatus,
    MaintenanceEvent,
    MaintenanceType,
    Material,
    MaterialLot,
    Operator,
    ParameterDefinition,
    ParameterMeasurement,
    Process,
    ProcessChange,
    Product,
    QualityInspection,
)


class DataIngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_synthetic(
        self, output_dir: str, dataset_id: str
    ) -> Dict[str, int]:
        """Ingest all CSV files from a synthetic generation output directory."""
        path = Path(output_dir)
        ds_uid = uuid.UUID(dataset_id)
        stats: Dict[str, int] = {}

        logger.info(f"Ingesting synthetic dataset from {path}")

        # Order matters due to FK constraints
        for table_name, ingestor in [
            ("machines", self._ingest_machines),
            ("products", self._ingest_products),
            ("materials", self._ingest_materials),
            ("material_lots", self._ingest_material_lots),
            ("operators", self._ingest_operators),
            ("processes", self._ingest_processes),
            ("parameter_definitions", self._ingest_param_defs),
            ("batches", self._ingest_batches),
            ("batch_material_lots", self._ingest_batch_lots),
            ("maintenance_events", self._ingest_maintenance),
            ("process_changes", self._ingest_process_changes),
            ("quality_inspections", self._ingest_quality),
            ("failure_events", self._ingest_failure_events),
            ("environmental_conditions", self._ingest_env_conditions),
            ("parameter_measurements", self._ingest_measurements),
        ]:
            csv_path = path / f"{table_name}.csv"
            if not csv_path.exists():
                logger.debug(f"Skipping {table_name} (file not found)")
                continue

            df = pd.read_csv(csv_path)
            if df.empty:
                continue

            try:
                count = await ingestor(df, ds_uid)
                stats[table_name] = count
                logger.info(f"Ingested {count} {table_name}")
            except Exception as e:
                logger.warning(f"Failed to ingest {table_name}: {e}")

        stats["total_records"] = sum(stats.values())
        return stats

    def _parse_uuid(self, val) -> uuid.UUID:
        if isinstance(val, uuid.UUID):
            return val
        return uuid.UUID(str(val))

    def _safe_float(self, val) -> float | None:
        try:
            f = float(val)
            return None if pd.isna(f) else f
        except (TypeError, ValueError):
            return None

    def _safe_str(self, val) -> str | None:
        if pd.isna(val) if not isinstance(val, str) else False:
            return None
        return str(val) if val else None

    async def _ingest_machines(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            # Skip if already exists
            existing = await self.db.get(Machine, self._parse_uuid(row["id"]))
            if existing:
                continue
            m = Machine(
                id=self._parse_uuid(row["id"]),
                name=str(row["name"]),
                machine_code=str(row["machine_code"]),
                machine_type=str(row["machine_type"]),
                manufacturer=self._safe_str(row.get("manufacturer")),
                model_number=self._safe_str(row.get("model_number")),
                location=self._safe_str(row.get("location")),
                status=MachineStatus.OPERATIONAL,
            )
            self.db.add(m)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_products(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            existing = await self.db.get(Product, self._parse_uuid(row["id"]))
            if existing:
                continue
            p = Product(
                id=self._parse_uuid(row["id"]),
                name=str(row["name"]),
                product_code=str(row["product_code"]),
                product_family=self._safe_str(row.get("product_family")),
            )
            self.db.add(p)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_materials(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            existing = await self.db.get(Material, self._parse_uuid(row["id"]))
            if existing:
                continue
            m = Material(
                id=self._parse_uuid(row["id"]),
                name=str(row["name"]),
                material_code=str(row["material_code"]),
                material_type=str(row["material_type"]),
                supplier=self._safe_str(row.get("supplier")),
            )
            self.db.add(m)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_material_lots(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            existing = await self.db.get(MaterialLot, self._parse_uuid(row["id"]))
            if existing:
                continue
            lot = MaterialLot(
                id=self._parse_uuid(row["id"]),
                material_id=self._parse_uuid(row["material_id"]),
                lot_number=str(row["lot_number"]),
                received_date=pd.to_datetime(row.get("received_date"), utc=True, errors="coerce"),
                quantity=self._safe_float(row.get("quantity")),
                unit=self._safe_str(row.get("unit")),
                supplier_lot_number=self._safe_str(row.get("supplier_lot_number")),
            )
            self.db.add(lot)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_operators(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            existing = await self.db.get(Operator, self._parse_uuid(row["id"]))
            if existing:
                continue
            op = Operator(
                id=self._parse_uuid(row["id"]),
                name=str(row["name"]),
                operator_code=str(row["operator_code"]),
                shift=self._safe_str(row.get("shift")),
                certification_level=self._safe_str(row.get("certification_level")),
                department=self._safe_str(row.get("department")),
            )
            self.db.add(op)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_processes(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            existing = await self.db.get(Process, self._parse_uuid(row["id"]))
            if existing:
                continue
            p = Process(
                id=self._parse_uuid(row["id"]),
                name=str(row["name"]),
                process_code=str(row["process_code"]),
                process_type=str(row["process_type"]),
                description=self._safe_str(row.get("description")),
                version=str(row.get("version", "1.0")),
            )
            self.db.add(p)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_param_defs(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            existing = await self.db.get(ParameterDefinition, self._parse_uuid(row["id"]))
            if existing:
                continue
            p = ParameterDefinition(
                id=self._parse_uuid(row["id"]),
                name=str(row["name"]),
                parameter_code=str(row["parameter_code"]),
                unit=self._safe_str(row.get("unit")),
                nominal_value=self._safe_float(row.get("nominal_value")),
                lower_limit=self._safe_float(row.get("lower_limit")),
                upper_limit=self._safe_float(row.get("upper_limit")),
                critical_lower_limit=self._safe_float(row.get("critical_lower_limit")),
                critical_upper_limit=self._safe_float(row.get("critical_upper_limit")),
            )
            self.db.add(p)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_batches(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            existing = await self.db.get(Batch, self._parse_uuid(row["id"]))
            if existing:
                continue
            op_id = None
            if pd.notna(row.get("operator_id")):
                try:
                    op_id = self._parse_uuid(row["operator_id"])
                except Exception:
                    pass

            b = Batch(
                id=self._parse_uuid(row["id"]),
                batch_number=str(row["batch_number"]),
                machine_id=self._parse_uuid(row["machine_id"]),
                product_id=self._parse_uuid(row["product_id"]),
                process_id=self._parse_uuid(row["process_id"]),
                operator_id=op_id,
                dataset_id=dataset_id,
                start_time=pd.to_datetime(row["start_time"], utc=True),
                end_time=pd.to_datetime(row.get("end_time"), utc=True, errors="coerce"),
                planned_quantity=self._safe_float(row.get("planned_quantity")),
                actual_quantity=self._safe_float(row.get("actual_quantity")),
                unit=self._safe_str(row.get("unit")),
                is_defective=bool(row.get("is_defective", False)),
                defect_rate=self._safe_float(row.get("defect_rate")),
            )
            self.db.add(b)
            count += 1
            if count % 100 == 0:
                await self.db.flush()
        await self.db.flush()
        return count

    async def _ingest_batch_lots(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            bl = BatchMaterialLot(
                batch_id=self._parse_uuid(row["batch_id"]),
                material_lot_id=self._parse_uuid(row["material_lot_id"]),
                quantity_used=self._safe_float(row.get("quantity_used")),
                unit=self._safe_str(row.get("unit")),
            )
            self.db.add(bl)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_maintenance(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            try:
                mtype = MaintenanceType(str(row.get("maintenance_type", "preventive")))
            except ValueError:
                mtype = MaintenanceType.PREVENTIVE

            me = MaintenanceEvent(
                id=self._parse_uuid(row["id"]),
                machine_id=self._parse_uuid(row["machine_id"]),
                dataset_id=dataset_id,
                maintenance_type=mtype,
                start_time=pd.to_datetime(row["start_time"], utc=True),
                end_time=pd.to_datetime(row.get("end_time"), utc=True, errors="coerce"),
                duration_hours=self._safe_float(row.get("duration_hours")),
                description=self._safe_str(row.get("description")),
                technician=self._safe_str(row.get("technician")),
                work_order=self._safe_str(row.get("work_order")),
            )
            self.db.add(me)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_process_changes(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            pc = ProcessChange(
                id=self._parse_uuid(row["id"]),
                process_id=self._parse_uuid(row["process_id"]),
                machine_id=(
                    self._parse_uuid(row["machine_id"])
                    if pd.notna(row.get("machine_id"))
                    else None
                ),
                dataset_id=dataset_id,
                change_time=pd.to_datetime(row["change_time"], utc=True),
                change_type=str(row.get("change_type", "parameter_adjustment")),
                parameter_name=self._safe_str(row.get("parameter_name")),
                old_value=self._safe_str(row.get("old_value")),
                new_value=self._safe_str(row.get("new_value")),
                changed_by=self._safe_str(row.get("changed_by")),
                reason=self._safe_str(row.get("reason")),
                approved_by=self._safe_str(row.get("approved_by")),
            )
            self.db.add(pc)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_quality(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            try:
                result = InspectionResult(str(row.get("result", "pass")))
            except ValueError:
                result = InspectionResult.PENDING

            qi = QualityInspection(
                id=self._parse_uuid(row["id"]),
                batch_id=self._parse_uuid(row["batch_id"]),
                dataset_id=dataset_id,
                inspection_time=pd.to_datetime(row["inspection_time"], utc=True),
                inspector=self._safe_str(row.get("inspector")),
                result=result,
                defect_count=int(row.get("defect_count") or 0),
                defect_rate=self._safe_float(row.get("defect_rate")),
                notes=self._safe_str(row.get("notes")),
            )
            self.db.add(qi)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_failure_events(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            try:
                sev = FailureSeverity(str(row.get("severity", "moderate")))
            except ValueError:
                sev = FailureSeverity.MODERATE

            batch_id = None
            if pd.notna(row.get("batch_id")):
                try:
                    batch_id = self._parse_uuid(row["batch_id"])
                except Exception:
                    pass

            machine_id = None
            if pd.notna(row.get("machine_id")):
                try:
                    machine_id = self._parse_uuid(row["machine_id"])
                except Exception:
                    pass

            fe = FailureEvent(
                id=self._parse_uuid(row["id"]),
                batch_id=batch_id,
                machine_id=machine_id,
                dataset_id=dataset_id,
                event_time=pd.to_datetime(row["event_time"], utc=True),
                event_type=str(row.get("event_type", "quality_failure")),
                severity=sev,
                description=str(row.get("description", "")),
                affected_quantity=self._safe_float(row.get("affected_quantity")),
                downtime_hours=self._safe_float(row.get("downtime_hours")),
                detected_by=self._safe_str(row.get("detected_by")),
                root_cause_label=self._safe_str(row.get("root_cause_label")),
                is_synthetic_ground_truth=bool(row.get("is_synthetic_ground_truth", False)),
            )
            self.db.add(fe)
            count += 1
        await self.db.flush()
        return count

    async def _ingest_env_conditions(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        for _, row in df.iterrows():
            ec = EnvironmentalCondition(
                id=self._parse_uuid(row["id"]),
                machine_id=(
                    self._parse_uuid(row["machine_id"])
                    if pd.notna(row.get("machine_id"))
                    else None
                ),
                dataset_id=dataset_id,
                timestamp=pd.to_datetime(row["timestamp"], utc=True),
                ambient_temperature=self._safe_float(row.get("ambient_temperature")),
                ambient_humidity=self._safe_float(row.get("ambient_humidity")),
                ambient_pressure=self._safe_float(row.get("ambient_pressure")),
                vibration_level=self._safe_float(row.get("vibration_level")),
            )
            self.db.add(ec)
            count += 1
            if count % 500 == 0:
                await self.db.flush()
        await self.db.flush()
        return count

    async def _ingest_measurements(self, df: pd.DataFrame, dataset_id: uuid.UUID) -> int:
        count = 0
        chunk_size = 500

        for i in range(0, len(df), chunk_size):
            chunk = df.iloc[i : i + chunk_size]
            for _, row in chunk.iterrows():
                batch_id = None
                if pd.notna(row.get("batch_id")):
                    try:
                        batch_id = self._parse_uuid(row["batch_id"])
                    except Exception:
                        pass

                machine_id = None
                if pd.notna(row.get("machine_id")):
                    try:
                        machine_id = self._parse_uuid(row["machine_id"])
                    except Exception:
                        pass

                pm = ParameterMeasurement(
                    id=self._parse_uuid(row["id"]),
                    parameter_definition_id=self._parse_uuid(row["parameter_definition_id"]),
                    machine_id=machine_id,
                    batch_id=batch_id,
                    dataset_id=dataset_id,
                    timestamp=pd.to_datetime(row["timestamp"], utc=True),
                    value=float(row["value"]),
                    is_out_of_spec=bool(row.get("is_out_of_spec", False)),
                    is_anomalous=bool(row.get("is_anomalous", False)),
                    quality_flag=self._safe_str(row.get("quality_flag")),
                )
                self.db.add(pm)
                count += 1
            await self.db.flush()

        return count
