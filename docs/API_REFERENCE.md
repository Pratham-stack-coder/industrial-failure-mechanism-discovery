# IFMD Platform: API Reference Manual

The IFMD platform provides a fully typed asynchronous REST API powered by FastAPI.
All JSON request and response payloads adhere to strict Pydantic schemas.

Base URL: `/api`

---

## 1. System Health

### `GET /api/health`
Check application and database health status.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "app_name": "Industrial Failure Mechanism Discovery",
  "version": "0.1.0",
  "database": "connected"
}
```

---

## 2. Dataset Management

### `GET /api/data/datasets`
List registered datasets.
- Query params: `skip` (int, default 0), `limit` (int, default 20)

**Response `200 OK`:**
```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Synthetic Benchmark Run",
    "description": "5 embedded physical mechanisms",
    "source_type": "synthetic",
    "record_count": 500,
    "time_range_start": "2024-01-01T00:00:00Z",
    "time_range_end": "2024-01-30T00:00:00Z",
    "is_validated": true,
    "created_at": "2024-01-30T12:00:00Z"
  }
]
```

### `POST /api/data/generate`
Synthesizes an industrial benchmark dataset with ground-truth failure mechanisms and ingests it into relational tables.
- Form data: `n_batches` (int, default 500), `random_seed` (int, default 42)

**Response `200 OK`:**
```json
{
  "dataset_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Synthetic Dataset (seed=42, batches=500)",
  "output_dir": "./data/synthetic/run_42",
  "ingestion_stats": {
    "total_records": 500,
    "machines": 4,
    "batches": 500,
    "failures": 42
  },
  "message": "Synthetic dataset generated and ingested."
}
```

### `POST /api/data/upload`
Upload custom CSV, JSON, or Parquet dataset file.
- Form multipart: `file` (binary), `name` (string), `description` (optional string)

---

## 3. Failure Investigations

### `POST /api/investigations`
Create a new investigation record for a dataset and temporal analysis window.

**Request Body:**
```json
{
  "name": "Investigation - Line 2 Spindle Overheat Excursion",
  "description": "Dimensional failures observed across Batch 102 to 105",
  "dataset_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "analysis_start_time": "2024-01-10T00:00:00Z",
  "analysis_end_time": "2024-01-15T00:00:00Z"
}
```

### `POST /api/investigations/{id}/run`
Trigger the asynchronous discovery and ranking pipeline.
- Performs temporal feature extraction.
- Constructs the heterogeneous entity-event graph.
- Discovers candidate causal chains.
- Gathers supporting, contradicting, and missing evidence.
- Ranks hypotheses using multi-factor objective scoring.

### `GET /api/investigations/{id}/mechanisms`
Retrieve ranked candidate mechanism hypotheses for an investigation.

**Response `200 OK`:**
```json
{
  "investigation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "total": 5,
  "mechanisms": [
    {
      "id": "7ca85f64-5717-4562-b3fc-2c963f66afa6",
      "rank": 1,
      "name": "Cooling System Degradation",
      "mechanism_type": "thermal",
      "overall_score": 0.885,
      "confidence": 0.85,
      "cause": "Coolant flow restriction",
      "process_condition": "Continuous high-load milling",
      "intermediate_effect": "Spindle thermal elevation",
      "observable_failure": "Dimensional tolerance excursion",
      "temporal_consistency_score": 0.92,
      "evidence_strength_score": 0.86,
      "evidence_coverage_score": 0.84,
      "contradiction_penalty": 0.04,
      "supporting_evidence_count": 8,
      "contradicting_evidence_count": 0,
      "missing_evidence_count": 1
    }
  ]
}
```

### `GET /api/investigations/{id}/timeline`
Retrieve reconstructed chronological event sequence.

### `GET /api/investigations/{id}/graph`
Retrieve heterogeneous entity-event graph in JSON node-link format.

---

## 4. Mechanism & Evidence Inspection

### `GET /api/mechanisms/{id}`
Retrieve full details and physics breakdown of a specific candidate mechanism.

### `GET /api/mechanisms/{id}/evidence`
Retrieve individual evidence records.
- Query params: `polarity` (`supporting`, `contradicting`, `missing`, `inconclusive`)

---

## 5. Research Evaluation

### `POST /api/evaluation/evaluate`
Launch an empirical evaluation benchmark comparing against ground truth.

**Request Body:**
```json
{
  "dataset_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "experiment_type": "full_system",
  "description": "Validation against 500-batch benchmark"
}
```

### `GET /api/evaluation/results`
Retrieve historical benchmark experiment metrics (NDCG@5, MRR, Precision@K).
