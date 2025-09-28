from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


pytestmark = pytest.mark.camjam_mocked_hw

from src.hardware.camjam.motor_controller import CamJamMotorController


@pytest.fixture
def camjam_config():
    return {
        "pwm_frequency": 1000,
        "motors": {
            "left": {
                "pwm_pin": 18,
                "forward_pin": 4,
                "reverse_pin": 17,
                "trim": 0.1,
                "speed_curve": [
                    [0.0, 0.0],
                    [0.5, 0.45],
                    [1.0, 1.0],
                ],
            },
            "right": {
                "pwm_pin": 19,
                "forward_pin": 27,
                "reverse_pin": 22,
                "trim": -0.05,
                "speed_curve": [
                    [0.0, 0.0],
                    [1.0, 1.0],
                ],
            },
        },
    }


@pytest.fixture
def pigpio_stub():
    pi = MagicMock()
    pi.write = MagicMock()
    pi.set_mode = MagicMock()
    pi.set_PWM_dutycycle = MagicMock()
    pi.set_PWM_frequency = MagicMock()
    pigpio_module = SimpleNamespace(pi=MagicMock(return_value=pi), OUTPUT=1)
    return pigpio_module, pi


def duty_for(speed):
    return int(round(255 * abs(speed)))


def test_drive_translates_pwm_and_direction(camjam_config, pigpio_stub):
    pigpio_module, pi = pigpio_stub
    controller = CamJamMotorController(config=camjam_config, pigpio_module=pigpio_module)

    controller.drive(0.5, -0.75)

    # 0.5 + 0.1 trim = 0.6, which the curve maps to 0.56
    pi.set_PWM_dutycycle.assert_any_call(camjam_config["motors"]["left"]["pwm_pin"], duty_for(0.56))
    pi.set_PWM_dutycycle.assert_any_call(camjam_config["motors"]["right"]["pwm_pin"], duty_for(0.75 - camjam_config["motors"]["right"]["trim"]))

    pi.write.assert_any_call(camjam_config["motors"]["left"]["forward_pin"], 1)
    pi.write.assert_any_call(camjam_config["motors"]["left"]["reverse_pin"], 0)
    pi.write.assert_any_call(camjam_config["motors"]["right"]["forward_pin"], 0)
    pi.write.assert_any_call(camjam_config["motors"]["right"]["reverse_pin"], 1)


def test_brake_short_brakes_both_motors(camjam_config, pigpio_stub):
    pigpio_module, pi = pigpio_stub
    controller = CamJamMotorController(config=camjam_config, pigpio_module=pigpio_module)

    controller.brake()

    for motor in camjam_config["motors"].values():
        pi.write.assert_any_call(motor["forward_pin"], 1)
        pi.write.assert_any_call(motor["reverse_pin"], 1)
        pi.set_PWM_dutycycle.assert_any_call(motor["pwm_pin"], 255)


def test_speed_commands_are_saturated(camjam_config, pigpio_stub):
    pigpio_module, pi = pigpio_stub
    controller = CamJamMotorController(config=camjam_config, pigpio_module=pigpio_module)

    controller.drive(3.0, -4.0)

    for motor in camjam_config["motors"].values():
        pi.set_PWM_dutycycle.assert_any_call(motor["pwm_pin"], 255)


def test_trim_offsets_are_applied_before_curve(camjam_config, pigpio_stub):
    pigpio_module, pi = pigpio_stub
    controller = CamJamMotorController(config=camjam_config, pigpio_module=pigpio_module)

    controller.drive(0.4, 0.4)

    left_expected = duty_for(0.45)  # 0.4 + 0.1 trim then curve reduces to 0.45
    right_expected = duty_for(0.35)  # 0.4 - 0.05 trim

    pi.set_PWM_dutycycle.assert_any_call(camjam_config["motors"]["left"]["pwm_pin"], left_expected)
    pi.set_PWM_dutycycle.assert_any_call(camjam_config["motors"]["right"]["pwm_pin"], right_expected)


def test_emergency_stop_cuts_power_and_blocks_new_commands(camjam_config, pigpio_stub):
    pigpio_module, pi = pigpio_stub
    controller = CamJamMotorController(config=camjam_config, pigpio_module=pigpio_module)

    controller.drive(0.5, 0.5)
    drive_call_count = pi.set_PWM_dutycycle.call_count

    controller.emergency_stop()

    for motor in camjam_config["motors"].values():
        pi.set_PWM_dutycycle.assert_any_call(motor["pwm_pin"], 0)
        pi.write.assert_any_call(motor["forward_pin"], 0)
        pi.write.assert_any_call(motor["reverse_pin"], 0)

    estop_call_count = pi.set_PWM_dutycycle.call_count
    assert estop_call_count == drive_call_count + len(camjam_config["motors"])

    controller.drive(0.8, 0.8)
    assert pi.set_PWM_dutycycle.call_count == estop_call_count

    controller.reset_estop()
    controller.drive(0.2, 0.2)

    assert pi.set_PWM_dutycycle.call_count > estop_call_count
