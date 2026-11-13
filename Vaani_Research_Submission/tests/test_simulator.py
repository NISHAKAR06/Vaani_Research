"""
Tests for Stand-in Model Service rate limiting, quota tracking, and latency calculations.
"""

import pytest
import asyncio
from src.simulator.rate_limiter import SimulatorRateLimiter
from src.simulator.load_controller import LoadController

@pytest.mark.asyncio
async def test_simulator_rate_limiter_rpm_exhaustion():
    limiter = SimulatorRateLimiter(rpm_limit=3, max_concurrency=10)
    
    # Send 3 allowed requests
    for i in range(3):
        allowed, reason, retry_after = await limiter.check_and_acquire(tokens_est := 10)
        assert allowed is True
        await limiter.release_concurrency()

    # 4th request must be rate limited
    allowed, reason, retry_after = await limiter.check_and_acquire(tokens_est := 10)
    assert allowed is False
    assert "Rate limit exceeded" in reason
    assert retry_after is not None and retry_after > 0

@pytest.mark.asyncio
async def test_simulator_daily_budget_exhaustion():
    limiter = SimulatorRateLimiter(daily_request_limit=2)
    
    # 1st request
    allowed, _, _ = await limiter.check_and_acquire()
    assert allowed is True
    await limiter.release_concurrency()

    # 2nd request
    allowed, _, _ = await limiter.check_and_acquire()
    assert allowed is True
    await limiter.release_concurrency()

    # 3rd request -> daily quota exceeded
    allowed, reason, _ = await limiter.check_and_acquire()
    assert allowed is False
    assert "Daily request budget exhausted" in reason

def test_load_controller_overload_multiplier():
    ctrl = LoadController(base_latency_ms=300.0, overload_latency_multiplier=2.0)
    
    # Unloaded (concurrency 1)
    ttft_1, total_1 = ctrl.calculate_latencies(current_concurrency=1)
    
    # Under heavy load (concurrency 8)
    ttft_8, total_8 = ctrl.calculate_latencies(current_concurrency=8)
    
    assert total_8 > total_1, f"Expected higher latency under concurrency load: {total_8} vs {total_1}"

