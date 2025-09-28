# CamJam UI Requirements

## Overview
The CamJam rover frontend must provide responsive, accessible controls and telemetry views that allow operators to safely drive the robot, manipulate its PanTilt servos, and monitor onboard sensors across desktop, tablet, and phone devices.

## Drive Controls
- Provide joystick, keyboard, and touch input methods for drive commands.
- Joystick control must support proportional forward/reverse throttle and left/right steering with visual feedback of the current vector.
- Keyboard controls shall accept WASD and arrow keys, with configurable repeat rate and focus trapping to prevent accidental inputs.
- Touch controls shall expose virtual drive pads with haptic feedback hooks and multi-touch support for throttle and steering.
- All drive interactions must emit `drive/setpoint` messages to the control service via WebSocket using a normalized `{vx, vy, omega}` payload.
- Display connection status and last command timestamp near the drive controls.

## PanTilt Servo Controls
- Provide independent sliders for pan and tilt angles with clear labels and degree readouts.
- Sliders must support keyboard and pointer manipulation with ARIA metadata for screen readers.
- Slider value changes shall debounce into `pantilt/command` messages over WebSocket with payload `{panDeg, tiltDeg}`.
- Include preset buttons for center, sweep, and downward inspection positions.

## Telemetry Widgets
- Show ultrasonic distance readings for front, rear, and side sensors with color-coded proximity thresholds (green > 40cm, amber 20-40cm, red < 20cm).
- Provide line-follow sensor indicators for left, center, and right detectors showing live state (on/off) plus a trend sparkline for the last 10 samples.
- Telemetry updates arrive via WebSocket `telemetry/state` events; the UI must reflect stale data if no update arrives within 2 seconds.
- Present network latency and heartbeat indicators sourced from the control service.

## Responsiveness and Layout
- Layout must adapt between desktop (three-column), tablet (two-column), and phone (single-column stacked) breakpoints.
- Ensure all controls remain reachable within 44px touch targets on mobile.
- Provide dark and light themes toggleable by the operator.

## Accessibility & Internationalization
- All interactive controls require accessible names, roles, and states following WCAG 2.2 AA.
- Provide caption support for telemetry widgets and ensure focus order follows logical control flow.
- Enable internationalization by sourcing copy from a locale file and supporting right-to-left layouts.

## Performance & Reliability
- WebSocket connections must automatically reconnect with exponential backoff and surface retry status to the user.
- Command issuance must queue while disconnected and flush upon reconnection, providing user feedback on queued commands.
- Ensure low-latency rendering (<16ms frame budget) through memoized updates and virtualization where feasible.

## Instrumentation
- Emit analytics events for command interactions, telemetry anomalies, and layout breakpoint changes to support quantitative monitoring.

