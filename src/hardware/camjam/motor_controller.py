"""CamJam EduKit 3 dual motor controller helpers.

This module exposes :class:`CamJamMotorController`, a thin abstraction around the
CamJam EduKit 3 L293D motor driver board.  It automatically loads the
pin-mapping and tuning information from ``config/camjam.yaml`` (or accepts the
structure directly) and provides a high-level differential drive interface.

Example
-------
>>> from src.hardware.camjam.motor_controller import CamJamMotorController
>>> with CamJamMotorController() as drive:
...     drive.drive(0.35, 0.35)  # roll forward
...     drive.drive(0.1, -0.1)   # pivot in place
...     drive.brake()
...     drive.emergency_stop()

The controller can be tuned through per-motor trim values and arbitrary speed
curves that compensate for gearbox tolerances.  Refer to
``docs/hardware/camjam-motors.md`` for detailed guidance on data collection and
calibration.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, cast

yaml: Any | None
try:  # pragma: no cover - optional dependency
    yaml = importlib.import_module("yaml")
except ModuleNotFoundError:  # pragma: no cover - exercised when PyYAML is missing
    yaml = None


@dataclass(frozen=True)
class _MotorChannel:
    """Holds the static configuration for one motor channel."""

    name: str
    pwm_pin: int
    forward_pin: int
    reverse_pin: int
    trim: float
    speed_curve: tuple[tuple[float, float], ...]


class _BaseBackend:
    """Interface expected from low level GPIO backends."""

    def setup_motor(
        self,
        motor: _MotorChannel,
        frequency: int,
    ) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def command_motor(
        self,
        motor: _MotorChannel,
        value: float,
    ) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def brake_motor(self, motor: _MotorChannel) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def estop_motor(self, motor: _MotorChannel) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def shutdown(self) -> None:  # pragma: no cover - abstract
        raise NotImplementedError


class _PigpioBackend(_BaseBackend):
    """Backend implementation that talks to ``pigpio``."""

    def __init__(
        self,
        pigpio_module: Any,
        *,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        self._pigpio = pigpio_module
        if hasattr(pigpio_module, "pi"):
            if host is None and port is None:
                self._pi = pigpio_module.pi()
            elif port is None:
                self._pi = pigpio_module.pi(host)
            else:
                self._pi = pigpio_module.pi(host, port)
        else:  # pragma: no cover - defensive branch
            raise RuntimeError("pigpio module does not expose pi()")
        if not self._pi:  # pragma: no cover - defensive branch
            raise RuntimeError("Unable to connect to pigpio daemon")

    def setup_motor(self, motor: _MotorChannel, frequency: int) -> None:
        self._pi.set_mode(motor.forward_pin, self._pigpio.OUTPUT)
        self._pi.set_mode(motor.reverse_pin, self._pigpio.OUTPUT)
        self._pi.set_mode(motor.pwm_pin, self._pigpio.OUTPUT)
        self._pi.write(motor.forward_pin, 0)
        self._pi.write(motor.reverse_pin, 0)
        self._pi.set_PWM_frequency(motor.pwm_pin, frequency)
        self._pi.set_PWM_dutycycle(motor.pwm_pin, 0)

    def command_motor(self, motor: _MotorChannel, value: float) -> None:
        duty = int(round(255 * abs(value)))
        self._pi.set_PWM_dutycycle(motor.pwm_pin, duty)
        if value > 0:
            self._pi.write(motor.forward_pin, 1)
            self._pi.write(motor.reverse_pin, 0)
        elif value < 0:
            self._pi.write(motor.forward_pin, 0)
            self._pi.write(motor.reverse_pin, 1)
        else:
            self._pi.write(motor.forward_pin, 0)
            self._pi.write(motor.reverse_pin, 0)

    def brake_motor(self, motor: _MotorChannel) -> None:
        self._pi.write(motor.forward_pin, 1)
        self._pi.write(motor.reverse_pin, 1)
        self._pi.set_PWM_dutycycle(motor.pwm_pin, 255)

    def estop_motor(self, motor: _MotorChannel) -> None:
        self._pi.set_PWM_dutycycle(motor.pwm_pin, 0)
        self._pi.write(motor.forward_pin, 0)
        self._pi.write(motor.reverse_pin, 0)

    def shutdown(self) -> None:
        try:
            self._pi.stop()
        except AttributeError:  # pragma: no cover - pigpio always exposes stop()
            pass


class _RPiGPIOBackend(_BaseBackend):
    """Backend that falls back to ``RPi.GPIO`` PWM when pigpio is unavailable."""

    def __init__(self, gpio_module: Any) -> None:
        self._gpio = gpio_module
        self._gpio.setmode(self._gpio.BCM)
        self._pwm_instances: dict[int, Any] = {}

    def setup_motor(self, motor: _MotorChannel, frequency: int) -> None:
        self._gpio.setup(motor.forward_pin, self._gpio.OUT)
        self._gpio.setup(motor.reverse_pin, self._gpio.OUT)
        self._gpio.setup(motor.pwm_pin, self._gpio.OUT)
        pwm = self._gpio.PWM(motor.pwm_pin, frequency)
        pwm.start(0)
        self._pwm_instances[motor.pwm_pin] = pwm
        self._gpio.output(motor.forward_pin, self._gpio.LOW)
        self._gpio.output(motor.reverse_pin, self._gpio.LOW)

    def _set_pwm(self, motor: _MotorChannel, duty: int) -> None:
        pwm = self._pwm_instances[motor.pwm_pin]
        pwm.ChangeDutyCycle(duty * 100 / 255)

    def command_motor(self, motor: _MotorChannel, value: float) -> None:
        duty = int(round(255 * abs(value)))
        self._set_pwm(motor, duty)
        if value > 0:
            self._gpio.output(motor.forward_pin, self._gpio.HIGH)
            self._gpio.output(motor.reverse_pin, self._gpio.LOW)
        elif value < 0:
            self._gpio.output(motor.forward_pin, self._gpio.LOW)
            self._gpio.output(motor.reverse_pin, self._gpio.HIGH)
        else:
            self._gpio.output(motor.forward_pin, self._gpio.LOW)
            self._gpio.output(motor.reverse_pin, self._gpio.LOW)

    def brake_motor(self, motor: _MotorChannel) -> None:
        self._set_pwm(motor, 255)
        self._gpio.output(motor.forward_pin, self._gpio.HIGH)
        self._gpio.output(motor.reverse_pin, self._gpio.HIGH)

    def estop_motor(self, motor: _MotorChannel) -> None:
        self._set_pwm(motor, 0)
        self._gpio.output(motor.forward_pin, self._gpio.LOW)
        self._gpio.output(motor.reverse_pin, self._gpio.LOW)

    def shutdown(self) -> None:
        for pwm in self._pwm_instances.values():
            pwm.stop()
        self._gpio.cleanup()


def _load_yaml_config(config_path: Path) -> Mapping[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load CamJam configuration files")
    with config_path.open("r", encoding="utf-8") as handle:
        return cast(Mapping[str, Any], yaml.safe_load(handle))


def _ensure_curve(points: Iterable[Sequence[float]]) -> tuple[tuple[float, float], ...]:
    curve: list[tuple[float, float]] = []
    for entry in points:
        if len(entry) != 2:
            raise ValueError("Curve points must contain exactly two floats")
        curve.append((float(entry[0]), float(entry[1])))
    curve.sort(key=lambda x: x[0])
    if not curve:
        curve = [(0.0, 0.0), (1.0, 1.0)]
    elif curve[0][0] > 0.0:
        curve.insert(0, (0.0, 0.0))
    if curve[-1][0] < 1.0:
        curve.append((1.0, 1.0))
    return tuple(curve)


def _interpolate(curve: Sequence[tuple[float, float]], value: float) -> float:
    magnitude = abs(value)
    sign = 1.0 if value >= 0 else -1.0

    if magnitude <= curve[0][0]:
        return sign * curve[0][1]
    for idx in range(1, len(curve)):
        x0, y0 = curve[idx - 1]
        x1, y1 = curve[idx]
        if magnitude <= x1 or idx == len(curve) - 1:
            if x1 == x0:
                return sign * y1
            position = (magnitude - x0) / (x1 - x0)
            interpolated = y0 + position * (y1 - y0)
            return sign * interpolated
    return sign * curve[-1][1]


class CamJamMotorController:
    """Differential-drive helper for the CamJam EduKit 3 drivetrain.

    Parameters
    ----------
    config:
        Parsed configuration dictionary matching the structure of
        ``config/camjam.yaml``.  When omitted the YAML file is loaded from disk.
    config_path:
        Optional override for the configuration file location.
    pigpio_module:
        Optional module object that exposes ``pi()``, ``OUTPUT`` and other
        attributes from the `pigpio <https://abyz.me.uk/rpi/pigpio/>`_ library.
        Providing it allows dependency injection during testing.
    gpio_module:
        Optional replacement for ``RPi.GPIO`` when ``pigpio`` is unavailable.

    Notes
    -----
    The controller maintains per-motor trim and speed curves which are applied
    before saturating the duty cycle.  Commands are clamped to the ``[-1, 1]``
    range to protect the L293D H-bridge.  ``emergency_stop`` immediately cuts
    power and latches the controller until :meth:`reset_estop` is called.
    """

    def __init__(
        self,
        *,
        config: Mapping[str, Any] | None = None,
        config_path: Path | str | None = None,
        pigpio_module: Any | None = None,
        gpio_module: Any | None = None,
        pigpio_host: str | None = None,
        pigpio_port: int | None = None,
    ) -> None:
        if config is None:
            path = Path(config_path) if config_path else Path("config") / "camjam.yaml"
            if not path.exists():
                raise FileNotFoundError(f"CamJam configuration not found at {path}")
            config = _load_yaml_config(path)
        self._frequency = int(config.get("pwm_frequency", 1000))
        motors = config.get("motors", {})
        if not motors:
            raise ValueError("CamJam configuration must define motors")
        self._motors: dict[str, _MotorChannel] = {}
        for name, details in motors.items():
            channel = _MotorChannel(
                name=name,
                pwm_pin=int(details["pwm_pin"]),
                forward_pin=int(details["forward_pin"]),
                reverse_pin=int(details["reverse_pin"]),
                trim=float(details.get("trim", 0.0)),
                speed_curve=_ensure_curve(details.get("speed_curve", ((0.0, 0.0), (1.0, 1.0)))),
            )
            self._motors[name] = channel

        self._backend = self._select_backend(pigpio_module, gpio_module, pigpio_host, pigpio_port)
        for motor in self._motors.values():
            self._backend.setup_motor(motor, self._frequency)
        self._estop = False

    def _select_backend(
        self,
        pigpio_module: Any | None,
        gpio_module: Any | None,
        pigpio_host: str | None,
        pigpio_port: int | None,
    ) -> _BaseBackend:
        if pigpio_module is not None:
            return _PigpioBackend(pigpio_module, host=pigpio_host, port=pigpio_port)

        try:  # pragma: no branch - we only want the first available backend
            pigpio_runtime = importlib.import_module("pigpio")
        except ImportError:
            pigpio_runtime = None
        else:
            return _PigpioBackend(pigpio_runtime, host=pigpio_host, port=pigpio_port)

        module: Any | None = gpio_module
        if module is None:
            try:
                module = importlib.import_module("RPi.GPIO")
            except ImportError as exc:  # pragma: no cover - executed only on systems without GPIO
                raise RuntimeError("Neither pigpio nor RPi.GPIO are available") from exc
        return _RPiGPIOBackend(module)

    def drive(self, left_speed: float, right_speed: float) -> None:
        """Command the left and right motors.

        Parameters
        ----------
        left_speed, right_speed:
            Values in ``[-1, 1]`` representing the requested motor speeds.  A
            positive value drives the motor forward, a negative value reverses
            it.  Commands are saturated and compensated for trim/curves.
        """

        if self._estop:
            return
        self._command_motor("left", left_speed)
        self._command_motor("right", right_speed)

    def _command_motor(self, name: str, request: float) -> None:
        motor = self._motors[name]
        compensated = self._apply_trim_and_curve(motor, request)
        self._backend.command_motor(motor, compensated)

    def _apply_trim_and_curve(self, motor: _MotorChannel, request: float) -> float:
        trimmed = max(-1.0, min(1.0, request + motor.trim))
        curved = _interpolate(motor.speed_curve, trimmed)
        return max(-1.0, min(1.0, curved))

    def brake(self) -> None:
        """Short both motors for rapid deceleration."""

        if self._estop:
            return
        for motor in self._motors.values():
            self._backend.brake_motor(motor)

    def stop(self) -> None:
        """Coast both motors by dropping PWM without tripping the E-stop."""

        if self._estop:
            return
        for motor in self._motors.values():
            self._backend.command_motor(motor, 0.0)

    def emergency_stop(self) -> None:
        """Cut all outputs and latch the controller in a safe state."""

        for motor in self._motors.values():
            self._backend.estop_motor(motor)
        self._estop = True

    def reset_estop(self) -> None:
        """Release the emergency stop latch and return to normal operation."""

        self._estop = False

    def close(self) -> None:
        """Release hardware resources."""

        self._backend.shutdown()

    def __enter__(self) -> "CamJamMotorController":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
