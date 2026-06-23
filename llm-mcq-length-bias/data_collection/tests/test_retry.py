"""Unit tests for the exponential-backoff retry layer."""
import pytest

from retry import call_with_retry, RetryError, is_retryable_status


def test_succeeds_first_try():
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        return 42
    assert call_with_retry(fn, max_retries=3, base_delay_s=0.0, max_delay_s=0.0,
                           sleep=lambda s: None) == 42
    assert calls["n"] == 1


def test_retries_then_succeeds():
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"
    out = call_with_retry(fn, max_retries=5, base_delay_s=0.0, max_delay_s=0.0,
                          sleep=lambda s: None)
    assert out == "ok" and calls["n"] == 3


def test_exhausts_and_raises():
    def fn():
        raise RuntimeError("always")
    with pytest.raises(RetryError) as ei:
        call_with_retry(fn, max_retries=2, base_delay_s=0.0, max_delay_s=0.0,
                        sleep=lambda s: None)
    assert ei.value.attempts == 3  # 1 initial + 2 retries


def test_non_retryable_stops_immediately():
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        raise RuntimeError("auth")
    with pytest.raises(RetryError):
        call_with_retry(fn, max_retries=5, base_delay_s=0.0, max_delay_s=0.0,
                        should_retry=lambda e: False, sleep=lambda s: None)
    assert calls["n"] == 1  # no retries attempted


def test_backoff_delays_are_capped_and_increasing():
    delays = []
    def fn():
        raise RuntimeError("x")
    with pytest.raises(RetryError):
        call_with_retry(fn, max_retries=4, base_delay_s=1.0, max_delay_s=4.0,
                        jitter=False, sleep=delays.append)
    assert delays == [1.0, 2.0, 4.0, 4.0]  # 1,2,4 then capped at 4


def test_is_retryable_status():
    assert is_retryable_status(429) and is_retryable_status(503)
    assert not is_retryable_status(401) and not is_retryable_status(200)
    assert not is_retryable_status(None)
