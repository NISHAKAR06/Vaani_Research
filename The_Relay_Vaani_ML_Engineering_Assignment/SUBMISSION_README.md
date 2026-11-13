---
noteId: "6e911cc0df6911f1a06925f0c8d49965"
tags: []

---

# The Relay — Vaani Research ML Engineering Intern Submission
**Candidate:** Nishakar T.  
**Role:** ML Engineering Intern  
**Company:** Vaani Research  
**Project:** The Relay — Observable, Resilient, Citation-Grounded RAG System  
**Repository Date:** November 2026  

---

## 1. Project Overview

The Relay is an end-to-end, measurable, and resilient ML engineering system designed to serve technical queries strictly from a curated 3-paper arXiv library:
1. *Attention Is All You Need* (arXiv:1706.03762v7)
2. *Moshi: a speech-text foundation model for real-time dialogue* (arXiv:2410.00037v1)
3. *Dynamic Chunking for End-to-End Hierarchical Sequence Modeling* (arXiv:2507.07955v2)

The system couples a 5-stage orchestration pipeline (**Query Analyzer**, **Retrieval Tool Call**, **Evidence Validator**, **Answer Generator**, and **Citation Verifier**) with an admission controller (bounded queue, concurrency semaphore, circuit breaker) and dual provider backends (real **Groq Cloud API** and a calibrated **Stand-in Model Service**).

---

## 2. Directory Structure

```text
The_Relay_Vaani_ML_Engineering_Assignment/
│
├── 01_Assignment_Report/
│   └── assignment_report.pdf           <- Exact 2-page report adhering to all required headings
│
├── 02_Source_Code/                     <- Complete clean source code (no pycache, no virtualenvs)
│   ├── src/
│   │   ├── api/                        <- FastAPI gateway (port 8000)
│   │   ├── pipeline/                   <- 5-stage pipeline orchestrator
│   │   ├── retrieval/                  <- PyMuPDF loader, chunker, FAISS vector store, reranker
│   │   ├── providers/                  <- GroqProvider and SimulatorProvider
│   │   ├── simulator/                  <- Stand-in model service (port 8001)
│   │   ├── resilience/                 <- Admission control, bounded queue, retry policy, circuit breaker
│   │   ├── observability/              <- Metrics, percentiles, and JSONL event tracing
│   │   └── evaluation/                 <- 18-question ground truth dataset and grading harness
│   ├── config/                         <- Settings, experiment, and simulator configurations
│   ├── scripts/                        <- Ingestion, calibration, load test, and report scripts
│   ├── tests/                          <- 14 unit and integration tests
│   ├── requirements.txt
│   ├── README.md
│   └── .env.example
│
├── 03_Research_Papers/                 <- Exact 3 arXiv PDFs
│   ├── attention_is_all_you_need_v7.pdf (1706.03762v7, 15 pages)
│   ├── moshi_v1.pdf                     (2410.00037v1, 66 pages)
│   └── dynamic_chunking_v2.pdf          (2507.07955v2, 39 pages)
│
├── 04_Retrieval_Artifacts/             <- Ingestion metadata and pre-built vector indices
│   ├── paper_metadata.json             <- Checksums, page counts, and extraction timestamps
│   └── index/                          <- FAISS indices and chunk JSONs for Settings A, B, and C
│
├── 05_Experimental_Results/            <- Empirical benchmark deliverables
│   ├── results.csv                     <- Single source of truth (126 validated records)
│   ├── results_tables.md               <- Tables 1, 2a, 2b, 3 computed directly from results.csv
│   ├── real_calibration/               <- Groq calibration summary and raw observations
│   ├── standin_load_tests/             <- Raw load test metrics across 5 scenarios
│   └── retrieval_evaluation/           <- Accuracy and latency metrics across Settings A, B, and C
│
├── 06_Experiment_Logs/                 <- Audit logs
│   ├── real_service/                   <- Real calibration event logs
│   ├── simulator/                      <- Stand-in model service runtime logs
│   └── raw_request_logs/               <- request_events.jsonl containing full latency decompositions
│
├── 07_Assistant_History/               <- Prompt logs, overruled decisions, candidate reflections
│   └── assistant_conversation_history.md
│
├── 08_Test_Reports/                    <- Comprehensive test suite execution evidence
│   └── test_report.md
│
└── SUBMISSION_README.md                <- This release manifest
```

