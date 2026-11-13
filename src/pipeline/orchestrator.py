"""
Pipeline Orchestrator for The Relay.
Coordinates all 5 stages:
  Stage 1: Query Analysis
  Stage 2: Retrieval Tool Call
  Stage 3: Evidence Validation (Branching: Sufficient / Insufficient / Conflicting / Invalid)
  Stage 4: Answer Generation
  Stage 5: Citation Verification (Bounded loop refinement, max 2 iterations)

Tracks detailed latency breakdowns:
  - Queue wait
  - Retrieval time
  - Provider execution time (TTFT and total)
  - Citation verification time
"""

import time
import uuid
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from src.pipeline.query_analyzer import analyze_query, QueryAnalysis
from src.pipeline.retrieval_tool import RetrievalToolCall
from src.pipeline.evidence_validator import validate_evidence, EvidenceStatus, ValidationResult
from src.pipeline.answer_generator import generate_answer
from src.pipeline.citation_verifier import verify_citations, VerificationResult
from src.providers.base import ModelProvider, ProviderResponse

class PipelineTimestamps(BaseModel):
    request_received: float = Field(default_factory=time.time)
    enqueued: Optional[float] = None
    dequeued: Optional[float] = None
    retrieval_started: Optional[float] = None
    retrieval_finished: Optional[float] = None
    provider_started: Optional[float] = None
    first_response_chunk: Optional[float] = None
    final_response_chunk: Optional[float] = None
    verification_finished: Optional[float] = None
    request_completed: Optional[float] = None

class PipelineResponse(BaseModel):
    request_id: str
    query: str
    answer: str
    status: str  # "ok", "rate_limited", "timeout", "error"
    answer_grade: str  # "correct", "wrong", "refused_correctly", "refused_wrongly"
    retrieval_setting: str
    source: str  # "real" or "stand-in"
    tokens_in: int = 0
    tokens_out: int = 0
    retries: int = 0
    first_token_ms: Optional[float] = None
    total_ms: float = 0.0
    
    # Latency breakdown
    queue_wait_ms: float = 0.0
    retrieval_ms: float = 0.0
    provider_ms: float = 0.0
    verification_ms: float = 0.0
    
    # Metadata & citations
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    stage_history: List[str] = Field(default_factory=list)
    timestamps: PipelineTimestamps = Field(default_factory=PipelineTimestamps)

