"""
Regression tests for Stand-in streaming concurrency lifecycle tracking.
"""

import pytest
import asyncio
from src.simulator.rate_limiter import SimulatorRateLimiter
from src.simulator.streaming import stream_text_chunks

@pytest.mark.asyncio
async def test_streaming_holds_concurrency_until_completion():
    limiter = SimulatorRateLimiter(max_concurrency=2)
    
    # Acquire slot 1
    allowed, _, _ = await limiter.check_and_acquire()
    assert allowed is True
    assert limiter.active_concurrency == 1

    # Start stream generator with cleanup_callback
    gen = stream_text_chunks(
        full_text="word1 word2 word3",
        ttft_seconds=0.02,
        total_seconds=0.06,
        model_id="test-model",
        cleanup_callback=limiter.release_concurrency
    )

    # Concurrency must still be 1 while streaming is in progress
    chunks = []
    async for chunk in gen:
        chunks.append(chunk)
        # While consuming chunks, concurrency slot is still held
        assert limiter.active_concurrency == 1

    # After consumption finishes, callback has fired and concurrency is 0
    assert limiter.active_concurrency == 0
    assert len(chunks) > 0
