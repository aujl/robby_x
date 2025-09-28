# CamJam Test Strategy

This document summarises the multi-layered validation strategy for the CamJam buggy platform, covering motors, sensors, PanTilt servos, and the telemetry/video streaming stack.  It differentiates between unit, integration, and hardware-in-the-loop (HIL) coverage so that contributors can plan regressions confidently.

## Guiding principles

* **Simulation first** – deterministic simulators back every unit test to keep feedback loops fast.
* **Mocked hardware parity** – unit and integration tests exercise pigpio- and I2C-facing code paths against strict mocks that emulate the CamJam wiring definitions in `config/camjam.yaml`.
* **HIL as nightly gate** – full-stack verification of the assembled buggy runs nightly (or before releases) to capture drift in physical components, calibration, or firmware updates.
* **Structured telemetry** – every layer emits structured diagnostics aligned with [`docs/diagnostics/camjam-logging.md`](../diagnostics/camjam-logging.md) so failures remain actionable.

## Motors

| Test class | Scope | Tooling | Frequency | Acceptance criteria |
|------------|-------|---------|-----------|---------------------|
| Unit | `CamJamMotorController` PWM generation, trim handling, emergency stop behaviour using pigpio mocks. | `pytest -m camjam_mocked_hw tests/hardware/motors` | On every push / PR. | PWM duty cycle and GPIO direction match lookup tables; E-stop prevents subsequent commands until reset. |
| Integration | Drive profile regression across simulator traces; compare duty cycle envelopes against simulator-provided duty map. | `pytest -m camjam_simulation tests/simulation/test_camjam_sim.py::test_straight_line_scenario_encoder_progression` | On every push / PR. | Encoder deltas remain within ±2 ticks of scripted scenario; simulated command log reproduces reference profile. |
| HIL | Physical buggy run on 2×5 m track with speed/trim sweeps. Data captured via telemetry bridge and analysed for drift. | `scripts/hil/run_motor_characterisation.py` (triggered nightly) | Nightly / before releases. | Velocity error < 5 %, deviation between commanded and measured PWM < 3 % after calibration. |

## Sensors

| Test class | Scope | Tooling | Frequency | Acceptance criteria |
|------------|-------|---------|-----------|---------------------|
| Unit | Ultrasonic, line follow, and wheel encoder filtering and normalisation. | `pytest -m camjam_unit tests/hardware/sensors` | On every push / PR. | Filtering removes outliers; hysteresis works in both directions; encoder debouncing rejects sub-5 ms pulses. |
| Integration | Sensor fusion against simulator-provided scripted tracks (line transitions, obstacle approach). | `pytest -m camjam_simulation tests/simulation/test_camjam_sim.py::test_ultrasonic_obstacle_distance_script` | On every push / PR. | Simulated readings track golden dataset within tolerance; state machines publish structured telemetry events. |
| HIL | Live data logging while driving figure-eight course; cross-check with simulator baselines. | `scripts/hil/run_sensor_validation.py` | Nightly / before releases. | Ultrasonic variance < 10 %, line follower hysteresis gap maintained, encoder slip < 2 ticks per second drift. |

## PanTilt servos

| Test class | Scope | Tooling | Frequency | Acceptance criteria |
|------------|-------|---------|-----------|---------------------|
| Unit | Servo command generation, safety angle limits, and scripted sweep iterator. | `pytest -m camjam_unit tests/hardware/pantilt` (future expansion) | On every push / PR. | Commands respect min/max angles; fails safe on invalid inputs; sweeps generate deterministic sequences. |
| Integration | Servo sweep playback in simulator and synchronisation with video overlay cues. | `pytest -m camjam_simulation tests/simulation/test_camjam_sim.py::test_pan_tilt_sweep_angles_match_scenario` | On every push / PR. | Scripted positions cover configured waypoints; overlay timestamps align within ±50 ms. |
| HIL | Physical sweep captured by CSI camera; overlay tool verifies coverage and jitter. | `scripts/hil/run_pantilt_alignment.py` | Nightly / before releases. | Reported angles within ±2° of target; jitter < 40 ms at 50 % duty. |

## Streaming and telemetry

| Test class | Scope | Tooling | Frequency | Acceptance criteria |
|------------|-------|---------|-----------|---------------------|
| Unit | WebSocket publishers, telemetry serializers, and UI-level React hooks. | `npm run test` (Vitest) and `pytest -m camjam_unit tests/services` | On every push / PR. | Serialisers reject malformed payloads; hooks render default state and update on mock frames. |
| Integration | End-to-end stream loop using simulator frames and mocked MJPEG gateway. | `pytest -m camjam_mocked_hw tests/services/test_camjam_diagnostics.py` and `npm run test -- tests/telemetry.test.tsx` | On every push / PR. | Latency budget < 100 ms per cycle in simulator; diagnostics emitted for each dropped frame. |
| HIL | Full stack streaming with LTE link; store-and-forward pipeline generates nightly bundle. | `scripts/hil/run_streaming_validation.py` | Nightly / before releases. | 15 minute run with < 0.5 % dropped frames; telemetry backlog drained within 5 seconds. |

## Execution matrix

The CI pipeline ties the above layers together:

* **`ci.yml`** executes unit and integration suites on every push/PR, partitioned into backend, simulator, mocked hardware, and frontend jobs. Coverage is aggregated and uploaded as an artifact plus rendered as a badge.
* **`hil-nightly.yml`** runs nightly on `main` (and manually on demand). It flashes the latest build to the CamJam buggy, executes the HIL scripts, and uploads telemetry bundles for manual review.

See [README badges](../../README.md) for live status indicators. Contributors **must** keep simulator fixtures up to date with any new hardware calibrations so that regression thresholds remain representative.
