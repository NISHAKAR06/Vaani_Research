"""
Streaming module for the Stand-in Model Service.
Yields SSE / JSON chunk streams with calibrated inter-token delays.
Guarantees concurrency slot release upon stream completion or client disconnect.
"""

import asyncio
import json
from typing import AsyncIterator, List, Optional, Callable, Awaitable

async def stream_text_chunks(
    full_text: str,
    ttft_seconds: float,
    total_seconds: float,
    model_id: str,
    cleanup_callback: Optional[Callable[[], Awaitable[None]]] = None
) -> AsyncIterator[str]:
    """
    Yields Server-Sent Events (SSE) chunks mimicking OpenAI / Groq streaming responses.
    Executes cleanup_callback on stream completion or cancellation.
    """
    try:
        # Wait until calibrated TTFT
        await asyncio.sleep(ttft_seconds)

        words = full_text.split()
        if not words:
            words = ["I", "have", "no", "information."]

        remaining_time = max(0.01, total_seconds - ttft_seconds)
        delay_per_chunk = remaining_time / len(words)

        for idx, word in enumerate(words):
            chunk_data = {
                "id": f"sim-stream-{idx}",
                "object": "chat.completion.chunk",
                "model": model_id,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": (" " if idx > 0 else "") + word},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"
            await asyncio.sleep(delay_per_chunk)

        final_chunk = {
            "id": "sim-stream-final",
            "object": "chat.completion.chunk",
            "model": model_id,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    finally:
        if cleanup_callback is not None:
            await cleanup_callback()
