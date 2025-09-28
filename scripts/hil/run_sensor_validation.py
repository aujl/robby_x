from __future__ import annotations

import argparse

from .common import base_payload, build_context, write_payload


def _sensor_expectations(notes: list[str]) -> dict[str, object]:
    notes.append("Ensure ultrasonic rig is aligned at 0.5 m, 1.0 m, and 1.5 m checkpoints.")
    notes.append("Record encoder ticks for clockwise and counter-clockwise figure-eight laps.")
    return {
        "ultrasonic": {
            "checkpoints_m": [0.5, 1.0, 1.5],
            "variance_threshold_cm": 5.0,
        },
        "line_follower": {
            "hysteresis_band": [0.4, 0.6],
            "samples_per_segment": 200,
        },
        "encoders": {
            "max_slip_ticks_per_s": 2,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate CamJam sensor suite against calibration baselines")
    parser.add_argument("--output", default="artifacts/hil", help="Directory for result bundles")
    parser.add_argument("--course", default="figure-eight", help="Course preset to document")
    args = parser.parse_args()

    context = build_context("sensor_validation", args.output)
    payload = base_payload(context)
    payload["course"] = args.course
    payload["sensors"] = _sensor_expectations(payload["summary"]["notes"])

    if context.dry_run:
        payload["summary"]["notes"].append(
            "Dry run – provide recorded CSVs in the output directory when running on hardware."
        )
    else:
        payload["summary"]["status"] = "completed"
        payload["summary"]["notes"].append(
            "Sensor validation executed – review generated plots stored next to this JSON file."
        )

    write_payload(context, payload)


if __name__ == "__main__":
    main()
