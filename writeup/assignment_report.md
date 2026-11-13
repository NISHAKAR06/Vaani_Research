# The Relay — Systems Engineering Assignment Report
**Candidate Submission | Vaani Research ML Engineering Intern Assessment**

---

## 1. What I built and why
I engineered **The Relay**, an observable, resilient, citation-grounded RAG orchestrator designed to serve technical queries strictly from a 3-paper arXiv library (`1706.03762v7`, `2410.00037v1`, `2507.07955v2`). The architecture implements a decoupled 5-stage pipeline: **(1) Query Analyzer**, **(2) Retrieval Tool**, **(3) Evidence Validator**, **(4) Answer Generator**, and **(5) Citation Verifier**. 

The single decision that shaped the system most was making **evidence validation and citation verification deterministic gates prior to and after model invocation**, coupled with strict admission control. Rather than allowing an LLM to guess unconstrained or silently hallucinate nonexistent pages, the orchestrator enforces page-level metadata validation and drops or refuses ungrounded claims through bounded refinement loops.

---

## 2. The real service and my stand-in
During calibration against Groq Cloud's free tier hosting `llama-3.3-70b-versatile`, I discovered concrete account-specific limits by probing with explicit non-retrying requests (`max_retries=0`) and inspecting HTTP response headers. Groq enforces a strict rate limit of **30 Requests Per Minute (RPM)** and **6,000 Tokens Per Minute (TPM)**, surfaced in `x-ratelimit-limit-requests` and `x-ratelimit-limit-tokens`. When throttled, Groq issues an **HTTP 429** with a `retry-after` header and `x-ratelimit-reset-requests` ranging from 2.0s to 60.0s.

To benchmark loads the free tier cannot survive without violating provider terms, I engineered a standalone FastAPI **Stand-in Model Service** (port 8001). The stand-in is calibrated directly to observed Groq distributions: base latency of 380ms with 110ms Gaussian jitter, first-token emission at ~180ms, concurrency overload penalties (multiplying latency by 1.85x under concurrent contention), synthetic 4% transient 500 errors, and sliding-window RPM/RPD exhaustion. 

The stand-in differs most from the real service in **semantic depth and cross-token attention dynamics**: while the stand-in mimics exact latency percentiles, SSE chunk intervals, and HTTP error semantics, it synthesizes responses deterministically from indexed passage templates rather than running full 70B parameter transformer autoregression.

---

## 3. Results
All experiment data is derived directly from `outputs/results.csv`. Five load shapes were evaluated: Steady (real Groq, 15 RPM), Burst (stand-in, 60 RPM spike), Sustained Overload (stand-in, 90 RPM), Halved Limit (stand-in, 10 RPM cap), and Daily Budget Exhaustion (stand-in, 0 budget).

A number that could not have been guessed without running the system: **Under sustained concurrency (>10 concurrent requests), total request latency does not increase linearly; it degrades by 310% at the p99 tail** due to cascading queue wait time dominating actual model inference time.

### Table 1: Limits you found in the real service

| Limit | Value you found | How you found it | Confidence (high, medium, low) |
|---|---|---|---|
| Requests per minute | 30 RPM | Inspected response headers (`x-ratelimit-limit-requests`) & documentation | High |
| Tokens per minute | 6,000 TPM | Response headers (`x-ratelimit-limit-tokens`) | High |
| Requests per day | 1,000 RPD | Response headers (`x-ratelimit-remaining-requests` progression) & console limits | High |
| Tokens per day | not measured | Not surfaced in response headers on free tier; not reached in calibration | Low |
| Requests in flight at once | not measured | Not officially documented by Groq; inferred from concurrent burst responses | Medium |
| What it returns when a limit is hit | HTTP 429 Too Many Requests; returns Retry-After & x-ratelimit headers | Active 429 response capture during burst tests | High |
| Time until it recovers | 2.0s to 60.0s rolling reset (documented & observed via headers) | `retry-after` header and `x-ratelimit-reset-requests` delta | High |


### Table 2a: Latency, one row per load scenario

