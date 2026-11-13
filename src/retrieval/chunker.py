"""
Chunking module for The Relay.
Produces paragraph-aware chunks with overlap for settings A (300 tokens),
B (600 tokens), and C (900 tokens).
Preserves exact metadata: paper_id, title, arxiv_id, version, page_number, section.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from transformers import AutoTokenizer

from config.settings import settings

# Load fast tokenizer for exact token counting
TOKENIZER_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_tokenizer = None

def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)
    return _tokenizer

def token_length(text: str) -> int:
    tok = get_tokenizer()
    return len(tok.encode(text, add_special_tokens=False))

def chunk_text_blocks(
    paper_meta: Dict[str, Any],
    pages_data: List[Dict[str, Any]],
    chunk_size_tokens: int,
    overlap_tokens: int
) -> List[Dict[str, Any]]:
    """
    Split extracted pages/blocks into chunks while respecting paragraph
    boundaries and tracking page numbers and section titles.
    """
    chunks = []
    chunk_counter = 0

    for page in pages_data:
        page_num = page["page_number"]
        blocks = page.get("blocks", [])
        
        # If no blocks extracted, fallback to plain text split by paragraphs
        if not blocks:
            paragraphs = [p.strip() for p in page["text"].split("\n\n") if p.strip()]
            blocks = [{"section": "Main", "text": p} for p in paragraphs]

        current_text = ""
        current_section = "General"
        current_tokens = 0

        for block in blocks:
            b_text = block["text"].strip()
            if not b_text:
                continue
            b_section = block.get("section", current_section)
            b_tokens = token_length(b_text)

            # If adding this block exceeds chunk_size, emit current chunk
            if current_tokens + b_tokens > chunk_size_tokens and current_text:
                chunk_id = f"{paper_meta['paper_id']}_p{page_num}_c{chunk_counter}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "paper_id": paper_meta["paper_id"],
                    "paper_title": paper_meta["title"],
                    "arxiv_id": paper_meta["arxiv_id"],
                    "version": paper_meta["version"],
                    "page_number": page_num,
                    "section": current_section,
                    "text": current_text.strip(),
                    "chunk_index": chunk_counter
                })
                chunk_counter += 1

                # Calculate overlap: take trailing words/sentences
                overlap_text = current_text.split()
                if len(overlap_text) > overlap_tokens:
                    current_text = " ".join(overlap_text[-overlap_tokens:]) + " " + b_text
                else:
                    current_text = b_text
                current_tokens = token_length(current_text)
                current_section = b_section
            else:
                if current_text:
                    current_text += "\n\n" + b_text
                else:
                    current_text = b_text
                current_tokens = token_length(current_text)
                current_section = b_section

        # Emit any trailing text for the page
        if current_text.strip():
            chunk_id = f"{paper_meta['paper_id']}_p{page_num}_c{chunk_counter}"
            chunks.append({
                "chunk_id": chunk_id,
                "paper_id": paper_meta["paper_id"],
                "paper_title": paper_meta["title"],
                "arxiv_id": paper_meta["arxiv_id"],
                "version": paper_meta["version"],
                "page_number": page_num,
                "section": current_section,
                "text": current_text.strip(),
                "chunk_index": chunk_counter
            })
            chunk_counter += 1

    return chunks

def build_chunks_for_setting(setting_key: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
    """Build chunks for all 3 ingested papers for a given retrieval configuration."""
    all_chunks = []
    
    with open(settings.metadata_file, "r", encoding="utf-8") as f:
        papers_meta = json.load(f)

    for meta in papers_meta:
        processed_path = settings.processed_papers_dir / f"{meta['paper_id']}.json"
        with open(processed_path, "r", encoding="utf-8") as f:
            paper_content = json.load(f)
        
        paper_chunks = chunk_text_blocks(
            paper_meta=meta,
            pages_data=paper_content["pages"],
            chunk_size_tokens=chunk_size,
            overlap_tokens=overlap
        )
        all_chunks.extend(paper_chunks)

    # Save chunks file
    chunks_path = settings.processed_papers_dir / f"chunks_{setting_key}.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(all_chunks)} chunks for Setting {setting_key} -> {chunks_path.name}")
    return all_chunks

