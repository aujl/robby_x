"""Helper factories that toggle between physical and simulated CamJam hardware."""

from __future__ import annotations

from typing import Any

from .motor_controller import CamJamMotorController
from .servo_controller import CamJamPanTiltServos
from .sensors.encoders import WheelEncoders
from .sensors.ultrasonic import UltrasonicRanger

__all__ = [
    "CamJamMotorController",
    "CamJamPanTiltServos",
    "WheelEncoders",
    "UltrasonicRanger",
    "get_motor_controller",
    "get_wheel_encoders",
    "get_ultrasonic_ranger",
    "get_pan_tilt_servos",
]


def _simulation_context():
    from src.simulation import camjam as camjam_sim

    return camjam_sim.get_simulation_context()


def _simulation_enabled() -> bool:
    from src.simulation import camjam as camjam_sim

    return camjam_sim.simulation_enabled()


def get_motor_controller(**kwargs: Any) -> CamJamMotorController:
    """Return a motor controller for the current runtime context."""

    if _simulation_enabled():
        return _simulation_context().create_motor_controller()
    return CamJamMotorController(**kwargs)


def get_wheel_encoders(*, sample_reader=None, **kwargs: Any) -> WheelEncoders:
    """Return wheel encoders backed by either hardware or simulation."""

    if _simulation_enabled():
        return _simulation_context().create_wheel_encoders(**kwargs)
    if sample_reader is None:
        raise ValueError("sample_reader is required when not running in simulation")
    return WheelEncoders(sample_reader=sample_reader, **kwargs)


def get_ultrasonic_ranger(*, echo_time_reader=None, **kwargs: Any) -> UltrasonicRanger:
    """Return an ultrasonic ranger instance for the active environment."""

    if _simulation_enabled():
        return _simulation_context().create_ultrasonic_ranger(**kwargs)
    if echo_time_reader is None:
        raise ValueError("echo_time_reader is required when not running in simulation")
    return UltrasonicRanger(echo_time_reader=echo_time_reader, **kwargs)


def get_pan_tilt_servos(**kwargs: Any) -> CamJamPanTiltServos:
    """Return the pan/tilt servo helper appropriate for the environment."""

    if _simulation_enabled():
        return _simulation_context().create_pan_tilt_servos(**kwargs)
    return CamJamPanTiltServos(**kwargs)

