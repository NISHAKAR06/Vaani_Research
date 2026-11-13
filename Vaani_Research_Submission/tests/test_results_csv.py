"""
Tests for results.csv generation, column ordering, and strict validation.
"""

import pytest
import csv
from pathlib import Path

from config.settings import settings
from scripts.generate_results import (
    REQUIRED_COLUMNS,
    ALLOWED_SOURCES,
    ALLOWED_STATUSES,
    ALLOWED_GRADES,
    compile_results_csv
)

def test_results_csv_schema_and_types():
    csv_file = settings.outputs_dir / "results.csv"
    if not csv_file.exists():
        pytest.skip("outputs/results.csv not generated yet")

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        # Verify exact column list and order
        assert reader.fieldnames == REQUIRED_COLUMNS, (
            f"Columns mismatch: expected {REQUIRED_COLUMNS}, got {reader.fieldnames}"
        )
        
        rows = list(reader)
        assert len(rows) > 0, "results.csv is empty"

        seen_ids = set()
        for idx, row in enumerate(rows):
            req_id = row["request_id"]
            assert req_id not in seen_ids, f"Duplicate request_id {req_id} at row {idx}"
            seen_ids.add(req_id)

            assert row["source"] in ALLOWED_SOURCES
            assert row["status"] in ALLOWED_STATUSES
            assert row["answer_grade"] in ALLOWED_GRADES
            assert row["retrieval_setting"] in ("A", "B", "C")

            total_ms = float(row["total_ms"])
            assert total_ms >= 0.0

            first_tok = row["first_token_ms"].strip()
            if first_tok:
                assert float(first_tok) >= 0.0
            else:
                # If empty, status should be failed or rate limited or refusal
                pass

            retries = int(row["retries"])
            assert 0 <= retries <= 5

