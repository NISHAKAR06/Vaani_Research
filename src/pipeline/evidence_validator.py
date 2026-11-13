"""
Stage 3: Evidence Validator
Determines whether retrieved passages adequately support an answer.
Branches into 4 explicit outcomes:
  1. SUFFICIENT: Evidence supports answer -> continue to Stage 4.
  2. INSUFFICIENT: Inadequate support -> return correct refusal.
  3. CONFLICTING: Evidence contains cross-paper or cross-section conflicts -> explain conflict with citations.
  4. INVALID: Similarity scores too low or query misaligned -> bounded retry retrieval.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.pipeline.query_analyzer import QueryAnalysis

class EvidenceStatus(str, Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    CONFLICTING = "conflicting"
    INVALID = "invalid"

class ValidationResult(BaseModel):
    status: EvidenceStatus
    explanation: str
    passages: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    reformulated_query: Optional[str] = None
    refusal_message: Optional[str] = None

# Relevance threshold for cosine similarity / rerank scores
SIMILARITY_MIN_THRESHOLD = 0.28
SIMILARITY_INVALID_THRESHOLD = 0.18

def validate_evidence(
    analysis: QueryAnalysis,
    retrieved_chunks: List[Dict[str, Any]],
    attempt_count: int = 1
) -> ValidationResult:
    """
    Validates the retrieved passages against query intent and scores.
    """
    # If question was explicitly identified as out of scope and no chunks exist or score is minimal
    if not retrieved_chunks:
        return ValidationResult(
            status=EvidenceStatus.INSUFFICIENT,
            explanation="No relevant passages could be retrieved from the 3-paper library.",
            refusal_message=(
                "I cannot answer this question based on the provided papers. "
                "The library contains only 'Attention Is All You Need' (1706.03762v7), "
                "'Moshi' (2410.00037v1), and 'Dynamic Chunking' (2507.07955v2), "
                "none of which contain the required information."
            )
        )

    best_score = max(c.get("score", 0.0) for c in retrieved_chunks)

    # 0. Out-of-Scope entity check: if question references out-of-scope entities, refuse immediately
    if analysis.is_potentially_unsupported:
        return ValidationResult(
            status=EvidenceStatus.INSUFFICIENT,
            explanation=f"Question references out-of-scope entity not present in 3-paper library.",
            refusal_message=(
                "I cannot answer this question based on the provided papers. "
                "The library contains only 'Attention Is All You Need' (1706.03762v7), "
                "'Moshi' (2410.00037v1), and 'Dynamic Chunking' (2507.07955v2), "
                "none of which discuss this topic."
            ),
            passages=retrieved_chunks
        )

    # 1. Invalid Evidence branch: scores are catastrophically low and we have not exhausted retries
    if best_score < SIMILARITY_INVALID_THRESHOLD and attempt_count == 1:
        # Reformulate query to broader terms
        reformulated = f"{analysis.main_topic} model architecture sequence"
        return ValidationResult(
            status=EvidenceStatus.INVALID,
            explanation=f"Top similarity score ({best_score:.3f}) is below valid threshold ({SIMILARITY_INVALID_THRESHOLD}). Retrying retrieval.",
            reformulated_query=reformulated,
            passages=retrieved_chunks
        )

    # 2. Insufficient Evidence branch: best score is still below answerable threshold
    if best_score < SIMILARITY_MIN_THRESHOLD or analysis.is_potentially_unsupported:
        # Check if query keywords actually appear anywhere in retrieved chunks
        q_words = [w for w in analysis.main_topic.lower().split() if len(w) > 3]
        matched_words = sum(
            1 for w in q_words if any(w in c["text"].lower() for c in retrieved_chunks)
        )
        if matched_words == 0:
            return ValidationResult(
                status=EvidenceStatus.INSUFFICIENT,
                explanation=f"Retrieved passages do not mention key terms from the question: {q_words}",
                refusal_message=(
                    "The provided library does not contain information to answer this question. "
                    "The three papers ('Attention Is All You Need', 'Moshi', and 'Dynamic Chunking') "
                    "do not discuss this topic."
                ),
                passages=retrieved_chunks
            )

    # 3. Conflicting Evidence branch: cross-paper comparison where multiple papers give different mechanisms
    if analysis.is_cross_paper:
        papers_present = set(c["arxiv_id"] for c in retrieved_chunks)
        if len(papers_present) > 1:
            return ValidationResult(
                status=EvidenceStatus.CONFLICTING,
                explanation=f"Comparative query across multiple papers ({papers_present}). Model must synthesize and contrast specific approaches.",
                passages=retrieved_chunks
            )

    # 4. Sufficient Evidence branch
    return ValidationResult(
        status=EvidenceStatus.SUFFICIENT,
        explanation=f"Sufficient evidence retrieved (top score: {best_score:.3f}). Proceeding to answer generation.",
        passages=retrieved_chunks
    )
