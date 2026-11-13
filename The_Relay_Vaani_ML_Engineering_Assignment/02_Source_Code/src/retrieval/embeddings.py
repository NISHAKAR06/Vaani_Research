"""
Embedding model wrapper using sentence-transformers (all-MiniLM-L6-v2).
Provides normalized dense vectors for FAISS inner product search.
"""

from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer

from config.settings import settings

_model = None

def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        try:
            # Prefer local cache to eliminate remote HF hub network round-trips
            _model = SentenceTransformer(settings.embedding_model_name, local_files_only=True)
        except Exception:
            _model = SentenceTransformer(settings.embedding_model_name)
    return _model

def encode_texts(texts: Union[str, List[str]], batch_size: int = 64) -> np.ndarray:
    """Encode texts to unit-normalized float32 numpy arrays."""
    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True
    )
    return embeddings.astype(np.float32)

def encode_query(query: str) -> np.ndarray:
    """Encode a single query string to 1xD float32 vector."""
    model = get_embedding_model()
    vec = model.encode(
        query,
        normalize_embeddings=True,
        convert_to_numpy=True
    )
    return np.expand_dims(vec.astype(np.float32), axis=0)

