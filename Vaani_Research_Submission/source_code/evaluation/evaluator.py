"""
Evaluation and Quality Grading Module for The Relay.
Performs deterministic evaluation of pipeline answers against human-curated ground truth.
Grades each response into one of the 4 strict categories:
  - "correct": Answer contains factual points and verified citations matching ground truth.
  - "wrong": Answer has factual errors, invalid citations, or failed to answer.
  - "refused_correctly": Unsupported question properly refused.
  - "refused_wrongly": Legitimate in-scope question refused inappropriately.
"""

import json
from typing import Dict, Any, List
from config.settings import settings

def load_evaluation_questions() -> List[Dict[str, Any]]:
    questions_file = settings.PROJECT_ROOT / "src" / "evaluation" / "questions.json"
    with open(questions_file, "r", encoding="utf-8") as f:
        return json.load(f)

def grade_pipeline_response(
    question_spec: Dict[str, Any],
    pipeline_answer: str,
    citations_found: List[Dict[str, Any]],
    status: str
) -> str:
    """
    Deterministically grades an answer against the question's ground-truth spec.
    """
    if status != "ok":
        return "wrong"

    answer_lower = pipeline_answer.lower()
    is_refusal = any(
        kw in answer_lower
        for kw in [
            "cannot answer", "do not contain", "insufficient evidence",
            "does not discuss", "not supported", "cannot provide a verified"
        ]
    )

    should_refuse = question_spec.get("should_refuse", False)

    # 1. Refusal evaluation
    if should_refuse:
        return "refused_correctly" if is_refusal else "wrong"

    if is_refusal and not should_refuse:
        return "refused_wrongly"

    # 2. Citation evaluation: must have at least one citation
    if not citations_found:
        return "wrong"

    # Check that citations match expected papers
    expected_papers = [p.lower() for p in question_spec.get("expected_papers", [])]
    cited_papers = [c["paper"].lower() for c in citations_found]

    # Verify at least one cited paper matches expected paper tags
    has_expected_paper = any(
        any(exp in cp or cp in exp for exp in expected_papers)
        for cp in cited_papers
    )
    if not has_expected_paper and expected_papers:
        return "wrong"

    # Check key technical terms from expected answer
    expected_answer_words = [
        w.lower().strip(".,()[]")
        for w in question_spec["expected_answer"].split()
        if len(w) > 4
    ]
    matches = sum(1 for w in expected_answer_words if w in answer_lower)
    match_ratio = matches / max(1, len(expected_answer_words))

    if match_ratio >= 0.20:
        return "correct"
    else:
        return "wrong"