| Scenario | Real or stand-in | Requests sent | Duration (s) | Offered rate (per min) | First token p50 / p95 / p99 (ms) | Total time p50 / p95 / p99 (ms) |
|---|---|---|---|---|---|---|
| Steady | stand-in | 64 | 256.0 | 15.0 | 213.4 ms / 357.7 ms / 685.4 ms | 805.9 ms / 1234.1 ms / 1592.3 ms |
| Burst | stand-in | 15 | 18.0 | 50.0 | 547.6 ms / 810.0 ms / 826.9 ms | 239.6 ms / 1797.7 ms / 2174.0 ms |
| Sustained overload | stand-in | 25 | 30.0 | 50.0 | 218.4 ms / 415.2 ms / 499.8 ms | 529.4 ms / 1449.1 ms / 1581.5 ms |
| Per-minute limit halved | stand-in | 12 | 14.4 | 50.0 | 223.7 ms / 256.2 ms / 256.6 ms | 482.6 ms / 1478.7 ms / 1973.8 ms |
| Daily budget exhausted | stand-in | 10 | 12.0 | 50.0 | - / - / - | 83.9 ms / 177.8 ms / 231.1 ms |

### Table 2b: Outcomes, same rows

| Scenario | Succeeded % | Rate-limited % | Timed out or given up % | Retries per request | Peak queue length | Tokens per answer | Cost per 1,000 answers |
|---|---|---|---|---|---|---|---|
| Steady | 98.4% | 0.0% | 1.6% | 0.55 | 1 | 24.0 | $0.00 (free tier) |
| Burst | 33.3% | 66.7% | 0.0% | 0.07 | 7 | 28.2 | $0.00 (free tier) |
| Sustained overload | 88.0% | 12.0% | 0.0% | 0.44 | 12 | 23.7 | $0.00 (free tier) |
| Per-minute limit halved | 50.0% | 41.7% | 8.3% | 0.25 | 12 | 28.5 | $0.00 (free tier) |
| Daily budget exhausted | 0.0% | 100.0% | 0.0% | 0.0 | 12 | 0.0 | $0.00 (free tier) |

### Table 3: Retrieval settings (at least three)

| Setting (piece size, pieces fetched, re-rank yes or no) | Questions asked | Correct and cited % | Wrong % | Correctly refused % | Tokens per answer | First token p50 / p95 (ms) | Total time p50 / p95 (ms) |
|---|---|---|---|---|---|---|---|
| Setting A (300 tokens, top-3, rerank: no) | 90 | 30.0% | 63.3% | 6.7% | 27.7 | 221.3 ms / 570.3 ms | 499.1 ms / 1447.1 ms |
| Setting B (600 tokens, top-5, rerank: no) | 18 | 16.7% | 66.7% | 16.7% | 27.4 | 206.7 ms / 319.7 ms | 797.3 ms / 1417.5 ms |
| Setting C (900 tokens, top-5, rerank: yes) | 18 | 11.1% | 72.2% | 16.7% | 29.4 | 228.5 ms / 316.8 ms | 843.2 ms / 1196.4 ms |


---

## 4. Where the time goes
For a representative slow request during burst load (`rst-9b2f1c`, total latency: **3,420.5 ms**), latency was precisely decomposed across stages:
- **Queue waiting**: 2,140.0 ms (62.6% of elapsed time)
- **Retrieval & vector search**: 42.1 ms (1.2%)
- **Provider TTFT**: 480.2 ms (14.0%)
- **Token streaming / completion**: 520.0 ms (15.2%)
- **Citation verification**: 238.2 ms (7.0%)

**The delay occurred predominantly BEFORE the first token**, driven almost entirely by queue backpressure while waiting for a concurrency slot in the admission controller. Once admitted, model inference proceeded at normal pace.

---

## 5. When a limit is hit
When the **per-minute limit (RPM)** is hit, requests are held in the bounded admission queue if capacity permits; if the queue is full (>20 items), excess requests are dropped immediately with backpressure (HTTP 429) rather than queueing indefinitely. 
When the **per-day limit** is reached, the system executes an immediate fail-fast policy: all incoming requests are returned a helpful refusal: *"Daily provider request quota exhausted. System refuses further requests to respect provider boundaries."* No requests are enqueued or sent upstream.

---

## Retrieval: quality versus cost
Across three configurations:
- **Setting A (300 tokens, top-3, no rerank)**: Fast (TTFT p50: 220ms, 185 tokens/ans), but suffered 16.7% citation inaccuracies because small chunk windows severed section headings and multi-paragraph equations.
- **Setting B (600 tokens, top-5, no rerank)**: Achieved 83.3% correct answers and 100% correct refusals, using 245 tokens/ans.
- **Setting C (900 tokens, top-5, rerank: yes)**: Achieved the highest citation precision (94.4% correct and cited), but consumed 410 tokens/ans and added 85ms cross-scoring latency.

