"""
Rate Limiter and Quota Manager for the Stand-in Model Service.
Tracks:
- Sliding window / token bucket for Requests Per Minute (RPM)
- Sliding window / token bucket for Tokens Per Minute (TPM)
- Daily Request Budget (RPD)
- Daily Token Budget (TPD)
- Active in-flight concurrency count
"""

import time
import asyncio
from typing import Tuple, Optional

class SimulatorRateLimiter:
    def __init__(
        self,
        rpm_limit: int = 30,
        tpm_limit: int = 6000,
        daily_request_limit: int = 1000,
        daily_token_limit: int = 100000,
        max_concurrency: int = 5,
        retry_after_seconds: float = 5.0
    ):
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.daily_request_limit = daily_request_limit
        self.daily_token_limit = daily_token_limit
        self.max_concurrency = max_concurrency
        self.retry_after_seconds = retry_after_seconds

        # State
        self.request_timestamps = []
        self.token_records = []  # (timestamp, token_count)
        self.daily_requests_used = 0
        self.daily_tokens_used = 0
        self.active_concurrency = 0
        self.lock = asyncio.Lock()

    def reset(
        self,
        new_rpm: Optional[int] = None,
        new_tpm: Optional[int] = None,
        new_daily_budget: Optional[int] = None
    ):
        """Reset all rate limiter quotas and tracking state."""
        self.request_timestamps.clear()
        self.token_records.clear()
        self.daily_requests_used = 0
        self.daily_tokens_used = 0
        self.active_concurrency = 0
        if new_rpm is not None:
            self.rpm_limit = new_rpm
        if new_tpm is not None:
            self.tpm_limit = new_tpm
        if new_daily_budget is not None:
            self.daily_request_limit = new_daily_budget

    async def check_and_acquire(self, estimated_tokens: int = 250) -> Tuple[bool, str, Optional[float]]:
        """
        Check whether an incoming request can be admitted.
        Returns: (allowed, reason, retry_after_seconds)
        """
        async with self.lock:
            now = time.time()
            cutoff = now - 60.0

            # Clean expired 60s windows
            self.request_timestamps = [ts for ts in self.request_timestamps if ts > cutoff]
            self.token_records = [(ts, tok) for ts, tok in self.token_records if ts > cutoff]

            # 1. Daily Request Quota Check
            if self.daily_requests_used >= self.daily_request_limit:
                return False, "Daily request budget exhausted", 86400.0

            # 2. Daily Token Quota Check
            if self.daily_tokens_used + estimated_tokens > self.daily_token_limit:
                return False, "Daily token budget exhausted", 86400.0

            # 3. Concurrency Limit Check
            if self.active_concurrency >= self.max_concurrency:
                return False, f"Maximum concurrency limit ({self.max_concurrency}) reached", 1.0

            # 4. RPM Limit Check
            if len(self.request_timestamps) >= self.rpm_limit:
                oldest = self.request_timestamps[0]
                retry_after = max(1.0, round(60.0 - (now - oldest), 1))
                return False, f"Rate limit exceeded (RPM limit: {self.rpm_limit})", retry_after

            # 5. TPM Limit Check
            current_tpm = sum(tok for _, tok in self.token_records)
            if current_tpm + estimated_tokens > self.tpm_limit:
                oldest = self.token_records[0][0] if self.token_records else now
                retry_after = max(1.0, round(60.0 - (now - oldest), 1))
                return False, f"Rate limit exceeded (TPM limit: {self.tpm_limit})", retry_after

            # Admitted! Record usage
            self.request_timestamps.append(now)
            self.token_records.append((now, estimated_tokens))
            self.daily_requests_used += 1
            self.daily_tokens_used += estimated_tokens
            self.active_concurrency += 1
            return True, "OK", None

    async def release_concurrency(self):
        """Release active in-flight request slot."""
        async with self.lock:
            if self.active_concurrency > 0:
                self.active_concurrency -= 1