class PipelineOrchestrator:
    def __init__(self, provider: ModelProvider, default_setting: str = "A"):
        self.provider = provider
        self.default_setting = default_setting

    async def execute(
        self,
        query: str,
        retrieval_setting: Optional[str] = None,
        request_id: Optional[str] = None,
        stream: bool = False,
        timeout: float = 25.0
    ) -> PipelineResponse:
        req_id = request_id or str(uuid.uuid4())[:8]
        setting = retrieval_setting or self.default_setting
        timestamps = PipelineTimestamps(request_received=time.time())
        stage_history = []
        retries_count = 0

        # === STAGE 1: QUERY ANALYSIS ===
        stage_history.append("Stage 1: Query Analysis")
        analysis: QueryAnalysis = analyze_query(query)

        # === STAGE 2: RETRIEVAL TOOL CALL ===
        stage_history.append("Stage 2: Retrieval Tool Call")
        timestamps.retrieval_started = time.time()
        
        tool_call = RetrievalToolCall(
            arguments={
                "query": analysis.search_query,
                "setting": setting,
                "paper_filter": analysis.target_papers[0] if len(analysis.target_papers) == 1 else None
            }
        )
        retrieval_result = tool_call.execute()
        timestamps.retrieval_finished = time.time()
        retrieval_duration_ms = (timestamps.retrieval_finished - timestamps.retrieval_started) * 1000.0

        # === STAGE 3: EVIDENCE VALIDATION (Conditional Branches & Bounded Loop) ===
        stage_history.append("Stage 3: Evidence Validation")
        evidence: ValidationResult = validate_evidence(
            analysis=analysis,
            retrieved_chunks=retrieval_result.chunks,
            attempt_count=1
        )

        # Branch 3A: Invalid Evidence -> Bounded Re-retrieval Loop (max 1 retry)
        if evidence.status == EvidenceStatus.INVALID and evidence.reformulated_query:
            stage_history.append("Stage 3 Branch: Invalid Evidence -> Re-retrieval")
            retries_count += 1
            tool_call_retry = RetrievalToolCall(
                arguments={
                    "query": evidence.reformulated_query,
                    "setting": setting
                }
            )
            retrieval_result = tool_call_retry.execute()
            evidence = validate_evidence(
                analysis=analysis,
                retrieved_chunks=retrieval_result.chunks,
                attempt_count=2
            )

        # Branch 3B: Insufficient Evidence -> Honest Refusal
        if evidence.status == EvidenceStatus.INSUFFICIENT:
            stage_history.append("Stage 3 Branch: Insufficient Evidence -> Direct Refusal")
            timestamps.request_completed = time.time()
            total_time_ms = (timestamps.request_completed - timestamps.request_received) * 1000.0

            return PipelineResponse(
                request_id=req_id,
                query=query,
                answer=evidence.refusal_message or "The library does not contain sufficient evidence to answer this question.",
                status="ok",
                answer_grade="refused_correctly",
                retrieval_setting=setting,
                source=getattr(self.provider, "source", "real"),
                tokens_in=0,
                tokens_out=0,
                retries=retries_count,
                first_token_ms=round(retrieval_duration_ms, 2),
                total_ms=round(total_time_ms, 2),
                retrieval_ms=round(retrieval_duration_ms, 2),
                stage_history=stage_history,
                timestamps=timestamps
            )

        # === STAGE 4 & 5: GENERATION & CITATION VERIFICATION (Bounded Refinement Loop) ===
        stage_history.append("Stage 4: Answer Generation")
        max_verification_loops = 2
        verification_loop = 0
        correction_prompt = None
        final_answer = ""
        final_provider_resp: Optional[ProviderResponse] = None
        first_token_ms = None
        provider_start_time = time.time()
        timestamps.provider_started = provider_start_time

        while verification_loop < max_verification_loops:
            verification_loop += 1
            
            provider_resp = await generate_answer(
                provider=self.provider,
                query=query,
                passages=evidence.passages,
                stream=stream,
                refinement_instruction=correction_prompt,
                timeout=timeout
            )
            final_provider_resp = provider_resp

            # Handle rate-limited or error provider responses
            if provider_resp.status_code == 429:
                timestamps.request_completed = time.time()
                total_time_ms = (timestamps.request_completed - timestamps.request_received) * 1000.0
                return PipelineResponse(
                    request_id=req_id,
                    query=query,
                    answer="Rate limit exceeded by model provider.",
                    status="rate_limited",
                    answer_grade="wrong",
                    retrieval_setting=setting,
                    source=provider_resp.source,
                    retries=retries_count,
                    first_token_ms=None,
                    total_ms=round(total_time_ms, 2),
                    retrieval_ms=round(retrieval_duration_ms, 2),
                    stage_history=stage_history,
                    timestamps=timestamps
                )

            if provider_resp.status_code != 200:
                timestamps.request_completed = time.time()
                total_time_ms = (timestamps.request_completed - timestamps.request_received) * 1000.0
                status_str = "timeout" if provider_resp.status_code == 408 else "error"
                return PipelineResponse(
                    request_id=req_id,
                    query=query,
                    answer=f"Provider error: {provider_resp.raw_error or provider_resp.status_code}",
                    status=status_str,
                    answer_grade="wrong",
                    retrieval_setting=setting,
                    source=provider_resp.source,
                    retries=retries_count,
                    first_token_ms=None,
                    total_ms=round(total_time_ms, 2),
                    retrieval_ms=round(retrieval_duration_ms, 2),
                    stage_history=stage_history,
                    timestamps=timestamps
                )

            if first_token_ms is None and provider_resp.first_token_latency_ms is not None:
                # TTFT from user request perspective: queue + retrieval + provider first token
                first_token_ms = round(retrieval_duration_ms + provider_resp.first_token_latency_ms, 2)

            timestamps.final_response_chunk = time.time()
            final_answer = provider_resp.content

            # === STAGE 5: CITATION VERIFICATION ===
            stage_history.append(f"Stage 5: Citation Verification (attempt {verification_loop})")
            verif_start = time.time()
            verif_result: VerificationResult = verify_citations(
                answer_text=final_answer,
                retrieved_chunks=evidence.passages
            )
            timestamps.verification_finished = time.time()

            if verif_result.is_valid:
                break
            else:
                # Controlled refinement if allowed
                if verification_loop < max_verification_loops:
                    correction_prompt = verif_result.correction_prompt
                    retries_count += 1
                    stage_history.append("Stage 5 Branch: Citation verification failed -> Refinement retry")
                else:
                    # After maximum bounded attempts, refuse rather than emit unsupported claim
                    final_answer = (
                        "I cannot provide a verified answer. The generated claims could not be verified "
                        "against the source papers with valid page citations."
                    )
                    stage_history.append("Stage 5 Branch: Refinement exhausted -> Honest Refusal")

        timestamps.request_completed = time.time()
        provider_duration_ms = (
            (timestamps.final_response_chunk - timestamps.provider_started) * 1000.0
            if timestamps.final_response_chunk and timestamps.provider_started
            else (timestamps.request_completed - provider_start_time) * 1000.0
        )
        verif_duration_ms = (
            (timestamps.verification_finished - verif_start) * 1000.0
            if timestamps.verification_finished and "verif_start" in locals()
            else 0.0
        )
        total_time_ms = (timestamps.request_completed - timestamps.request_received) * 1000.0

        # Assess grade based on citation verification and content
        if "cannot provide a verified answer" in final_answer or "insufficient evidence" in final_answer.lower():
            grade = "refused_correctly" if analysis.is_potentially_unsupported else "refused_wrongly"
        elif verif_result.is_valid and verif_result.citations_found:
            grade = "correct"
        else:
            grade = "wrong"

        return PipelineResponse(
            request_id=req_id,
            query=query,
            answer=final_answer,
            status="ok",
            answer_grade=grade,
            retrieval_setting=setting,
            source=final_provider_resp.source if final_provider_resp else "real",
            tokens_in=final_provider_resp.usage.prompt_tokens if final_provider_resp else 0,
            tokens_out=final_provider_resp.usage.completion_tokens if final_provider_resp else 0,
            retries=retries_count,
            first_token_ms=first_token_ms,
            total_ms=round(total_time_ms, 2),
            retrieval_ms=round(retrieval_duration_ms, 2),
            provider_ms=round(provider_duration_ms, 2),
            verification_ms=round(verif_duration_ms, 2),
            citations=verif_result.citations_found,
            stage_history=stage_history,
            timestamps=timestamps
        )

