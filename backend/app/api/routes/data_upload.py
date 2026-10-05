"""
Data upload routes — CSV/JSON ingestion pipeline.
POST /api/data/upload       — upload a CSV dataset
POST /api/data/generate     — generate synthetic dataset
GET  /api/data/datasets     — list datasets
"""

import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import Dataset
from app.services.data_ingestion import DataIngestionService

router = APIRouter()

ALLOWED_EXTENSIONS = {".csv", ".json", ".parquet"}
MAX_SIZE = settings.max_upload_size_bytes


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV/JSON/Parquet dataset for analysis.
    The file is validated, quality-checked, and ingested into the database.
    """
    # Validate file extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"File type '{suffix}' not supported. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # Read content
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size ({len(content)//1024//1024}MB) exceeds limit ({settings.max_upload_size_mb}MB)",
        )

    # Parse
    try:
        if suffix == ".csv":
            df = pd.read_csv(io.BytesIO(content))
        elif suffix == ".json":
            df = pd.read_json(io.BytesIO(content))
        elif suffix == ".parquet":
            df = pd.read_parquet(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")

    if df.empty:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    # Save file
    save_dir = Path(settings.data_dir) / "raw"
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / f"{uuid.uuid4()}_{file.filename}"
    file_path.write_bytes(content)

    # Quality report
    quality_report = {
        "n_rows": len(df),
        "n_columns": len(df.columns),
        "columns": list(df.columns),
        "missing_pct": {col: round(df[col].isna().mean() * 100, 2) for col in df.columns},
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }

    # Create dataset record
    dataset = Dataset(
        name=name,
        description=description,
        source_type="upload",
        file_path=str(file_path),
        record_count=len(df),
        schema_info={"columns": list(df.columns)},
        quality_report=quality_report,
        is_validated=True,
    )
    db.add(dataset)
    await db.flush()
    await db.refresh(dataset)

    logger.info(f"Dataset uploaded: {dataset.id} ({len(df)} rows)")
    return {
        "dataset_id": str(dataset.id),
        "name": dataset.name,
        "record_count": len(df),
        "quality_report": quality_report,
        "message": "Dataset uploaded successfully. Use /api/investigations to create an investigation.",
    }


@router.post("/generate")
async def generate_synthetic_dataset(
    n_batches: int = Form(500),
    random_seed: int = Form(42),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a synthetic industrial dataset with hidden failure mechanisms.
    The dataset is persisted to disk and registered in the database.
    """
    from app.services.synthetic_generator import SyntheticDataGenerator, GeneratorConfig
    from app.services.data_ingestion import DataIngestionService

    config = GeneratorConfig(
        n_batches=n_batches,
        random_seed=random_seed,
    )
    gen = SyntheticDataGenerator(config=config)

    output_dir = str(Path(settings.data_dir) / "synthetic" / f"run_{uuid.uuid4().hex[:8]}")
    gen.save(output_dir=output_dir)

    # Create dataset record
    dataset = Dataset(
        name=f"Synthetic Dataset (seed={random_seed}, batches={n_batches})",
        description=(
            "Synthetically generated industrial dataset with 5 hidden failure mechanisms: "
            "cooling degradation, material contamination, wear acceleration, "
            "process drift, and thermal expansion."
        ),
        source_type="synthetic",
        file_path=output_dir,
        record_count=n_batches,
        schema_info={"synthetic": True, "n_mechanisms": 5},
        quality_report={"generated": True, "random_seed": random_seed},
        is_validated=True,
    )
    db.add(dataset)
    await db.flush()

    # Ingest into database tables
    ingestion = DataIngestionService(db)
    stats = await ingestion.ingest_synthetic(output_dir=output_dir, dataset_id=str(dataset.id))

    await db.refresh(dataset)
    dataset.record_count = stats.get("total_records", n_batches)

    logger.info(f"Synthetic dataset generated: {dataset.id}")
    return {
        "dataset_id": str(dataset.id),
        "name": dataset.name,
        "output_dir": output_dir,
        "ingestion_stats": stats,
        "message": "Synthetic dataset generated and ingested. Use /api/investigations to investigate.",
    }
