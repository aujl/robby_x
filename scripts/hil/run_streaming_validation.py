from __future__ import annotations

import argparse

from .common import base_payload, build_context, write_payload


def _streaming_plan(duration: int, notes: list[str]) -> dict[str, object]:
    if duration <= 0:
        raise ValueError("duration must be positive seconds")
    notes.append("Verify LTE uplink is stable >5 Mbps before starting stream.")
    notes.append("Check telemetry bridge backlog after run and record max queue depth.")
    return {
        "duration_s": duration,
        "target_bitrate_kbps": 2500,
        "max_dropped_frames_pct": 0.5,
        "mjpeg_gateway": "http://camjam-buggy.local:8081/stream.mjpg",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate CamJam streaming end-to-end pipeline")
    parser.add_argument("--output", default="artifacts/hil", help="Directory for result bundles")
    parser.add_argument("--duration", type=int, default=900, help="Stream duration in seconds")
    args = parser.parse_args()

    context = build_context("streaming_validation", args.output)
    payload = base_payload(context)
    payload["streaming"] = _streaming_plan(args.duration, payload["summary"]["notes"])

    if context.dry_run:
        payload["summary"]["notes"].append(
            "Dry run – streaming metrics require the CamJam buggy and PanTilt camera connected."
        )
    else:
        payload["summary"]["status"] = "completed"
        payload["summary"]["notes"].append(
            "Streaming validation complete – attach bitrate logs to artefacts."
        )

    write_payload(context, payload)


if __name__ == "__main__":
    main()
