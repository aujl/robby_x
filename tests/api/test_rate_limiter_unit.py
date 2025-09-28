import asyncio

import pytest

import src.api.control_service.rate_limiter as rate_limiter_module
from src.api.control_service.rate_limiter import TokenBucket

pytestmark = pytest.mark.camjam_unit


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value

    def advance(self, delta: float) -> None:
        self.value += delta


def test_token_bucket_allow_and_refill(monkeypatch: pytest.MonkeyPatch) -> None:
    async def runner() -> None:
        clock = FakeClock()
        monkeypatch.setattr(rate_limiter_module.time, "monotonic", clock.monotonic)

        bucket = TokenBucket(rate_per_second=2.0, capacity=2)

        assert await bucket.allow() is True
        assert await bucket.allow() is True
        assert await bucket.allow() is False

        clock.advance(0.5)
        assert await bucket.allow() is True

    asyncio.run(runner())


def test_wait_for_token_blocks_until_available(monkeypatch: pytest.MonkeyPatch) -> None:
    async def runner() -> None:
        clock = FakeClock()
        monkeypatch.setattr(rate_limiter_module.time, "monotonic", clock.monotonic)

        sleep_calls: list[float] = []

        async def fake_sleep(duration: float) -> None:
            sleep_calls.append(duration)
            clock.advance(duration)

        monkeypatch.setattr(rate_limiter_module.asyncio, "sleep", fake_sleep)

        bucket = TokenBucket(rate_per_second=4.0, capacity=1)
        assert await bucket.allow() is True

        await bucket.wait_for_token()

        assert sleep_calls == [pytest.approx(0.25, rel=1e-6)]

        clock.advance(0.25)
        assert await bucket.allow() is True

    asyncio.run(runner())


def test_configure_validates_inputs() -> None:
    bucket = TokenBucket(rate_per_second=5.0, capacity=3)

    with pytest.raises(ValueError):
        bucket.configure(rate_per_second=0.0, capacity=3)

    with pytest.raises(ValueError):
        bucket.configure(rate_per_second=1.0, capacity=0)

    bucket.configure(rate_per_second=2.5, capacity=6)
    assert True  # configuration accepted
