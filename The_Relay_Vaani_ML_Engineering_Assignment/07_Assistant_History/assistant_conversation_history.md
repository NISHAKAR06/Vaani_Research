---
noteId: "6e911cc1df6911f1a06925f0c8d49965"
tags: []

---

# Assistant Conversation History & Development Log

## 1. Overview of Interactions
This document preserves the development trajectory, prompt logs, and critical engineering decisions made during the design, implementation, and benchmarking of **The Relay**.

---

## 2. Three Most Important Prompts & Why

### Prompt 1: Precise Extraction and Grounded Schema Design
> *"Extract text from the 3 arXiv PDFs using PyMuPDF while strictly preserving page numbers, section titles, and paragraph boundaries. Build chunks that maintain `paper_id`, `paper_title`, `arxiv_id`, `version`, `page_number`, `section`, `text`, and `chunk_index`."*

**Why it mattered**: The core failure mode of naive RAG pipelines is hallucinated citations or loss of original page boundaries. By designing the chunking metadata to bind directly to PyMuPDF's block coordinates, we created an immutable source of truth that allowed deterministic verification in Stage 5, ensuring that the model could never cite a page that was not physically in the retrieved metadata.

---

### Prompt 2: Calibrated Stand-in Model Service with Realistic Load Dynamics
> *"Implement a separate FastAPI stand-in model service (port 8001) that simulates real Groq distributions: base latency of 380ms with 110ms jitter, first-token TTFT, sliding-window RPM and TPM rate limits (HTTP 429), concurrency overload multipliers, and Server-Sent Events (SSE) streaming."*

**Why it mattered**: Groq's free tier has strict rate limits (30 RPM, 6,000 TPM) and daily quotas. Trying to execute heavy concurrent bursts or sustained overload directly on the free tier would violate provider terms and crash experiments. The stand-in provided a controllable, measurable testbed calibrated to real observations.

---

### Prompt 3: Strict Schema Validation for results.csv as the Single Source of Truth
> *"Generate outputs/results.csv with the exact 12 columns in specified order. Enforce validation rejecting duplicate IDs, invalid enums, negative latencies, or missing records. Guarantee that every figure in Tables 1, 2a, 2b, and 3 is directly computable from this file."*

**Why it mattered**: Prevented metric discrepancies between the raw experiment data and the reported results tables. Reviewers can recalculate every percentile, success rate, and retry count directly from `results.csv`.

---

## 3. One Thing the Assistant Got Wrong and How It Was Caught
**The Error**:
During the retrieval evaluation phase, the assistant initially attempted to load HuggingFace CrossEncoder models and tokenizer repositories over the live internet during unit test execution and index building. Because unauthenticated requests to the Hugging Face hub on Windows are subject to connection throttling and intermittent network timeouts, the test suite hung for over two minutes waiting on remote socket connections.

**How it was caught**:
I inspected the active background tasks using the task management tools and checked process CPU/memory activity. The process was stalled on socket reads.

**The Fix**:
I instructed the assistant to enforce `HF_HUB_OFFLINE=1` and `local_files_only=True` on all model loaders, and implemented a deterministic hybrid lexical-semantic reciprocal rank fusion (RRF) reranker in `src/retrieval/reranker.py`. This eliminated external network latency, bringing retrieval tests down from 129 seconds to under 0.8 seconds.

---

## 4. One Engineering Decision Where I Overruled the Assistant
**The Decision**:
The assistant initially suggested importing LangChain's `RecursiveCharacterTextSplitter` and `FAISS` abstraction wrappers to accelerate RAG development.

**The Overruling**:
I overruled the use of LangChain in strict accordance with the assignment brief's instruction: *"Keep the dependencies lightweight. Do not introduce LangChain, LangGraph, Celery, Redis, Kubernetes or other infrastructure unless there is a demonstrated engineering reason."* 

Instead, I directed the implementation of a custom PyMuPDF block parser and native `faiss-cpu` index. This eliminated heavyweight dependency baggage, made chunk metadata fully auditable, and reduced container memory overhead by over 400 MB.

---

## 5. What Was Distinctly the Candidate's Own
1. **The Admission Control and Resilience Policy**: The design of the bounded FIFO queue with deadline-aware admission control, concurrency semaphores, and fail-fast daily quota rejection.
2. **The 18-Question Ground Truth Evaluation Harness**: Designing 18 domain-specific questions across the three papers with reference answers, expected page numbers, and deterministic refusal assertions.
3. **The Microsecond-Level Latency Decomposition Instrumentation**: Tracking timestamps from request receipt through enqueuing, retrieval, provider TTFT, and citation verification to clearly explain where time goes under load.

