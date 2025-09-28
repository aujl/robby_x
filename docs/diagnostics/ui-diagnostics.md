# CamJam Diagnostics Panel

The diagnostics panel in the web console provides an operator-focused summary of hardware telemetry, event history, and camera health. It consumes the payload produced by `CamJamDiagnostics.ui_payload()` and renders it alongside live telemetry updates.

## Layout Overview

1. **Ultrasonic Awareness** – highlights the most recent distance measurements for each HC-SR04 sensor with contextual danger/caution styling.
2. **Line Sensor Activity** – shows real-time states and a rolling sparkline history for the left, centre, and right sensors.
3. **CamJam Timeline** – lists the six most recent diagnostics events (motor commands, sensor updates, servo movements, and stream changes). Each entry displays the emitting component, event name, and a formatted payload summary.
4. **Camera Status** – visualises the current video stream state, the latest Pan/Tilt angles (including preset if active), and whether updates are stale.

## Integrating Diagnostics Data

* The `ControlContext` now exposes a `diagnostics` object with health summaries, per-component histories, and the event timeline.
* Front-end modules can request the latest payload from `/services/diagnostics` (to be provided by the API gateway) or hydrate it from WebSocket broadcasts. Until the backend wiring is complete, the UI falls back to empty defaults.
* `DiagnosticsState.events` SHOULD be an array of `DiagnosticsEvent` objects with `Date` timestamps for ease of rendering in the timeline.

## Usage Tips

* Highlight unusual readings by injecting custom `detail` strings into the `video_stream` log entries (e.g., "Bitrate degraded"), which surface automatically in the panel.
* Provide meaningful `source` labels for motor commands and servo presets so operators can differentiate autonomous manoeuvres from manual overrides.
* When extending the panel, prefer appending new cards to the second grid row to maintain visual balance with the CamJam Timeline and Camera Status blocks.

Refer to [`frontend/src/components/TelemetryPanel.tsx`](../../frontend/src/components/TelemetryPanel.tsx) for the React implementation and [`frontend/tests/telemetry.test.tsx`](../../frontend/tests/telemetry.test.tsx) for usage examples.
