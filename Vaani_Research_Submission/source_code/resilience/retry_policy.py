"""
Retry Policy for The Relay.
Enforces:
- Transient failures only (HTTP 429, 500, 502, 503, 504, 408).
- Maximum 1 retry by default.
- Exponential backoff with jitter.
- Honors Retry-After headers from providers.
- Deadline expiration checks (never retries after deadline).
- Prevents retry storms.
"""

import random
import time
from typing import Optional, Tuple

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504, 408}
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 422}

class RetryPolicy:
    def __init__(
        self,
        max_retries: int = 1,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 8.0,
        backoff_factor: float = 2.0,
        jitter_fraction: float = 0.25
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay_seconds
        self.max_delay = max_delay_seconds
        self.backoff_factor = backoff_factor
        self.jitter_fraction = jitter_fraction

    def should_retry(
        self,
        status_code: int,
        current_attempt: int,
        deadline_timestamp: Optional[float] = None
    ) -> bool:
        """Determines whether another attempt is permitted."""
        if current_attempt >= self.max_retries:
            return False

        if status_code in NON_RETRYABLE_STATUS_CODES:
            return False

        if status_code not in RETRYABLE_STATUS_CODES:
            return False

        # Deadline check
        if deadline_timestamp is not None:
            now = time.time()
            if now >= deadline_timestamp:
                return False

        return True

    def calculate_delay(
        self,
        current_attempt: int,
        retry_after_header: Optional[float] = None,
        deadline_timestamp: Optional[float] = None
    ) -> float:
        """
        Calculates delay in seconds, factoring in Retry-After, exponential backoff,
        and random jitter. Clamps to deadline if set.
        """
        if retry_after_header is not None and retry_after_header > 0:
            delay = retry_after_header
        else:
            raw_delay = self.base_delay * (self.backoff_factor ** current_attempt)
            jitter = raw_delay * self.jitter_fraction * (2 * random.random() - 1)
            delay = min(self.max_delay, max(0.1, raw_delay + jitter))

        # Check against deadline
        if deadline_timestamp is not None:
            time_left = deadline_timestamp - time.time()
            if delay > time_left:
                delay = max(0.0, time_left - 0.1)

        return round(delay, 2)

