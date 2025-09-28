"""Diagnostics instrumentation for CamJam hardware and video subsystems."""

from __future__ import annotations

import importlib
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any, Protocol, cast

structlog: Any | None
try:  # pragma: no cover - exercised through fallback logger in tests
    structlog = importlib.import_module("structlog")
except ModuleNotFoundError:  # pragma: no cover - structlog is optional for unit tests
    structlog = None


class DiagnosticsLogger(Protocol):
    """Contract shared by the real and fallback loggers."""

    def bind(self, **_: Any) -> "DiagnosticsLogger": ...

    def info(self, _event: str, **_: Any) -> None: ...

    def warning(self, _event: str, **_: Any) -> None: ...


def _get_logger(name: str) -> DiagnosticsLogger:
    if structlog is None:  # pragma: no cover - deterministic branch during unit tests
        return _FallbackLogger(name)
    return cast(DiagnosticsLogger, structlog.get_logger(name))


class _FallbackLogger:
    """Minimal logger used when structlog is not available."""

    def __init__(self, name: str) -> None:
        self.name = name

    def bind(self, **_: Any) -> _FallbackLogger:  # pragma: no cover - trivial
        return self

    def info(self, _event: str, **_: Any) -> None:  # pragma: no cover - noop logging
        return None

    def warning(self, _event: str, **_: Any) -> None:  # pragma: no cover - noop logging
        return None


@dataclass
class DiagnosticsEvent:
    """Structured log entry for UI and downstream analytics."""

    timestamp: float
    component: str
    event: str
    data: dict[str, Any]


