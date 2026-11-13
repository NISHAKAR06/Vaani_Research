"""
Load Controller for the Stand-in Model Service.
Simulates realistic latency distributions, overload latency penalties,
and probabilistic transient failures/timeouts.
"""

import random
import asyncio
from typing import Tuple

class LoadController:
    def __init__(
        self,
        base_latency_ms: float = 380.0,
        latency_jitter_ms: float = 110.0,
        first_token_latency_ms: float = 180.0,
        overload_latency_multiplier: float = 1.85,
        failure_probability: float = 0.04,
        timeout_probability: float = 0.02,
        seed: int = 42
    ):
        self.base_latency_ms = base_latency_ms
        self.latency_jitter_ms = latency_jitter_ms
        self.first_token_latency_ms = first_token_latency_ms
        self.overload_multiplier = overload_latency_multiplier
        self.failure_probability = failure_probability
        self.timeout_probability = timeout_probability
        self.random = random.Random(seed)

    def calculate_latencies(self, current_concurrency: int) -> Tuple[float, float]:
        """
        Calculates (ttft_ms, total_latency_ms) under current load conditions.
        Applies overload multiplier when concurrency > 1.
        """
        # Latency with Gaussian jitter
        raw_ttft = self.random.gauss(self.first_token_latency_ms, self.latency_jitter_ms * 0.4)
        raw_total = self.random.gauss(self.base_latency_ms, self.latency_jitter_ms)

        ttft = max(60.0, raw_ttft)
        total = max(ttft + 80.0, raw_total)

        # Apply overload multiplier if concurrent requests in-flight
        if current_concurrency > 1:
            load_factor = 1.0 + ((current_concurrency - 1) * 0.25 * self.overload_multiplier)
            ttft *= load_factor
            total *= load_factor

        return round(ttft, 2), round(total, 2)

    def check_fault_injection(self) -> Tuple[bool, str, int]:
        """
        Checks whether to inject a transient 500 error or a timeout.
        Returns: (should_fault, error_message, status_code)
        """
        roll = self.random.random()
        if roll < self.timeout_probability:
            return True, "Simulated gateway request timeout", 408
        if roll < (self.timeout_probability + self.failure_probability):
            return True, "Simulated internal provider transient error (HTTP 500)", 500
        return False, "", 200

