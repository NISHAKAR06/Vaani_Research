"""
Unified Retriever module for The Relay.
Implements the 3 assigned configurations:
  - Setting A: chunk size 300, top-k 3, rerank false
  - Setting B: chunk size 600, top-k 5, rerank false
  - Setting C: chunk size 900, top-k 5, rerank true

Provides timing metrics and structured passage metadata.
"""

import time
from typing import List, Dict, Any, Optional

from config.settings import settings
from src.retrieval.vector_store import VectorIndex
from src.retrieval.reranker import rerank_chunks

_indices = {}

def get_index_for_setting(setting_key: str) -> VectorIndex:
    global _indices
    setting_key = setting_key.upper()
    if setting_key not in _indices:
        idx = VectorIndex(setting_key)
        idx.load()
        _indices[setting_key] = idx
    return _indices[setting_key]

class RetrievalResult:
    def __init__(
        self,
        chunks: List[Dict[str, Any]],
        latency_ms: float,
        setting: str,
        query: str
    ):
        self.chunks = chunks
        self.latency_ms = latency_ms
        self.setting = setting
        self.query = query

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "setting": self.setting,
            "latency_ms": round(self.latency_ms, 2),
            "chunks_count": len(self.chunks),
            "chunks": self.chunks
        }

def retrieve(
    query: str,
    setting: str = "A",
    top_k: Optional[int] = None,
    paper_filter: Optional[str] = None
) -> RetrievalResult:
    """
    Execute retrieval according to configuration specification.
    Tracks precise retrieval execution latency.
    """
    start_time = time.perf_counter()
    setting = setting.upper()

    # Configuration defaults
    if setting == "A":
        default_k = 3
        do_rerank = False
    elif setting == "B":
        default_k = 5
        do_rerank = False
    elif setting == "C":
        default_k = 5
        do_rerank = True
    else:
        raise ValueError(f"Unknown retrieval setting: {setting}. Must be 'A', 'B', or 'C'.")

    k = top_k if top_k is not None else default_k
    vector_index = get_index_for_setting(setting)

    # For Setting C reranking, retrieve candidate pool then rerank
    fetch_k = k * 3 if do_rerank else k
    candidate_chunks = vector_index.search(query, top_k=fetch_k, paper_filter=paper_filter)

    if do_rerank:
        final_chunks = rerank_chunks(query, candidate_chunks, top_k=k)
    else:
        final_chunks = candidate_chunks[:k]

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    return RetrievalResult(
        chunks=final_chunks,
        latency_ms=elapsed_ms,
        setting=setting,
        query=query
    )

