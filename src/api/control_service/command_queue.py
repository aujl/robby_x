"""Asynchronous command queue for motor control."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from .rate_limiter import TokenBucket


@dataclass
class DriveCommand:
    left_speed: float
    right_speed: float
    duration_s: float | None = None

class MotorControllerProtocol(Protocol):
    """Behaviour required from the motor controller dependency."""

    def drive(self, left_speed: float, right_speed: float) -> None: ...

    def stop(self) -> None: ...

    def brake(self) -> None: ...

    def emergency_stop(self) -> None: ...

    def reset_estop(self) -> None: ...


class CommandQueueFullError(RuntimeError):
    """Raised when the command queue exceeds its configured capacity."""


class CommandQueue:
    """Background worker that executes drive commands sequentially."""

    def __init__(
        self,
        *,
        motor_controller: MotorControllerProtocol,
        limiter: TokenBucket,
        maxsize: int,
    ) -> None:
        """Initialise the queue with controller interfaces and limits."""
        self._motor_controller = motor_controller
        self._limiter = limiter
        self._maxsize = maxsize
        self._queue: asyncio.Queue[tuple[str, DriveCommand]] = asyncio.Queue()
        self._worker_task: asyncio.Task[None] | None = None
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        """Launch the background worker if it is not already running."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        """Signal shutdown and wait for the worker to exit."""
        self._shutdown.set()
        if self._worker_task is not None:
            await self._worker_task
            self._worker_task = None

    async def enqueue_drive(self, command: DriveCommand) -> int:
        """Queue a drive command and return the resulting queue depth."""
        if self._maxsize and self._queue.qsize() >= self._maxsize:
            raise CommandQueueFullError("Drive command queue is full")
        self._queue.put_nowait(("drive", command))
        return self._queue.qsize()

    async def clear(self) -> None:
        """Drain any pending commands without executing them."""
        while True:
            try:
                _ = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            else:
                self._queue.task_done()

    async def wait_until_idle(self) -> None:
        """Block until all queued commands have been processed."""
        await self._queue.join()

    def set_maxsize(self, maxsize: int) -> None:
        """Adjust the maximum queue depth enforced for new commands."""
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._maxsize = maxsize

    async def _worker(self) -> None:
        try:
            while True:
                if self._shutdown.is_set() and self._queue.empty():
                    break
                try:
                    item_type, command = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                try:
                    if item_type == "drive":
                        await self._limiter.wait_for_token()
                        self._motor_controller.drive(command.left_speed, command.right_speed)
                        if command.duration_s:
                            await asyncio.sleep(command.duration_s)
                            self._motor_controller.stop()
                finally:
                    self._queue.task_done()
        finally:
            # Drain remaining items to avoid pending join() callers hanging.
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:  # pragma: no cover - race guard
                    break
                else:
                    self._queue.task_done()
