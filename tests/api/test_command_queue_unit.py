import asyncio

import pytest

import src.api.control_service.command_queue as command_queue_module
from src.api.control_service.command_queue import (
    CommandQueue,
    CommandQueueFullError,
    DriveCommand,
)

pytestmark = pytest.mark.camjam_unit


class StubMotorController:
    def __init__(self) -> None:
        self.invocations: list[tuple[str, tuple[float, ...]]] = []

    def drive(self, left: float, right: float) -> None:
        self.invocations.append(("drive", (left, right)))

    def stop(self) -> None:
        self.invocations.append(("stop", tuple()))

    def brake(self) -> None:
        self.invocations.append(("brake", tuple()))

    def emergency_stop(self) -> None:
        self.invocations.append(("estop", tuple()))

    def reset_estop(self) -> None:
        self.invocations.append(("reset", tuple()))


class ImmediateLimiter:
    def __init__(self) -> None:
        self.calls = 0

    async def wait_for_token(self) -> None:
        self.calls += 1


class BlockingLimiter:
    def __init__(self) -> None:
        self.event = asyncio.Event()
        self.calls = 0

    async def wait_for_token(self) -> None:
        self.calls += 1
        await self.event.wait()


def test_command_queue_processes_drive_with_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    async def runner() -> None:
        motor = StubMotorController()
        limiter = ImmediateLimiter()
        queue = CommandQueue(motor_controller=motor, limiter=limiter, maxsize=3)

        sleep_calls: list[float] = []

        async def fake_sleep(duration: float) -> None:
            sleep_calls.append(duration)

        monkeypatch.setattr(command_queue_module.asyncio, "sleep", fake_sleep)

        await queue.start()
        await queue.enqueue_drive(DriveCommand(left_speed=0.4, right_speed=-0.2, duration_s=0.5))
        await queue.wait_until_idle()
        await queue.stop()

        assert motor.invocations == [("drive", (0.4, -0.2)), ("stop", tuple())]
        assert sleep_calls == [0.5]
        assert limiter.calls == 1

    asyncio.run(runner())


def test_enqueue_drive_respects_maxsize(monkeypatch: pytest.MonkeyPatch) -> None:
    async def runner() -> None:
        motor = StubMotorController()
        limiter = BlockingLimiter()
        queue = CommandQueue(motor_controller=motor, limiter=limiter, maxsize=1)

        await queue.start()
        await queue.enqueue_drive(DriveCommand(left_speed=0.1, right_speed=0.1))

        with pytest.raises(CommandQueueFullError):
            await queue.enqueue_drive(DriveCommand(left_speed=0.2, right_speed=0.2))

        limiter.event.set()
        await queue.wait_until_idle()
        await queue.stop()

        drive_calls = [entry for entry in motor.invocations if entry[0] == "drive"]
        assert drive_calls == [("drive", (0.1, 0.1))]
        assert limiter.calls >= 1

    asyncio.run(runner())


def test_clear_drains_queue_without_worker() -> None:
    async def runner() -> None:
        motor = StubMotorController()
        limiter = ImmediateLimiter()
        queue = CommandQueue(motor_controller=motor, limiter=limiter, maxsize=5)

        await queue.enqueue_drive(DriveCommand(left_speed=0.3, right_speed=0.3))
        await queue.enqueue_drive(DriveCommand(left_speed=-0.1, right_speed=-0.1))

        assert queue._queue.qsize() == 2
        await queue.clear()
        assert queue._queue.qsize() == 0

    asyncio.run(runner())


def test_set_maxsize_validation() -> None:
    motor = StubMotorController()
    limiter = ImmediateLimiter()
    queue = CommandQueue(motor_controller=motor, limiter=limiter, maxsize=2)

    with pytest.raises(ValueError):
        queue.set_maxsize(0)

    queue.set_maxsize(4)
    assert queue._maxsize == 4
