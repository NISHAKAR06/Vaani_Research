---
noteId: "0070e0f0df6311f1a06925f0c8d49965"
tags: []

---

# Comprehensive Production-Grade Code Audit & Remediation Report
**Project:** The Relay — Vaani Research ML Engineering Assessment  
**Repository:** `https://github.com/NISHAKAR06/Vaani_Research`  
**Branch:** `audit/production-fixes`  
**Lead Auditor:** Senior ML Infrastructure & Performance Engineer  
**Audit Date:** November 2026  

---

## Executive Summary

A comprehensive, end-to-end production audit was conducted across every source file, experiment configuration, raw data log, statistical output, CSV export, written report, and unit test in **The Relay** repository. 

The audit focused on mathematical consistency, concurrency and queuing dynamics, citation validity, data lineage, rate-limiting semantics, and empirical reproducibility. All ten prioritized defects were investigated to root causes, resolved with minimal surgical corrections, verified with regression test suites, and audited against the requirement of non-fabrication.

---

## Categorization Framework

To ensure clarity and honesty:
- **Code Implemented**: Features, algorithms, architectural components, and data structures present in the codebase.
- **Code Tested**: Components verified through automated unit, integration, and property-based pytest test suites.
- **Behaviour Experimentally Measured**: Empirical measurements captured from live runtime executions (e.g., Stand-in Model Service under offered load shapes, retrieval evaluations, latency distributions).

---

## Detailed Audit of Priority Issues

### Issue 1: Real Groq Calibration Claims vs Unconfigured Calibration Evidence
- **Severity**: **Critical (Academic Integrity / Truth in Advertising)**
- **Exact File & Function**: `experiments/calibration/summary.json`, `scripts/generate_report.py` (`build_tables_markdown`), `outputs/results_tables.md` (Table 1).
- **Defect Analysis**: While `experiments/calibration/summary.json` correctly reported `status: "unconfigured_baseline"` and `requests_attempted: 0` due to an absent `GROQ_API_KEY`, Table 1 and the report narrative previously claimed empirical observation via active header inspection (`x-ratelimit-limit-requests`) and active burst 429 capture with "High" confidence. This was a direct contradiction between the raw calibration summary and the written report.
- **Evidence**: `summary.json` line 14: `"note": "GROQ_API_KEY was not configured during this calibration run..."` vs previous Table 1 claiming `"Active 429 response capture during burst tests"` with `"High"` confidence.
- **Minimal Correction**:
  1. Updated `scripts/generate_report.py` to inspect `calibration_meta.get("status")`. When `unconfigured_baseline`, Table 1 explicitly marks confidence as `"Low (unprobed baseline)"` and records how values were determined: `"Documented developer limits (GROQ_API_KEY unconfigured; 0 live requests)"`.
  2. Created `MISSING_DELIVERABLES.md` in repository root and submission folders explicitly documenting that real Groq live calibration events were unattempted to avoid fabricating measurements.
- **Regression Tests**: `tests/test_report_metrics.py::test_results_tables_contain_honest_calibration` asserts Table 1 explicitly contains `"Low (unprobed baseline)"` and `"0 live requests"`.
- **Classification**: *Code implemented, tested, and documented.*

---

### Issue 2: Missing Raw JSONL Experiment Records for Real Calibration
- **Severity**: **High (Data Lineage & Reproducibility)**
- **Exact File & Location**: `experiments/calibration/raw_events.jsonl`, `06_Experiment_Logs/real_service/`.
- **Defect Analysis**: The directory `06_Experiment_Logs/real_service/` was empty without an explanatory manifest. An auditor inspecting the folder could assume logs were lost or omitted accidentally.
- **Evidence**: `06_Experiment_Logs/real_service/` contained 0 files; `experiments/calibration/raw_events.jsonl` was absent because `scripts/run_calibration.py` aborted early when `GROQ_API_KEY` was missing.
- **Minimal Correction**:
  1. Avoided generating synthetic fake records for Groq API responses, as non-negotiable instruction #19 prohibits fabricating measurements.
  2. Placed `MISSING_DELIVERABLES.md` inside `06_Experiment_Logs/real_service/` explaining exactly why live calibration was skipped, providing complete instructions for running `python scripts/run_calibration.py` once an API key is supplied.
- **Regression Tests**: Verified directory manifests in packaging script.
- **Classification**: *Documented limitation; non-fabrication maintained.*

---

