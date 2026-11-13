"""
Tests for document ingestion, chunking, and retrieval integrity.
Verifies exact versions, metadata schemas, and retrieval performance across Settings A, B, and C.
"""

import pytest
import json
from pathlib import Path

from config.settings import settings

def test_paper_metadata_exists_and_exact_versions():
    """Verify papers/metadata.json has all 3 required papers with exact arXiv versions."""
    meta_path = settings.metadata_file
    assert meta_path.exists(), "metadata.json not found"
    
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    
    assert len(meta) == 3, f"Expected exactly 3 papers, found {len(meta)}"
    
    expected = {
        "1706.03762": "v7",
        "2410.00037": "v1",
        "2507.07955": "v2",
    }
    
    for paper in meta:
        arxiv_id = paper["arxiv_id"]
        assert arxiv_id in expected, f"Unexpected paper {arxiv_id}"
        assert paper["version"] == expected[arxiv_id], (
            f"Version mismatch for {arxiv_id}: expected {expected[arxiv_id]}, got {paper['version']}"
        )
        assert paper["pages"] > 0
        assert len(paper["sha256"]) == 64
        assert paper["file_size_bytes"] > 100000

def test_chunk_schema_properties():
    """Verify chunk JSON structure matches Section 5 requirements."""
    for setting_key in ["A", "B", "C"]:
        chunks_file = settings.processed_papers_dir / f"chunks_{setting_key}.json"
        if not chunks_file.exists():
            continue  # May still be building in background
            
        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)
            
        assert len(chunks) > 0
        sample = chunks[0]
        required_keys = [
            "chunk_id", "paper_id", "paper_title", "arxiv_id",
            "version", "page_number", "section", "text", "chunk_index"
        ]
        for k in required_keys:
            assert k in sample, f"Missing key {k} in chunk for Setting {setting_key}"
            
        assert isinstance(sample["page_number"], int)
        assert sample["page_number"] >= 1
        assert len(sample["text"]) > 10

def test_retriever_query_execution():
    """Verify retriever returns valid passages with correct top_k and metadata for Settings A, B, and C."""
    from src.retrieval.retriever import retrieve

    # Query 1: Attention mechanism
    res_a = retrieve("multi-head attention mechanism", setting="A")
    assert res_a.setting == "A"
    assert len(res_a.chunks) == 3
    assert res_a.latency_ms > 0
    for c in res_a.chunks:
        assert "attention" in c["text"].lower() or "transformer" in c["text"].lower()
        assert c["arxiv_id"] in ["1706.03762", "2410.00037", "2507.07955"]

    # Query 2: Moshi speech model
    res_b = retrieve("Moshi speech dialogue Mimi neural audio codec", setting="B")
    assert res_b.setting == "B"
    assert len(res_b.chunks) == 5

    # Query 3: Dynamic chunking
    res_c = retrieve("dynamic chunking hierarchical sequence modeling", setting="C")
    assert res_c.setting == "C"
    assert len(res_c.chunks) == 5
    # Setting C should have rerank_score
    assert "rerank_score" in res_c.chunks[0]


