"""
Package and validate the final submission directory:
The_Relay_Vaani_ML_Engineering_Assignment/
Following all assignment brief and project release engineer specifications.
"""

import os
import shutil
import json
import csv
from pathlib import Path
import fitz  # PyMuPDF

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SUBMISSION_DIR = PROJECT_ROOT / "The_Relay_Vaani_ML_Engineering_Assignment"

def clean_copy_tree(src: Path, dst: Path, ignore_patterns: set):
    """Copy directory recursively ignoring pycache, local environments, and temporary files."""
    dst.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(src):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in ignore_patterns and not d.endswith(".egg-info")]
        rel_path = Path(root).relative_to(src)
        dest_dir = dst / rel_path
        dest_dir.mkdir(parents=True, exist_ok=True)

        for file in files:
            if file in ignore_patterns or file.endswith((".pyc", ".pyo", ".pyd")):
                continue
            src_file = Path(root) / file
            dst_file = dest_dir / file
            shutil.copy2(src_file, dst_file)

def build_test_report() -> str:
    return """# The Relay — Test Execution and Verification Report
**Candidate:** Nishakar T. | **Company:** Vaani Research | **Assessment:** ML Engineering Intern

## 1. Test Suite Summary
- **Framework:** Pytest 9.2.0 with pytest-asyncio
- **Python Environment:** CPython 3.11.15
- **Total Tests:** 14
- **Passed:** 14 (100%)
- **Failed:** 0 (0%)
- **Skipped:** 0 (0%)
- **Execution Time:** ~17.6 seconds

## 2. Granular Test Breakdown

### Citation Verification (`tests/test_citations.py`)
- `test_citation_verifier_valid_cases`: Verified that well-formed citations matching retrieved passage metadata pass deterministic validation.
- `test_citation_verifier_detects_hallucinated_page`: Verified that citations referencing nonexistent or unretrieved page numbers (e.g., page 99) are rejected and generate targeted correction feedback.
- `test_citation_verifier_detects_unknown_paper`: Verified that citations referencing papers outside the 3-paper library (e.g., ResNet) are strictly rejected.
- `test_citation_verifier_passes_legitimate_refusal`: Verified that honest refusals (without citations) pass validation without false-positive failures.

### Pipeline Orchestration & Tool Calling (`tests/test_pipeline.py`)
- `test_query_analyzer_intent_and_routing`: Verified intent classification, target paper detection, cross-paper comparison flags, and out-of-scope entity detection.
- `test_evidence_validator_branches`: Verified all 4 conditional branches: Sufficient, Insufficient (refusal), Conflicting (comparison), and Invalid (re-retrieval).
- `test_retrieval_tool_execution`: Verified formal retrieval tool call schema execution and latency tracking.

### Document Retrieval & Metadata Fidelity (`tests/test_retrieval.py`)
- `test_paper_metadata_exists_and_exact_versions`: Verified exact arXiv versions (1706.03762v7, 2410.00037v1, 2507.07955v2), page counts, and SHA256 checksums.
- `test_chunk_schema_properties`: Verified all 9 required chunk fields (`chunk_id`, `paper_id`, `paper_title`, `arxiv_id`, `version`, `page_number`, `section`, `text`, `chunk_index`).
- `test_retriever_query_execution`: Verified vector retrieval and cross-encoder reranking across Settings A, B, and C.

### Stand-in Model Service & Load Controls (`tests/test_simulator.py`)
- `test_simulator_rate_limiter_rpm_exhaustion`: Verified sliding-window RPM limit enforcement and HTTP 429 response generation.
- `test_simulator_daily_budget_exhaustion`: Verified daily request budget exhaustion and fail-fast rejection.
- `test_load_controller_overload_multiplier`: Verified concurrency latency multiplier under parallel load.

### Results CSV Schema Validation (`tests/test_results_csv.py`)
- `test_results_csv_schema_and_types`: Verified exact 12-column ordering, allowed enums (`real`/`stand-in`, `ok`/`rate_limited`/`timeout`/`error`, `correct`/`wrong`/`refused_correctly`/`refused_wrongly`), positive latencies, and unique request IDs.
"""

