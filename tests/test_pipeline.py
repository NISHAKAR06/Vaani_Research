"""
Tests for 5-stage pipeline orchestration, branching, and bounded refinement loops.
"""

import pytest
from src.pipeline.query_analyzer import analyze_query
from src.pipeline.evidence_validator import validate_evidence, EvidenceStatus
from src.pipeline.retrieval_tool import RetrievalToolCall
from src.pipeline.citation_verifier import verify_citations

def test_query_analyzer_intent_and_routing():
    # Transformer factual
    q1 = "What scaling factor is used in scaled dot-product attention in the Transformer?"
    res1 = analyze_query(q1)
    assert "1706.03762" in res1.target_papers
    assert res1.question_type in ("factual", "architecture")
    assert not res1.is_cross_paper

    # Moshi speech
    q2 = "What is the Mimi neural audio codec frame rate in Moshi?"
    res2 = analyze_query(q2)
    assert "2410.00037" in res2.target_papers

    # Cross paper comparison
    q3 = "Compare the attention mechanism in Transformer with Dynamic Chunking."
    res3 = analyze_query(q3)
    assert res3.is_cross_paper is True
    assert res3.question_type == "comparative"

    # Out of scope / unsupported
    q4 = "What is the architecture of DeepSeek-R1?"
    res4 = analyze_query(q4)
    assert res4.is_potentially_unsupported is True

def test_evidence_validator_branches():
    analysis_inscope = analyze_query("Transformer attention scaling factor")
    
    # 1. Empty passages -> Insufficient branch
    res_empty = validate_evidence(analysis_inscope, [])
    assert res_empty.status == EvidenceStatus.INSUFFICIENT
    assert res_empty.refusal_message is not None

    # 2. Valid high-scoring passage -> Sufficient branch
    mock_chunk = {
        "paper_id": "attention_is_all_you_need",
        "arxiv_id": "1706.03762",
        "version": "v7",
        "page_number": 4,
        "section": "3.2.1",
        "text": "We compute the attention function on a set of queries simultaneously, scaled by 1/sqrt(d_k).",
        "score": 0.85
    }
    res_suff = validate_evidence(analysis_inscope, [mock_chunk])
    assert res_suff.status == EvidenceStatus.SUFFICIENT

    # 3. Very low score -> Invalid branch (triggers retry)
    mock_bad_chunk = dict(mock_chunk)
    mock_bad_chunk["score"] = 0.05
    res_inv = validate_evidence(analysis_inscope, [mock_bad_chunk], attempt_count=1)
    assert res_inv.status == EvidenceStatus.INVALID
    assert res_inv.reformulated_query is not None

def test_retrieval_tool_execution():
    tool = RetrievalToolCall(
        arguments={"query": "multi-head attention", "setting": "A"}
    )
    result = tool.execute()
    assert result.setting == "A"
    assert len(result.chunks) == 3
    assert result.latency_ms > 0

