# CamJam Diagnostics Logging

This document captures the structured logging requirements for the CamJam rover hardware and the PanTilt camera subsystem.

## Events to Capture

All diagnostics events MUST be logged with structured key/value payloads using `structlog` when available. When the runtime lacks `structlog`, the fallback logger defined in `src/services/diagnostics/camjam.py` SHALL be used so that log calls remain side-effect free. Each event MUST include an ISO-8601 timestamp, the emitting component, an event name, and a payload with the fields below.

| Component      | Event                            | Required fields                                                                                                 |
| -------------- | -------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `motors`       | `drive_command`                  | `left_speed`, `right_speed`, optional `duration_s`, optional `queue_depth`, `source`                             |
| `ultrasonic`   | `range_measurement`              | `sensor` identifier, `distance_cm`, `valid` flag, and any filtering metadata                                     |
| `line`         | `sensor_state`                   | `sensor` identifier and boolean `active` status                                                                  |
| `pan_tilt`     | `position_update`                | `pan_deg`, `tilt_deg`, optional `preset` label                                                                   |
| `video_stream` | `status`                         | `status` (`idle`, `starting`, `live`, `fallback`, `error`), optional `detail`, optional `src` URI                |

Every event SHOULD be appended to the diagnostics history queue maintained by `CamJamDiagnostics`. Downstream analytics can subscribe to this feed to compute trends and trigger alerts.

## Retention and Rotation

* **In-memory history** – the diagnostics service SHALL retain the most recent 200 events in memory by default. The ring buffer length is configurable per deployment via the `history_size` constructor argument.
* **UI payload** – when building UI telemetry, only the latest 10 samples per sensor are returned unless a different limit is explicitly requested.
* **Disk persistence** – operators MAY configure `structlog` to emit JSON lines to disk or a remote collector. When persisted, apply a 7-day retention policy for raw event files and a 30-day retention policy for aggregated metrics.
* **Privacy** – payloads MUST avoid user identifiers; only mechanical state and anonymous source labels (e.g., `operator`, `autonomy`, `test-suite`) are permitted.

## Alerting Thresholds

A component is considered **stale** when no event is recorded for more than `stale_after_s` (default 5 seconds). Stale status MUST be surfaced in the health report and UI diagnostics payload so operators can react promptly.

## Example

```json
{
  "timestamp": "2024-07-01T12:34:56.789Z",
  "component": "motors",
  "event": "drive_command",
  "data": {
    "left_speed": 0.42,
    "right_speed": 0.40,
    "duration_s": 1.5,
    "queue_depth": 2,
    "source": "operator"
  }
}
```

Refer to [`src/services/diagnostics/camjam.py`](../../src/services/diagnostics/camjam.py) for the reference implementation that enforces these policies.
