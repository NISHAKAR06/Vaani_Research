---
noteId: "6e90f5b0df6911f1a06925f0c8d49965"
tags: []

---

### Table 1: Limits you found in the real service

| Limit | Value you found | How you found it | Confidence (high, medium, low) |
|---|---|---|---|
| Requests per minute | 30 RPM | Documented developer limits (GROQ_API_KEY unconfigured; 0 live requests) | Low (unprobed baseline) |
| Tokens per minute | 6,000 TPM | Documented developer limits (GROQ_API_KEY unconfigured; 0 live requests) | Low (unprobed baseline) |
| Requests per day | 1,000 RPD | Documented developer console quota (unprobed live) | Low (unprobed baseline) |
| Tokens per day | not measured | Not surfaced in free tier documentation | Low (not measured) |
| Requests in flight at once | not measured | Not documented by Groq; unmeasured | Low (not measured) |
| What it returns when a limit is hit | HTTP 429 Too Many Requests (documented specification; unprobed live) | Documented Groq rate-limiting behavior | Low (unprobed baseline) |
| Time until it recovers | 2.0s to 60.0s rolling window (documented specification; unprobed live) | Documented rolling window reset interval | Low (unprobed baseline) |


### Table 2a: Latency, one row per load scenario

| Scenario | Real or stand-in | Requests sent | Duration (s) | Offered rate (per min) | First token p50 / p95 / p99 (ms) | Total time p50 / p95 / p99 (ms) |
|---|---|---|---|---|---|---|
| Steady | stand-in | 10 | 43.1 | 13.9 | 426.9 ms / 918.0 ms / 1179.1 ms | 714.8 ms / 1150.7 ms / 1227.3 ms |
| Burst | stand-in | 15 | 2.4 | 375.0 | 1164.9 ms / 1768.5 ms / 1804.7 ms | 224.9 ms / 1788.3 ms / 2159.1 ms |
| Sustained overload | stand-in | 25 | 16.3 | 92.0 | 489.8 ms / 958.5 ms / 1113.1 ms | 540.1 ms / 1517.9 ms / 1609.2 ms |
| Per-minute limit halved | stand-in | 12 | 22.2 | 32.4 | 529.4 ms / 562.6 ms / 563.6 ms | 524.2 ms / 1503.2 ms / 1995.5 ms |
| Daily budget exhausted | stand-in | 10 | 27.1 | 22.1 | - / - / - | 91.8 ms / 104.4 ms / 105.2 ms |

### Table 2b: Outcomes, same rows

| Scenario | Succeeded % | Rate-limited % | Timed out or given up % | Retries per request | Peak queue length | Tokens per answer | Cost per 1,000 answers |
|---|---|---|---|---|---|---|---|
| Steady | 100.0% | 0.0% | 0.0% | 0.5 | 0 | 27.9 | $0.00 (free tier) |
| Burst | 33.3% | 66.7% | 0.0% | 0.07 | 0 | 28.2 | $0.00 (free tier) |
| Sustained overload | 88.0% | 12.0% | 0.0% | 0.44 | 0 | 23.7 | $0.00 (free tier) |
| Per-minute limit halved | 50.0% | 41.7% | 8.3% | 0.25 | 0 | 28.5 | $0.00 (free tier) |
| Daily budget exhausted | 0.0% | 100.0% | 0.0% | 0.0 | 0 | 0.0 | $0.00 (free tier) |

### Table 3: Retrieval settings (at least three)

| Setting (piece size, pieces fetched, re-rank yes or no) | Questions asked | Correct and cited % | Wrong % | Correctly refused % | Tokens per answer | First token p50 / p95 (ms) | Total time p50 / p95 (ms) |
|---|---|---|---|---|---|---|---|
| Setting A (300 tokens, top-3, rerank: no) | 18 | 27.8% | 55.6% | 16.7% | 27.4 | 483.8 ms / 756.6 ms | 814.4 ms / 1120.6 ms |
| Setting B (600 tokens, top-5, rerank: no) | 18 | 16.7% | 66.7% | 16.7% | 27.4 | 436.2 ms / 673.9 ms | 768.8 ms / 1429.1 ms |
| Setting C (900 tokens, top-5, rerank: yes) | 18 | 11.1% | 72.2% | 16.7% | 29.4 | 491.9 ms / 758.9 ms | 848.7 ms / 1299.4 ms |
