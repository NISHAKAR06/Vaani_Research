"""
Stage 5: Citation Verifier
Deterministically checks generated answer citations against retrieved passage metadata:
- Citation format regex matching exact version tags [arXiv:IDvV, p.X, §Y]
- Strict exact version requirement (1706.03762v7, 2410.00037v1, 2507.07955v2)
- Rejection of unversioned bare arXiv IDs
- Valid page number actually present in retrieved metadata
- Claim-to-source support checking: verifies that cited claim content is supported by the page text
- Fallback / refusal trigger if citations fail after 1 bounded regeneration attempt.
"""

import re
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field

# Valid papers with EXACT mandatory version tags
EXACT_VALID_PAPERS = {
    "1706.03762v7": "attention_is_all_you_need",
    "2410.00037v1": "moshi_realtime_dialogue",
    "2507.07955v2": "dynamic_chunking_sequence_modeling",
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

def _extract_claim_sentence(text: str, citation_start_idx: int) -> str:
    """Find the sentence preceding the citation tag."""
    preceding = text[:citation_start_idx]
    # Split on sentence terminators
    sentences = re.split(r"(?<=[.!?])\s+", preceding)
    return sentences[-1].strip() if sentences else preceding.strip()

def _check_claim_support(claim_text: str, source_text: str) -> bool:
    """
    Verify that key terms from the cited claim sentence appear in the source passage.
    """
    claim_words = re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", claim_text.lower())
    # Filter common stopwords
    stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
        "model", "using", "uses", "which", "into", "each", "have", "has", "been"
    }
    content_words = [w for w in claim_words if w not in stopwords]
    if not content_words:
        return True  # trivial claim

    source_lower = source_text.lower()
    matches = sum(1 for w in content_words if w in source_lower)
    match_ratio = matches / len(content_words)
    # Require at least 25% content term alignment with the cited passage
    return match_ratio >= 0.25

def verify_citations(
    answer_text: str,
    retrieved_chunks: List[Dict[str, Any]],
    is_refusal: bool = False
) -> VerificationResult:
    """
    Deterministically parses and validates every citation in the answer text.
    Enforces exact version tags, page bounds, and claim-to-source support.
    """
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

    matches = list(CITATION_REGEX.finditer(answer_text))
    if not matches:
        return VerificationResult(
            is_valid=False,
            citations_found=[],
            invalid_reasons=["No valid inline citations matching [arXiv:<id><ver>, p.<page>, §<section>] were found."],
            correction_prompt="Your previous answer lacked required citations. Please rewrite and cite your claims using exact tags like [arXiv:1706.03762v7, p.3, §2]."
        )

    # Build lookup of valid (paper_tag, page_number) -> list of passage texts
    valid_page_passages: Dict[Tuple[str, int], List[str]] = {}
    for c in retrieved_chunks:
        full_tag = f"{c['arxiv_id']}{c['version']}".lower()
        key = (full_tag, c["page_number"])
        if key not in valid_page_passages:
            valid_page_passages[key] = []
        valid_page_passages[key].append(c["text"])

    invalid_reasons = []
    citations_found = []

    for match_obj in matches:
        paper_tag, page_str, section = match_obj.groups()
        paper_clean = paper_tag.strip().lower()
        page_num = int(page_str.strip())
        sec_clean = section.strip() if section else ""

        citation_record = {
            "paper": paper_clean,
            "page": page_num,
            "section": sec_clean,
            "raw": match_obj.group(0)
        }
        citations_found.append(citation_record)

        # 1. Enforce exact version: bare arXiv IDs without version (e.g. 1706.03762) are rejected!
        if paper_clean not in EXACT_VALID_PAPERS:
            if not re.search(r"v\d+$", paper_clean):
                invalid_reasons.append(
                    f"Citation '{paper_tag}' lacks required exact version tag (must be 1706.03762v7, 2410.00037v1, or 2507.07955v2)."
                )
            else:
                invalid_reasons.append(
                    f"Paper '{paper_tag}' is not in the allowed 3-paper library."
                )
            continue

        # 2. Check page number validity against retrieved passages
        if (paper_clean, page_num) not in valid_page_passages:
            invalid_reasons.append(
                f"Page {page_num} for paper {paper_tag} was not in retrieved passages metadata."
            )
            continue

        # 3. Check claim-to-source support
        claim_sentence = _extract_claim_sentence(answer_text, match_obj.start())
        source_texts = valid_page_passages[(paper_clean, page_num)]
        is_supported = any(_check_claim_support(claim_sentence, st) for st in source_texts)
        if not is_supported:
            invalid_reasons.append(
                f"Claim '{claim_sentence[:60]}...' is not factually supported by passage on page {page_num}."
            )

    is_valid = len(invalid_reasons) == 0
    correction_prompt = ""
    if not is_valid:
        correction_prompt = (
            f"The following citations were invalid:\n"
            + "\n".join(f"- {r}" for r in invalid_reasons)
            + "\nPlease regenerate the answer citing ONLY pages and papers provided in the retrieved passages with exact versions."
        )

    return VerificationResult(
        is_valid=is_valid,
        citations_found=citations_found,
        invalid_reasons=invalid_reasons,
        correction_prompt=correction_prompt
    )
