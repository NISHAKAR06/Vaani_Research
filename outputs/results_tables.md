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
