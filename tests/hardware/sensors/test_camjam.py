import asyncio
from dataclasses import asdict

import pytest
from src.hardware.camjam.sensors.encoders import WheelEncoders
from src.hardware.camjam.sensors.line_follow import LineFollower
from src.hardware.camjam.sensors.ultrasonic import UltrasonicRanger

pytestmark = pytest.mark.camjam_unit


class AsyncIteratorStub:
    def __init__(self, values):
        self._iter = iter(values)

    async def __call__(self):
        return next(self._iter)


def test_ultrasonic_distance_conversion_and_filtering():
    echo_stub = AsyncIteratorStub([0.002, 0.0021, 0.009, 0.00205])
    ranger = UltrasonicRanger(echo_time_reader=echo_stub)

    async def run_test():
        reading_1 = await ranger.read()
        reading_2 = await ranger.read()
        reading_3 = await ranger.read()
        reading_4 = await ranger.read()

        assert pytest.approx(reading_1.distance_m, rel=1e-3) == 0.343
        assert reading_1.valid

        assert pytest.approx(reading_2.distance_m, rel=1e-3) == 0.36015
        assert reading_2.valid

        assert not reading_3.valid, "Outlier should be flagged invalid"

        assert pytest.approx(reading_4.distance_m, rel=1e-3) == 0.3513
        assert reading_4.valid

        history = ranger.history
        assert all(r.valid for r in history)
        assert reading_4 in history

    asyncio.run(run_test())


def test_line_follow_normalization_and_hysteresis():
    left_stub = AsyncIteratorStub([100, 500, 800, 200])
    right_stub = AsyncIteratorStub([900, 600, 200, 450])

    follower = LineFollower(
        left_reader=left_stub,
        right_reader=right_stub,
        calibration=dict(left=(100, 900), right=(200, 1000)),
        active_threshold=0.6,
        inactive_threshold=0.4,
        ema_alpha=0.5,
    )

    async def run_test():
        reading_1 = await follower.read()
        reading_2 = await follower.read()
        reading_3 = await follower.read()
        reading_4 = await follower.read()

        assert reading_1.on_line, "Initial reading should trip due to right sensor"
        assert 0.0 <= reading_1.left <= 1.0
        assert 0.0 <= reading_1.right <= 1.0

        assert reading_2.on_line
        assert reading_3.on_line
        assert (
            not reading_4.on_line
        ), "Hysteresis should release once both fall below inactive threshold"

        left_values = [reading_1.left, reading_2.left, reading_3.left, reading_4.left]
        assert left_values[1] > left_values[0], "EMA should respond to increasing reflectance"
        assert left_values[3] < left_values[2], "EMA should decay when readings drop"

        telemetry_dict = asdict(reading_4)
        assert set(telemetry_dict) == {"left", "right", "on_line"}

    asyncio.run(run_test())


def test_encoder_velocity_and_debounce():
    sample_stub = AsyncIteratorStub(
        [
            (0, 0, 0.0),
            (10, 10, 0.1),
            (11, 11, 0.101),
            (21, 21, 0.2),
        ]
    )

    encoders = WheelEncoders(sample_reader=sample_stub, ticks_per_revolution=20, wheel_radius=0.03)

    async def run_test():
        reading_1 = await encoders.read()
        reading_2 = await encoders.read()
        reading_3 = await encoders.read()
        reading_4 = await encoders.read()

        assert reading_1.valid is False
        assert reading_2.valid is True
        assert pytest.approx(reading_2.angular_velocity_left, rel=1e-3) == pytest.approx(
            reading_2.angular_velocity_right, rel=1e-3
        )

        assert reading_3.valid is False, "Debounce should reject near-simultaneous pulse spikes"
        assert reading_3.cumulative_ticks_left == reading_2.cumulative_ticks_left

        assert reading_4.valid is True
        assert reading_4.cumulative_ticks_left == 21
        assert reading_4.cumulative_ticks_right == 21
        assert reading_4.angular_velocity_left > 0
        assert reading_4.linear_velocity_left > 0

        telemetry_dict = asdict(reading_4)
        assert "linear_velocity_left" in telemetry_dict
        assert "linear_velocity_right" in telemetry_dict

    asyncio.run(run_test())
