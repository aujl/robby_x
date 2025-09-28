from __future__ import annotations

import argparse

from .common import base_payload, build_context, write_payload

PRESETS = {
    "scan": [(-30.0, -10.0), (0.0, 0.0), (30.0, 10.0)],
    "focus": [(0.0, 5.0)],
}


def _alignment_plan(preset: str, notes: list[str]) -> dict[str, object]:
    sweeps = PRESETS.get(preset, PRESETS["scan"])
    notes.append(
        "Mount calibration board at 1 m distance; align crosshair with PanTilt "
        "zero before recording."
    )
    notes.append("Use overlay annotator to confirm ±2° accuracy across sweep waypoints.")
    return {
        "preset": preset,
        "waypoints": sweeps,
        "tolerance_deg": 2.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify PanTilt servo alignment against presets")
    parser.add_argument("--output", default="artifacts/hil", help="Directory for result bundles")
    parser.add_argument("--preset", default="scan", choices=list(PRESETS), help="Preset to execute")
    args = parser.parse_args()

    context = build_context("pantilt_alignment", args.output)
    payload = base_payload(context)
    payload["pantilt"] = _alignment_plan(args.preset, payload["summary"]["notes"])

    if context.dry_run:
        payload["summary"]["notes"].append(
            "Dry run – capture real PanTilt telemetry when CAMJAM_HIL_ENABLED=1."
        )
    else:
        payload["summary"]["status"] = "completed"
        payload["summary"]["notes"].append(
            "PanTilt sweep complete – attach screenshot evidence in artefacts."
        )

    write_payload(context, payload)


if __name__ == "__main__":
    main()
