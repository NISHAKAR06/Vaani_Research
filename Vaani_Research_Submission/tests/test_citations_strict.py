"""
Strict regression tests for exact version requirements and claim-to-source support checking.
"""

from src.pipeline.citation_verifier import verify_citations

def test_bare_arxiv_id_rejected():
    mock_chunks = [
        {
            "arxiv_id": "1706.03762",
            "version": "v7",
            "page_number": 4,
            "section": "3.2.1",
            "text": "Scaled Dot-Product Attention computes queries and keys with 1/sqrt(d_k)."
        }
    ]
    # Unversioned tag: arXiv:1706.03762 (missing v7)
    answer_unversioned = (
        "The attention mechanism scales dot products by 1/sqrt(d_k) [arXiv:1706.03762, p.4, §3.2.1]."
    )
    res = verify_citations(answer_unversioned, mock_chunks)
    assert res.is_valid is False
    assert any("lacks required exact version tag" in r for r in res.invalid_reasons)

def test_exact_version_accepted():
    mock_chunks = [
        {
            "arxiv_id": "1706.03762",
            "version": "v7",
            "page_number": 4,
            "section": "3.2.1",
            "text": "Scaled Dot-Product Attention computes queries and keys with 1/sqrt(d_k)."
        }
    ]
    # Exact tag: arXiv:1706.03762v7
    answer_versioned = (
        "The attention mechanism scales dot products by 1/sqrt(d_k) [arXiv:1706.03762v7, p.4, §3.2.1]."
    )
    res = verify_citations(answer_versioned, mock_chunks)
    assert res.is_valid is True
    assert len(res.citations_found) == 1

def test_unsupported_claim_content_rejected():
    mock_chunks = [
        {
            "arxiv_id": "1706.03762",
            "version": "v7",
            "page_number": 4,
            "section": "3.2.1",
            "text": "Scaled Dot-Product Attention computes queries and keys with 1/sqrt(d_k)."
        }
    ]
    # Claim asserts something completely unrelated to page 4 text (e.g. quantum biology DNA sequencing)
    hallucinated_claim = (
        "The model sequences synthetic DNA nucleotides in biological complexes [arXiv:1706.03762v7, p.4, §3.2.1]."
    )
    res = verify_citations(hallucinated_claim, mock_chunks)
    assert res.is_valid is False
    assert any("not factually supported by passage" in r for r in res.invalid_reasons)

