"""Common helpers for CamJam HIL scripts.

Each nightly hardware-in-the-loop (HIL) script writes telemetry bundles under the
configured output directory.  When ``CAMJAM_HIL_ENABLED`` is not set the scripts
run in "dry-run" mode so CI jobs on vanilla runners succeed while still
producing placeholder artefacts.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class HilRunContext:
    name: str
    output_dir: Path
    dry_run: bool
    timestamp: float

    @property
    def output_path(self) -> Path:
        return self.output_dir / f"{self.name}.json"


def build_context(name: str, output: str) -> HilRunContext:
    output_dir = Path(output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dry_run = os.environ.get("CAMJAM_HIL_ENABLED", "0") not in {"1", "true", "TRUE"}
    return HilRunContext(name=name, output_dir=output_dir, dry_run=dry_run, timestamp=time.time())


def write_payload(context: HilRunContext, payload: dict[str, Any]) -> None:
    metadata = {
        "metadata": {
            "dry_run": context.dry_run,
            "generated_at": context.timestamp,
            "script": context.name,
        }
    }
    output = {**metadata, **payload}
    context.output_path.write_text(json.dumps(output, indent=2))


def base_payload(context: HilRunContext) -> dict[str, Any]:
    return {
        "summary": {
            "status": "skipped" if context.dry_run else "pending",
            "notes": [],
        }
    }