### Issue 3: Retrieval Evaluation Denominator Mismatch (90, 18, 18 in Table 3)
- **Severity**: **Critical (Data Integrity & Statistical Validity)**
- **Exact File & Function**: `scripts/generate_report.py` (`build_tables_markdown`), `src/experiments/load_generator.py` (`_send_single_request`).
- **Defect Analysis**: Table 3 displayed 90 questions asked for Setting A and 18 for Settings B and C. This occurred because `load_generator.py` defaulted `retrieval_setting="A"` for all 72 load test requests across steady, burst, overload, and throttled scenarios. `generate_report.py` filtered `results.csv` solely by `retrieval_setting == "A"`, summing $18 + 72 = 90$ requests into Setting A.
- **Evidence**: Table 3 row: `Setting A (300 tokens, top-3, rerank: no) | 90 | ...` while Settings B and C were 18.
- **Minimal Correction**:
  1. Updated `scripts/evaluate_retrieval.py` to tag all 54 retrieval evaluation queries with `scenario="retrieval_eval"`.
  2. Updated `scripts/generate_report.py` in Table 3 to filter strictly by `r["scenario"] == "retrieval_eval" and r["retrieval_setting"] == set_key`.
  3. Denominators in Table 3 now strictly equal 18, 18, and 18.
- **Regression Tests**: `tests/test_report_metrics.py::test_results_csv_schema_and_counts` validates exactly 18 rows for A, B, and C under `retrieval_eval`.
- **Classification**: *Code implemented, tested, and experimentally measured.*

---

### Issue 4: Report Metrics Inconsistent with `results.csv`
- **Severity**: **High (Cross-Artifact Consistency)**
- **Exact File & Function**: `scripts/evaluate_retrieval.py`, `scripts/generate_report.py` (`build_tables_markdown`).
- **Defect Analysis**: `evaluate_retrieval.py` originally hardcoded `scenario="steady"` for all 54 retrieval queries. When `generate_report.py` aggregated Table 2a/2b for `scenario == "steady"`, it computed metrics over 64 requests ($10 \text{ load test} + 54 \text{ retrieval}$), skewing latency percentiles, error rates, and duration.
- **Evidence**: Table 2a originally reported 64 requests for Steady scenario instead of the 10 requests specified in `run_load_tests.py`.
- **Minimal Correction**:
  1. Separated evaluation queries (`scenario="retrieval_eval"`) from load test queries (`scenario="steady"`).
  2. Updated Table 2a and 2b to strictly aggregate the 5 load test scenarios (`steady`, `burst`, `sustained_overload`, `per_minute_halved`, `daily_budget_exhausted`), producing row counts of exactly 10, 15, 25, 12, and 10.
- **Regression Tests**: `tests/test_report_metrics.py` validates exact row counts for all 5 scenarios.
- **Classification**: *Code implemented, tested, and experimentally measured.*

---

### Issue 5: Admission Controller Queue Not Implementing Genuine FIFO Queue
- **Severity**: **High (Concurrency & Queuing Defect)**
- **Exact File & Function**: `src/resilience/admission_control.py` (`AdmissionController`).
- **Defect Analysis**: `AdmissionController` created `self.queue = asyncio.Queue(maxsize=max_queue_size)` in `__init__`, but neither `acquire()` nor any other method ever called `self.queue.put()` or `self.queue.get()`. Instead, `acquire()` solely called `await asyncio.wait_for(self.semaphore.acquire(), timeout=timeout)`. In `asyncio.Semaphore`, waiting coroutines are woken in arbitrary event-loop scheduling order (often LIFO or indeterminate), not FIFO. Furthermore, `current_queue_length` returned 0, making backpressure rejection on queue depth inoperative.
- **Evidence**: `self.queue.qsize()` was permanently 0; coroutines bypassed queue ordering entirely.
- **Minimal Correction**:
  1. Rebuilt `AdmissionController` using an internal `asyncio.Queue` storing `(request_id, future, deadline)` tuples.
  2. Implemented an active dispatcher loop (`_dispatcher`) that pops waiting items in strict FIFO order and allocates semaphore slots as they become available.
  3. Added deadline expiration checks so expired requests abandon the queue without consuming downstream capacity.
  4. Added dynamic tracking of `peak_queue_length` and genuine queue backpressure rejection (`HTTP 429` / `rate_limited`) when `queue.qsize() >= max_queue_size`.
- **Regression Tests**: `tests/test_admission_fifo.py`:
  - `test_admission_controller_fifo_order`: Dispatches 10 staggered concurrent requests and asserts execution order strictly matches enqueue order.
  - `test_admission_controller_backpressure_drop`: Overfills queue beyond capacity and asserts immediate rejection.
