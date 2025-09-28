import asyncio

import pytest

from src.simulation.camjam import (
    list_scenarios,
    load_scenario,
    reset_simulation_context,
    simulation_enabled,
)
from src.hardware.camjam import (
    get_motor_controller,
    get_pan_tilt_servos,
    get_ultrasonic_ranger,
    get_wheel_encoders,
)


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    monkeypatch.delenv("CAMJAM_SIMULATION", raising=False)
    monkeypatch.delenv("CAMJAM_SIM_SCENARIO", raising=False)
    reset_simulation_context()
    yield
    reset_simulation_context()


def test_scenario_registry_contains_all_expected_slugs():
    expected = {
        "idle",
        "straight_line",
        "skid_turns",
        "ultrasonic_obstacle",
        "line_follow_transitions",
        "pan_tilt_sweeps",
    }
    assert expected.issubset(set(list_scenarios()))


def test_straight_line_scenario_encoder_progression(monkeypatch):
    monkeypatch.setenv("CAMJAM_SIMULATION", "1")
    monkeypatch.setenv("CAMJAM_SIM_SCENARIO", "straight_line")

    encoders = get_wheel_encoders()

    async def _collect():
        return [await encoders.read() for _ in range(4)]

    readings = asyncio.run(_collect())

    cumulative = [
        (reading.cumulative_ticks_left, reading.cumulative_ticks_right)
        for reading in readings
    ]

    assert cumulative[0] == (0, 0)
    assert cumulative[1] == (8, 8)
    assert cumulative[2] == (16, 16)
    assert cumulative[3] == (24, 24)
    assert all(readings[idx].valid is (idx != 0) for idx in range(4))


def test_ultrasonic_obstacle_distance_script(monkeypatch):
    monkeypatch.setenv("CAMJAM_SIMULATION", "true")
    monkeypatch.setenv("CAMJAM_SIM_SCENARIO", "ultrasonic_obstacle")

    ranger = get_ultrasonic_ranger()

    async def _collect():
        return [await ranger.read() for _ in range(5)]

    readings = asyncio.run(_collect())
    distances = [round(reading.distance_m, 3) for reading in readings]

    assert distances == [1.5, 1.35, 1.15, 0.95, 0.8]
    assert all(reading.valid for reading in readings)


def test_pan_tilt_sweep_angles_match_scenario(monkeypatch):
    monkeypatch.setenv("CAMJAM_SIMULATION", "yes")
    monkeypatch.setenv("CAMJAM_SIM_SCENARIO", "pan_tilt_sweeps")

    servos = get_pan_tilt_servos()
    scripted_positions = list(servos.scripted_positions())

    assert len(scripted_positions) >= 4
    assert scripted_positions[0] == (-45.0, -10.0)
    assert scripted_positions[-1] == (45.0, 10.0)


def test_simulation_toggle_reflects_environment(monkeypatch):
    assert simulation_enabled() is False

    monkeypatch.setenv("CAMJAM_SIMULATION", "on")
    assert simulation_enabled() is True

    monkeypatch.setenv("CAMJAM_SIM_SCENARIO", "idle")
    scenario = load_scenario("idle")
    assert scenario.slug == "idle"
    assert scenario.encoder_samples[0].ticks_left == 0

    motor = get_motor_controller()
    motor.drive(0.1, 0.1)
    assert motor.command_log[-1] == (0.1, 0.1)
