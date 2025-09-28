# CamJam EduKit Sensor Requirements and Integration Guide

## Overview
The CamJam EduKit robotics bundle includes an ultrasonic ranging module, line-follow reflectance sensors, and optional wheel encoders. These peripherals extend the kit’s motor controller with obstacle detection, course alignment, and odometry telemetry. The goal of this document is to capture the functional requirements, wiring references, and calibration workflows that inform both the software interfaces and hardware integration.

## Requirements Summary
| Sensor | Purpose | Operating Range | Latency Budget | Telemetry Output |
| --- | --- | --- | --- | --- |
| HC-SR04 ultrasonic ranger | Detect obstacles and estimate forward distance | 0.02–4.0 m (nominal) | < 100 ms per sample | Calibrated distance in meters with confidence | 
| QRE1113 line-follow reflectance modules (left/right) | Track surface contrast for line following | 0–100 % normalized reflectance | < 25 ms per sample | Normalized reflectance (0.0–1.0) with hysteresis flag |
| Hall-effect wheel encoders | Optional odometry for both wheels | up to 100 Hz pulse rate | < 20 ms debounce | Wheel angular velocity (rad/s) and cumulative ticks |

## Sensor-Specific Requirements

### HC-SR04 Ultrasonic Ranger
* **Trigger-to-echo timing**: Software must assert the trigger pin for 10 µs and measure echo pulse width using asynchronous capture.
* **Conversion**: Use the speed of sound (343 m/s at 20°C) to translate echo duration into meters. Provide temperature compensation hook for future refinement.
* **Noise rejection**: Apply a median filter across the last three samples and reject outliers beyond ±20 % of the rolling median.
* **Telemetry**: Expose the filtered distance (float meters) plus a boolean flag indicating whether the value is considered valid.

### Line-Follow Reflectance Modules
* **Sampling**: Poll each reflectance sensor via ADC or GPIO timing every 10–20 ms.
* **Normalization**: Convert raw readings to a normalized 0.0–1.0 reflectance value using calibration minima/maxima captured during setup.
* **Debounce/Hysteresis**: Apply a simple exponential moving average (EMA) with α = 0.5 and track transitions crossing configurable thresholds to avoid chatter.
* **Telemetry**: Provide per-sensor normalized reflectance and a combined `on_line` boolean if either sensor exceeds the active threshold.

### Hall-Effect Wheel Encoders (Optional)
* **Pulse handling**: Debounce pulses arriving up to 100 Hz using a 5 ms minimum inter-pulse interval.
* **Velocity estimation**: Calculate wheel angular velocity by differentiating tick counts over the configured sample window.
* **Calibration**: Support runtime configuration of ticks-per-revolution and wheel radius to convert ticks to linear distance.
* **Telemetry**: Report cumulative tick count, angular velocity (rad/s), and optional linear velocity (m/s).

## Wiring and Pin Mapping
| Sensor | Pi GPIO Pins | Notes |
| --- | --- | --- |
| HC-SR04 | Trigger → BCM 23, Echo → BCM 24, VCC → 5V, GND → GND | Use level shifting or voltage divider on Echo if required |
| Left Reflectance | VCC → 3.3V, GND → GND, Signal → BCM 17 | Adjust pin mapping to match controller hat |
| Right Reflectance | VCC → 3.3V, GND → GND, Signal → BCM 27 | |
| Left Encoder | VCC → 3.3V, GND → GND, Signal → BCM 5 | Optional pull-up resistor |
| Right Encoder | VCC → 3.3V, GND → GND, Signal → BCM 6 | |

> **Note**: Actual pin assignments may differ depending on the motor driver board revision. Update the table to match deployed hardware before running calibration.

## Integration Workflow
1. **Hardware Verification**: Confirm correct wiring, secure connections, and ensure sensors receive the expected supply voltage.
2. **Software Configuration**: Install required GPIO libraries (e.g., `RPi.GPIO` or `gpiozero`) and configure the application to load the CamJam sensor modules.
3. **Calibration**:
   - **Ultrasonic**: Measure known distances (0.3 m, 0.6 m, 1.0 m) and adjust offset scaling using the provided calibration hook.
   - **Reflectance**: Capture calibration minima/maxima by sweeping the robot over line and background surfaces; store values in configuration or non-volatile storage.
   - **Encoders**: Rotate wheels through one revolution to record ticks-per-revolution and verify consistent direction readings.
4. **Validation**: Run the automated test suite to confirm data normalization, debouncing, and telemetry outputs meet the specified thresholds.
5. **Deployment**: Integrate the asynchronous sensor API into the motion controller to feed navigation and safety routines.

## Maintenance Considerations
* Periodically clean the reflectance sensors to prevent dust build-up altering calibration.
* Re-run ultrasonic calibration when ambient temperature changes significantly.
* Check encoder magnets and mounting hardware for slippage that could impact tick counts.

