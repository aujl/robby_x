import asyncio
import time
from dataclasses import dataclass
from typing import Any

import pytest

from src.api.control_service import (
    ControlServiceApp,
    ControlServiceConfig,
    RateLimitSettings,
    create_app,
)


pytestmark = pytest.mark.camjam_unit


class StubMotorController:
    def __init__(self) -> None:
        self.commands: list[tuple[str, tuple[Any, ...]]] = []
        self.estopped = False

    def drive(self, left: float, right: float) -> None:
        self.commands.append(("drive", (left, right, time.monotonic())))

    def stop(self) -> None:
        self.commands.append(("stop", tuple()))

    def brake(self) -> None:
        self.commands.append(("brake", tuple()))

    def emergency_stop(self) -> None:
        self.estopped = True
        self.commands.append(("estop", tuple()))

    def reset_estop(self) -> None:
        self.estopped = False
        self.commands.append(("reset", tuple()))


class StubServoController:
    def __init__(self) -> None:
        self.pan = 0.0
        self.tilt = 0.0

    def move_to(self, pan: float, tilt: float) -> None:
        self.pan = pan
        self.tilt = tilt


@dataclass
class StubUltrasonicReading:
    distance_m: float
    valid: bool


class StubUltrasonicRanger:
    def __init__(self) -> None:
        self._history: list[StubUltrasonicReading] = []

    @property
    def history(self) -> list[StubUltrasonicReading]:
        return self._history

    async def read(self) -> StubUltrasonicReading:
        reading = StubUltrasonicReading(distance_m=0.42, valid=True)
        self._history.append(reading)
        return reading


@dataclass
class StubLineTelemetry:
    left: float
    right: float
    on_line: bool


class StubLineFollower:
    async def read(self) -> StubLineTelemetry:
        return StubLineTelemetry(left=0.7, right=0.3, on_line=True)


@pytest.fixture
def control_app() -> tuple[ControlServiceApp, dict[str, Any], asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    motor = StubMotorController()
    servos = StubServoController()
    ultrasonic = StubUltrasonicRanger()
    line = StubLineFollower()

    config = ControlServiceConfig(
        api_keys={"test-key"},
        allowed_networks=["127.0.0.0/8"],
        ingress_rate_limit=RateLimitSettings(rate_per_second=10.0, burst=5),
        execution_rate_limit=RateLimitSettings(rate_per_second=50.0, burst=5),
        queue_maxsize=16,
    )

    app = create_app(
        config=config,
        motor_controller=motor,
        servo_controller=servos,
        ultrasonic_ranger=ultrasonic,
        line_follower=line,
    )

    loop.run_until_complete(app.start())

    context = {
        "motor": motor,
        "servos": servos,
        "ultrasonic": ultrasonic,
        "line": line,
    }

    yield app, context, loop

    loop.run_until_complete(app.shutdown())
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
    asyncio.set_event_loop(None)


def test_rejects_invalid_drive_payload(control_app) -> None:
    app, _, loop = control_app
    response = loop.run_until_complete(
        app.handle_request(
            "POST",
            "/drive/differential",
            json={"left_speed": 1.5, "right_speed": 0.2},
            headers={"X-Api-Key": "test-key"},
        )
    )
    assert response.status_code == 422


def test_rejects_remote_clients(control_app) -> None:
    app, _, loop = control_app
    response = loop.run_until_complete(
        app.handle_request(
            "POST",
            "/drive/stop",
            headers={
                "X-Api-Key": "test-key",
                "X-Forwarded-For": "8.8.8.8",
            },
        )
    )
    assert response.status_code == 403


def test_rate_limit_enforced(control_app) -> None:
    app, _, loop = control_app
    app.config.ingress_rate_limit = RateLimitSettings(rate_per_second=2.0, burst=2)
    app.ingress_limiter.configure(rate_per_second=2.0, capacity=2)
    headers = {"X-Api-Key": "test-key"}
    status_codes = []
    for _ in range(4):
        response = loop.run_until_complete(
            app.handle_request(
                "POST",
                "/drive/differential",
                json={"left_speed": 0.2, "right_speed": 0.2},
                headers=headers,
            )
        )
        status_codes.append(response.status_code)
    assert 429 in status_codes


def test_drive_commands_processed_sequentially(control_app) -> None:
    app, context, loop = control_app
    headers = {"X-Api-Key": "test-key"}
    commands = [
        {"left_speed": 0.1, "right_speed": 0.2},
        {"left_speed": -0.3, "right_speed": -0.4},
        {"left_speed": 0.5, "right_speed": -0.1},
    ]

    for payload in commands:
        response = loop.run_until_complete(
            app.handle_request("POST", "/drive/differential", json=payload, headers=headers)
        )
        assert response.status_code == 202

    loop.run_until_complete(asyncio.wait_for(app.command_queue.wait_until_idle(), timeout=2.0))

    drive_commands = [cmd for cmd in context["motor"].commands if cmd[0] == "drive"]
    assert len(drive_commands) == len(commands)
    executed_pairs = [(entry[1][0], entry[1][1]) for entry in drive_commands]
    assert executed_pairs == [(c["left_speed"], c["right_speed"]) for c in commands]
    timestamps = [entry[1][2] for entry in drive_commands]
    assert timestamps == sorted(timestamps)


def test_servo_command_validation(control_app) -> None:
    app, _, loop = control_app
    response = loop.run_until_complete(
        app.handle_request(
            "POST",
            "/pan-tilt/position",
            json={"pan_deg": 120, "tilt_deg": 10},
            headers={"X-Api-Key": "test-key"},
        )
    )
    assert response.status_code == 422


def test_ultrasonic_schema(control_app) -> None:
    app, _, loop = control_app
    response = loop.run_until_complete(
        app.handle_request(
            "GET",
            "/telemetry/ultrasonic",
            headers={"X-Api-Key": "test-key"},
        )
    )
    data = response.body
    assert response.status_code == 200
    assert data["distance_m"] == pytest.approx(0.42)
    assert data["valid"] is True
    assert isinstance(data["history"], list)


def test_line_schema(control_app) -> None:
    app, _, loop = control_app
    response = loop.run_until_complete(
        app.handle_request(
            "GET",
            "/telemetry/line",
            headers={"X-Api-Key": "test-key"},
        )
    )
    assert response.status_code == 200
    assert response.body == {"left": 0.7, "right": 0.3, "on_line": True}
