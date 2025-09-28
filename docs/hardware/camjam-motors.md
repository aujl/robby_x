# CamJam EduKit 3 Drivetrain Integration

The CamJam EduKit 3 robotics kit ships with a small L293D H-bridge board that
accepts 5 V logic-level control signals from the Raspberry Pi while driving the
12 V-tolerant dual motors from a separate two-AA battery pack. The stock wiring
exposes three control pins per motor channel on the Pi header:

| Signal | L293D pin | Purpose |
| ------ | --------- | ------- |
| ``PWM`` | ``EN1``/``EN2`` | Pulse-width modulation input that gates motor power. |
| ``FORWARD`` | ``1A``/``3A`` | Logic high drives the motor forward when ``PWM`` is active. |
| ``REVERSE`` | ``2A``/``4A`` | Logic high drives the motor in reverse when ``PWM`` is active. |

The CamJam board is happiest when the Pi provides a clean 5 V logic supply and
an isolated battery pack powers the motors. Brown-outs on the logic rail can
reset the Pi, so always keep the dual AA pack fresh and route ground returns
carefully.

## Motor controller module

``src/hardware/camjam/motor_controller.py`` exposes the
[`CamJamMotorController`](../../src/hardware/camjam/motor_controller.py) class
for differential-drive robots. The controller automatically loads
configuration from [`config/camjam.yaml`](../../config/camjam.yaml) and offers a
single ``drive(left, right)`` entry point alongside helpers for braking and
emergency stopping. Typical usage:

```python
from src.hardware.camjam.motor_controller import CamJamMotorController

with CamJamMotorController() as drive:
    drive.drive(0.35, 0.35)  # gentle forward motion
    drive.drive(0.2, -0.2)   # pivot in place
    drive.brake()            # short both motors
    drive.emergency_stop()   # cut power and latch the e-stop
```

### Emergency-stop expectations

``emergency_stop()`` immediately drops all PWM duty cycles to ``0`` and pulls
both direction pins low for every channel. The controller latches in the E-stop
state until ``reset_estop()`` is called—subsequent ``drive``/``brake`` commands
are ignored while latched to guarantee the motors remain de-energised. This
mirrors CamJam classroom safety guidance where an audible fault or stalled
robot must be recoverable by software alone.

### Short braking

Calling ``brake()`` raises both the forward and reverse pins while applying full
PWM duty. On the L293D this shorts the motor leads and produces a rapid stop.
Use ``stop()`` instead when coasting to a halt is desirable.

## Configuration template

```yaml
# config/camjam.yaml — template values shown below
pwm_frequency: 1000  # Hz, suitable for pigpio hardware PWM on pins 18/19

motors:
  left:
    pwm_pin: 18       # BCM pin used for EN1
    forward_pin: 4    # BCM pin used for 1A
    reverse_pin: 17   # BCM pin used for 2A
    trim: 0.0         # additive correction applied before the curve
    speed_curve:
      - [0.0, 0.0]
      - [1.0, 1.0]

  right:
    pwm_pin: 19       # BCM pin used for EN2
    forward_pin: 27   # BCM pin used for 3A
    reverse_pin: 22   # BCM pin used for 4A
    trim: 0.0
    speed_curve:
      - [0.0, 0.0]
      - [1.0, 1.0]
```

Populate the template with the actual wiring you adopted. The controller accepts
any monotonic ``speed_curve`` consisting of ``[input, output]`` pairs (with
``input`` in the ``0..1`` range) and linearly interpolates between them.

## Trim and speed-curve calibration

1. **Baseline trim:** Elevate the chassis, command ``drive(0.4, 0.4)`` and note
   which wheel spins faster. Adjust the ``trim`` value for the faster side by
   ``-0.05`` increments until both wheels spin at the same apparent rate. The
   trim offset is applied before the speed curve and is clamped to ``[-1, 1]``.
2. **Record response data:** Place the robot on blocks, sweep each motor from
   ``0.1`` to ``1.0`` in ``0.1`` increments and measure the free-running RPM.
   Normalise the RPM readings into the ``0..1`` range and log them alongside the
   command value.
3. **Fit the curve:** Add the samples as ``[command, observed]`` pairs in the
   ``speed_curve`` list (ensuring ``[0.0, 0.0]`` and ``[1.0, 1.0]`` brackets are
   present). The controller interpolates between points so only add breakpoints
   where the gearbox deviates appreciably.
4. **Validate on the floor:** With trims and curves in place, run slow forward
   and pivot manoeuvres on a smooth surface. Revisit the calibration if the
   robot still veers.

Developer note: keep the curve sparse—two or three interior points are usually
sufficient to linearise the CamJam motors. Excessively jagged curves can make
closed-loop controllers unstable.
