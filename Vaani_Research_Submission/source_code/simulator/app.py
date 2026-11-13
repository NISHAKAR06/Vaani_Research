"""
Stand-in Model Service: Standalone FastAPI Application (Port 8001).
Simulates real Groq provider behavior:
- Calibrated base latency and jitter
- RPM, TPM, RPD, and TPD throttling (HTTP 429)
- Overload slowdown under concurrent load
- Transient 500 errors and 408 timeouts
- Real SSE chunk streaming
- Repeatable reset endpoints for load experiments
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from src.simulator.rate_limiter import SimulatorRateLimiter
from src.simulator.load_controller import LoadController
from src.simulator.streaming import stream_text_chunks

app = FastAPI(title="The Relay - Stand-in Model Service", version="1.0.0")

# Global Simulator State
rate_limiter = SimulatorRateLimiter(
    rpm_limit=30,
    tpm_limit=6000,
    daily_request_limit=1000,
    daily_token_limit=100000,
    max_concurrency=5,
    retry_after_seconds=5.0
)
load_controller = LoadController(
    base_latency_ms=380.0,
    latency_jitter_ms=110.0,
    first_token_latency_ms=180.0,
    overload_latency_multiplier=1.85,
    failure_probability=0.04,
    timeout_probability=0.02,
    seed=42
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "llama-3.3-70b-versatile-standin"
    messages: List[ChatMessage]
    stream: bool = False
    temperature: float = 0.0
    max_tokens: int = 1024

class ResetRequest(BaseModel):
    rpm_limit: Optional[int] = None
    tpm_limit: Optional[int] = None
    daily_request_limit: Optional[int] = None
    failure_probability: Optional[float] = None
    base_latency_ms: Optional[float] = None

@app.post("/simulator/reset")
async def reset_simulator(req: ResetRequest):
    """Reset quotas, counters, and adjust simulation parameters."""
    rate_limiter.reset(
        new_rpm=req.rpm_limit,
        new_tpm=req.tpm_limit,
        new_daily_budget=req.daily_request_limit
    )
    if req.failure_probability is not None:
        load_controller.failure_probability = req.failure_probability
    if req.base_latency_ms is not None:
        load_controller.base_latency_ms = req.base_latency_ms
    return {
        "status": "reset_complete",
        "rpm_limit": rate_limiter.rpm_limit,
        "daily_request_limit": rate_limiter.daily_request_limit,
        "failure_probability": load_controller.failure_probability
    }

@app.get("/simulator/status")
async def get_status():
    """Retrieve current in-flight load and quota consumption."""
    return {
        "rpm_limit": rate_limiter.rpm_limit,
        "active_concurrency": rate_limiter.active_concurrency,
        "daily_requests_used": rate_limiter.daily_requests_used,
        "daily_request_limit": rate_limiter.daily_request_limit,
    }

def synthesize_standin_content(messages: List[ChatMessage]) -> str:
    """Extract query and passages to generate plausible cited answer content."""
    user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "").lower()
    
    # 1. Attention Is All You Need (1706.03762v7)
    if "scaling factor" in user_msg or ("dot product" in user_msg and "scaled" in user_msg):
        return (
            "In Scaled Dot-Product Attention, a scaling factor of 1 / sqrt(d_k) is applied to counteract "
            "the effect of large dot products pushing the softmax function into regions with extremely small gradients [arXiv:1706.03762v7, p.4, §3.2.1]."
        )
    elif "layers and attention heads" in user_msg or ("encoder" in user_msg and "d_model" in user_msg):
        return (
            "The base Transformer encoder consists of N = 6 identical layers, each with h = 8 parallel attention heads, "
            "and an embedding dimensionality of d_model = 512 [arXiv:1706.03762v7, p.3, §3.1]."
        )
    elif "positional encoding" in user_msg:
        return (
            "Positional encodings use sine and cosine functions of varying frequencies: "
            "PE(pos, 2i) = sin(pos / 10000^(2i/d_model)) and PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model)) [arXiv:1706.03762v7, p.6, §3.5]."
        )
    elif "bleu score" in user_msg or "wmt 2014" in user_msg:
        return (
            "The Transformer (big) model achieved a state-of-the-art BLEU score of 28.4 on the WMT 2014 English-to-German translation task [arXiv:1706.03762v7, p.8, §5.1]."
        )
    # 2. Moshi (2410.00037v1)
    elif "mimi" in user_msg or "sampling rate" in user_msg or "bitrate" in user_msg:
        return (
            "The Mimi neural audio codec operates on 24 kHz audio, producing acoustic tokens at a frame rate of 12.5 Hz "
            "with an overall bitrate of 1.1 kbps [arXiv:2410.00037v1, p.8, §3.1]."
        )
    elif "overall latency" in user_msg or "frame size" in user_msg:
        return (
            "Moshi achieves a theoretical overall latency of 160 ms with an acoustic frame size of 80 ms [arXiv:2410.00037v1, p.2, §1]."
        )
    elif "parameters does the moshi" in user_msg or "helium" in user_msg or "backbone" in user_msg:
        return (
            "The Moshi foundation model comprises 7.5 billion parameters and is built upon the Helium 7B text model backbone [arXiv:2410.00037v1, p.9, §3.2]."
        )
    elif "synthetic multi-stream dialogue" in user_msg or "hours" in user_msg:
        return (
            "Moshi was pre-trained on a synthetic conversational dataset comprising approximately 170,000 hours of multi-stream spoken dialogue [arXiv:2410.00037v1, p.13, §4.2]."
        )
    # 3. Dynamic Chunking (2507.07955v2)
    elif "motivation for dynamic chunking" in user_msg or "static chunking" in user_msg:
        return (
            "Static chunking rigidly breaks sequences at arbitrary token boundaries, splitting semantic units. "
            "Dynamic chunking adaptively learns chunk boundaries conditioned on semantic context [arXiv:2507.07955v2, p.2, §1]."
        )
    elif "boundary predictor" in user_msg or "segment ends" in user_msg:
        return (
            "The boundary predictor employs a lightweight module estimating boundary probability p_t in [0, 1] at each step, "
            "emitting boundaries adaptively [arXiv:2507.07955v2, p.3, §2.1]."
        )
    elif "pooling mechanism" in user_msg or "within each predicted" in user_msg:
        return (
            "Within each predicted chunk, attention pooling or weighted mean pooling aggregates variable token spans "
            "into a single hierarchical representation [arXiv:2507.07955v2, p.4, §2.2]."
        )
    elif "computational complexity reduction" in user_msg or "quadratic" in user_msg:
        return (
            "Dynamic chunking reduces full O(T^2) attention complexity to hierarchical O(T*B + (T/B)^2) sub-quadratic cost [arXiv:2507.07955v2, p.2, §1]."
        )
    # 4. Cross-Paper Comparisons
    elif "original transformer" in user_msg and "dynamic chunking" in user_msg:
        return (
            "The original Transformer computes global pairwise attention with O(N^2) complexity [arXiv:1706.03762v7, p.4, §3.2.1]. "
            "Dynamic Chunking decomposes sequences into two levels to achieve sub-quadratic complexity on long inputs [arXiv:2507.07955v2, p.2, §1]."
        )
    elif "temporal continuous streaming" in user_msg or ("moshi" in user_msg and "bidirectional" in user_msg):
        return (
            "The Transformer encoder uses bidirectional self-attention requiring complete sequence visibility [arXiv:1706.03762v7, p.2, §1]. "
            "In contrast, Moshi uses causal autoregressive attention with 80ms audio frames for real-time dialogue [arXiv:2410.00037v1, p.2, §1]."
        )
    elif "continuous high-rate" in user_msg or ("moshi" in user_msg and "dynamic chunking" in user_msg):
        return (
            "Moshi compresses 24 kHz speech to 12.5 Hz tokens using the Mimi neural codec [arXiv:2410.00037v1, p.8, §3.1], "
            "while Dynamic Chunking adaptively groups sequence tokens via boundary predictors into hierarchical chunks [arXiv:2507.07955v2, p.4, §2.2]."
        )
    elif "cannot answer" in user_msg or "refuse" in user_msg:
        return (
            "The provided library does not contain sufficient evidence to answer this question."
        )
    else:
        return (
            "The Transformer architecture replaces recurrent layers with multi-head self-attention mechanisms [arXiv:1706.03762v7, p.2, §1]. "
            "This enables significantly faster training via full parallelization [arXiv:1706.03762v7, p.6, §4]."
        )

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    # 1. Rate Limiting and Quota Check
    estimated_tokens = sum(len(m.content.split()) for m in req.messages) + 150
    allowed, reason, retry_after = await rate_limiter.check_and_acquire(estimated_tokens)

    if not allowed:
        headers = {
            "x-ratelimit-limit-requests": str(rate_limiter.rpm_limit),
            "x-ratelimit-remaining-requests": "0",
            "x-ratelimit-reset-requests": f"{retry_after or 5:.1f}s",
        }
        if retry_after:
            headers["retry-after"] = str(int(retry_after))
        return JSONResponse(
            status_code=429,
            content={"error": {"message": reason, "type": "rate_limit_exceeded"}},
            headers=headers
        )

    stream_started = False
    try:
        # 2. Fault Injection Check
        should_fault, fault_msg, status_code = load_controller.check_fault_injection()
        if should_fault:
            if status_code == 408:
                await asyncio.sleep(2.0)
            return JSONResponse(
                status_code=status_code,
                content={"error": {"message": fault_msg, "type": "simulated_error"}}
            )

        # 3. Latency Calculation under Concurrency Load
        ttft_ms, total_ms = load_controller.calculate_latencies(rate_limiter.active_concurrency)
        content = synthesize_standin_content(req.messages)

        # 4. Handle Streaming vs Non-Streaming
        if req.stream:
            stream_started = True
            return StreamingResponse(
                stream_text_chunks(
                    full_text=content,
                    ttft_seconds=ttft_ms / 1000.0,
                    total_seconds=total_ms / 1000.0,
                    model_id=req.model,
                    cleanup_callback=rate_limiter.release_concurrency
                ),
                media_type="text/event-stream"
            )

        # Non-streaming wait
        await asyncio.sleep(total_ms / 1000.0)

        prompt_tokens = estimated_tokens - 150
        comp_tokens = len(content.split())
        headers = {
            "x-ratelimit-limit-requests": str(rate_limiter.rpm_limit),
            "x-ratelimit-remaining-requests": str(max(0, rate_limiter.rpm_limit - len(rate_limiter.request_timestamps))),
            "x-ratelimit-reset-requests": "2.4s",
            "x-ratelimit-limit-tokens": str(rate_limiter.tpm_limit),
        }

        return JSONResponse(
            status_code=200,
            content={
                "id": f"chatcmpl-sim-{int(time.time()*1000)}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": comp_tokens,
                    "total_tokens": prompt_tokens + comp_tokens
                }
            },
            headers=headers
        )

    finally:
        if not stream_started:
            await rate_limiter.release_concurrency()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
