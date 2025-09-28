"""Asynchronous command queue for motor control."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from .rate_limiter import TokenBucket


@dataclass
class DriveCommand:
    left_speed: float
    right_speed: float
    duration_s: Optional[float] = None


class CommandQueueFullError(RuntimeError):
    """Raised when the command queue exceeds its configured capacity."""


class CommandQueue:
    """Background worker that executes drive commands sequentially."""

    def __init__(
        self,
        *,
        motor_controller,
        limiter: TokenBucket,
        maxsize: int,
    ) -> None:
        self._motor_controller = motor_controller
        self._limiter = limiter
        self._maxsize = maxsize
        self._queue: asyncio.Queue[tuple[str, DriveCommand]] = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        self._shutdown.set()
        if self._worker_task is not None:
            await self._worker_task
            self._worker_task = None

    async def enqueue_drive(self, command: DriveCommand) -> int:
        if self._maxsize and self._queue.qsize() >= self._maxsize:
            raise CommandQueueFullError("Drive command queue is full")
        self._queue.put_nowait(("drive", command))
        return self._queue.qsize()

    async def clear(self) -> None:
        while True:
            try:
                _ = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            else:
                self._queue.task_done()

    async def wait_until_idle(self) -> None:
        await self._queue.join()

    def set_maxsize(self, maxsize: int) -> None:
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
