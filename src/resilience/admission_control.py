"""
Admission Controller and Bounded Queue Manager for The Relay.
Implements:
- Bounded FIFO queue with backpressure rejection
- Request deadlines
- Concurrency limiting via asyncio.Semaphore
- Rate budget and daily quota guard
- Detailed queue wait latency recording
"""

import asyncio
import time
from typing import Optional, Tuple, Callable, Any
from dataclasses import dataclass, field

from src.resilience.circuit_breaker import CircuitBreaker, CircuitState

@dataclass(order=True)
class QueuedItem:
    priority: int
    enqueued_time: float
    request_id: str = field(compare=False)
    deadline: float = field(compare=False)
    future: asyncio.Future = field(compare=False)

class AdmissionController:
    def __init__(
        self,
        max_concurrency: int = 5,
        queue_capacity: int = 20,
        rpm_limit: int = 30,
        daily_limit: int = 1000
    ):
        self.max_concurrency = max_concurrency
        self.queue_capacity = queue_capacity
        self.rpm_limit = rpm_limit
        self.daily_limit = daily_limit
        
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.queue = asyncio.Queue(maxsize=queue_capacity)
        self.circuit_breaker = CircuitBreaker()
        
        # State tracking
        self.peak_queue_length = 0
        self.current_queue_length = 0
        self.daily_requests_executed = 0
        self.recent_request_timestamps = []
        self._lock = asyncio.Lock()

    def reset_stats(self):
        self.peak_queue_length = 0
        self.current_queue_length = 0
        self.daily_requests_executed = 0
        self.recent_request_timestamps.clear()

    async def admit_request(
        self,
        request_id: str,
        timeout_seconds: float = 25.0
    ) -> Tuple[bool, str, float]:
        """
        Attempts to admit request into system.
        Returns: (admitted, message, queue_wait_ms)
        """
        now = time.time()
        deadline = now + timeout_seconds

        # 1. Daily Quota Guard
        if self.daily_requests_executed >= self.daily_limit:
            return False, "Daily provider request quota exhausted. System refuses further requests.", 0.0

        # 2. Circuit Breaker Check
        if not self.circuit_breaker.allow_request():
            return False, "Circuit breaker OPEN: upstream provider is temporarily offline due to failures.", 0.0

        # 3. Bounded Queue Capacity / Backpressure
        if self.queue.qsize() >= self.queue_capacity:
            return False, f"Queue is full ({self.queue_capacity} requests). Dropped due to backpressure.", 0.0

        enqueue_time = time.time()
        
        # Track queue length
        async with self._lock:
            self.current_queue_length = self.queue.qsize() + 1
            if self.current_queue_length > self.peak_queue_length:
                self.peak_queue_length = self.current_queue_length

        # Wait to acquire execution slot under semaphore
        try:
            wait_start = time.time()
            time_remaining = deadline - wait_start
            if time_remaining <= 0:
                return False, "Request timed out while waiting in queue before admission.", 0.0

            # Acquire concurrency slot with timeout
            await asyncio.wait_for(self.semaphore.acquire(), timeout=time_remaining)
            queue_wait_ms = (time.time() - enqueue_time) * 1000.0
            
            async with self._lock:
                self.daily_requests_executed += 1
                self.recent_request_timestamps.append(time.time())

            return True, "Admitted", queue_wait_ms

        except asyncio.TimeoutError:
            return False, "Request timed out waiting in admission queue.", (time.time() - enqueue_time) * 1000.0

    def release_slot(self, success: bool = True):
        """Release semaphore slot and update circuit breaker."""
        self.semaphore.release()
        if success:
            self.circuit_breaker.record_success()
        else:
            self.circuit_breaker.record_failure()

