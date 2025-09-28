# CamJam Simulation Scenarios

The CamJam simulation harness provides deterministic scripts that mirror common
robot behaviours. Each scenario drives the simulated wheel encoders, HC-SR04
ultrasonic ranger, and pan/tilt servos with pre-baked telemetry so that the rest
of the software stack can be validated without physical hardware.

All timelines use timestamps measured in seconds, cumulative encoder ticks, and
servo angles in degrees. Ultrasonic distances are expressed in metres.

## Idle

Represents a powered but stationary robot. Encoders remain flat, the ranger
reports a constant distance, and the mast holds a neutral pose.

| Timestamp | Left ticks | Right ticks | Range (m) | Pan (°) | Tilt (°) | Motor command |
|-----------|------------|-------------|-----------|---------|----------|----------------|
| 0.0       | 0          | 0           | 2.5       | 0.0     | 0.0      | (0.0, 0.0)     |
| 0.1       | 0          | 0           | 2.5       | 0.0     | 0.0      | (0.0, 0.0)     |
| 0.2       | 0          | 0           | 2.5       | 0.0     | 0.0      | (0.0, 0.0)     |
| 0.3       | 0          | 0           | 2.5       | 0.0     | 0.0      | (0.0, 0.0)     |

## Straight line

Constant forward motion with balanced wheel speeds and a slightly downward
tilt to the mast for floor scanning.

| Timestamp | Left ticks | Right ticks | Range (m) | Pan (°) | Tilt (°) | Motor command |
|-----------|------------|-------------|-----------|---------|----------|----------------|
| 0.0       | 0          | 0           | 1.0       | 0.0     | -5.0     | (0.45, 0.45)  |
| 0.1       | 8          | 8           | 1.0       | 0.0     | -5.0     | (0.45, 0.45)  |
| 0.2       | 16         | 16          | 1.0       | 0.0     | -5.0     | (0.45, 0.45)  |
| 0.3       | 24         | 24          | 1.0       | 0.0     | -5.0     | (0.45, 0.45)  |

## Skid turns

The chassis pivots in place: the left wheel marches forward while the right
wheel reverses, producing mirrored encoder deltas.

| Timestamp | Left ticks | Right ticks | Range (m) | Pan (°) | Tilt (°) | Motor command |
|-----------|------------|-------------|-----------|---------|----------|----------------|
| 0.0       | 0          | 0           | 1.8       | -15.0   | -5.0     | (0.35, -0.35) |
| 0.1       | 5          | -5          | 1.8       | -5.0    | -5.0     | (0.35, -0.35) |
| 0.2       | 10         | -10         | 1.6       | 5.0     | -5.0     | (0.35, -0.35) |
| 0.3       | 15         | -15         | 1.6       | 15.0    | -5.0     | (0.35, -0.35) |

## Ultrasonic obstacle

A gradual deceleration as the robot approaches an obstacle. Distances contract
smoothly so the ranger's deviation filter keeps every sample valid.

| Timestamp | Left ticks | Right ticks | Range (m) | Pan (°) | Tilt (°) | Motor command |
|-----------|------------|-------------|-----------|---------|----------|----------------|
| 0.0       | 0          | 0           | 1.50      | 0.0     | -2.0     | (0.40, 0.40)  |
| 0.1       | 6          | 6           | 1.35      | 0.0     | -2.0     | (0.40, 0.40)  |
| 0.2       | 12         | 12          | 1.15      | 0.0     | -2.0     | (0.35, 0.35)  |
| 0.3       | 18         | 18          | 0.95      | 0.0     | -2.0     | (0.20, 0.20)  |
| 0.4       | 24         | 24          | 0.80      | 0.0     | -2.0     | (0.00, 0.00)  |

## Line-follow transitions

Mimics the bias corrections that occur when the robot oscillates across a line.
The left encoder advances slightly quicker than the right during corrective
pulses before returning to symmetry.

| Timestamp | Left ticks | Right ticks | Range (m) | Pan (°) | Tilt (°) | Motor command |
|-----------|------------|-------------|-----------|---------|----------|----------------|
| 0.0       | 0          | 0           | 1.00      | -10.0   | -5.0     | (0.30, 0.25)  |
| 0.1       | 5          | 4           | 0.95      | -5.0    | -5.0     | (0.35, 0.25)  |
| 0.2       | 12         | 10          | 0.90      | 0.0     | -5.0     | (0.25, 0.35)  |
| 0.3       | 20         | 19          | 0.95      | 5.0     | -5.0     | (0.30, 0.28)  |
| 0.4       | 30         | 30          | 1.00      | 10.0    | -5.0     | (0.32, 0.32)  |

## Pan/tilt sweeps

The drivetrain remains stationary while the sensor mast scans from port to
starboard and back, sampling different ranges at each pose.

| Timestamp | Left ticks | Right ticks | Range (m) | Pan (°) | Tilt (°) | Motor command |
|-----------|------------|-------------|-----------|---------|----------|----------------|
| 0.0       | 0          | 0           | 2.0       | -45.0   | -10.0    | (0.0, 0.0)    |
| 0.1       | 0          | 0           | 2.2       | -22.5   | -5.0     | (0.0, 0.0)    |
| 0.2       | 0          | 0           | 2.4       | 0.0     | 0.0      | (0.0, 0.0)    |
| 0.3       | 0          | 0           | 2.1       | 22.5    | 5.0      | (0.0, 0.0)    |
| 0.4       | 0          | 0           | 2.0       | 45.0    | 10.0     | (0.0, 0.0)    |

