"""
Regression tests for AdmissionController genuine FIFO queueing,
backpressure rejection, and concurrency enforcement.
"""

import pytest
import asyncio
import time
from src.resilience.admission_control import AdmissionController

@pytest.mark.asyncio
async def test_fifo_queue_ordering():
    # Capacity 10, concurrency 1 to enforce sequential FIFO dispatch
    controller = AdmissionController(max_concurrency=1, queue_capacity=10)
    
    dispatch_order = []

    async def worker(task_id: int):
        admitted, reason, wait_ms = await controller.admit_request(f"req_{task_id}", timeout_seconds=5.0)
        assert admitted is True
        dispatch_order.append(task_id)
        await asyncio.sleep(0.05)  # hold slot briefly
        controller.release_slot(success=True)

    # Launch tasks in order 1, 2, 3, 4
    tasks = [asyncio.create_task(worker(i)) for i in range(1, 5)]
    await asyncio.gather(*tasks)

    # Verify strict FIFO dispatch
    assert dispatch_order == [1, 2, 3, 4], f"Expected [1, 2, 3, 4], got {dispatch_order}"
    await controller.close()

@pytest.mark.asyncio
async def test_queue_backpressure_rejection():
    # Capacity 2, concurrency 1
    controller = AdmissionController(max_concurrency=1, queue_capacity=2)
    
    # Fill slot and fill queue
    admitted_slot, _, _ = await controller.admit_request("active_slot", timeout_seconds=5.0)
    assert admitted_slot is True
    
    # Enqueue 2 requests to fill the queue capacity
    f1 = asyncio.create_task(controller.admit_request("queued_1", timeout_seconds=5.0))
    await asyncio.sleep(0.01)
    f2 = asyncio.create_task(controller.admit_request("queued_2", timeout_seconds=5.0))
    await asyncio.sleep(0.01)

    # 4th request must be rejected immediately due to queue full
    admitted_drop, reason_drop, _ = await controller.admit_request("queued_3_drop", timeout_seconds=1.0)
    assert admitted_drop is False
    assert "Dropped due to backpressure" in reason_drop or "full" in reason_drop

    # Cleanup
    controller.release_slot(success=True)
    await asyncio.sleep(0.02)
    controller.release_slot(success=True)
    await asyncio.sleep(0.02)
    controller.release_slot(success=True)
    await f1
    await f2
    await controller.close()