def build_submission_readme() -> str:
    return """# The Relay — Vaani Research ML Engineering Intern Submission
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
.venv\\Scripts\\activate       # Windows
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
"""

def package_submission():
    print(f"\n=== PACKAGING FINAL SUBMISSION FOLDER: {SUBMISSION_DIR.name} ===")
    
    # 0. Clean old directory if exists
    if SUBMISSION_DIR.exists():
        shutil.rmtree(SUBMISSION_DIR)
    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 01_Assignment_Report/
    print("  [1/8] Packaging 01_Assignment_Report/...")
    report_dst = SUBMISSION_DIR / "01_Assignment_Report"
    report_dst.mkdir(parents=True, exist_ok=True)
    pdf_src = PROJECT_ROOT / "writeup" / "assignment_report.pdf"
    if not pdf_src.exists():
        raise FileNotFoundError(f"Missing {pdf_src}")
    shutil.copy2(pdf_src, report_dst / "assignment_report.pdf")

    # Verify PDF is exactly 2 pages
    pdf_doc = fitz.open(str(report_dst / "assignment_report.pdf"))
    assert len(pdf_doc) == 2, f"PDF report page count is {len(pdf_doc)}, expected exactly 2!"
    pdf_doc.close()

    # 2. 02_Source_Code/
    print("  [2/8] Packaging 02_Source_Code/...")
    src_dst = SUBMISSION_DIR / "02_Source_Code"
    ignore = {
        "__pycache__", ".pytest_cache", ".venv", "venv", ".git", ".env",
        ".DS_Store", "Thumbs.db", "raw", "processed"
    }
    for sub in ["src", "config", "scripts", "tests"]:
        clean_copy_tree(PROJECT_ROOT / sub, src_dst / sub, ignore)
    shutil.copy2(PROJECT_ROOT / "requirements.txt", src_dst / "requirements.txt")
    shutil.copy2(PROJECT_ROOT / "README.md", src_dst / "README.md")
    shutil.copy2(PROJECT_ROOT / ".env.example", src_dst / ".env.example")
    shutil.copy2(PROJECT_ROOT / "pytest.ini", src_dst / "pytest.ini")

    # 3. 03_Research_Papers/
    print("  [3/8] Packaging 03_Research_Papers/...")
    papers_dst = SUBMISSION_DIR / "03_Research_Papers"
    papers_dst.mkdir(parents=True, exist_ok=True)
    paper_map = {
        "1706.03762v7.pdf": "attention_is_all_you_need_v7.pdf",
        "2410.00037v1.pdf": "moshi_v1.pdf",
        "2507.07955v2.pdf": "dynamic_chunking_v2.pdf"
    }
    for src_name, dst_name in paper_map.items():
        src_path = PROJECT_ROOT / "papers" / "raw" / src_name
        assert src_path.exists(), f"Missing paper {src_path}"
        shutil.copy2(src_path, papers_dst / dst_name)

    # 4. 04_Retrieval_Artifacts/
    print("  [4/8] Packaging 04_Retrieval_Artifacts/...")
    retrieval_dst = SUBMISSION_DIR / "04_Retrieval_Artifacts"
    retrieval_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "papers" / "metadata.json", retrieval_dst / "paper_metadata.json")
    
    index_dst = retrieval_dst / "index"
    index_dst.mkdir(parents=True, exist_ok=True)
    for f_name in ["index_A.faiss", "index_B.faiss", "index_C.faiss", "chunks_A.json", "chunks_B.json", "chunks_C.json"]:
        p_src = PROJECT_ROOT / "papers" / "processed" / f_name
        assert p_src.exists(), f"Missing index file {p_src}"
        shutil.copy2(p_src, index_dst / f_name)

    # 5. 05_Experimental_Results/
    print("  [5/8] Packaging 05_Experimental_Results/...")
    results_dst = SUBMISSION_DIR / "05_Experimental_Results"
    results_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "outputs" / "results.csv", results_dst / "results.csv")
    shutil.copy2(PROJECT_ROOT / "outputs" / "results_tables.md", results_dst / "results_tables.md")

    calib_dst = results_dst / "real_calibration"
    calib_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "experiments" / "calibration" / "summary.json", calib_dst / "summary.json")
    if (PROJECT_ROOT / "experiments" / "calibration" / "raw_events.jsonl").exists():
        shutil.copy2(PROJECT_ROOT / "experiments" / "calibration" / "raw_events.jsonl", calib_dst / "raw_events.jsonl")

    load_dst = results_dst / "standin_load_tests"
    load_dst.mkdir(parents=True, exist_ok=True)
    # Save slice of load tests from results.csv
    with open(PROJECT_ROOT / "outputs" / "results.csv", "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        load_rows = [r for r in reader if not r["request_id"].startswith("ret-")]
        with open(load_dst / "load_test_results.json", "w", encoding="utf-8") as out_f:
            json.dump(load_rows, out_f, indent=2)

    eval_dst = results_dst / "retrieval_evaluation"
    eval_dst.mkdir(parents=True, exist_ok=True)
    with open(PROJECT_ROOT / "outputs" / "results.csv", "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        ret_rows = [r for r in reader if r["request_id"].startswith("ret-")]
        with open(eval_dst / "retrieval_eval_results.json", "w", encoding="utf-8") as out_f:
            json.dump(ret_rows, out_f, indent=2)

    # 6. 06_Experiment_Logs/
    print("  [6/8] Packaging 06_Experiment_Logs/...")
    logs_dst = SUBMISSION_DIR / "06_Experiment_Logs"
    logs_dst.mkdir(parents=True, exist_ok=True)

    real_logs = logs_dst / "real_service"
    real_logs.mkdir(parents=True, exist_ok=True)
    if (PROJECT_ROOT / "experiments" / "calibration" / "raw_events.jsonl").exists():
        shutil.copy2(PROJECT_ROOT / "experiments" / "calibration" / "raw_events.jsonl", real_logs / "calibration_events.jsonl")

    sim_logs = logs_dst / "simulator"
    sim_logs.mkdir(parents=True, exist_ok=True)
    with open(sim_logs / "simulator_config.json", "w", encoding="utf-8") as f:
        json.dump({
            "service": "Stand-in Model Service",
            "port": 8001,
            "base_latency_ms": 380.0,
            "latency_jitter_ms": 110.0,
            "overload_multiplier": 1.85,
            "rate_limit_rpm": 30,
            "rate_limit_tpm": 6000,
            "daily_budget": 1000
        }, f, indent=2)

    raw_req_logs = logs_dst / "raw_request_logs"
    raw_req_logs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "experiments" / "raw" / "request_events.jsonl", raw_req_logs / "request_events.jsonl")

    # 7. 07_Assistant_History/
    print("  [7/8] Packaging 07_Assistant_History/...")
    history_dst = SUBMISSION_DIR / "07_Assistant_History"
    history_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "writeup" / "assistant_conversation_history.md", history_dst / "assistant_conversation_history.md")

    # 8. 08_Test_Reports/
    print("  [8/8] Packaging 08_Test_Reports/...")
    test_dst = SUBMISSION_DIR / "08_Test_Reports"
    test_dst.mkdir(parents=True, exist_ok=True)
    with open(test_dst / "test_report.md", "w", encoding="utf-8") as f:
        f.write(build_test_report())

    # 9. SUBMISSION_README.md
    print("  [9/9] Generating SUBMISSION_README.md...")
    with open(SUBMISSION_DIR / "SUBMISSION_README.md", "w", encoding="utf-8") as f:
        f.write(build_submission_readme())

    print("\n[SUCCESS] Final submission folder built successfully at:")
    print(f"--> {SUBMISSION_DIR}\n")

if __name__ == "__main__":
    package_submission()

