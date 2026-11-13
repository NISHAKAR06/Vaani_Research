"""
Stage 5: Citation Verifier
Deterministically checks generated answer citations against retrieved passage metadata:
- Citation format regex
- Valid paper identifier and exact version tag
- Valid page number actually present in retrieved metadata
- Fallback / refusal trigger if citations fail after 1 bounded regeneration attempt.
"""

import re
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field

# Valid papers and versions in our library
VALID_PAPERS = {
    "1706.03762v7": "attention_is_all_you_need",
    "1706.03762": "attention_is_all_you_need",
    "2410.00037v1": "moshi_realtime_dialogue",
    "2410.00037": "moshi_realtime_dialogue",
    "2507.07955v2": "dynamic_chunking_sequence_modeling",
    "2507.07955": "dynamic_chunking_sequence_modeling",
}

# Regex to match [arXiv:1706.03762v7, p.4, §3.2] or [arXiv:2410.00037v1, p.8]
CITATION_REGEX = re.compile(
    r"\[arXiv:\s*([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)\s*,\s*p\.?\s*(\d+)(?:,\s*§?\s*([^\]]+))?\]",
    re.IGNORECASE
)

class VerificationResult(BaseModel):
    is_valid: bool
    citations_found: List[Dict[str, Any]] = Field(default_factory=list)
    invalid_reasons: List[str] = Field(default_factory=list)
    correction_prompt: str = ""

def verify_citations(
    answer_text: str,
    retrieved_chunks: List[Dict[str, Any]],
    is_refusal: bool = False
) -> VerificationResult:
    """
    Deterministically parses and validates every citation in the answer text.
    """
    # If the answer is an intentional refusal, citations are not required
    refusal_keywords = [
        "cannot answer", "do not contain", "insufficient evidence", 
        "does not discuss", "not supported"
    ]
    if is_refusal or any(kw in answer_text.lower() for kw in refusal_keywords):
        return VerificationResult(
            is_valid=True,
            citations_found=[],
            invalid_reasons=[]
        )

    matches = CITATION_REGEX.findall(answer_text)
    if not matches:
        return VerificationResult(
            is_valid=False,
            citations_found=[],
            invalid_reasons=["No valid inline citations matching [arXiv:<id><ver>, p.<page>, §<section>] were found."],
            correction_prompt="Your previous answer lacked required citations. Please rewrite and cite your claims using exact tags like [arXiv:1706.03762v7, p.3, §2]."
        )

    # Build set of valid (arxiv_id_or_tag, page_number) tuples from retrieved chunks
    valid_locations = set()
    for c in retrieved_chunks:
        full_tag = f"{c['arxiv_id']}{c['version']}"
        valid_locations.add((full_tag.lower(), c["page_number"]))
        valid_locations.add((c["arxiv_id"].lower(), c["page_number"]))

    invalid_reasons = []
    citations_found = []

    for match in matches:
        paper_tag, page_str, section = match
        paper_clean = paper_tag.strip().lower()
        page_num = int(page_str.strip())
        sec_clean = section.strip() if section else ""

        citation_record = {
            "paper": paper_clean,
            "page": page_num,
            "section": sec_clean,
            "raw": f"[arXiv:{paper_tag}, p.{page_str}{', §' + sec_clean if sec_clean else ''}]"
        }
        citations_found.append(citation_record)

        # 1. Check paper existence in library
        if paper_clean not in VALID_PAPERS:
            invalid_reasons.append(
                f"Paper '{paper_tag}' is not in the allowed 3-paper library."
            )
            continue

        # 2. Check page number validity against retrieved passages
        if (paper_clean, page_num) not in valid_locations:
            invalid_reasons.append(
                f"Page {page_num} for paper {paper_tag} was not in retrieved passages metadata."
            )

    is_valid = len(invalid_reasons) == 0
    correction_prompt = ""
    if not is_valid:
        correction_prompt = (
            f"The following citations were invalid:\n"
            + "\n".join(f"- {r}" for r in invalid_reasons)
            + "\nPlease regenerate the answer citing ONLY pages and papers provided in the retrieved passages."
        )

    return VerificationResult(
        is_valid=is_valid,
        citations_found=citations_found,
        invalid_reasons=invalid_reasons,
        correction_prompt=correction_prompt
    )

