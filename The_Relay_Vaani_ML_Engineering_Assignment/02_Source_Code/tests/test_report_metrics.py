import csv
import json
import pytest
from pathlib import Path

def test_results_csv_schema_and_counts():
    csv_file = Path("outputs/results.csv")
    assert csv_file.exists(), "outputs/results.csv must exist"
    
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    
    assert len(reader) == 126, f"Expected 126 records (54 retrieval eval + 72 load test), found {len(reader)}"
    
    # Check scenario breakdown
    retrieval_eval_rows = [r for r in reader if r["scenario"] == "retrieval_eval"]
    assert len(retrieval_eval_rows) == 54, f"Expected 54 retrieval_eval rows, found {len(retrieval_eval_rows)}"
    
    setting_a = [r for r in retrieval_eval_rows if r["retrieval_setting"] == "A"]
    setting_b = [r for r in retrieval_eval_rows if r["retrieval_setting"] == "B"]
    setting_c = [r for r in retrieval_eval_rows if r["retrieval_setting"] == "C"]
    
    assert len(setting_a) == 18, f"Setting A must have exactly 18 queries, found {len(setting_a)}"
    assert len(setting_b) == 18, f"Setting B must have exactly 18 queries, found {len(setting_b)}"
    assert len(setting_c) == 18, f"Setting C must have exactly 18 queries, found {len(setting_c)}"
    
    # Load scenarios must have exactly 10, 15, 25, 12, 10
    steady_rows = [r for r in reader if r["scenario"] == "steady"]
    burst_rows = [r for r in reader if r["scenario"] == "burst"]
    overload_rows = [r for r in reader if r["scenario"] == "sustained_overload"]
    halved_rows = [r for r in reader if r["scenario"] == "per_minute_halved"]
    budget_rows = [r for r in reader if r["scenario"] == "daily_budget_exhausted"]
    
    assert len(steady_rows) == 10, f"Expected 10 steady rows, got {len(steady_rows)}"
    assert len(burst_rows) == 15, f"Expected 15 burst rows, got {len(burst_rows)}"
    assert len(overload_rows) == 25, f"Expected 25 sustained_overload rows, got {len(overload_rows)}"
    assert len(halved_rows) == 12, f"Expected 12 per_minute_halved rows, got {len(halved_rows)}"
    assert len(budget_rows) == 10, f"Expected 10 daily_budget_exhausted rows, got {len(budget_rows)}"

def test_results_tables_contain_honest_calibration():
    tables_file = Path("outputs/results_tables.md")
    assert tables_file.exists()
    content = tables_file.read_text(encoding="utf-8")
    
    assert "Low (unprobed baseline)" in content
    assert "GROQ_API_KEY unconfigured; 0 live requests" in content
    assert "Setting A (300 tokens, top-3, rerank: no) | 18" in content
    assert "Setting B (600 tokens, top-5, rerank: no) | 18" in content
    assert "Setting C (900 tokens, top-5, rerank: yes) | 18" in content
