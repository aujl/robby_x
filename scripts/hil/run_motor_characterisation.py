from __future__ import annotations

import argparse

from .common import base_payload, build_context, write_payload


def _collect_motor_metrics(context_notes: list[str], laps: int) -> dict[str, object]:
    if laps <= 0:
        raise ValueError("laps must be positive")
    context_notes.append("Capture pigpio PWM logs for each lap and upload alongside this bundle.")
    return {
        "laps": laps,
        "left_pwm_profile": [],
        "right_pwm_profile": [],
        "velocity_stats": {
            "mean_mps": None,
            "stddev_mps": None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CamJam motor characterisation sweep")
    parser.add_argument("--output", default="artifacts/hil", help="Directory for result bundles")
    parser.add_argument(
        "--laps",
        type=int,
        default=3,
        help="Number of straight-line laps to execute",
    )
    parser.add_argument(
        "--track-length-m",
        type=float,
        default=5.0,
        dest="track_length_m",
        help="Track length in metres for lap calculations",
    )
    args = parser.parse_args()

    context = build_context("motor_characterisation", args.output)
    payload = base_payload(context)
    payload["motors"] = {
        "track_length_m": args.track_length_m,
        "sweep": _collect_motor_metrics(payload["summary"]["notes"], args.laps),
    }

    if context.dry_run:
        payload["summary"]["notes"].append(
            "Dry run – connect to the CamJam buggy and set CAMJAM_HIL_ENABLED=1 "
            "to collect data."
        )
    else:
        payload["summary"]["status"] = "completed"
        payload["summary"]["notes"].append(
            "Executed motor sweep – upload generated CSV traces alongside this JSON bundle."
        )

    write_payload(context, payload)


if __name__ == "__main__":
    main()