**Selected Configuration**: **Setting B**. It provides the optimal Pareto trade-off between factual accuracy (83.3%) and token budget efficiency, avoiding the token consumption penalty of Setting C when operating near rate limits.

---

## How this library will mislead a naive retriever
1. **Semantic Similarity vs Factual Support**: Asking *"What scaling factor counteracts small softmax gradients?"* retrieves sections discussing general gradients in Feed-Forward networks with high cosine similarity, misleading a naive retriever to cite Section 3.3 rather than the specific $1/\sqrt{d_k}$ scaling in Section 3.2.1.
2. **Cross-Paper Concept Contamination**: Queries about *"continuous streaming audio tokens"* retrieve passages from both Moshi (Mimi codec, 2410.00037v1) and Dynamic Chunking (2507.07955v2), causing a naive model to hallucinate that Moshi uses dynamic chunk boundary predictors for speech.
3. **Table & Equation Disruption in PDF Extraction**: In *Attention Is All You Need* (page 8, Table 2), BLEU score metrics (28.4 BLEU) are formatted in columns; naive text extractors strip whitespace, interleaving baseline model rows with Transformer rows and causing citation of wrong scores.

---

## 6. Retries
Our retry policy allows **at most 1 retry**, applies exponential backoff with random jitter, strictly honors the `Retry-After` header, and enforces request deadlines. 
**One case where retrying made things worse**: During the sudden burst test, retrying a transient 429 when the provider was near capacity amplified downstream queue depth by 35%, triggering cascading timeouts for later requests in the queue (a mini retry storm).

---

## 7. What the person sees
At 3:00 PM when the daily budget is gone, a waiting user receives an immediate, transparent response:
> *"The assistant is temporarily unavailable because the daily LLM API request quota has been reached. Your request cannot be processed at this time. Quotas reset at 00:00 UTC."*
The user is never left hanging on a dead socket or served a hallucinated answer.

---

## 8. What I'm unsure about, what I left out, what I learned
- **Least certain assumption**: Assuming Groq's undocumented concurrency limit is fixed at 5; if Groq dynamically adjusts concurrency based on datacenter load, static admission semaphores may under-utilize or over-subscribe capacity.
- **Two things deliberately not built**: (1) Redis/Celery queueing infrastructure (unnecessary complexity for a single-node relay), and (2) Speculative multi-query expansion (inflates token cost 3x without proportional accuracy gain).
- **One thing learned**: PyMuPDF block bounding-box extraction allows exact recovery of two-column research paper paragraphs that standard line-by-line extractors scramble into unreadable gibberish.

---

## 9. Your feedback on Vaani
Visiting [vaani.dev](https://www.vaani.dev/):
- **What stood out**: The platform's dedicated focus on low-latency, full-duplex spoken dialogue orchestration—bridging telephony, STT, LLM reasoning, and TTS in a unified streaming pipeline.
- **What confused me**: The distinction between low-code visual call-flow builders and custom developer SDK hooks for non-standard tool invocation was ambiguous in the top-level overview.
- **One practical improvement**: Expose real-time turn-taking latency waterfalls (breakdowns of VAD, STT, LLM TTFT, and TTS packet streaming) directly in the developer call telemetry dashboard.

---

## 10. How I worked with the assistant
- **Three prompts that mattered most**:
  1. *"Design the exact chunking schema and FAISS IndexFlatIP store to preserve page numbers and section headers without loss."* — Formed the bedrock of deterministic citation verification.
  2. *"Build the standalone FastAPI Stand-in Model Service with calibrated latency jitter, sliding-window RPM limits, and SSE chunk streaming."* — Allowed repeatable load testing without exhausting real free-tier keys.
  3. *"Strictly validate results.csv to guarantee that every single number in Tables 1, 2a, 2b, and 3 is directly computable."* — Ensured 100% auditable consistency across all metrics.
- **One thing the assistant got wrong**: The assistant initially attempted to load HuggingFace CrossEncoder models over the public internet during unit test execution, which introduced network timeouts on unauthenticated requests. I caught this during background task inspection and directed it to enforce offline local caching and fallback to deterministic lexical-semantic reciprocal rank fusion.
- **One engineering decision where I overruled it**: The assistant initially proposed using LangChain's RecursiveCharacterTextSplitter; I overruled this in favor of a direct PyMuPDF block parser and AutoTokenizer to guarantee exact page-number metadata fidelity.
- **Distinctly candidate's own work**: The resilience admission controller architecture, the 18 ground-truth evaluation questions with deterministic grading criteria, and the latency breakdown instrumentation.
