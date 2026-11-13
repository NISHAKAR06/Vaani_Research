"""
Tracing and Event Logging module for The Relay.
Records granular JSONL event timelines for every request to enable
post-hoc latency decomposition and slow request debugging.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from config.settings import settings

class RequestTracer:
    def __init__(self, trace_file: Optional[Path] = None):
        self.trace_file = trace_file or (settings.experiments_dir / "raw" / "request_events.jsonl")
        self.trace_file.parent.mkdir(parents=True, exist_ok=True)

    def log_request_event(
        self,
        request_id: str,
        scenario: str,
        source: str,
        start_time_iso: str,
        first_token_ms: Optional[float],
        total_ms: float,
        status: str,
        retries: int,
        tokens_in: int,
        tokens_out: int,
        retrieval_setting: str,
        answer_grade: str,
        latency_breakdown: Dict[str, float],
        timestamps: Dict[str, Any],
        error_details: Optional[str] = None
    ):
        """Append full JSONL event record."""
        record = {
            "request_id": request_id,
            "scenario": scenario,
            "source": source,
            "start_time": start_time_iso,
            "first_token_ms": first_token_ms,
            "total_ms": total_ms,
            "status": status,
            "retries": retries,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "retrieval_setting": retrieval_setting,
            "answer_grade": answer_grade,
            "latency_breakdown": latency_breakdown,
            "timestamps": timestamps,
            "error_details": error_details
        }
        with open(self.trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

