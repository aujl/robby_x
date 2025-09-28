"""Configuration structures for the control service API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Set


@dataclass
class RateLimitSettings:
    """Token-bucket parameters for rate limiting."""

    rate_per_second: float
    burst: int

    def __post_init__(self) -> None:
        if self.rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        if self.burst <= 0:
            raise ValueError("burst must be a positive integer")


@dataclass
class ControlServiceConfig:
    """Runtime configuration for the API."""

    api_keys: Set[str] = field(default_factory=set)
    allowed_networks: Iterable[str] = field(default_factory=lambda: ("127.0.0.0/8",))
    ingress_rate_limit: RateLimitSettings = field(
        default_factory=lambda: RateLimitSettings(rate_per_second=5.0, burst=5)
    )
    execution_rate_limit: RateLimitSettings = field(
        default_factory=lambda: RateLimitSettings(rate_per_second=10.0, burst=5)
    )
    queue_maxsize: int = 32

    def __post_init__(self) -> None:
        if self.queue_maxsize <= 0:
            raise ValueError("queue_maxsize must be positive")
        if not self.api_keys:
            raise ValueError("At least one API key must be configured")
        self.allowed_networks = tuple(self.allowed_networks)

    def snapshot(self) -> dict[str, object]:
        """Return a serialisable copy of the configuration."""

        return {
            "ingress_rate_limit": {
                "rate_per_second": self.ingress_rate_limit.rate_per_second,
                "burst": self.ingress_rate_limit.burst,
            },
            "execution_rate_limit": {
                "rate_per_second": self.execution_rate_limit.rate_per_second,
                "burst": self.execution_rate_limit.burst,
            },
            "queue_maxsize": self.queue_maxsize,
            "allowed_networks": list(self.allowed_networks),
        }
