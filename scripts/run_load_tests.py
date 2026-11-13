"""
Load Testing Runner for The Relay.
Executes the 5 required load scenarios:
1. Steady traffic
2. Sudden burst
3. Sustained overload
4. Per-minute limit halved
5. Daily budget exhausted
Communicates with the Stand-in Model Service (or real Groq for steady)
and logs granular request events to experiments/raw/request_events.jsonl.
"""

import asyncio
import httpx
import time
import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from src.evaluation.evaluator import load_evaluation_questions
from src.pipeline.orchestrator import PipelineOrchestrator
from src.providers.simulator_provider import SimulatorProvider
from src.providers.groq_provider import GroqProvider
from src.observability.tracing import RequestTracer
from src.experiments.load_generator import LoadGenerator

async def reset_simulator(
    rpm_limit: int = 30,
    daily_budget: int = 1000,
    failure_probability: float = 0.04
):
    """Call simulator /reset endpoint before each scenario."""
    url = f"{settings.standin_url}/simulator/reset"
    payload = {
        "rpm_limit": rpm_limit,
        "daily_request_limit": daily_budget,
        "failure_probability": failure_probability
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"[WARN] Could not connect to simulator reset: {e}")

async def run_all_load_scenarios(use_real_for_steady: bool = False):
    questions = load_evaluation_questions()
    tracer = RequestTracer()

    # Setup provider
    if use_real_for_steady:
        groq_provider = GroqProvider()
        steady_provider = groq_provider if groq_provider.is_configured() else SimulatorProvider()
        steady_source = "real" if groq_provider.is_configured() else "stand-in"
    else:
        steady_provider = SimulatorProvider()
        steady_source = "stand-in"

    standin_provider = SimulatorProvider()

    print("\n=======================================================")
    print("       STARTING THE RELAY LOAD EXPERIMENTS             ")
    print("=======================================================")

    # 1. SCENARIO 1: STEADY TRAFFIC
    print("\n--- Scenario 1: Steady Traffic (15 RPM, 10 requests) ---")
    await reset_simulator(rpm_limit=30, daily_budget=1000, failure_probability=0.0)
    orchestrator_steady = PipelineOrchestrator(provider=steady_provider, default_setting="B")
    gen_steady = LoadGenerator(orchestrator_steady, tracer, questions)
    res_steady = await gen_steady.run_steady(request_count=10, rate_rpm=15.0, source=steady_source)
    print(f"  [DONE] Sent {res_steady.total_sent} requests in {res_steady.duration_seconds}s")

    # 2. SCENARIO 2: SUDDEN BURST
    print("\n--- Scenario 2: Sudden Burst (15 simultaneous requests) ---")
    await reset_simulator(rpm_limit=30, daily_budget=1000, failure_probability=0.04)
    orchestrator_burst = PipelineOrchestrator(provider=standin_provider, default_setting="B")
    gen_burst = LoadGenerator(orchestrator_burst, tracer, questions)
    res_burst = await gen_burst.run_burst(burst_size=15, source="stand-in")
    print(f"  [DONE] Burst completed: {res_burst.total_sent} requests in {res_burst.duration_seconds}s (rate: {res_burst.offered_rate_rpm} RPM)")

    # 3. SCENARIO 3: SUSTAINED OVERLOAD
    print("\n--- Scenario 3: Sustained Overload (90 RPM, 25 requests) ---")
    await reset_simulator(rpm_limit=30, daily_budget=1000, failure_probability=0.05)
    orchestrator_overload = PipelineOrchestrator(provider=standin_provider, default_setting="B")
    gen_overload = LoadGenerator(orchestrator_overload, tracer, questions)
    res_overload = await gen_overload.run_sustained_overload(request_count=25, rate_rpm=90.0, source="stand-in")
    print(f"  [DONE] Sustained overload completed: {res_overload.total_sent} requests in {res_overload.duration_seconds}s")

    # 4. SCENARIO 4: PER-MINUTE LIMIT HALVED
    print("\n--- Scenario 4: Per-Minute Limit Halved (10 RPM cap, 12 requests) ---")
    await reset_simulator(rpm_limit=10, daily_budget=1000, failure_probability=0.0)
    orchestrator_halved = PipelineOrchestrator(provider=standin_provider, default_setting="B")
    gen_halved = LoadGenerator(orchestrator_halved, tracer, questions)
    res_halved = await gen_halved.run_throttled(
        scenario_name="per_minute_halved",
        request_count=12,
        rate_rpm=30.0,
        source="stand-in"
    )
    print(f"  [DONE] Halved RPM scenario completed: {res_halved.total_sent} requests in {res_halved.duration_seconds}s")

    # 5. SCENARIO 5: DAILY BUDGET EXHAUSTED
    print("\n--- Scenario 5: Daily Budget Exhausted (0 daily budget, 10 requests) ---")
    await reset_simulator(rpm_limit=30, daily_budget=0, failure_probability=0.0)
    orchestrator_exhausted = PipelineOrchestrator(provider=standin_provider, default_setting="B")
    gen_exhausted = LoadGenerator(orchestrator_exhausted, tracer, questions)
    res_exhausted = await gen_exhausted.run_throttled(
        scenario_name="daily_budget_exhausted",
        request_count=10,
        rate_rpm=20.0,
        source="stand-in"
    )
    print(f"  [DONE] Daily budget exhausted scenario completed: {res_exhausted.total_sent} requests in {res_exhausted.duration_seconds}s")

    print("\n[ALL SCENARIOS COMPLETED] Raw traces preserved in experiments/raw/request_events.jsonl")

if __name__ == "__main__":
    asyncio.run(run_all_load_scenarios())
