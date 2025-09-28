"""Line-follow sensor abstraction with normalization and hysteresis."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

AnalogReader = Callable[[], Awaitable[float]]


@dataclass
class LineTelemetry:
    """Normalized readings for the pair of reflectance sensors."""

    left: float
    right: float
    on_line: bool


class LineFollower:
    """Normalize raw reflectance values and apply hysteresis filtering."""

    def __init__(
        self,
        *,
        left_reader: AnalogReader,
        right_reader: AnalogReader,
        calibration: dict[str, tuple[float, float]] | None = None,
        ema_alpha: float = 0.5,
        active_threshold: float = 0.6,
        inactive_threshold: float = 0.4,
    ) -> None:
        """Initialise the filter with optional calibration and hysteresis settings."""
        if not 0.0 < ema_alpha <= 1.0:
            raise ValueError("ema_alpha must be between 0 and 1")
        if inactive_threshold > active_threshold:
            raise ValueError("inactive_threshold must be <= active_threshold")

        self._left_reader = left_reader
        self._right_reader = right_reader
        self._ema_alpha = ema_alpha
        self._active_threshold = active_threshold
        self._inactive_threshold = inactive_threshold

        calibration = calibration or {}
        self._calibration_left = calibration.get("left", (0.0, 1.0))
        self._calibration_right = calibration.get("right", (0.0, 1.0))

        self._ema_left: float | None = None
        self._ema_right: float | None = None
        self._on_line = False

    def set_calibration(
        self,
        *,
        left: tuple[float, float] | None = None,
        right: tuple[float, float] | None = None,
    ) -> None:
        """Update the min/max calibration bounds."""
        if left is not None:
            self._calibration_left = left
        if right is not None:
            self._calibration_right = right

    async def read(self) -> LineTelemetry:
        """Return the current normalized telemetry from both sensors."""
        raw_left = await self._left_reader()
        raw_right = await self._right_reader()

        normalized_left = self._normalize(raw_left, self._calibration_left)
        normalized_right = self._normalize(raw_right, self._calibration_right)

        self._ema_left = self._apply_ema(self._ema_left, normalized_left)
        self._ema_right = self._apply_ema(self._ema_right, normalized_right)

        self._update_hysteresis()

        return LineTelemetry(left=self._ema_left, right=self._ema_right, on_line=self._on_line)

    def _apply_ema(self, previous: float | None, current: float) -> float:
        if previous is None:
            return current
        return self._ema_alpha * current + (1.0 - self._ema_alpha) * previous

    def _normalize(self, value: float, bounds: tuple[float, float]) -> float:
        low, high = bounds
        if high <= low:
            return 0.0
        normalized = (value - low) / (high - low)
        return max(0.0, min(1.0, normalized))

    def _update_hysteresis(self) -> None:
        assert self._ema_left is not None and self._ema_right is not None

        if not self._on_line:
            if (
                self._ema_left >= self._active_threshold
                or self._ema_right >= self._active_threshold
            ):
                self._on_line = True
        else:
            if (
                self._ema_left < self._inactive_threshold
                and self._ema_right < self._inactive_threshold
            ):
                self._on_line = False

