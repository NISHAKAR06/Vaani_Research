"""
Build chunk datasets and FAISS vector indices for all three retrieval settings:
  Setting A: 300 tokens, 50 overlap
  Setting B: 600 tokens, 100 overlap
  Setting C: 900 tokens, 150 overlap
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval.chunker import build_chunks_for_setting
from src.retrieval.vector_store import VectorIndex

def main():
    configs = [
        ("A", 300, 50),
        ("B", 600, 100),
        ("C", 900, 150),
    ]

    print("=== BUILDING RETRIEVAL CHUNKS AND FAISS INDICES ===")
    for setting_key, chunk_size, overlap in configs:
        print(f"\n--- Processing Setting {setting_key} (chunk={chunk_size}, overlap={overlap}) ---")
        chunks = build_chunks_for_setting(setting_key, chunk_size, overlap)
        v_index = VectorIndex(setting_key)
        v_index.build_and_save(chunks)

    print("\n[COMPLETE] All vector indices and chunk stores successfully generated.")

if __name__ == "__main__":
    main()