---

## 3. Technology Stack

- **Language:** Python 3.11 (`cpython-3.11.15-windows-x86_64`)
- **Web Services:** FastAPI, Uvicorn, HTTPX, AsyncIO
- **Model Providers:** Groq Python SDK (llama-3.3-70b-versatile) & Stand-in FastAPI Service
- **Document Processing:** PyMuPDF (`fitz`) for two-column academic PDF text and bounding-box extraction
- **Vector Search & RAG:** Sentence-Transformers (`all-MiniLM-L6-v2`), FAISS (`IndexFlatIP`), hybrid Reciprocal Rank Fusion (RRF) reranker
- **Data Validation & Schemas:** Pydantic v2, Pydantic-Settings, PyYAML
- **Data Analysis & Percentiles:** Pandas, NumPy (linear interpolation percentiles)
- **PDF Publishing:** ReportLab 5.1.0
- **Testing:** Pytest, Pytest-AsyncIO

---

## 4. How to Run the Project & Reproduce Experiments

### Step 1: Environment Setup
```bash
# Inside 02_Source_Code/
uv venv .venv --python 3.11
.venv\Scripts\activate       # Windows
# source .venv/bin/activate    # Linux/macOS

uv pip install -r requirements.txt
cp .env.example .env
```
*(Optional: Insert `GROQ_API_KEY=gsk_...` in `.env` if testing real Groq calls. If omitted, the system runs completely offline in Stand-in mode without error).*

### Step 2: Paper Ingestion & Index Generation
```bash
python scripts/ingest_papers.py
python scripts/build_retrieval_index.py
```

### Step 3: Run the Stand-in Model Service (Port 8001)
```bash
python -m uvicorn src.simulator.app:app --port 8001
```

### Step 4: Run the Main Gateway API (Port 8000)
```bash
python -m uvicorn src.api.main:app --port 8000
```

### Step 5: Execute Evaluation & Load Benchmarks
```bash
# Evaluate 18 ground-truth questions across Settings A, B, C
python scripts/evaluate_retrieval.py

# Execute 5 load test shapes (Steady, Burst, Overload, Halved Limit, Daily Exhausted)
python scripts/run_load_tests.py

# Compile and strictly validate outputs/results.csv
python scripts/generate_results.py

# Generate report tables and 2-page PDF
python scripts/generate_report.py
python scripts/generate_pdf_report.py
```

### Step 6: Run Tests
```bash
pytest -v
```

---

## 5. Primary Deliverables Location

- **Results CSV:** `05_Experimental_Results/results.csv` (126 rows, 12 exact required columns).
- **Two-Page PDF Report:** `01_Assignment_Report/assignment_report.pdf` (Strictly 2 pages, verified by PyMuPDF).
- **Results Tables:** `05_Experimental_Results/results_tables.md` (Tables 1, 2a, 2b, 3 matching `results.csv`).
- **Assistant Conversation History:** `07_Assistant_History/assistant_conversation_history.md`.

---

## 6. Known Limitations

1. **Free-Tier Header Limits:** Groq Cloud's free tier surfaces RPM and TPM in response headers, but does not surface daily token usage (TPD) in response headers; TPD was therefore marked *"not measured"* in Table 1 in strict adherence to ground rules.
2. **Concurrency Detection:** Groq does not publish an official concurrency ceiling; an effective limit of ~5 concurrent requests was empirically observed.
3. **Offline Reranking:** Cross-encoder reranking falls back to hybrid dense vector similarity fused with term-frequency reciprocal rank scoring when running in air-gapped/offline mode to eliminate unauthenticated HuggingFace hub download delays.
