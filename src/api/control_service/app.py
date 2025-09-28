"""Minimal control service application without external web frameworks."""

from __future__ import annotations

import ipaddress
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from .command_queue import (
    CommandQueue,
    CommandQueueFullError,
    DriveCommand,
    MotorControllerProtocol,
)
from .config import ControlServiceConfig, RateLimitSettings
from .rate_limiter import TokenBucket


@dataclass
class Response:
    """Lightweight HTTP-style response."""

    status_code: int
    body: dict[str, Any]


class ServoControllerProtocol(Protocol):
    def move_to(self, pan: float, tilt: float) -> None: ...

    @property
    def pan(self) -> float: ...

    @property
    def tilt(self) -> float: ...


class UltrasonicSampleProtocol(Protocol):
    distance_m: float
    valid: bool


class UltrasonicRangerProtocol(Protocol):
    async def read(self) -> UltrasonicSampleProtocol: ...

    @property
    def history(self) -> Iterable[UltrasonicSampleProtocol]: ...


class LineTelemetryProtocol(Protocol):
    left: float
    right: float
    on_line: bool


class LineFollowerProtocol(Protocol):
    async def read(self) -> LineTelemetryProtocol: ...


class ControlServiceApp:
    """Application facade that mimics a small subset of FastAPI."""

    def __init__(
        self,
        *,
        config: ControlServiceConfig,
        motor_controller: MotorControllerProtocol,
        servo_controller: ServoControllerProtocol,
        ultrasonic_ranger: UltrasonicRangerProtocol,
        line_follower: LineFollowerProtocol,
    ) -> None:
        self.config = config
        self.motor_controller = motor_controller
        self.servo_controller = servo_controller
        self.ultrasonic_ranger = ultrasonic_ranger
        self.line_follower = line_follower
        self.ingress_limiter = TokenBucket(
            rate_per_second=config.ingress_rate_limit.rate_per_second,
            capacity=config.ingress_rate_limit.burst,
        )
        self.execution_limiter = TokenBucket(
            rate_per_second=config.execution_rate_limit.rate_per_second,
            capacity=config.execution_rate_limit.burst,
        )
        self.command_queue = CommandQueue(
            motor_controller=motor_controller,
            limiter=self.execution_limiter,
            maxsize=config.queue_maxsize,
        )
        self._allowed_networks = [ipaddress.ip_network(net) for net in config.allowed_networks]
        self._routes: dict[tuple[str, str], Callable[[dict[str, Any]], Awaitable[Response]]] = {
            ("POST", "/drive/differential"): self._handle_drive,
            ("POST", "/drive/stop"): self._handle_stop,
            ("POST", "/drive/brake"): self._handle_brake,
            ("POST", "/drive/emergency-stop"): self._handle_estop,
            ("POST", "/drive/reset"): self._handle_reset,
            ("POST", "/pan-tilt/position"): self._handle_pan_tilt,
            ("GET", "/telemetry/ultrasonic"): self._handle_ultrasonic,
            ("GET", "/telemetry/line"): self._handle_line,
            ("GET", "/config"): self._handle_get_config,
            ("PATCH", "/config"): self._handle_patch_config,
        }

    async def start(self) -> None:
        await self.command_queue.start()

    async def shutdown(self) -> None:
        await self.command_queue.stop()
        self.motor_controller.stop()
        if hasattr(self.motor_controller, "close"):
            self.motor_controller.close()

    async def handle_request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        headers = headers or {}
        auth_error = self._authenticate(headers)
        if auth_error is not None:
            return auth_error

        route = self._routes.get((method.upper(), path))
        if route is None:
            return Response(status_code=404, body={"detail": "Not Found"})

        try:
            result = await route(json or {})
        except ValueError as exc:
            return Response(status_code=422, body={"detail": str(exc)})
        return result

    def _authenticate(self, headers: dict[str, str]) -> Response | None:
        api_key = headers.get("X-Api-Key")
        if api_key not in self.config.api_keys:
            return Response(status_code=401, body={"detail": "Invalid API key"})

        forwarded = headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0].strip() if forwarded else "127.0.0.1"
        try:
            ip_obj = ipaddress.ip_address(client_ip)
        except ValueError:
            return Response(status_code=400, body={"detail": "Invalid client IP"})
        if not any(ip_obj in network for network in self._allowed_networks):
            return Response(status_code=403, body={"detail": "Client network not permitted"})
        return None

    async def _handle_drive(self, payload: dict[str, Any]) -> Response:
        left = self._validate_speed(payload.get("left_speed"), "left_speed")
        right = self._validate_speed(payload.get("right_speed"), "right_speed")
        duration = payload.get("duration_s")
        if duration is not None:
            if not isinstance(duration, (int, float)) or duration <= 0:
                raise ValueError("duration_s must be a positive number")
            duration_value = float(duration)
        else:
            duration_value = None

        if not await self.ingress_limiter.allow():
            return Response(status_code=429, body={"detail": "Command rate limit exceeded"})
        try:
            depth = await self.command_queue.enqueue_drive(
                DriveCommand(left_speed=left, right_speed=right, duration_s=duration_value)
            )
        except CommandQueueFullError as exc:
            return Response(status_code=503, body={"detail": str(exc)})
        return Response(status_code=202, body={"status": "queued", "queue_depth": depth})

    async def _handle_stop(self, payload: dict[str, Any]) -> Response:
        self.motor_controller.stop()
        await self.command_queue.clear()
        return Response(status_code=200, body={"status": "stopped"})

    async def _handle_brake(self, payload: dict[str, Any]) -> Response:
        self.motor_controller.brake()
        await self.command_queue.clear()
        return Response(status_code=200, body={"status": "braking"})

    async def _handle_estop(self, payload: dict[str, Any]) -> Response:
        await self.command_queue.clear()
        self.motor_controller.emergency_stop()
        return Response(status_code=200, body={"status": "estop"})

    async def _handle_reset(self, payload: dict[str, Any]) -> Response:
        self.motor_controller.reset_estop()
        return Response(status_code=200, body={"status": "ready"})

    async def _handle_pan_tilt(self, payload: dict[str, Any]) -> Response:
        pan = payload.get("pan_deg")
        tilt = payload.get("tilt_deg")
        if not isinstance(pan, (int, float)) or not -90.0 <= float(pan) <= 90.0:
            raise ValueError("pan_deg must be between -90 and 90 degrees")
        if not isinstance(tilt, (int, float)) or not -45.0 <= float(tilt) <= 45.0:
            raise ValueError("tilt_deg must be between -45 and 45 degrees")
        self.servo_controller.move_to(float(pan), float(tilt))
        return Response(
            status_code=200,
            body={
                "pan_deg": float(self.servo_controller.pan),
                "tilt_deg": float(self.servo_controller.tilt),
            },
        )

    async def _handle_ultrasonic(self, payload: dict[str, Any]) -> Response:
        reading = await self.ultrasonic_ranger.read()
        history = []
        for sample in getattr(self.ultrasonic_ranger, "history", []):
            history.append({"distance_m": float(sample.distance_m), "valid": bool(sample.valid)})
        return Response(
            status_code=200,
            body={
                "distance_m": float(reading.distance_m),
                "valid": bool(reading.valid),
                "history": history,
            },
        )

    async def _handle_line(self, payload: dict[str, Any]) -> Response:
        telemetry = await self.line_follower.read()
        return Response(
            status_code=200,
            body={
                "left": float(telemetry.left),
                "right": float(telemetry.right),
                "on_line": bool(telemetry.on_line),
            },
        )

    async def _handle_get_config(self, payload: dict[str, Any]) -> Response:
        return Response(status_code=200, body=self.config.snapshot())

    async def _handle_patch_config(self, payload: dict[str, Any]) -> Response:
        ingress = payload.get("ingress_rate_limit")
        if ingress is not None:
            self.config.ingress_rate_limit = RateLimitSettings(
                rate_per_second=float(ingress["rate_per_second"]),
                burst=int(ingress["burst"]),
            )
            self.ingress_limiter.configure(
                rate_per_second=self.config.ingress_rate_limit.rate_per_second,
                capacity=self.config.ingress_rate_limit.burst,
            )
        execution = payload.get("execution_rate_limit")
        if execution is not None:
            self.config.execution_rate_limit = RateLimitSettings(
                rate_per_second=float(execution["rate_per_second"]),
                burst=int(execution["burst"]),
            )
            self.execution_limiter.configure(
                rate_per_second=self.config.execution_rate_limit.rate_per_second,
                capacity=self.config.execution_rate_limit.burst,
            )
        queue_maxsize = payload.get("queue_maxsize")
        if queue_maxsize is not None:
            queue_value = int(queue_maxsize)
            if queue_value <= 0:
                raise ValueError("queue_maxsize must be positive")
            self.config.queue_maxsize = queue_value
            self.command_queue.set_maxsize(queue_value)
        return Response(status_code=200, body=self.config.snapshot())

    @staticmethod
    def _validate_speed(value: Any, name: str) -> float:
        if not isinstance(value, (int, float)):
            raise ValueError(f"{name} is required")
        float_value = float(value)
        if float_value < -1.0 or float_value > 1.0:
            raise ValueError(f"{name} must be between -1 and 1")
        return float_value


def create_app(
    *,
    config: ControlServiceConfig | None = None,
    motor_controller: Any = None,
    servo_controller: Any = None,
    ultrasonic_ranger: Any = None,
    line_follower: Any = None,
) -> ControlServiceApp:
    if config is None:
        config = ControlServiceConfig(api_keys={"local"})
    if (
        motor_controller is None
        or servo_controller is None
        or ultrasonic_ranger is None
        or line_follower is None
    ):
        raise RuntimeError("All hardware adapters must be provided explicitly in this environment")
    return ControlServiceApp(
        config=config,
        motor_controller=motor_controller,
        servo_controller=servo_controller,
        ultrasonic_ranger=ultrasonic_ranger,
        line_follower=line_follower,
    )


__all__ = [
    "create_app",
    "ControlServiceApp",
    "Response",
    "ControlServiceConfig",
    "RateLimitSettings",
]
