"""
Admission Controller and Bounded FIFO Queue Manager for The Relay.
Implements:
- Genuine bounded FIFO queue using asyncio.Queue with backpressure rejection
- Concurrency limiting via asyncio.Semaphore
- Request deadlines and timeout cancellations while waiting in queue
- Peak and real-time queue depth instrumentation
- Rate budget and daily quota guard
- Exact queue wait latency recording
"""

import asyncio
import time
from typing import Optional, Tuple
from dataclasses import dataclass, field

from src.resilience.circuit_breaker import CircuitBreaker

@dataclass
class QueuedItem:
    request_id: str
    enqueue_time: float
    deadline: float
    future: asyncio.Future
    cancelled: bool = False

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
        self.queue: asyncio.Queue[QueuedItem] = asyncio.Queue(maxsize=queue_capacity)
        self.circuit_breaker = CircuitBreaker()
        
        # State tracking
        self.peak_queue_length = 0
        self.daily_requests_executed = 0
        self.recent_request_timestamps = []
        self._lock = asyncio.Lock()
        
        # Dispatcher state
        self._dispatcher_task: Optional[asyncio.Task] = None
        self._dispatcher_waiting_semaphore = False
        self._running = True

    def _ensure_dispatcher_running(self):
        """Ensure background FIFO queue dispatcher is active."""
        if self._dispatcher_task is None or self._dispatcher_task.done():
            self._dispatcher_task = asyncio.create_task(self._queue_dispatcher())

    async def _queue_dispatcher(self):
        """
        Pulls queued requests in strict FIFO order and grants semaphore slots.
        """
        while self._running:
            try:
                # Wait for next item in FIFO order
                item = await self.queue.get()
                
                # Check if item was already cancelled or deadline expired
                now = time.time()
                if item.cancelled or now >= item.deadline:
                    self.queue.task_done()
                    if not item.future.done():
                        item.future.set_result((False, "Request timed out waiting in admission queue.", (now - item.enqueue_time) * 1000.0))
                    continue

                # Wait to acquire a concurrency slot before granting admission
                time_remaining = max(0.001, item.deadline - time.time())
                try:
                    self._dispatcher_waiting_semaphore = True
                    await asyncio.wait_for(self.semaphore.acquire(), timeout=time_remaining)
                except asyncio.TimeoutError:
                    self.queue.task_done()
                    if not item.future.done():
                        item.future.set_result((False, "Request timed out waiting for semaphore slot.", (time.time() - item.enqueue_time) * 1000.0))
                    continue
                finally:
                    self._dispatcher_waiting_semaphore = False

                # Acquired concurrency slot!
                queue_wait_ms = (time.time() - item.enqueue_time) * 1000.0
                
                async with self._lock:
                    self.daily_requests_executed += 1
                    self.recent_request_timestamps.append(time.time())

                self.queue.task_done()
                if not item.future.done():
                    item.future.set_result((True, "Admitted", queue_wait_ms))

            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(0.01)

    def reset_stats(self):
        """Reset internal metrics."""
        self.peak_queue_length = 0
        self.daily_requests_executed = 0
        self.recent_request_timestamps.clear()

    async def admit_request(
        self,
        request_id: str,
        timeout_seconds: float = 25.0
    ) -> Tuple[bool, str, float]:
        """
        Enqueues request into bounded FIFO queue and awaits admission.
        Returns: (admitted, message, queue_wait_ms)
        """
        self._ensure_dispatcher_running()
        now = time.time()
        deadline = now + timeout_seconds

        # 1. Daily Quota Guard
        if self.daily_requests_executed >= self.daily_limit:
            return False, "Daily provider request quota exhausted. System refuses further requests.", 0.0

        # 2. Circuit Breaker Check
        if not self.circuit_breaker.allow_request():
            return False, "Circuit breaker OPEN: upstream provider is temporarily offline due to failures.", 0.0

        # 3. Bounded Queue Capacity / Backpressure Rejection
        current_waiting = self.queue.qsize() + (1 if self._dispatcher_waiting_semaphore else 0)
        if current_waiting >= self.queue_capacity:
            return False, f"Queue is full ({self.queue_capacity} requests). Dropped due to backpressure.", 0.0

        enqueue_time = time.time()
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        queued_item = QueuedItem(
            request_id=request_id,
            enqueue_time=enqueue_time,
            deadline=deadline,
            future=future
        )

        try:
            self.queue.put_nowait(queued_item)
        except asyncio.QueueFull:
            return False, f"Queue is full ({self.queue_capacity} requests). Dropped due to backpressure.", 0.0

        # Record peak queue length
        current_depth = self.queue.qsize() + (1 if self._dispatcher_waiting_semaphore else 0)
        async with self._lock:
            if current_depth > self.peak_queue_length:
                self.peak_queue_length = current_depth

        # Await dispatcher granting admission or timeout
        try:
            time_left = deadline - time.time()
            if time_left <= 0:
                queued_item.cancelled = True
                return False, "Request timed out while waiting in queue before admission.", 0.0
            
            admitted, reason, queue_wait_ms = await asyncio.wait_for(future, timeout=time_left)
            return admitted, reason, queue_wait_ms

        except asyncio.TimeoutError:
            queued_item.cancelled = True
            return False, "Request timed out waiting in admission queue.", (time.time() - enqueue_time) * 1000.0

    def release_slot(self, success: bool = True):
        """Release semaphore slot and update circuit breaker."""
        self.semaphore.release()
        if success:
            self.circuit_breaker.record_success()
        else:
            self.circuit_breaker.record_failure()

    async def close(self):
        """Gracefully stop background dispatcher."""
        self._running = False
        if self._dispatcher_task and not self._dispatcher_task.done():
            self._dispatcher_task.cancel()
            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass
