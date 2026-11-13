"""
Metrics and Percentile Computation Module for The Relay.
Implements numpy-based linear percentile calculation (p50, p95, p99)
and outcome summaries for results tables.
"""

from typing import List, Dict, Any, Optional
import numpy as np

def compute_percentiles(values: List[float]) -> Dict[str, Optional[float]]:
    """
    Computes p50, p95, p99 using numpy linear interpolation.
    Returns None for empty sets.
    """
    if not values:
        return {"p50": None, "p95": None, "p99": None}
    
    arr = np.array(values, dtype=np.float64)
    return {
        "p50": round(float(np.percentile(arr, 50)), 1),
        "p95": round(float(np.percentile(arr, 95)), 1),
        "p99": round(float(np.percentile(arr, 99)), 1),
    }

def summarize_scenario_outcomes(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarize success, rate-limited, timeout, retries, and token stats from request records.
    """
    total = len(records)
    if total == 0:
        return {}

    succeeded = sum(1 for r in records if r["status"] == "ok")
    rate_limited = sum(1 for r in records if r["status"] == "rate_limited")
    timed_out = sum(1 for r in records if r["status"] in ("timeout", "error"))
    total_retries = sum(r.get("retries", 0) for r in records)
    
    first_tokens = [r["first_token_ms"] for r in records if r.get("first_token_ms") is not None]
    total_times = [r["total_ms"] for r in records if r.get("total_ms") is not None]

    answers_tokens = [r["tokens_out"] for r in records if r["status"] == "ok"]
    avg_tokens_per_ans = round(float(np.mean(answers_tokens)), 1) if answers_tokens else 0.0

    return {
        "total_requests": total,
        "succeeded_pct": round((succeeded / total) * 100.0, 1),
        "rate_limited_pct": round((rate_limited / total) * 100.0, 1),
        "timed_out_pct": round((timed_out / total) * 100.0, 1),
        "retries_per_request": round(total_retries / total, 2),
        "tokens_per_answer": avg_tokens_per_ans,
        "first_token_percentiles": compute_percentiles(first_tokens),
        "total_time_percentiles": compute_percentiles(total_times)
    }