class CamJamDiagnostics:
    """Collect diagnostics telemetry and health status for CamJam hardware."""

    def __init__(
        self,
        *,
        history_size: int = 200,
        stale_after_s: float = 5.0,
        time_source: Callable[[], float] | None = None,
    ) -> None:
        """Initialise diagnostics buffers and capture configuration."""
        if history_size <= 0:
            raise ValueError("history_size must be positive")
        if stale_after_s <= 0:
            raise ValueError("stale_after_s must be positive")

        self._history: deque[DiagnosticsEvent] = deque(maxlen=history_size)
        self._motor_history: deque[dict[str, Any]] = deque(maxlen=history_size)
        self._ultrasonic_history: dict[str, deque[dict[str, Any]]] = {}
        self._line_history: dict[str, deque[dict[str, Any]]] = {}

        self._pan_deg = 0.0
        self._tilt_deg = 0.0
        self._pan_tilt_preset: str | None = None

        self._stream_status: str = "idle"
        self._stream_detail: str | None = None
        self._stream_src: str | None = None

        self._last_motor_ts: float | None = None
        self._last_motor_payload: dict[str, Any] | None = None
        self._last_ultrasonic_ts: dict[str, float] = {}
        self._last_line_ts: dict[str, float] = {}
        self._last_pan_tilt_ts: float | None = None
        self._last_stream_ts: float | None = None

        self._time_source = time_source or __import__("time").time
        self._stale_after = float(stale_after_s)
        self._logger = _get_logger("camjam.diagnostics").bind(service="camjam")

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------
    def record_motor_command(
        self,
        *,
        left_speed: float,
        right_speed: float,
        duration_s: float | None = None,
        queue_depth: int | None = None,
        source: str = "operator",
    ) -> None:
        """Record a motor drive command and emit a diagnostics event."""
        timestamp = self._now()
        payload = {
            "left_speed": float(left_speed),
            "right_speed": float(right_speed),
            "duration_s": float(duration_s) if duration_s is not None else None,
            "queue_depth": queue_depth,
            "source": source,
        }
        self._motor_history.append(payload)
        self._last_motor_ts = timestamp
        self._last_motor_payload = payload
        self._append_event("motors", "drive_command", payload, timestamp)

    def record_ultrasonic(self, sensor: str, *, distance_cm: float, valid: bool) -> None:
        """Record an ultrasonic measurement for the named sensor."""
        timestamp = self._now()
        payload = {
            "sensor": sensor,
            "distance_cm": float(distance_cm),
            "valid": bool(valid),
        }
        history = self._ultrasonic_history.setdefault(sensor, deque(maxlen=self._history.maxlen))
        history.append(payload)
        self._last_ultrasonic_ts[sensor] = timestamp
        self._append_event("ultrasonic", "range_measurement", payload, timestamp)

    def record_line_event(self, sensor: str, *, active: bool) -> None:
        """Record a line sensor activation state change."""
        timestamp = self._now()
        payload = {
            "sensor": sensor,
            "active": bool(active),
        }
        history = self._line_history.setdefault(sensor, deque(maxlen=self._history.maxlen))
        history.append(payload)
        self._last_line_ts[sensor] = timestamp
        self._append_event("line", "sensor_state", payload, timestamp)

    def record_pan_tilt(
        self,
        *,
        pan_deg: float,
        tilt_deg: float,
        preset: str | None = None,
    ) -> None:
        """Record the most recent pan/tilt position and preset metadata."""
        timestamp = self._now()
        self._pan_deg = float(pan_deg)
        self._tilt_deg = float(tilt_deg)
        self._pan_tilt_preset = preset
        self._last_pan_tilt_ts = timestamp
        payload = {
            "pan_deg": self._pan_deg,
            "tilt_deg": self._tilt_deg,
            "preset": preset,
        }
        self._append_event("pan_tilt", "position_update", payload, timestamp)

    def record_stream_status(
        self,
        *,
        status: str,
        detail: str | None = None,
        src: str | None = None,
    ) -> None:
        """Record the status of the video streaming pipeline."""
        timestamp = self._now()
        self._stream_status = status
        self._stream_detail = detail
        self._stream_src = src
        self._last_stream_ts = timestamp
        payload = {
            "status": status,
            "detail": detail,
            "src": src,
        }
        self._append_event("video_stream", "status", payload, timestamp)

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def health_report(self) -> dict[str, Any]:
        """Summarise the health of each subsystem with stale detection."""
        now = self._now()

        def component_status(last_ts: float | None) -> str:
            if last_ts is None:
                return "unknown"
            if now - last_ts > self._stale_after:
                return "stale"
            return "ok"

        ultrasonic = {
            sensor: {
                "status": component_status(self._last_ultrasonic_ts.get(sensor)),
                "last_event_ts": self._last_ultrasonic_ts.get(sensor),
                "last_distance_cm": history[-1]["distance_cm"] if history else None,
                "valid": history[-1]["valid"] if history else None,
            }
            for sensor, history in self._ultrasonic_history.items()
        }

        line_sensors = {
            sensor: {
                "status": component_status(self._last_line_ts.get(sensor)),
                "last_event_ts": self._last_line_ts.get(sensor),
                "active": history[-1]["active"] if history else None,
            }
            for sensor, history in self._line_history.items()
        }

        pan_tilt_status = {
            "status": component_status(self._last_pan_tilt_ts),
            "last_event_ts": self._last_pan_tilt_ts,
            "pan_deg": self._pan_deg,
            "tilt_deg": self._tilt_deg,
            "preset": self._pan_tilt_preset,
        }

        video_stale = component_status(self._last_stream_ts) == "stale"
        video_status = {
            "status": self._stream_status,
            "detail": self._stream_detail,
            "src": self._stream_src,
            "last_event_ts": self._last_stream_ts,
            "stale": video_stale,
        }

        return {
            "motors": {
                "status": component_status(self._last_motor_ts),
                "last_event_ts": self._last_motor_ts,
                "last_command": self._last_motor_payload,
            },
            "ultrasonic": ultrasonic,
            "line_sensors": line_sensors,
            "pan_tilt": pan_tilt_status,
            "video_stream": video_status,
        }

    def ui_payload(self, history: int = 10) -> dict[str, Any]:
        """Generate a structured payload for the diagnostics UI."""
        if history <= 0:
            raise ValueError("history must be positive")

        health = self.health_report()
        motors_payload = {
            **health["motors"],
            "history": self._serialize_history(self._motor_history, history),
        }
        ultrasonic_payload = {
            sensor: self._serialize_history(samples, history)
            for sensor, samples in self._ultrasonic_history.items()
        }
        line_payload = {
            sensor: self._serialize_history(samples, history)
            for sensor, samples in self._line_history.items()
        }

        events = [asdict(event) for event in self._tail(self._history, history)]

        pan_tilt = {
            **health["pan_tilt"],
            "stale": health["pan_tilt"]["status"] == "stale",
        }
        video_stream = {
            **health["video_stream"],
        }

        return {
            "motors": motors_payload,
            "ultrasonic": ultrasonic_payload,
            "line_sensors": line_payload,
            "pan_tilt": pan_tilt,
            "video_stream": video_stream,
            "events": events,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _append_event(
        self,
        component: str,
        event: str,
        payload: Mapping[str, Any],
        timestamp: float | None = None,
    ) -> None:
        ts = timestamp if timestamp is not None else self._now()
        entry = DiagnosticsEvent(timestamp=ts, component=component, event=event, data=dict(payload))
        self._history.append(entry)
        self._logger.bind(component=component).info(event, timestamp=ts, **dict(payload))

    def _serialize_history(
        self,
        history: deque[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        samples = list(history)[-limit:]
        samples.reverse()
        result: list[dict[str, Any]] = []
        for sample in samples:
            result.append(dict(sample))
        return result

    def _tail(self, history: deque[DiagnosticsEvent], limit: int) -> Iterable[DiagnosticsEvent]:
        return list(history)[-limit:]

    def _now(self) -> float:
        return float(self._time_source())
