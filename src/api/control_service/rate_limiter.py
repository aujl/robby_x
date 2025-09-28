"""Token bucket rate limiter utilities."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class TokenBucketState:
    rate_per_second: float
    capacity: int


class TokenBucket:
    """Asynchronous token bucket implementation."""

    def __init__(self, *, rate_per_second: float, capacity: int) -> None:
        self._state = TokenBucketState(rate_per_second=rate_per_second, capacity=capacity)
        self._tokens = float(capacity)
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    def configure(self, *, rate_per_second: float, capacity: int) -> None:
        """Update the limiter parameters."""

        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._state = TokenBucketState(rate_per_second=rate_per_second, capacity=capacity)

    async def allow(self) -> bool:
        """Attempt to consume a token without blocking."""

        async with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    async def wait_for_token(self) -> None:
        """Block until a token is available and consume it."""

        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                deficit = max(0.0, 1.0 - self._tokens)
                wait_time = deficit / self._state.rate_per_second if self._state.rate_per_second > 0 else 0.1
            await asyncio.sleep(wait_time)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = max(0.0, now - self._updated_at)
        if elapsed <= 0:
            return
        self._tokens = min(
            float(self._state.capacity),
            self._tokens + elapsed * self._state.rate_per_second,
        )
        self._updated_at = now
