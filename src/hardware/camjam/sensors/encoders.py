"""Hall-effect wheel encoder aggregation and filtering."""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

SampleReader = Callable[[], Awaitable[tuple[int, int, float]]]


@dataclass
class EncoderTelemetry:
    """Normalized telemetry output for the pair of wheel encoders."""

    cumulative_ticks_left: int
    cumulative_ticks_right: int
    angular_velocity_left: float
    angular_velocity_right: float
    linear_velocity_left: float
    linear_velocity_right: float
    valid: bool


class WheelEncoders:
    """Compute wheel velocities from raw hall-effect encoder ticks."""

    def __init__(
        self,
        *,
        sample_reader: SampleReader,
        ticks_per_revolution: int = 20,
        wheel_radius: float = 0.03,
        min_interval: float = 0.005,
    ) -> None:
        if ticks_per_revolution <= 0:
            raise ValueError("ticks_per_revolution must be positive")
        if wheel_radius <= 0:
            raise ValueError("wheel_radius must be positive")
        if min_interval <= 0:
            raise ValueError("min_interval must be positive")

        self._sample_reader = sample_reader
        self._ticks_per_revolution = ticks_per_revolution
        self._wheel_radius = wheel_radius
        self._min_interval = min_interval

        self._last_valid_sample: tuple[int, int, float] | None = None

    def calibrate(
        self,
        *,
        ticks_per_revolution: int | None = None,
        wheel_radius: float | None = None,
    ) -> None:
        """Update calibration constants for the encoder conversion."""
        if ticks_per_revolution is not None:
            if ticks_per_revolution <= 0:
                raise ValueError("ticks_per_revolution must be positive")
            self._ticks_per_revolution = ticks_per_revolution
        if wheel_radius is not None:
            if wheel_radius <= 0:
                raise ValueError("wheel_radius must be positive")
            self._wheel_radius = wheel_radius

    async def read(self) -> EncoderTelemetry:
        """Return filtered telemetry for the wheel encoders."""
        sample = await self._sample_reader()
        ticks_left, ticks_right, timestamp = sample

        if self._last_valid_sample is None:
            self._last_valid_sample = sample
            return EncoderTelemetry(
                cumulative_ticks_left=ticks_left,
                cumulative_ticks_right=ticks_right,
                angular_velocity_left=0.0,
                angular_velocity_right=0.0,
                linear_velocity_left=0.0,
                linear_velocity_right=0.0,
                valid=False,
            )

        last_left, last_right, last_time = self._last_valid_sample
        delta_t = timestamp - last_time

        if delta_t <= 0 or delta_t < self._min_interval:
            return EncoderTelemetry(
                cumulative_ticks_left=last_left,
                cumulative_ticks_right=last_right,
                angular_velocity_left=0.0,
                angular_velocity_right=0.0,
                linear_velocity_left=0.0,
                linear_velocity_right=0.0,
                valid=False,
            )

        delta_left = ticks_left - last_left
        delta_right = ticks_right - last_right

        angular_left = self._ticks_to_angular_velocity(delta_left, delta_t)
        angular_right = self._ticks_to_angular_velocity(delta_right, delta_t)

        linear_left = angular_left * self._wheel_radius
        linear_right = angular_right * self._wheel_radius

        self._last_valid_sample = sample

        return EncoderTelemetry(
            cumulative_ticks_left=ticks_left,
            cumulative_ticks_right=ticks_right,
            angular_velocity_left=angular_left,
            angular_velocity_right=angular_right,
            linear_velocity_left=linear_left,
            linear_velocity_right=linear_right,
            valid=True,
        )

    def _ticks_to_angular_velocity(self, delta_ticks: int, delta_t: float) -> float:
        revolutions = delta_ticks / self._ticks_per_revolution
        return revolutions * 2.0 * math.pi / delta_t

