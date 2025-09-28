"""Asynchronous HC-SR04 ultrasonic sensor interface."""

from __future__ import annotations

from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from statistics import median

EchoTimeReader = Callable[[], Awaitable[float]]


@dataclass
class UltrasonicReading:
    """Telemetry for a single ultrasonic sensor measurement."""

    distance_m: float
    valid: bool


class UltrasonicRanger:
    """High-level HC-SR04 distance reader with filtering and calibration hooks."""

    def __init__(
        self,
        *,
        echo_time_reader: EchoTimeReader,
        speed_of_sound: float = 343.0,
        median_window: int = 3,
        max_deviation: float = 0.2,
        history_size: int = 5,
    ) -> None:
        if median_window < 1:
            raise ValueError("median_window must be >= 1")

        self._echo_time_reader = echo_time_reader
        self._speed_of_sound = speed_of_sound
        self._offset = 0.0
        self._median_window = median_window
        self._max_deviation = max_deviation
        self._raw_samples: deque[float] = deque(maxlen=median_window)
        self._history: deque[UltrasonicReading] = deque(maxlen=history_size)

    def calibrate(
        self,
        *,
        speed_of_sound: float | None = None,
        offset: float | None = None,
    ) -> None:
        """Adjust the conversion coefficients used for distance estimation."""
        if speed_of_sound is not None:
            self._speed_of_sound = speed_of_sound
        if offset is not None:
            self._offset = offset

    @property
    def history(self) -> list[UltrasonicReading]:
        """Return the list of recent valid readings."""
        return list(self._history)

    async def read(self) -> UltrasonicReading:
        """Trigger a measurement and return the filtered distance."""
        echo_duration = await self._echo_time_reader()
        raw_distance = self._offset + (echo_duration * self._speed_of_sound) / 2.0

        self._raw_samples.append(raw_distance)
        is_valid = self._is_within_deviation(raw_distance)

        reading = UltrasonicReading(distance_m=raw_distance, valid=is_valid)
        if is_valid:
            self._history.append(reading)
        return reading

    def _is_within_deviation(self, raw_distance: float) -> bool:
        """Check whether the new reading should be considered valid."""
        if len(self._raw_samples) < self._median_window:
            return True

        window_median = median(self._raw_samples)
        if window_median == 0:
            return True

        deviation = abs(raw_distance - window_median) / window_median
        return deviation <= self._max_deviation

