"""
Retrieval Evaluation Script for The Relay.
Runs all 18 self-authored questions across Settings A, B, and C.
Evaluates:
- Answer correctness and citation validity
- Correct refusal rate on out-of-scope questions
- Tokens per answer
- TTFT and total latency percentiles
- Logs raw events for inclusion in outputs/results.csv
"""

import asyncio
import time
import uuid
import sys
import httpx
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from src.evaluation.evaluator import load_evaluation_questions, grade_pipeline_response
from src.pipeline.orchestrator import PipelineOrchestrator
from src.providers.simulator_provider import SimulatorProvider
from src.providers.groq_provider import GroqProvider
from src.observability.tracing import RequestTracer

async def reset_simulator(rpm_limit: int = 500, tpm_limit: int = 500000, daily_budget: int = 10000):
    url = f"{settings.standin_url}/simulator/reset"
    payload = {
        "rpm_limit": rpm_limit,
        "tpm_limit": tpm_limit,
        "daily_request_limit": daily_budget,
        "failure_probability": 0.0
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"[WARN] Simulator reset failed: {e}")

async def evaluate_retrieval_settings(provider_source: str = "stand-in"):
    questions = load_evaluation_questions()
    tracer = RequestTracer()
    
    if provider_source == "real":
        provider = GroqProvider()
    else:
        provider = SimulatorProvider()

    settings_to_test = ["A", "B", "C"]
    print(f"\n=== EVALUATING {len(questions)} QUESTIONS ACROSS RETRIEVAL SETTINGS A, B, C ===")

    for set_key in settings_to_test:
        await reset_simulator(rpm_limit=500, tpm_limit=500000, daily_budget=10000)
        print(f"\n--- Testing Setting {set_key} ---")
        orchestrator = PipelineOrchestrator(provider=provider, default_setting=set_key)

        for q_idx, q_spec in enumerate(questions, 1):
            req_id = f"ret-{set_key}-{q_spec['question_id']}"
            start_iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

            resp = await orchestrator.execute(
                query=q_spec["question"],
                retrieval_setting=set_key,
                request_id=req_id
            )

            # Evaluate grade against human reference answer
            grade = grade_pipeline_response(
                question_spec=q_spec,
                pipeline_answer=resp.answer,
                citations_found=resp.citations,
                status=resp.status
            )
            resp.answer_grade = grade

            # Log to JSONL
            tracer.log_request_event(
                request_id=resp.request_id,
                scenario="steady",
                source=provider_source,
                start_time_iso=start_iso,
                first_token_ms=resp.first_token_ms,
                total_ms=resp.total_ms,
                status=resp.status,
                retries=resp.retries,
                tokens_in=resp.tokens_in,
                tokens_out=resp.tokens_out,
                retrieval_setting=set_key,
                answer_grade=grade,
                latency_breakdown={
                    "queue_wait_ms": resp.queue_wait_ms,
                    "retrieval_ms": resp.retrieval_ms,
                    "provider_ms": resp.provider_ms,
                    "verification_ms": resp.verification_ms,
                },
                timestamps=resp.timestamps.model_dump()
            )
            print(f"  [{q_idx}/{len(questions)}] {q_spec['question_id']}: grade={grade}, {resp.total_ms:.1f}ms")

    print("\n[SUCCESS] Retrieval evaluation completed for Settings A, B, and C.")

if __name__ == "__main__":
    asyncio.run(evaluate_retrieval_settings())
