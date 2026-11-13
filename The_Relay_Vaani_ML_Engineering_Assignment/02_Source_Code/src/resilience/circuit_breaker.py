"""
Circuit Breaker pattern for provider protection.
Prevents cascading failure and protects upstream model providers
when experiencing sustained errors.
"""

import time
from enum import Enum
from typing import Optional

class CircuitState(str, Enum):
    CLOSED = "closed"        # Healthy, requests allowed through
    OPEN = "open"            # Unhealthy, fail-fast without calling provider
    HALF_OPEN = "half_open"  # Testing recovery with single canary request

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 10.0
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def allow_request(self) -> bool:
        """Check whether request is permitted through the circuit."""
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True

    def record_success(self):
        """Record successful upstream request."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        """Record upstream failure and trip circuit if threshold reached."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

