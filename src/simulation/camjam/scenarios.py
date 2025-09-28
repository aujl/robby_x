"""Deterministic motion and sensor scripts for CamJam simulations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class EncoderSample:
    """Represents a cumulative tick count sample for both wheels."""

    ticks_left: int
    ticks_right: int
    timestamp: float


@dataclass(frozen=True)
class UltrasonicSample:
    """One HC-SR04 distance measurement in metres."""

    distance_m: float


@dataclass(frozen=True)
class ServoSample:
    """Pan/tilt servo target angles in degrees."""

    pan_angle: float
    tilt_angle: float


@dataclass(frozen=True)
class MotorCommand:
    """Idealized differential-drive command for each timestep."""

    left_speed: float
    right_speed: float


@dataclass(frozen=True)
class CamJamScenario:
    """Aggregate script describing motion, sensing and actuation."""

    slug: str
    label: str
    description: str
    encoder_samples: Tuple[EncoderSample, ...]
    ultrasonic_samples: Tuple[UltrasonicSample, ...]
    servo_samples: Tuple[ServoSample, ...]
    motor_commands: Tuple[MotorCommand, ...]


def _build_scenarios() -> Dict[str, CamJamScenario]:
    """Return the catalogue of baked-in simulation scenarios."""

    idle = CamJamScenario(
        slug="idle",
        label="Idle hover",
        description="No motion, constant range measurement, centred servos.",
        encoder_samples=(
            EncoderSample(0, 0, 0.0),
            EncoderSample(0, 0, 0.1),
            EncoderSample(0, 0, 0.2),
            EncoderSample(0, 0, 0.3),
        ),
        ultrasonic_samples=(
            UltrasonicSample(2.5),
            UltrasonicSample(2.5),
            UltrasonicSample(2.5),
            UltrasonicSample(2.5),
        ),
        servo_samples=(
            ServoSample(0.0, 0.0),
            ServoSample(0.0, 0.0),
            ServoSample(0.0, 0.0),
            ServoSample(0.0, 0.0),
        ),
        motor_commands=(
            MotorCommand(0.0, 0.0),
            MotorCommand(0.0, 0.0),
            MotorCommand(0.0, 0.0),
            MotorCommand(0.0, 0.0),
        ),
    )

    straight_line = CamJamScenario(
        slug="straight_line",
        label="Straight line",
        description="Drives forward at constant speed with stable servo and range readings.",
        encoder_samples=(
            EncoderSample(0, 0, 0.0),
            EncoderSample(8, 8, 0.1),
            EncoderSample(16, 16, 0.2),
            EncoderSample(24, 24, 0.3),
        ),
        ultrasonic_samples=(
            UltrasonicSample(1.0),
            UltrasonicSample(1.0),
            UltrasonicSample(1.0),
            UltrasonicSample(1.0),
        ),
        servo_samples=(
            ServoSample(0.0, -5.0),
            ServoSample(0.0, -5.0),
            ServoSample(0.0, -5.0),
            ServoSample(0.0, -5.0),
        ),
        motor_commands=(
            MotorCommand(0.45, 0.45),
            MotorCommand(0.45, 0.45),
            MotorCommand(0.45, 0.45),
            MotorCommand(0.45, 0.45),
        ),
    )

    skid_turns = CamJamScenario(
        slug="skid_turns",
        label="Skid turns",
        description="Left wheel advances while right reverses to pivot in place.",
        encoder_samples=(
            EncoderSample(0, 0, 0.0),
            EncoderSample(5, -5, 0.1),
            EncoderSample(10, -10, 0.2),
            EncoderSample(15, -15, 0.3),
        ),
        ultrasonic_samples=(
            UltrasonicSample(1.8),
            UltrasonicSample(1.8),
            UltrasonicSample(1.6),
            UltrasonicSample(1.6),
        ),
        servo_samples=(
            ServoSample(-15.0, -5.0),
            ServoSample(-5.0, -5.0),
            ServoSample(5.0, -5.0),
            ServoSample(15.0, -5.0),
        ),
        motor_commands=(
            MotorCommand(0.35, -0.35),
            MotorCommand(0.35, -0.35),
            MotorCommand(0.35, -0.35),
            MotorCommand(0.35, -0.35),
        ),
    )

    ultrasonic_obstacle = CamJamScenario(
        slug="ultrasonic_obstacle",
        label="Approaching obstacle",
        description="Constant drive with decreasing range to simulate obstacle closing in.",
        encoder_samples=(
            EncoderSample(0, 0, 0.0),
            EncoderSample(6, 6, 0.1),
            EncoderSample(12, 12, 0.2),
            EncoderSample(18, 18, 0.3),
            EncoderSample(24, 24, 0.4),
        ),
        ultrasonic_samples=(
            UltrasonicSample(1.5),
            UltrasonicSample(1.35),
            UltrasonicSample(1.15),
            UltrasonicSample(0.95),
            UltrasonicSample(0.8),
        ),
        servo_samples=(
            ServoSample(0.0, -2.0),
            ServoSample(0.0, -2.0),
            ServoSample(0.0, -2.0),
            ServoSample(0.0, -2.0),
            ServoSample(0.0, -2.0),
        ),
        motor_commands=(
            MotorCommand(0.4, 0.4),
            MotorCommand(0.4, 0.4),
            MotorCommand(0.35, 0.35),
            MotorCommand(0.2, 0.2),
            MotorCommand(0.0, 0.0),
        ),
    )

    line_follow = CamJamScenario(
        slug="line_follow_transitions",
        label="Line-follow transitions",
        description="Alternating speed bias to mimic corrections when reacquiring a line.",
        encoder_samples=(
            EncoderSample(0, 0, 0.0),
            EncoderSample(5, 4, 0.1),
            EncoderSample(12, 10, 0.2),
            EncoderSample(20, 19, 0.3),
            EncoderSample(30, 30, 0.4),
        ),
        ultrasonic_samples=(
            UltrasonicSample(1.0),
            UltrasonicSample(0.95),
            UltrasonicSample(0.9),
            UltrasonicSample(0.95),
            UltrasonicSample(1.0),
        ),
        servo_samples=(
            ServoSample(-10.0, -5.0),
            ServoSample(-5.0, -5.0),
            ServoSample(0.0, -5.0),
            ServoSample(5.0, -5.0),
            ServoSample(10.0, -5.0),
        ),
        motor_commands=(
            MotorCommand(0.3, 0.25),
            MotorCommand(0.35, 0.25),
            MotorCommand(0.25, 0.35),
            MotorCommand(0.3, 0.28),
            MotorCommand(0.32, 0.32),
        ),
    )

    pan_tilt = CamJamScenario(
        slug="pan_tilt_sweeps",
        label="Pan/tilt sweeps",
        description="Stationary base while the mast scans the environment.",
        encoder_samples=(
            EncoderSample(0, 0, 0.0),
            EncoderSample(0, 0, 0.1),
            EncoderSample(0, 0, 0.2),
            EncoderSample(0, 0, 0.3),
            EncoderSample(0, 0, 0.4),
        ),
        ultrasonic_samples=(
            UltrasonicSample(2.0),
            UltrasonicSample(2.2),
            UltrasonicSample(2.4),
            UltrasonicSample(2.1),
            UltrasonicSample(2.0),
        ),
        servo_samples=(
            ServoSample(-45.0, -10.0),
            ServoSample(-22.5, -5.0),
            ServoSample(0.0, 0.0),
            ServoSample(22.5, 5.0),
            ServoSample(45.0, 10.0),
        ),
        motor_commands=(
            MotorCommand(0.0, 0.0),
            MotorCommand(0.0, 0.0),
            MotorCommand(0.0, 0.0),
            MotorCommand(0.0, 0.0),
            MotorCommand(0.0, 0.0),
        ),
    )

    return {
        scenario.slug: scenario
        for scenario in (
            idle,
            straight_line,
            skid_turns,
            ultrasonic_obstacle,
            line_follow,
            pan_tilt,
        )
    }


SCENARIOS: Dict[str, CamJamScenario] = _build_scenarios()

