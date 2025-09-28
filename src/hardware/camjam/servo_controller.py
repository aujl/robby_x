"""Basic abstraction for the CamJam pan/tilt servo kit."""

from __future__ import annotations

from typing import Iterable, Tuple


class CamJamPanTiltServos:
    """Track servo positions and enforce mechanical limits."""

    def __init__(
        self,
        *,
        pan_limits: Tuple[float, float] = (-90.0, 90.0),
        tilt_limits: Tuple[float, float] = (-45.0, 45.0),
    ) -> None:
        self._pan_limits = pan_limits
        self._tilt_limits = tilt_limits
        self._pan = 0.0
        self._tilt = 0.0

    @property
    def pan(self) -> float:
        return self._pan

    @property
    def tilt(self) -> float:
        return self._tilt

    @property
    def pan_limits(self) -> Tuple[float, float]:
        return self._pan_limits

    @property
    def tilt_limits(self) -> Tuple[float, float]:
        return self._tilt_limits

    def move_to(self, pan: float, tilt: float) -> None:
        self._pan = self._clamp(pan, self._pan_limits)
        self._tilt = self._clamp(tilt, self._tilt_limits)

    def scripted_positions(self) -> Iterable[Tuple[float, float]]:
        """Hardware does not expose scripted sweeps; return an empty iterator."""

        return ()

    @staticmethod
    def _clamp(value: float, limits: Tuple[float, float]) -> float:
        lower, upper = limits
        if lower > upper:
            lower, upper = upper, lower
        return max(lower, min(upper, value))


__all__ = ["CamJamPanTiltServos"]
