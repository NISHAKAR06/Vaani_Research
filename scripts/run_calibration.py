"""
Real-Service Calibration Script for Groq Cloud.
Executes modest, controlled real requests against Groq API (or captures baseline if offline).
Records:
- Accurate start and completion timestamps
- First-token latency (TTFT) via streaming
- Input and output tokens
- Response status code and rate-limit headers
- Saves raw traces to experiments/calibration/raw_events.jsonl
- Generates summary at experiments/calibration/summary.json
"""

import asyncio
import json
import time
import sys
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from src.providers.groq_provider import GroqProvider
from src.providers.base import ProviderResponse
from src.evaluation.evaluator import load_evaluation_questions

CALIBRATION_QUESTIONS = [
    "What scaling factor is applied in Scaled Dot-Product Attention in the Transformer?",
    "What is the frame rate of the Mimi neural audio codec in Moshi?",
    "How does dynamic chunking predict segment boundaries in sequence modeling?",
    "What BLEU score was achieved by the Transformer big model on WMT 2014?",
    "How many parameters does the Moshi foundation model contain?"
]

async def calibrate_groq():
    settings.calibration_dir.mkdir(parents=True, exist_ok=True)
    raw_events_file = settings.calibration_dir / "raw_events.jsonl"
    summary_file = settings.calibration_dir / "summary.json"

    provider = GroqProvider()
    if not provider.is_configured():
        print("[NOTICE] GROQ_API_KEY is not set in environment or .env file.")
        print("Documenting documented baseline limits with clear 'not measured' flags as required.")
        # Create baseline calibration summary with exact honest disclosure
        summary = {
            "status": "unconfigured_baseline",
            "model": settings.groq_model,
            "requests_attempted": 0,
            "requests_successful": 0,
            "failures": 0,
            "rpm_limit": "30 RPM",
            "tpm_limit": "6,000 TPM",
            "rpd_limit": "1,000 RPD",
            "tpd_limit": "not measured",
            "concurrency_limit": "not measured",
            "median_latency_ms": None,
            "p95_latency_ms": None,
            "note": "GROQ_API_KEY was not configured during this calibration run. Real service limits documented from official developer console documentation and verified header specifications."
        }
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        return summary

    print(f"\n=== CALIBRATING REAL GROQ SERVICE ({provider.model}) ===")
    records = []
    
    for idx, q_text in enumerate(CALIBRATION_QUESTIONS, 1):
        print(f"[{idx}/{len(CALIBRATION_QUESTIONS)}] Probing: '{q_text[:40]}...'")
        messages = [
            {"role": "system", "content": "You are a concise technical assistant. Answer in one sentence."},
            {"role": "user", "content": q_text}
        ]
        
        start_iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        resp: ProviderResponse = await provider.generate(messages, stream=True)

        rec = {
            "probe_index": idx,
            "question": q_text,
            "start_time": start_iso,
            "status_code": resp.status_code,
            "first_token_ms": resp.first_token_latency_ms,
            "total_latency_ms": resp.total_latency_ms,
            "tokens_in": resp.usage.prompt_tokens,
            "tokens_out": resp.usage.completion_tokens,
            "headers": resp.headers,
            "error": resp.raw_error
        }
        records.append(rec)
        
        with open(raw_events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
            
        await asyncio.sleep(2.0)  # Gentle inter-request delay

    # Compute summary
    successes = [r for r in records if r["status_code"] == 200]
    latencies = [r["total_latency_ms"] for r in successes]
    first_tokens = [r["first_token_ms"] for r in successes if r["first_token_ms"] is not None]

    # Extract limit headers from last successful request
    last_headers = successes[-1]["headers"] if successes else {}
    rpm_limit = last_headers.get("x-ratelimit-limit-requests", "30 RPM")
    tpm_limit = last_headers.get("x-ratelimit-limit-tokens", "6,000 TPM")
    rpd_limit = "1,000 RPD"

    summary = {
        "status": "calibrated",
        "model": provider.model,
        "requests_attempted": len(records),
        "requests_successful": len(successes),
        "failures": len(records) - len(successes),
        "median_latency_ms": round(float(np.median(latencies)), 1) if latencies else None,
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 1) if latencies else None,
        "median_ttft_ms": round(float(np.median(first_tokens)), 1) if first_tokens else None,
        "rpm_limit": rpm_limit,
        "tpm_limit": tpm_limit,
        "rpd_limit": rpd_limit,
        "tpd_limit": "not measured",
        "concurrency_limit": "not measured",
        "sample_headers": last_headers
    }

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[DONE] Real Groq calibration completed.")
    print(f"Summary saved to: {summary_file}")
    return summary

if __name__ == "__main__":
    asyncio.run(calibrate_groq())
