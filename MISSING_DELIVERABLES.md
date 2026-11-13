---
noteId: "de158f60df6211f1a06925f0c8d49965"
tags: []

---

# Missing Deliverables & Calibration Disclosure Notice

## 1. Real Groq Live Calibration Logs (`experiments/calibration/raw_events.jsonl`)

### Status
**Not Provided / Unprobed Baseline Only**

### Reason
The environment variable `GROQ_API_KEY` was not provided during benchmark runs. In strict accordance with the non-negotiable instruction:
> *"Never fabricate measurements, limits, citations or results. Do not replace real Groq measurements with simulated values."*

the system refrained from fabricating synthetic HTTP request traces or spoofing live header measurements.

### Real Limits Source
The baseline limits in `experiments/calibration/summary.json` and Table 1 of the report:
- **RPM Limit**: 30 Requests Per Minute
- **TPM Limit**: 6,000 Tokens Per Minute
- **RPD Limit**: 1,000 Requests Per Day
- **Error Behavior**: HTTP 429 Too Many Requests with `Retry-After` header
- **Recovery Window**: 2.0s to 60.0s rolling reset

are taken strictly from official Groq Cloud developer console documentation and documented API specifications. They are explicitly marked in Table 1 as **"Low (unprobed baseline)"** confidence to avoid overstating empirical verification.

### How to Collect Live Groq Calibration Records
When a valid Groq API key is available:
1. Export the API key:
   ```bash
   export GROQ_API_KEY="gsk_..."
   ```
2. Run the live calibration script:
   ```bash
   python scripts/run_calibration.py
   ```
3. This will probe Groq directly with unretried requests, log raw HTTP request/response headers to `experiments/calibration/raw_events.jsonl`, calculate empirical TTFT/latency percentiles, and update `experiments/calibration/summary.json` with **High** confidence ratings.
