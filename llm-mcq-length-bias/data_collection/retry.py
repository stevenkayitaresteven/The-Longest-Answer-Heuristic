"""
retry.py
========
Rate-limit-safe retry with exponential backoff and optional jitter.

No silent failures: transient errors are retried up to ``RetryConfig.max_retries``;
on exhaustion the *last* exception is re-raised wrapped in ``RetryError`` so the
caller (and the run manifest) sees exactly what failed and how many attempts were
made. Non-retryable errors (e.g. authentication) are raised immediately.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Callable, Iterable, Type, TypeVar

T = TypeVar("T")
log = logging.getLogger("data_collection.retry")


class RetryError(RuntimeError):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, attempts: int, last_exc: BaseException):
        super().__init__(f"failed after {attempts} attempt(s): {last_exc!r}")
        self.attempts = attempts
        self.last_exc = last_exc


def is_retryable_status(status: int | None) -> bool:
    """HTTP statuses worth retrying: 408/429 and all 5xx."""
    return status is not None and (status in (408, 429) or 500 <= status < 600)


def call_with_retry(
    fn: Callable[[], T],
    *,
    max_retries: int,
    base_delay_s: float,
    max_delay_s: float,
    jitter: bool = True,
    retry_on: Iterable[Type[BaseException]] = (Exception,),
    should_retry: Callable[[BaseException], bool] = lambda e: True,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Invoke ``fn`` with exponential backoff.

    Parameters
    ----------
    fn : zero-arg callable performing the (network) action.
    max_retries : number of *additional* attempts after the first.
    base_delay_s, max_delay_s : backoff schedule ``min(base*2**i, max)``.
    jitter : add U[0, delay/2] to spread out concurrent retries.
    retry_on : exception types eligible for retry.
    should_retry : extra predicate (e.g. inspect HTTP status) gating a retry.
    sleep : injectable sleeper (tests pass a no-op to avoid real delays).
    """
    attempt = 0
    last_exc: BaseException | None = None
    while attempt <= max_retries:
        try:
            return fn()
        except tuple(retry_on) as exc:  # type: ignore[misc]
            last_exc = exc
            if not should_retry(exc) or attempt == max_retries:
                if not should_retry(exc):
                    log.warning("non-retryable error; not retrying: %r", exc)
                break
            delay = min(base_delay_s * (2 ** attempt), max_delay_s)
            if jitter:
                delay += random.uniform(0, delay / 2.0)
            log.warning("attempt %d/%d failed (%r); backing off %.1fs",
                        attempt + 1, max_retries + 1, exc, delay)
            sleep(delay)
            attempt += 1
    assert last_exc is not None
    raise RetryError(attempt + 1, last_exc)