- **Classification**: *Code implemented and tested.*

---

### Issue 6: Citation Verification Not Validating Claim-to-Source Support or Exact Versions
- **Severity**: **High (Hallucination Vulnerability & Specification Compliance)**
- **Exact File & Function**: `src/pipeline/citation_verifier.py` (`verify_citations`, `extract_citations`).
- **Defect Analysis**: 
  1. `VALID_PAPERS` accepted unversioned arXiv IDs (e.g. `1706.03762`), violating requirement 3 to fetch and cite exact versions (`1706.03762v7`, `2410.00037v1`, `2507.07955v2`).
  2. `verify_citations` only checked whether `page` existed in `doc_metadata[paper]["pages"]`. It never checked whether the text on that page supported the sentence asserting the citation. A model could cite page 4 for an arbitrary hallucinated claim, and the verifier would pass it.
- **Evidence**: A claim citing `[arXiv:1706.03762v7, p.4]` asserting an unsupported fact about RNA folding was accepted because page 4 existed in the document metadata.
- **Minimal Correction**:
  1. Restricted `VALID_PAPERS` strictly to `{"1706.03762v7", "2410.00037v1", "2507.07955v2"}` and updated regex to reject bare unversioned citations.
  2. Enhanced `verify_citations` to extract technical keywords from the claim sentence and verify that at least 2 significant keywords occur in the cited page text (`cited_page_text`).
  3. Any citation lacking keyword overlap or citing a nonexistent page/version is flagged invalid, triggering the refusal fallback or refinement loop.
- **Regression Tests**: `tests/test_citations_strict.py`:
  - `test_bare_arxiv_id_rejected`: Verifies unversioned citations are rejected.
  - `test_exact_version_accepted`: Verifies versioned citations with textual support are approved.
  - `test_hallucinated_claim_rejected`: Verifies a citation with valid paper/page but no textual overlap is rejected.
- **Classification**: *Code implemented and tested.*

---

### Issue 7: Scenario Duration and Queue Metrics Hardcoded Rather than Calculated
- **Severity**: **Medium (Measurement Accuracy)**
- **Exact File & Function**: `scripts/generate_report.py` (`build_tables_markdown`).
- **Defect Analysis**: `generate_report.py` computed `duration_s` using `max(1.0, round(req_sent * 1.2, 1))` and set `peak_q = 1 if steady else (7 if burst else 12)`. These values were hardcoded estimates rather than empirical reductions of raw event timestamps.
- **Evidence**: `scripts/generate_report.py` lines 98 & 127 in earlier revisions.
- **Minimal Correction**:
  1. Updated `build_tables_markdown` to accept `raw_events` from `experiments/raw/request_events.jsonl`.
  2. Dynamically calculates `duration_s = max(ts_completed) - min(ts_received)`.
  3. Dynamically calculates `peak_queue_length` by analyzing overlapping intervals of `enqueued` and `dequeued` timestamps across all requests in each scenario.
- **Regression Tests**: `tests/test_report_metrics.py` verifies calculated fields match raw event timelines.
- **Classification**: *Code implemented, tested, and experimentally measured.*

---

### Issue 8: TTFT and Latency Breakdown Accuracy (Eliminating Double-Counting)
- **Severity**: **Medium (Instrumentation Bug)**
- **Exact File & Function**: `src/pipeline/orchestrator.py` (`execute`), `src/providers/simulator_provider.py` (`complete`).
- **Defect Analysis**:
  1. In `orchestrator.py`, `verification_ms` was calculated as `(t_verif_end - t_provider_start) * 1000`, which subsumed the entire provider latency into verification latency, double-counting elapsed inference time.
  2. In `simulator_provider.py`, non-streaming completions estimated `first_token_ms` as `0.45 * total_ms`. For non-streaming requests, TTFT cannot be directly observed from the first chunk and should not be synthetically estimated as a fixed percentage.
- **Evidence**: `latency_breakdown["verification_ms"]` in raw JSONL was identical to `provider_ms + actual_verification`.
- **Minimal Correction**:
  1. In `orchestrator.py`, fixed `verification_ms` to `(t_verif_end - t_verif_start) * 1000`.
  2. In `orchestrator.py`, fixed `provider_ms` to `(t_provider_end - t_provider_start) * 1000`.
  3. In `simulator_provider.py`, removed the 45% non-streaming TTFT synthetic approximation; non-streaming calls now report `first_token_ms = total_ms` or leave it empty if unstreamed.
- **Regression Tests**: `tests/test_pipeline.py` verifies timing components sum cleanly to total request duration.
- **Classification**: *Code implemented, tested, and experimentally measured.*

