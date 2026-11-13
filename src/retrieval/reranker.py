"""
Re-ranking module for Setting C.
Combines semantic vector score with BM25 / token-level lexical overlap cross-scoring.
Optionally integrates HuggingFace CrossEncoder if locally cached without blocking.
"""

import math
import re
from typing import List, Dict, Any

def tokenize_simple(text: str) -> List[str]:
    """Extract lowercase alphanumeric tokens."""
    return re.findall(r"\b\w{2,}\b", text.lower())

def compute_lexical_score(query_tokens: List[str], doc_tokens: List[str]) -> float:
    """Compute BM25-like term frequency and length penalty cross score."""
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    tf_counts = {}
    for t in doc_tokens:
        tf_counts[t] = tf_counts.get(t, 0) + 1
    
    score = 0.0
    k1 = 1.2
    b = 0.75
    avg_len = 300.0  # reference average passage length
    len_norm = 1.0 - b + b * (doc_len / avg_len)

    for q in query_tokens:
        tf = tf_counts.get(q, 0)
        if tf > 0:
            term_score = (tf * (k1 + 1.0)) / (tf + k1 * len_norm)
            score += term_score

    return score

def rerank_chunks(query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Reranks candidate chunks by fusing vector similarity (semantic)
    with exact query-passage lexical overlap cross-scoring.
    Guarantees deterministic, fast, offline execution.
    """
    if not chunks:
        return []

    q_tokens = tokenize_simple(query)

    for chunk in chunks:
        # Base dense vector score (cosine similarity, typically 0.0 to 1.0)
        base_vector_score = float(chunk.get("score", 0.5))
        
        # Lexical cross-scoring
        c_tokens = tokenize_simple(chunk["text"])
        lex_score = compute_lexical_score(q_tokens, c_tokens)
        
        # Section header match bonus
        section_tokens = tokenize_simple(chunk.get("section", ""))
        section_overlap = sum(1 for q in q_tokens if q in section_tokens)
        section_bonus = 0.15 * section_overlap

        # Normalized fused score
        # Base vector provides semantic recall; lexical + section provides precise factual precision
        fused_score = (0.60 * base_vector_score) + (0.30 * min(lex_score / 5.0, 1.0)) + section_bonus
        chunk["rerank_score"] = round(float(fused_score), 4)

    # Sort descending by rerank_score
    sorted_chunks = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
    return sorted_chunks[:top_k]
