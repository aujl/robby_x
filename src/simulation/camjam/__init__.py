"""Simulation harness for CamJam EduKit components."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from src.hardware.camjam.sensors.encoders import WheelEncoders
from src.hardware.camjam.sensors.ultrasonic import UltrasonicRanger

from .scenarios import CamJamScenario, SCENARIOS, EncoderSample, ServoSample, UltrasonicSample

__all__ = [
    "CamJamSimulation",
    "SimulatedMotorController",
    "SimulatedPanTiltServos",
    "list_scenarios",
    "load_scenario",
    "reset_simulation_context",
    "simulation_enabled",
]


def simulation_enabled() -> bool:
    """Return whether CamJam simulation mode is enabled."""

    value = os.getenv("CAMJAM_SIMULATION", "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def list_scenarios() -> List[str]:
    """Return the available scenario slugs."""

    return sorted(SCENARIOS.keys())


def load_scenario(slug: str) -> CamJamScenario:
    """Retrieve a scenario definition by slug."""

    try:
        return SCENARIOS[slug]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"Unknown CamJam simulation scenario: {slug}") from exc


@dataclass
class _IndexTracker:
    value: int = 0


class ScenarioPlayback:
    """Iterate over the scripted sensor and actuator samples."""

    def __init__(self, scenario: CamJamScenario) -> None:
        self._scenario = scenario
        self._encoder_index = _IndexTracker()
        self._ultrasonic_index = _IndexTracker()
        self._servo_index = _IndexTracker()
        self._motor_index = _IndexTracker()

    @property
    def scenario(self) -> CamJamScenario:
        return self._scenario

    def reset(self) -> None:
        self._encoder_index.value = 0
        self._ultrasonic_index.value = 0
        self._servo_index.value = 0
        self._motor_index.value = 0

    def next_encoder_sample(self) -> EncoderSample:
        return self._next_sample(self._scenario.encoder_samples, self._encoder_index)

    def next_ultrasonic_sample(self) -> UltrasonicSample:
        return self._next_sample(self._scenario.ultrasonic_samples, self._ultrasonic_index)

    def next_servo_sample(self) -> ServoSample:
        return self._next_sample(self._scenario.servo_samples, self._servo_index)

    def expected_motor_command(self) -> Tuple[float, float]:
        sample = self._next_sample(self._scenario.motor_commands, self._motor_index)
        return (sample.left_speed, sample.right_speed)

    @staticmethod
    def _next_sample(sequence: Sequence, tracker: _IndexTracker):
        if not sequence:  # pragma: no cover - scenarios always populate sequences
            raise RuntimeError("Scenario sequence is empty")
        idx = min(tracker.value, len(sequence) - 1)
        sample = sequence[idx]
        if tracker.value < len(sequence) - 1:
            tracker.value += 1
        return sample


class SimulatedMotorController:
    """Drop-in replacement for :class:`CamJamMotorController` in simulation mode."""

    def __init__(self, playback: ScenarioPlayback) -> None:
        self._playback = playback
        self._estop = False
        self.command_log: List[Tuple[float, float]] = []
        self.expected_log: List[Tuple[float, float]] = []

    def drive(self, left_speed: float, right_speed: float) -> None:
        if self._estop:
            return
        self.command_log.append((left_speed, right_speed))
        self.expected_log.append(self._playback.expected_motor_command())

    def brake(self) -> None:
        if self._estop:
            return
        self.command_log.append((0.0, 0.0))

    def stop(self) -> None:
        if self._estop:
            return
        self.command_log.append((0.0, 0.0))

    def emergency_stop(self) -> None:
        self._estop = True
        self.command_log.append((0.0, 0.0))

    def reset_estop(self) -> None:
        self._estop = False

    def close(self) -> None:  # pragma: no cover - nothing to release in simulation
        pass

    def __enter__(self) -> "SimulatedMotorController":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class _SimulatedEncoderSampleReader:
    def __init__(self, playback: ScenarioPlayback) -> None:
        self._playback = playback

    async def __call__(self) -> Tuple[int, int, float]:
        sample = self._playback.next_encoder_sample()
        return (sample.ticks_left, sample.ticks_right, sample.timestamp)


class _SimulatedUltrasonicEchoReader:
    def __init__(self, playback: ScenarioPlayback) -> None:
        self._playback = playback

    async def __call__(self) -> float:
        sample = self._playback.next_ultrasonic_sample()
        # Convert distance to echo duration using the same nominal speed of sound as UltrasonicRanger
        return (2.0 * sample.distance_m) / 343.0


class SimulatedPanTiltServos:
    """Simulation stand-in for the CamJam pan/tilt servo bracket."""

    def __init__(
        self,
        playback: ScenarioPlayback,
        *,
        pan_limits: Tuple[float, float] = (-90.0, 90.0),
        tilt_limits: Tuple[float, float] = (-45.0, 45.0),
    ) -> None:
        self._playback = playback
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
        """Yield the scripted servo positions without consuming playback state."""

        return (
            (sample.pan_angle, sample.tilt_angle)
            for sample in self._playback.scenario.servo_samples
        )

    @staticmethod
    def _clamp(value: float, limits: Tuple[float, float]) -> float:
        return max(limits[0], min(limits[1], value))


class CamJamSimulation:
    """High-level entry point that wires simulated components together."""

    def __init__(self, scenario: CamJamScenario) -> None:
        self._playback = ScenarioPlayback(scenario)

    @property
    def scenario(self) -> CamJamScenario:
        return self._playback.scenario

    def reset(self) -> None:
        self._playback.reset()

    def create_motor_controller(self) -> SimulatedMotorController:
        return SimulatedMotorController(self._playback)

    def create_wheel_encoders(self, **kwargs) -> WheelEncoders:
        reader = _SimulatedEncoderSampleReader(self._playback)
        return WheelEncoders(sample_reader=reader, **kwargs)

    def create_ultrasonic_ranger(self, **kwargs) -> UltrasonicRanger:
        reader = _SimulatedUltrasonicEchoReader(self._playback)
        return UltrasonicRanger(echo_time_reader=reader, **kwargs)

    def create_pan_tilt_servos(self, **kwargs) -> SimulatedPanTiltServos:
        return SimulatedPanTiltServos(self._playback, **kwargs)


_SIMULATION_CONTEXT: CamJamSimulation | None = None


def _scenario_from_env() -> CamJamScenario:
    slug = os.getenv("CAMJAM_SIM_SCENARIO", "idle")
    return load_scenario(slug)


def get_simulation_context() -> CamJamSimulation:
    global _SIMULATION_CONTEXT
    if _SIMULATION_CONTEXT is None or _SIMULATION_CONTEXT.scenario.slug != os.getenv(
        "CAMJAM_SIM_SCENARIO", "idle"
    ):
        _SIMULATION_CONTEXT = CamJamSimulation(_scenario_from_env())
    return _SIMULATION_CONTEXT


def reset_simulation_context() -> None:
    global _SIMULATION_CONTEXT
    _SIMULATION_CONTEXT = None


