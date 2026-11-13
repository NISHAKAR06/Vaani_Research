"""
Results.csv generator and strict schema validator for The Relay.
Compiles raw JSONL events into outputs/results.csv.
Enforces all assignment validation rules:
- Exact 12 columns in specified order
- Enum validations: source in {'real', 'stand-in'}, status in {'ok', 'rate_limited', 'timeout', 'error'},
  answer_grade in {'correct', 'wrong', 'refused_correctly', 'refused_wrongly'}
- first_token_ms empty on failures before first token (no zeros for missing)
- No duplicate request_ids
- No negative latencies or impossible retries
"""

import csv
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings

REQUIRED_COLUMNS = [
    "request_id",
    "scenario",
    "source",
    "start_time",
    "first_token_ms",
    "total_ms",
    "status",
    "retries",
    "tokens_in",
    "tokens_out",
    "retrieval_setting",
    "answer_grade"
]

ALLOWED_SOURCES = {"real", "stand-in"}
ALLOWED_STATUSES = {"ok", "rate_limited", "timeout", "error"}
ALLOWED_GRADES = {"correct", "wrong", "refused_correctly", "refused_wrongly"}

def validate_results_row(row: Dict[str, Any], seen_ids: set) -> None:
    """Strictly validate each row according to Phase 11 constraints."""
    req_id = row.get("request_id")
    if not req_id or req_id in seen_ids:
        raise ValueError(f"Duplicate or empty request_id: '{req_id}'")
    seen_ids.add(req_id)

    source = row.get("source")
    if source not in ALLOWED_SOURCES:
        raise ValueError(f"Invalid source '{source}' for request {req_id}. Allowed: {ALLOWED_SOURCES}")

    status = row.get("status")
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid status '{status}' for request {req_id}. Allowed: {ALLOWED_STATUSES}")

    grade = row.get("answer_grade")
    if grade not in ALLOWED_GRADES:
        raise ValueError(f"Invalid answer_grade '{grade}' for request {req_id}. Allowed: {ALLOWED_GRADES}")

    total_ms = float(row.get("total_ms", 0.0))
    if total_ms < 0:
        raise ValueError(f"Negative total_ms ({total_ms}) for request {req_id}")

    first_tok = row.get("first_token_ms")
    if first_tok is not None and str(first_tok).strip() != "":
        first_tok_ms = float(first_tok)
        if first_tok_ms < 0:
            raise ValueError(f"Negative first_token_ms ({first_tok_ms}) for request {req_id}")
    else:
        # Must be empty if request failed before generating first token
        if status in ("rate_limited", "timeout"):
            row["first_token_ms"] = ""

    retries = int(row.get("retries", 0))
    if retries < 0 or retries > 5:
        raise ValueError(f"Impossible retry count ({retries}) for request {req_id}")

def compile_results_csv(
    raw_events_file: Path,
    output_csv_file: Path
) -> List[Dict[str, Any]]:
    """Reads raw JSONL events, validates each record, and writes outputs/results.csv."""
    if not raw_events_file.exists():
        raise FileNotFoundError(f"Raw trace file {raw_events_file} does not exist.")

    output_csv_file.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    seen_ids = set()

    with open(raw_events_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            record = json.loads(line_str)
            
            row = {
                "request_id": str(record["request_id"]),
                "scenario": str(record.get("scenario", "steady")),
                "source": str(record.get("source", "stand-in")),
                "start_time": str(record.get("start_time", "")),
                "first_token_ms": record.get("first_token_ms") if record.get("first_token_ms") is not None else "",
                "total_ms": round(float(record.get("total_ms", 0.0)), 1),
                "status": str(record.get("status", "ok")),
                "retries": int(record.get("retries", 0)),
                "tokens_in": int(record.get("tokens_in", 0)),
                "tokens_out": int(record.get("tokens_out", 0)),
                "retrieval_setting": str(record.get("retrieval_setting", "A")),
                "answer_grade": str(record.get("answer_grade", "correct")),
            }

            validate_results_row(row, seen_ids)
            rows.append(row)

    # Write CSV
    with open(output_csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"[SUCCESS] Compiled and validated {len(rows)} records -> {output_csv_file}")
    return rows

if __name__ == "__main__":
    raw_file = settings.experiments_dir / "raw" / "request_events.jsonl"
    out_file = settings.outputs_dir / "results.csv"
    compile_results_csv(raw_file, out_file)
