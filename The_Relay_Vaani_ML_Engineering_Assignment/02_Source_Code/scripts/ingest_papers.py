"""
Ingest and validate the exact 3 arXiv papers required for The Relay:
- "Attention Is All You Need", arXiv:1706.03762v7
- "Moshi: a speech-text foundation model for real-time dialogue", arXiv:2410.00037v1
- "Dynamic Chunking for End-to-End Hierarchical Sequence Modeling", arXiv:2507.07955v2

Extracts clean text with page numbers, section headers, paragraph boundaries,
and saves validated metadata and page extractions.
"""

import os
import sys
import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import fitz  # PyMuPDF

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings

PAPERS_TO_INGEST = [
    {
        "paper_id": "attention_is_all_you_need",
        "title": "Attention Is All You Need",
        "arxiv_id": "1706.03762",
        "version": "v7",
        "url": "https://arxiv.org/pdf/1706.03762v7",
        "filename": "1706.03762v7.pdf",
    },
    {
        "paper_id": "moshi_realtime_dialogue",
        "title": "Moshi: a speech-text foundation model for real-time dialogue",
        "arxiv_id": "2410.00037",
        "version": "v1",
        "url": "https://arxiv.org/pdf/2410.00037v1",
        "filename": "2410.00037v1.pdf",
    },
    {
        "paper_id": "dynamic_chunking_sequence_modeling",
        "title": "Dynamic Chunking for End-to-End Hierarchical Sequence Modeling",
        "arxiv_id": "2507.07955",
        "version": "v2",
        "url": "https://arxiv.org/pdf/2507.07955v2",
        "filename": "2507.07955v2.pdf",
    },
]

def calculate_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def download_paper(paper_meta: dict, target_dir: Path) -> Path:
    """Download PDF from arXiv with User-Agent and validate download."""
    target_path = target_dir / paper_meta["filename"]
    if target_path.exists() and target_path.stat().st_size > 10000:
        print(f"  [OK] Found existing file: {target_path.name} ({target_path.stat().st_size:,} bytes)")
        return target_path

    print(f"  [FETCH] Downloading {paper_meta['url']} -> {target_path.name}...")
    headers = {"User-Agent": "Vaani-Relay-Research/1.0 (academic; ml-intern-project)"}
    req = urllib.request.Request(paper_meta["url"], headers=headers)
    
    with urllib.request.urlopen(req, timeout=30) as resp, open(target_path, "wb") as out_file:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} fetching {paper_meta['url']}")
        out_file.write(resp.read())

    size = target_path.stat().st_size
    if size < 10000:
        raise ValueError(f"Downloaded PDF {target_path.name} seems too small or corrupt: {size} bytes")
    print(f"  [SUCCESS] Saved {target_path.name} ({size:,} bytes)")
    return target_path

def extract_sections_and_paragraphs(page: fitz.Page) -> list[dict]:
    """
    Extract text blocks from a page, identifying potential section titles
    and paragraphs using font sizing and block structure.
    """
    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
    extracted = []
    
    current_section = "General / Main"
    section_regex = re.compile(r"^(\d+(\.\d+)*\s+[A-Z][A-Za-z0-9\s,\-–—]+|[A-Z][A-Z\s]{3,})$")

    for b in blocks:
        if b[6] != 0:  # 0 indicates text block
            continue
        text = b[4].strip()
        if not text:
            continue
        
        # Check if block looks like a section header
        first_line = text.split("\n")[0].strip()
        if len(first_line) < 80 and section_regex.match(first_line):
            current_section = first_line
        
        extracted.append({
            "section": current_section,
            "text": text,
            "bbox": [round(b[0], 2), round(b[1], 2), round(b[2], 2), round(b[3], 2)],
        })

    return extracted

def ingest_all_papers():
    """Main ingestion runner: fetch, parse, validate, and store."""
    settings.raw_papers_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_papers_dir.mkdir(parents=True, exist_ok=True)

    metadata_records = []

    print("\n=== STARTING PAPER INGESTION & EXTRACTION ===")
    for spec in PAPERS_TO_INGEST:
        print(f"\nProcessing: {spec['title']} ({spec['arxiv_id']}{spec['version']})")
        pdf_path = download_paper(spec, settings.raw_papers_dir)

        # Validate with PyMuPDF
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF {pdf_path}: {e}")

        page_count = len(doc)
        if page_count == 0:
            raise ValueError(f"PDF {pdf_path.name} has 0 pages!")

        sha256 = calculate_sha256(pdf_path)
        timestamp = datetime.now(timezone.utc).isoformat()

        paper_record = {
            "paper_id": spec["paper_id"],
            "title": spec["title"],
            "arxiv_id": spec["arxiv_id"],
            "version": spec["version"],
            "full_arxiv_tag": f"{spec['arxiv_id']}{spec['version']}",
            "url": spec["url"],
            "sha256": sha256,
            "file_size_bytes": pdf_path.stat().st_size,
            "pages": page_count,
            "ingested_at": timestamp,
        }

        # Extract per-page text
        pages_data = []
        total_chars = 0
        for page_idx in range(page_count):
            page_num = page_idx + 1
            page = doc[page_idx]
            plain_text = page.get_text("text").strip()
            total_chars += len(plain_text)
            blocks_data = extract_sections_and_paragraphs(page)

            pages_data.append({
                "page_number": page_num,
                "character_count": len(plain_text),
                "text": plain_text,
                "blocks": blocks_data,
            })

        if total_chars < 1000:
            raise ValueError(f"Extraction yielded too few characters ({total_chars}) for {spec['filename']}")

        # Save processed JSON for this paper
        processed_file = settings.processed_papers_dir / f"{spec['paper_id']}.json"
        with open(processed_file, "w", encoding="utf-8") as f:
            json.dump({
                "metadata": paper_record,
                "pages": pages_data
            }, f, indent=2, ensure_ascii=False)

        print(f"  [PARSED] Extracted {page_count} pages, {total_chars:,} chars -> {processed_file.name}")
        metadata_records.append(paper_record)
        doc.close()

    # Save overall metadata.json
    with open(settings.metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata_records, f, indent=2)

    print(f"\n[DONE] Successfully ingested all {len(metadata_records)} papers.")
    print(f"Metadata saved to: {settings.metadata_file}\n")

if __name__ == "__main__":
    ingest_all_papers()

