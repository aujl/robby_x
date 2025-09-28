# CamJam simulation harness

The CamJam EduKit hardware can be swapped for a deterministic software
simulation by exporting two environment variables before running any code that
instantiates the hardware factories in `src.hardware.camjam`:

```bash
export CAMJAM_SIMULATION=1           # enable the simulation back-end
export CAMJAM_SIM_SCENARIO=idle      # pick a scripted scenario
```

`CAMJAM_SIMULATION` accepts `1`, `true`, `yes`, or `on` (case insensitive). When
unset, the factories fall back to real hardware classes and require concrete
GPIO/ADC readers. `CAMJAM_SIM_SCENARIO` defaults to `idle` and can be set to any
slug listed in [`camjam-scenarios.md`](camjam-scenarios.md).

Once enabled, the helper functions
`get_motor_controller()`, `get_wheel_encoders()`, `get_ultrasonic_ranger()` and
`get_pan_tilt_servos()` will return simulation stand-ins that replay the chosen
script. The encoders and ultrasonic ranger still funnel through the production
signal-processing code so velocity filtering and outlier rejection behave
exactly as they do against the real sensors.

## Limitations

* The servo simulation exposes pre-scripted positions for regression testing,
  whereas the physical servos simply honour commanded positions.
* Only the wheel encoders, HC-SR04 ranger, and pan/tilt servos are modelled.
  Line-follow sensors and other optional peripherals still require test stubs or
  hardware-in-the-loop.
* Motor commands issued during simulation are logged but do not influence the
  scripted telemetry; the playback remains deterministic regardless of control
  feedback.

Use the simulation for repeatable unit tests and integration dry-runs. Switch
`CAMJAM_SIMULATION` off when deploying to the real robot so that factory calls
instantiate GPIO-backed classes and expect live sensor feeds.
