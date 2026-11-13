"""
FastAPI Routes for The Relay.
Provides:
  - POST /query: Executes the 5-stage pipeline under admission control
  - GET /health: Health check and provider availability
  - GET /metrics: Active queue and throughput metrics
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from config.settings import settings
from src.api.schemas import QueryRequest, QueryResponse, CitationSchema
from src.pipeline.orchestrator import PipelineOrchestrator
from src.providers.groq_provider import GroqProvider
from src.providers.simulator_provider import SimulatorProvider
from src.resilience.admission_control import AdmissionController

router = APIRouter()

# Providers
_groq_provider = GroqProvider()
_simulator_provider = SimulatorProvider()
_admission_controller = AdmissionController(
    max_concurrency=settings.default_max_concurrency,
    queue_capacity=settings.default_queue_capacity,
    rpm_limit=settings.default_rpm_budget,
    daily_limit=settings.default_daily_request_budget
)

@router.post("/query", response_model=QueryResponse)
async def handle_query(req: QueryRequest):
    # Select provider
    if req.source == "real":
        if not _groq_provider.is_configured():
            raise HTTPException(
                status_code=503,
                detail="GROQ_API_KEY is not configured on this server. Please use source='stand-in' or set GROQ_API_KEY."
            )
        provider = _groq_provider
    else:
        provider = _simulator_provider

    # Admission Control & Queueing
    admitted, reason, queue_wait_ms = await _admission_controller.admit_request(
        request_id="api_req",
        timeout_seconds=req.timeout_seconds
    )
    if not admitted:
        status_code = 429 if "queue is full" in reason.lower() or "limit" in reason.lower() else 503
        raise HTTPException(status_code=status_code, detail=reason)

    try:
        orchestrator = PipelineOrchestrator(provider=provider, default_setting=req.retrieval_setting)
        pipeline_resp = await orchestrator.execute(
            query=req.query,
            retrieval_setting=req.retrieval_setting,
            stream=req.stream,
            timeout=req.timeout_seconds
        )
        pipeline_resp.queue_wait_ms = queue_wait_ms
        _admission_controller.release_slot(success=(pipeline_resp.status == "ok"))

        citations = [
            CitationSchema(
                paper=c["paper"],
                page=c["page"],
                section=c.get("section", ""),
                raw=c["raw"]
            )
            for c in pipeline_resp.citations
        ]

        return QueryResponse(
            request_id=pipeline_resp.request_id,
            query=pipeline_resp.query,
            answer=pipeline_resp.answer,
            status=pipeline_resp.status,
            answer_grade=pipeline_resp.answer_grade,
            retrieval_setting=pipeline_resp.retrieval_setting,
            source=pipeline_resp.source,
            tokens_in=pipeline_resp.tokens_in,
            tokens_out=pipeline_resp.tokens_out,
            retries=pipeline_resp.retries,
            first_token_ms=pipeline_resp.first_token_ms,
            total_ms=pipeline_resp.total_ms,
            citations=citations,
            latency_breakdown={
                "queue_wait_ms": pipeline_resp.queue_wait_ms,
                "retrieval_ms": pipeline_resp.retrieval_ms,
                "provider_ms": pipeline_resp.provider_ms,
                "verification_ms": pipeline_resp.verification_ms,
            }
        )
    except Exception as e:
        _admission_controller.release_slot(success=False)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "groq_configured": _groq_provider.is_configured(),
        "standin_url": settings.standin_url,
        "circuit_breaker_state": _admission_controller.circuit_breaker.state.value
    }

