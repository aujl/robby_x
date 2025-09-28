from types import SimpleNamespace

import pytest

import src.hardware.camjam as camjam

pytestmark = pytest.mark.camjam_unit


def test_factories_use_runtime_implementations(monkeypatch: pytest.MonkeyPatch) -> None:
    motor_instance = object()
    encoder_instance = object()
    ultrasonic_instance = object()
    servo_instance = object()

    monkeypatch.setattr(camjam, "_simulation_enabled", lambda: False)
    monkeypatch.setattr(camjam, "CamJamMotorController", lambda **_: motor_instance)
    monkeypatch.setattr(camjam, "WheelEncoders", lambda **_: encoder_instance)
    monkeypatch.setattr(camjam, "UltrasonicRanger", lambda **_: ultrasonic_instance)
    monkeypatch.setattr(camjam, "CamJamPanTiltServos", lambda **_: servo_instance)

    encoders = camjam.get_wheel_encoders(sample_reader=SimpleNamespace())
    ranger = camjam.get_ultrasonic_ranger(echo_time_reader=SimpleNamespace())
    motor = camjam.get_motor_controller()
    servos = camjam.get_pan_tilt_servos()

    assert encoders is encoder_instance
    assert ranger is ultrasonic_instance
    assert motor is motor_instance
    assert servos is servo_instance


def test_factories_require_readers_outside_simulation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(camjam, "_simulation_enabled", lambda: False)

    with pytest.raises(ValueError):
        camjam.get_wheel_encoders()

    with pytest.raises(ValueError):
        camjam.get_ultrasonic_ranger()


def test_factories_delegate_to_simulation_context(monkeypatch: pytest.MonkeyPatch) -> None:
    context = SimpleNamespace(
        create_motor_controller=lambda **_: "sim-motor",
        create_wheel_encoders=lambda **_: "sim-encoders",
        create_ultrasonic_ranger=lambda **_: "sim-ranger",
        create_pan_tilt_servos=lambda **_: "sim-servos",
    )

    monkeypatch.setattr(camjam, "_simulation_enabled", lambda: True)
    monkeypatch.setattr(camjam, "_simulation_context", lambda: context)

    assert camjam.get_motor_controller() == "sim-motor"
    assert camjam.get_wheel_encoders() == "sim-encoders"
    assert camjam.get_ultrasonic_ranger() == "sim-ranger"
    assert camjam.get_pan_tilt_servos() == "sim-servos"
