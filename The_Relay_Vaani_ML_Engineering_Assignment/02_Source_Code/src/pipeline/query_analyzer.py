"""
Stage 1: Query Analyzer
Analyzes the incoming question to determine:
- Intent and main topic
- Candidate target paper(s)
- Question category (factual, architecture, comparative, out_of_scope)
- Whether the question requires cross-paper comparison
- Formulated search query
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class QueryAnalysis(BaseModel):
    original_query: str
    main_topic: str
    intent: str
    target_papers: List[str] = Field(default_factory=list)  # e.g. ["1706.03762", "2410.00037", "2507.07955"]
    question_type: str = "factual"  # "factual", "architecture", "comparative", "out_of_scope"
    is_cross_paper: bool = False
    is_potentially_unsupported: bool = False
    search_query: str

# Known paper keyword fingerprints
PAPER_FINGERPRINTS = {
    "1706.03762": [
        "attention", "transformer", "self-attention", "vaswani", "bleu", 
        "multi-head", "scaled dot-product", "positional encoding", "wmt", "decoder"
    ],
    "2410.00037": [
        "moshi", "mimi", "dialogue", "speech", "acoustic", "codec", 
        "full-duplex", "audio", "kyutai", "latency", "streaming speech"
    ],
    "2507.07955": [
        "dynamic chunking", "hierarchical sequence", "chunking", "boundary predictor", 
        "segment", "hierarchical", "downsampling", "subsampling"
    ]
}

def analyze_query(query: str) -> QueryAnalysis:
    """
    Deterministic query analyzer mapping incoming queries to paper domains,
    intent, and cross-paper requirements.
    """
    q_lower = query.lower()
    
    # Identify matching papers
    matched_papers = []
    for arxiv_id, keywords in PAPER_FINGERPRINTS.items():
        if any(kw in q_lower for kw in keywords):
            matched_papers.append(arxiv_id)

    # Check for cross-paper or comparison intent
    comparison_indicators = ["compare", "contrast", "difference between", "versus", "vs", "both", "differ"]
    is_comparative = any(ci in q_lower for ci in comparison_indicators) or len(matched_papers) > 1

    # Check for out-of-scope indicators (topics known not to exist in the 3 papers)
    out_of_scope_indicators = [
        "deepseek", "resnet", "quantum", "biology", "alphafold", "protein", "stock market",
        "weather", "convolutional neural network", "llama 3", "gpt-4"
    ]
    is_unsupported = any(osi in q_lower for osi in out_of_scope_indicators) and not matched_papers

    # Classify question type
    if is_comparative:
        q_type = "comparative"
    elif is_unsupported:
        q_type = "out_of_scope"
    elif any(w in q_lower for w in ["architecture", "layer", "dimension", "hyperparameter", "heads"]):
        q_type = "architecture"
    else:
        q_type = "factual"

    # Refine search query: remove boilerplate question framing
    cleaned_query = query
    for prefix in ["what is ", "explain ", "how does ", "describe ", "can you tell me ", "what are "]:
        if q_lower.startswith(prefix):
            cleaned_query = query[len(prefix):]
            break

    return QueryAnalysis(
        original_query=query,
        main_topic=cleaned_query.rstrip("?").strip(),
        intent=f"Retrieve technical evidence for: {cleaned_query.strip()}",
        target_papers=matched_papers,
        question_type=q_type,
        is_cross_paper=is_comparative,
        is_potentially_unsupported=is_unsupported,
        search_query=cleaned_query.strip()
    )
