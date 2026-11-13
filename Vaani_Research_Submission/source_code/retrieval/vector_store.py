"""
Vector store implementation using FAISS IndexFlatIP (cosine similarity on normalized vectors).
Manages building, saving, loading, and querying indexes for Settings A, B, and C.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import faiss
import numpy as np

from config.settings import settings
from src.retrieval.embeddings import encode_texts, encode_query

class VectorIndex:
    def __init__(self, setting_key: str):
        self.setting_key = setting_key
        self.index_file = settings.processed_papers_dir / f"index_{setting_key}.faiss"
        self.chunks_file = settings.processed_papers_dir / f"chunks_{setting_key}.json"
        self.index: faiss.IndexFlatIP = None
        self.chunks: List[Dict[str, Any]] = []

    def build_and_save(self, chunks: List[Dict[str, Any]]):
        """Build FAISS index from chunks and save to disk."""
        self.chunks = chunks
        texts = [c["text"] for c in chunks]
        print(f"Embedding {len(texts)} chunks for Setting {self.setting_key}...")
        embeddings = encode_texts(texts)
        
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

        # Save FAISS index
        faiss.write_index(self.index, str(self.index_file))
        print(f"Saved FAISS index ({self.index.ntotal} vectors) -> {self.index_file.name}")

    def load(self):
        """Load FAISS index and chunk metadata from disk."""
        if not self.index_file.exists() or not self.chunks_file.exists():
            raise FileNotFoundError(f"Index or chunks not found for Setting {self.setting_key}")
        
        self.index = faiss.read_index(str(self.index_file))
        with open(self.chunks_file, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

    def search(
        self,
        query: str,
        top_k: int = 5,
        paper_filter: str = None
    ) -> List[Dict[str, Any]]:
        """
        Search for top_k most similar chunks.
        Optionally filter by paper_id or arxiv_id.
        """
        if self.index is None:
            self.load()

        q_vec = encode_query(query)
        # Fetch more candidates if filtering by paper
        fetch_k = top_k * 3 if paper_filter else top_k
        fetch_k = min(fetch_k, len(self.chunks))

        distances, indices = self.index.search(q_vec, fetch_k)

        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            chunk = dict(self.chunks[idx])
            chunk["score"] = float(score)

            if paper_filter:
                if paper_filter not in (chunk["paper_id"], chunk["arxiv_id"], chunk.get("full_arxiv_tag", "")):
                    continue

            results.append(chunk)
            if len(results) >= top_k:
                break

        return results

