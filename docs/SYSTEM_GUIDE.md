# IFMD Platform: Comprehensive System & Engineering Guide

## 1. Overview
The **Industrial Failure Mechanism Discovery (IFMD)** platform is a full-stack, software-only AI architecture designed for investigating why industrial failures occur by discovering and ranking competing failure mechanisms from heterogeneous temporal data.

---

## 2. Directory Structure & Architecture

```
industrial-failure-mechanism-discovery/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # FastAPI REST endpoints
│   │   │   ├── health.py        # System health & DB connection status
│   │   │   ├── datasets.py      # Dataset listing & inspection
│   │   │   ├── data_upload.py   # Upload & synthetic data generation
│   │   │   ├── investigations.py# Investigation pipeline orchestration
│   │   │   ├── mechanisms.py    # Candidate mechanism details & evidence
│   │   │   └── evaluation.py    # Research benchmarking endpoints
│   │   ├── core/                # Configuration, DB engine, structured logging
│   │   ├── graph/               # NetworkX heterogeneous graph builder
│   │   ├── mechanisms/          # Candidate mechanism discovery & templates
│   │   ├── ml/                  # Feature extractors & baseline models
│   │   │   ├── baselines/       # Isolation Forest, Random Forest, Correlation RCA
│   │   │   └── features/        # Multi-scale rolling & lag feature extraction
│   │   ├── models/              # SQLAlchemy async relational models
│   │   ├── ranking/             # Multi-factor objective ranking & penalties
│   │   ├── services/            # Ingestion, investigation, evaluation orchestration
│   │   ├── temporal/            # Ruptures change-point detection & cross-correlation
│   │   └── explainability/      # Grounded LLM report synthesis
│   ├── migrations/              # Alembic database migration scripts
│   └── tests/                   # Pytest unit and integration test suite
├── frontend/                    # React 18 + TypeScript + Vite + Tailwind dashboard
│   ├── src/
│   │   ├── components/          # Reusable UI cards, badges, charts, layout
│   │   ├── pages/               # 10 engineering dashboard views
│   │   ├── services/            # Axios API client
│   │   └── types/               # TypeScript interface schemas
├── research/                    # Empirical evaluation, ablations, and baselines
│   ├── baselines/               # Scripts to benchmark baseline models
│   ├── ablations/               # Controlled ablation experiment runners
│   ├── evaluation/              # IR & ranking metrics (NDCG@K, MRR)
│   ├── experiments/             # Multi-trial automated benchmark harness
│   └── results/                 # Publication-ready tables and plots
├── scripts/                     # Standalone CLI tools for data generation & experiments
└── docs/                        # Research paper, system guide, and API reference
```

---

## 3. Getting Started & Installation

### 3.1 Backend Setup
Requirements: Python 3.10+ and PostgreSQL (or Docker).

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp ../.env.example .env
# Edit .env with your PostgreSQL credentials
```

### 3.2 Database Initialization
Using Docker Compose for PostgreSQL:
```bash
docker-compose up -d postgres
```

Run database migrations:
```bash
cd backend
alembic upgrade head
```

### 3.3 Start the FastAPI Backend Server
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API docs are available at `http://localhost:8000/api/docs`.

### 3.4 Frontend Setup
Requirements: Node.js 18+ and npm.

```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 4. End-to-End Workflow

1. **Synthesize or Ingest Data:**
   - Go to `http://localhost:5173/upload`.
   - Click "Generate & Ingest Benchmark Dataset" with 500 batches.
   - Or upload a custom CSV/JSON/Parquet containing machine telemetry.
2. **Launch an Investigation:**
   - Go to `http://localhost:5173/investigations`.
   - Click "New Investigation", select the generated dataset, specify the time window, and click "Create & Run Pipeline".
3. **Inspect Discovered Hypotheses:**
   - View ranked candidate mechanisms ordered by multi-factor score.
   - Click "Full Analysis" to review physical causal steps (Root Cause $\rightarrow$ Process Condition $\rightarrow$ Intermediate State $\rightarrow$ Observable Failure).
   - Click "Evidence Explorer" to verify individual supporting and contradicting records.
4. **Explore the Relationship Graph & Timeline:**
   - Switch to "Timeline" to see the chronological chain of events.
   - Switch to "Relationship Graph" to inspect multi-hop machine-batch-material-sensor dependencies.
5. **Run Research Evaluation:**
   - Navigate to `http://localhost:5173/evaluation`.
   - Trigger benchmark evaluation comparing the full pipeline against Isolation Forest, Random Forest, and Ablations.

---

## 5. Running Tests & Benchmarks

Run backend unit and integration tests:
```bash
cd backend
pytest tests/ -v
```

Run research benchmark suite:
```bash
python scripts/run_research_benchmark.py --trials 5 --batches 300
```
Review generated tables at `research/results/tables/benchmark_results.md`.
