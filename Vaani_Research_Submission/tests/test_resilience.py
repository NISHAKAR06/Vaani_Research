import pytest
import time
from src.resilience.circuit_breaker import CircuitBreaker, CircuitState
from src.resilience.retry_policy import RetryPolicy

def test_circuit_breaker_transitions():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=0.1)
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True

    # 2 failures: still closed
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True

    # 3rd failure: trips to open
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False

    # Wait for recovery timeout
    time.sleep(0.12)
    # First request after recovery transitions to HALF_OPEN
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Success in half open resets to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0

def test_retry_policy_exponential_backoff_and_jitter():
    policy = RetryPolicy(max_retries=2, base_delay_seconds=1.0, backoff_factor=2.0, jitter_fraction=0.1)
    
    # Retryable vs non-retryable
    assert policy.should_retry(status_code=429, current_attempt=0) is True
    assert policy.should_retry(status_code=500, current_attempt=0) is True
    assert policy.should_retry(status_code=400, current_attempt=0) is False
    assert policy.should_retry(status_code=404, current_attempt=0) is False
    assert policy.should_retry(status_code=429, current_attempt=2) is False

    # Deadline expiration
    past_deadline = time.time() - 1.0
    assert policy.should_retry(status_code=500, current_attempt=0, deadline_timestamp=past_deadline) is False

    # Backoff delay
    delay_0 = policy.calculate_delay(current_attempt=0)
    delay_1 = policy.calculate_delay(current_attempt=1)
    assert 0.9 <= delay_0 <= 1.1
    assert 1.8 <= delay_1 <= 2.2