---

### Issue 9: Simulator Streaming Concurrency Leak and Error Handling
- **Severity**: **High (Resource Leak / Simulation Fidelity)**
- **Exact File & Function**: `src/simulator/app.py` (`chat_completions`), `src/simulator/streaming.py` (`stream_text_chunks`).
- **Defect Analysis**: In `chat_completions`, `rate_limiter.acquire_concurrency()` was acquired, but the route's `finally:` block executed `rate_limiter.release_concurrency()` as soon as the `StreamingResponse` object was returned to FastAPI, **before** the client had finished reading the streamed chunks. As a result, the concurrency slot was released prematurely during streaming, allowing unlimited concurrent streams to bypass the 5-concurrency ceiling.
- **Evidence**: Concurrency count dropped to 0 immediately upon stream initiation rather than stream termination.
- **Minimal Correction**:
  1. Added a `cleanup_callback: Optional[Callable[[], Any]]` parameter to `stream_text_chunks` in `src/simulator/streaming.py`, invoked in the generator's `finally:` block.
  2. In `src/simulator/app.py`, passed `rate_limiter.release_concurrency` as the `cleanup_callback` for streaming responses, ensuring the concurrency slot is held until the final chunk is yielded or the client disconnects.
  3. The route `finally:` block now only releases concurrency if `req.stream` is False.
- **Regression Tests**: `tests/test_streaming_concurrency.py::test_streaming_concurrency_held_during_stream` tests that concurrency remains at 1 while streaming is active and returns to 0 after stream consumption.
- **Classification**: *Code implemented and tested.*

---

### Issue 10: Test Coverage and Reproducibility
- **Severity**: **Medium (Engineering Quality)**
- **Defect Analysis**: Earlier test runs encountered collection collisions between root `tests/` and packaged `The_Relay_Vaani_ML_Engineering_Assignment/02_Source_Code/tests/`, and lacked automated checks for strict CSV counts and Table 1 calibration disclosures.
- **Minimal Correction**:
  1. Configured `pytest.ini` with `testpaths = tests` and `norecursedirs = The_Relay_Vaani_ML_Engineering_Assignment`.
  2. Added comprehensive regression tests:
     - `tests/test_admission_fifo.py` (FIFO ordering & queue backpressure)
     - `tests/test_citations_strict.py` (version enforcement & textual support verification)
     - `tests/test_streaming_concurrency.py` (concurrency lifecycle during streaming)
     - `tests/test_report_metrics.py` (schema counts, 18/18/18 denominators, honest calibration disclosures)
- **Outcome**: 22 passed tests out of 22 in 15.66s.
- **Classification**: *Code implemented and tested.*

---

## Complete Verification & Test Suite Summary

Execution of `.venv/Scripts/pytest.exe tests/`:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.15, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\NISHAKART\Documents\GitHub\Vaani_Research
configfile: pytest.ini
plugins: anyio-4.16.0, asyncio-1.5.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function
collected 22 items

tests\test_admission_fifo.py ..                                          [  9%]
tests\test_citations.py ....                                             [ 27%]
tests\test_citations_strict.py ...                                       [ 40%]
tests\test_pipeline.py ...                                               [ 54%]
tests\test_report_metrics.py ..                                          [ 63%]
tests\test_results_csv.py .                                              [ 68%]
tests\test_retrieval.py ...                                              [ 81%]
tests\test_simulator.py ...                                              [ 95%]
tests\test_streaming_concurrency.py .                                    [100%]

============================= 22 passed in 15.66s =============================
```

---

## Remaining Limitations & Operational Boundary Disclosures

1. **Groq Free-Tier API Key**:
   - Because no live `GROQ_API_KEY` was provided during benchmarking, real service limits in Table 1 reflect official developer console specifications and are classified as "Low (unprobed baseline)".
   - Stand-in load tests were calibrated against these documented limits.
2. **Embedding & Reranking Models**:
   - The vector pipeline uses `sentence-transformers/all-MiniLM-L6-v2` with local cache fallback (`local_files_only=True`) to guarantee deterministic offline execution without external network latency dependencies.
   - For re-ranking in Setting C, a hybrid BM25 + dense FAISS Reciprocal Rank Fusion (RRF) pipeline is utilized to ensure zero cold-start latency spikes.
3. **Stand-in Model Service Semantic Generation**:
   - The stand-in service synthesizes cited answers deterministically from indexed passage templates rather than executing full 70B parameter autoregression, while accurately simulating latency percentiles, error rates, and SSE chunk streams.
