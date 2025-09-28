from __future__ import annotations

import math

import pytest
from src.services.diagnostics.camjam import CamJamDiagnostics

pytestmark = pytest.mark.camjam_unit


class TimeStub:
    def __init__(self) -> None:
        self.now = 0.0

    def advance(self, seconds: float) -> None:
        self.now += seconds

    def __call__(self) -> float:
        return self.now


@pytest.fixture()
def time_stub() -> TimeStub:
    return TimeStub()


@pytest.fixture()
def diagnostics(time_stub: TimeStub) -> CamJamDiagnostics:
    return CamJamDiagnostics(history_size=5, stale_after_s=5.0, time_source=time_stub)


def _strip_timestamps(events):
    """Replace volatile timestamps with sentinel for snapshot comparisons."""
    sanitized = []
    for event in events:
        event = dict(event)
        event["timestamp"] = round(event["timestamp"], 2)
        sanitized.append(event)
    return sanitized


def test_motor_logging_and_ui_payload(diagnostics: CamJamDiagnostics) -> None:
    diagnostics.record_motor_command(
        left_speed=0.65,
        right_speed=-0.4,
        duration_s=1.2,
        queue_depth=3,
        source="test",
    )

    payload = diagnostics.ui_payload()
    motor_history = payload["motors"]["history"]

    assert len(motor_history) == 1
    entry = motor_history[0]
    assert math.isclose(entry["left_speed"], 0.65)
    assert math.isclose(entry["right_speed"], -0.4)
    assert entry["queue_depth"] == 3
    assert entry["source"] == "test"

    health = diagnostics.health_report()
    assert health["motors"]["status"] == "ok"
    assert math.isfinite(health["motors"]["last_event_ts"])


def test_ultrasonic_history_and_health(diagnostics: CamJamDiagnostics, time_stub: TimeStub) -> None:
    diagnostics.record_ultrasonic("front", distance_cm=42.0, valid=True)
    time_stub.advance(1.0)
    diagnostics.record_ultrasonic("front", distance_cm=45.0, valid=False)
    diagnostics.record_ultrasonic("left", distance_cm=30.0, valid=True)

    payload = diagnostics.ui_payload(history=2)
    ultrasonic = payload["ultrasonic"]
    assert set(ultrasonic.keys()) == {"front", "left"}
    assert [round(sample["distance_cm"], 1) for sample in ultrasonic["front"]] == [45.0, 42.0]

    health = diagnostics.health_report()
    assert health["ultrasonic"]["front"]["status"] == "ok"
    assert health["ultrasonic"]["left"]["status"] == "ok"
    assert health["ultrasonic"]["front"]["last_distance_cm"] == pytest.approx(45.0)


def test_line_sensor_and_camera_status(diagnostics: CamJamDiagnostics, time_stub: TimeStub) -> None:
    diagnostics.record_line_event("left", active=True)
    diagnostics.record_line_event("left", active=False)
    diagnostics.record_line_event("center", active=True)

    diagnostics.record_pan_tilt(pan_deg=10.0, tilt_deg=-5.0, preset="scan")
    diagnostics.record_stream_status(status="live", detail="Operational")

    payload = diagnostics.ui_payload()
    line_history: dict[str, list] = payload["line_sensors"]
    assert line_history["left"][0]["active"] is False
    assert line_history["left"][1]["active"] is True
    assert line_history["center"][0]["active"] is True

    pan_tilt = payload["pan_tilt"]
    assert pan_tilt["pan_deg"] == pytest.approx(10.0)
    assert pan_tilt["tilt_deg"] == pytest.approx(-5.0)
    assert pan_tilt["preset"] == "scan"

    video = payload["video_stream"]
    assert video["status"] == "live"
    assert video["detail"] == "Operational"
    assert video["stale"] is False

    events = diagnostics.ui_payload(history=5)["events"]
    assert len(events) >= 5
    sanitized = _strip_timestamps(events[-3:])
    assert sanitized[0]["component"] == "line"
    assert sanitized[1]["component"] == "pan_tilt"
    assert sanitized[2]["component"] == "video_stream"


def test_health_reports_stale_when_no_updates(
    diagnostics: CamJamDiagnostics, time_stub: TimeStub
) -> None:
    diagnostics.record_motor_command(left_speed=0.1, right_speed=0.1)
    diagnostics.record_stream_status(status="live")

    time_stub.advance(10.0)

    health = diagnostics.health_report()
    assert health["motors"]["status"] == "stale"
    assert health["video_stream"]["stale"] is True

    payload = diagnostics.ui_payload()
    assert payload["video_stream"]["stale"] is True
