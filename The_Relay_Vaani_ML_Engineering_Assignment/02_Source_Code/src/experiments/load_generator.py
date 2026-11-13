"""
Asynchronous Load Generator for The Relay.
Generates configurable load shapes:
- Steady: Constant inter-arrival pacing
- Burst: Concurrent batch spikes
- Sustained Overload: Continuous high-frequency traffic
- Throttled / Quota Exhaustion shapes
"""

import asyncio
import time
import uuid
from typing import List, Dict, Any, Callable, Coroutine
from dataclasses import dataclass

from src.pipeline.orchestrator import PipelineOrchestrator, PipelineResponse
from src.observability.tracing import RequestTracer

@dataclass
class LoadResult:
    scenario_name: str
    source: str
    total_sent: int
    duration_seconds: float
    offered_rate_rpm: float
    responses: List[PipelineResponse]

class LoadGenerator:
    def __init__(
        self,
        orchestrator: PipelineOrchestrator,
        tracer: RequestTracer,
        questions: List[Dict[str, Any]]
    ):
        self.orchestrator = orchestrator
        self.tracer = tracer
        self.questions = questions

    async def _send_single_request(
        self,
        question_idx: int,
        scenario_name: str,
        retrieval_setting: str = "A"
    ) -> PipelineResponse:
        q_spec = self.questions[question_idx % len(self.questions)]
        req_id = f"{scenario_name[:3]}-{uuid.uuid4().hex[:6]}"
        start_time_iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

        resp = await self.orchestrator.execute(
            query=q_spec["question"],
            retrieval_setting=retrieval_setting,
            request_id=req_id
        )

        # Log event to JSONL
        self.tracer.log_request_event(
            request_id=resp.request_id,
            scenario=scenario_name,
            source=resp.source,
            start_time_iso=start_time_iso,
            first_token_ms=resp.first_token_ms,
            total_ms=resp.total_ms,
            status=resp.status,
            retries=resp.retries,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            retrieval_setting=resp.retrieval_setting,
            answer_grade=resp.answer_grade,
            latency_breakdown={
                "queue_wait_ms": resp.queue_wait_ms,
                "retrieval_ms": resp.retrieval_ms,
                "provider_ms": resp.provider_ms,
                "verification_ms": resp.verification_ms,
            },
            timestamps=resp.timestamps.model_dump()
        )
        return resp

    async def run_steady(
        self,
        request_count: int = 10,
        rate_rpm: float = 15.0,
        source: str = "real"
    ) -> LoadResult:
        """Steady arrival rate with fixed pacing."""
        interval = 60.0 / rate_rpm
        responses = []
        start_time = time.perf_counter()

        for i in range(request_count):
            resp = await self._send_single_request(i, "steady")
            responses.append(resp)
            if i < request_count - 1:
                await asyncio.sleep(interval)

        duration = time.perf_counter() - start_time
        return LoadResult(
            scenario_name="steady",
            source=source,
            total_sent=len(responses),
            duration_seconds=round(duration, 2),
            offered_rate_rpm=rate_rpm,
            responses=responses
        )

    async def run_burst(
        self,
        burst_size: int = 15,
        source: str = "stand-in"
    ) -> LoadResult:
        """Sudden simultaneous spike of concurrent requests."""
        start_time = time.perf_counter()
        tasks = [
            self._send_single_request(i, "burst")
            for i in range(burst_size)
        ]
        responses = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start_time
        offered_rpm = round((burst_size / max(0.1, duration)) * 60.0, 1)

        return LoadResult(
            scenario_name="burst",
            source=source,
            total_sent=len(responses),
            duration_seconds=round(duration, 2),
            offered_rate_rpm=offered_rpm,
            responses=list(responses)
        )

    async def run_sustained_overload(
        self,
        request_count: int = 25,
        rate_rpm: float = 90.0,
        source: str = "stand-in"
    ) -> LoadResult:
        """Continuous request volume exceeding nominal capacity."""
        interval = 60.0 / rate_rpm
        responses = []
        start_time = time.perf_counter()

        # Fire requests at high rate using background tasks
        active_tasks = []
        for i in range(request_count):
            t = asyncio.create_task(self._send_single_request(i, "sustained_overload"))
            active_tasks.append(t)
            await asyncio.sleep(interval)

        responses = await asyncio.gather(*active_tasks)
        duration = time.perf_counter() - start_time
        return LoadResult(
            scenario_name="sustained_overload",
            source=source,
            total_sent=len(responses),
            duration_seconds=round(duration, 2),
            offered_rate_rpm=rate_rpm,
            responses=list(responses)
        )

    async def run_throttled(
        self,
        scenario_name: str,
        request_count: int = 12,
        rate_rpm: float = 30.0,
        source: str = "stand-in"
    ) -> LoadResult:
        """Run under throttled RPM or exhausted daily budget conditions."""
        interval = 60.0 / rate_rpm
        start_time = time.perf_counter()
        tasks = []
        for i in range(request_count):
            t = asyncio.create_task(self._send_single_request(i, scenario_name))
            tasks.append(t)
            await asyncio.sleep(interval)

        responses = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start_time
        return LoadResult(
            scenario_name=scenario_name,
            source=source,
            total_sent=len(responses),
            duration_seconds=round(duration, 2),
            offered_rate_rpm=rate_rpm,
            responses=list(responses)
        )

