"""
Tests for deterministic citation verification.
Verifies format, paper IDs, exact versions, and page bounds.
"""

from src.pipeline.citation_verifier import verify_citations

def test_citation_verifier_valid_cases():
    mock_chunks = [
        {
            "arxiv_id": "1706.03762",
            "version": "v7",
            "page_number": 4,
            "section": "3.2.1",
            "text": "Scaled Dot-Product Attention computes queries and keys with 1/sqrt(d_k)."
        }
    ]
    
    valid_answer = (
        "The attention mechanism scales dot products by 1/sqrt(d_k) to counteract small gradients "
        "[arXiv:1706.03762v7, p.4, §3.2.1]."
    )
    res = verify_citations(valid_answer, mock_chunks)
    assert res.is_valid is True
    assert len(res.citations_found) == 1
    assert res.citations_found[0]["page"] == 4

def test_citation_verifier_detects_hallucinated_page():
    mock_chunks = [
        {
            "arxiv_id": "1706.03762",
            "version": "v7",
            "page_number": 4,
            "section": "3.2.1",
            "text": "Some text."
        }
    ]
    
    # Page 99 is not in retrieved chunks!
    hallucinated_answer = (
        "The model uses 8 heads [arXiv:1706.03762v7, p.99, §3.2]."
    )
    res = verify_citations(hallucinated_answer, mock_chunks)
    assert res.is_valid is False
    assert any("Page 99" in reason for reason in res.invalid_reasons)
    assert len(res.correction_prompt) > 0

def test_citation_verifier_detects_unknown_paper():
    mock_chunks = []
    fake_paper_answer = "This is from ResNet [arXiv:1512.03385v1, p.2]."
    res = verify_citations(fake_paper_answer, mock_chunks)
    assert res.is_valid is False
    assert any("not in the allowed 3-paper library" in reason for reason in res.invalid_reasons)

def test_citation_verifier_passes_legitimate_refusal():
    refusal_answer = "The provided papers do not contain sufficient evidence to answer this question."
    res = verify_citations(refusal_answer, [], is_refusal=True)
    assert res.is_valid is True

