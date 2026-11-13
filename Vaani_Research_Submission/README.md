---
noteId: "c3b53640df6511f1a06925f0c8d49965"
tags: []

---

# The Relay — ML Systems Engineering Assignment
**Vaani Research | ML Engineering Assessment**

An observable, resilient, citation-grounded RAG orchestrator designed to serve technical queries strictly from a curated 3-paper arXiv library, featuring real Groq Cloud API integration, a calibrated Stand-in Model Service, admission control, load testing across 5 traffic shapes, and evidence-backed evaluation.

---

## 1. Project Overview & Architecture

The Relay implements an end-to-end 5-stage pipeline:
1. **Stage 1 (Query Analyzer)**: Extracts intent, identifies candidate papers, checks for cross-paper comparisons, and detects out-of-scope entities.
2. **Stage 2 (Retrieval Tool)**: Executes dense vector retrieval on FAISS indices with optional cross-scoring across Settings A (300tok/k=3), B (600tok/k=5), or C (900tok/k=5+rerank).
3. **Stage 3 (Evidence Validator)**: Evaluates similarity and entity alignment, branching into **Sufficient**, **Insufficient** (refusal), **Conflicting** (comparative synthesis), or **Invalid** (bounded re-retrieval).
4. **Stage 4 (Answer Generator)**: Solicits strict citation-grounded responses from the model provider (`GroqProvider` or `SimulatorProvider`).
5. **Stage 5 (Citation Verifier)**: Deterministically parses citations against retrieved metadata; executes a bounded refinement loop (max 2 iterations) before honest refusal.

```
+---------------------------------------------------------------------------------------+
|                                    THE RELAY                                          |
|                                                                                       |
|  [Client Query]                                                                       |
|         │                                                                             |
|         ▼                                                                             |
|  [Admission Controller] ─── (Bounded Queue: 20, Concurrency Semaphore: 5, Circuit Breaker)
|         │                                                                             |
|         ▼                                                                             |
|  [5-Stage Pipeline Orchestrator]                                                      |
|    ├── Stage 1: Query Analyzer (Intent, Target Papers, Cross-Paper Detection)        |
|    ├── Stage 2: Retrieval Tool Call (FAISS Dense Vector Index + Reranker)            |
|    ├── Stage 3: Evidence Validator (Sufficient / Insufficient Refusal / Retry Loop)  |
|    ├── Stage 4: Answer Generator (Grounded Prompting with Inline Citations)          |
|    └── Stage 5: Citation Verifier (Deterministic Page & Claim Check, Refinement)     |
|         │                                                                             |
|         ├──► [Groq API Provider]      (llama-3.3-70b-versatile, Rate-Limit Headers)   |
|         └──► [Stand-in Model Service] (FastAPI Port 8001: Calibrated Latency, 429s)   |
|                                                                                       |
|  [Observability Engine] ──► outputs/results.csv ──► outputs/results_tables.md         |
+---------------------------------------------------------------------------------------+
```

---

## 2. Curated Paper Library

The system is strictly bounded to exactly these three arXiv versions:
- **"Attention Is All You Need"** — [arXiv:1706.03762v7](https://arxiv.org/pdf/1706.03762v7) (15 pages, SHA256: `bdfaa68d...`)
- **"Moshi: a speech-text foundation model for real-time dialogue"** — [arXiv:2410.00037v1](https://arxiv.org/pdf/2410.00037v1) (66 pages, SHA256: `a687144c...`)
- **"Dynamic Chunking for End-to-End Hierarchical Sequence Modeling"** — [arXiv:2507.07955v2](https://arxiv.org/pdf/2507.07955v2) (39 pages, SHA256: `04a2b32e...`)

---

## 3. Prerequisites

- Python 3.11+
- Virtual environment tool (`uv` or `python -m venv`)
- Git

---

## 4. Setup Instructions

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/your-repo/the-relay.git
cd the-relay

# Using uv (fastest)
uv venv .venv --python 3.11
.venv\Scripts\activate   # On Windows
# source .venv/bin/activate  # On Linux/macOS

# Install dependencies
uv pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
To enable real Groq Cloud calls, paste your API key in `.env`:
```ini
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```
*(If no Groq key is provided, the system gracefully runs in Stand-in mode without crashing or faking measurements).*

---

## 5. Execution Workflow

### 1. Ingest Papers & Build Retrieval Indices
Downloads the 3 exact arXiv versions, extracts clean text blocks with PyMuPDF, and builds chunk indices for Settings A, B, and C:
```bash
python scripts/ingest_papers.py
python scripts/build_retrieval_index.py
```

### 2. Start the Stand-in Model Service (Port 8001)
Start the calibrated simulator in a separate terminal:
```bash
python -m uvicorn src.simulator.app:app --port 8001
```

### 3. Start the Main Relay API (Port 8000)
In another terminal, start the main gateway:
```bash
python -m uvicorn src.api.main:app --port 8000 --reload
```
Test query:
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"What scaling factor is used in scaled dot-product attention?\", \"retrieval_setting\": \"B\"}"
```

### 4. Run Real Service Calibration
Executes controlled requests against Groq to record observed latency and rate-limit headers:
```bash
python scripts/run_calibration.py
```

### 5. Run 18-Question Retrieval Evaluation
Evaluates all 18 ground-truth questions across Settings A, B, and C:
```bash
python scripts/evaluate_retrieval.py
```

### 6. Run the 5 Load Test Scenarios
Runs Steady, Burst, Sustained Overload, Halved RPM, and Daily Quota Exhaustion shapes:
```bash
python scripts/run_load_tests.py
```

### 7. Compile Results CSV & Validate Schema
```bash
python scripts/generate_results.py
```
Validates exact 12-column ordering, enums, and timestamps in `outputs/results.csv`.

### 8. Generate Final Results Tables & Assignment Report
```bash
python scripts/generate_report.py
```
Outputs:
- `outputs/results_tables.md` (Tables 1, 2a, 2b, 3)
- `writeup/assignment_report.md` (2-page report adhering to all 11 required headings)

### 9. Run the Test Suite
```bash
pytest -v
```

---

## 6. Output Files Summary

| File | Purpose |
|---|---|
| `outputs/results.csv` | Single source of truth containing 126 validated request records |
| `outputs/results_tables.md` | Tables 1, 2a, 2b, 3 calculated deterministically from raw data |
| `writeup/assignment_report.md` | Two-page written engineering report |
| `writeup/assistant_conversation_history.md` | Log of prompts, overruled decisions, and candidate reflections |
| `experiments/raw/request_events.jsonl` | Granular event-level timeline traces |
| `experiments/calibration/summary.json` | Empirical Groq rate-limit observations |

