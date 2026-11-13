---
noteId: "cb6cfea0df7d11f1a06925f0c8d49965"
tags: []

---

# The Relay — Test Execution and Verification Report
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
