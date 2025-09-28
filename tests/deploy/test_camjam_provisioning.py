from __future__ import annotations

import configparser
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_DIR = REPO_ROOT / "deploy" / "camjam"
SYSTEMD_DIR = DEPLOY_DIR / "systemd"
SCRIPTS_DIR = DEPLOY_DIR / "scripts"


@pytest.fixture(scope="module")
def pin_mapping() -> dict[str, dict[str, int]]:
    path = DEPLOY_DIR / "config" / "pins.yaml"
    sections: dict[str, dict[str, int]] = {}
    current_section: dict[str, int] | None = None
    with path.open() as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if not raw_line.startswith(" "):
                section_name = line.rstrip(":")
                current_section = {}
                sections[section_name] = current_section
            else:
                if current_section is None:
                    raise ValueError("Key/value encountered before section header")
                key, value = line.split(":", maxsplit=1)
                current_section[key.strip()] = int(value.strip())
    return sections


def test_pin_mapping_sections_present(pin_mapping: dict[str, dict[str, int]]) -> None:
    expected_sections = {"motors", "servos", "sensors", "leds", "power"}
    assert expected_sections.issubset(pin_mapping.keys())


@pytest.mark.parametrize(
    "unit_file, required_options",
    [
        (
            SYSTEMD_DIR / "camjam-control.service",
            {
                ("Service", "ExecStart"): "--config /etc/camjam/pins.yaml",
                ("Service", "Restart"): "on-failure",
            },
        ),
        (
            SYSTEMD_DIR / "camjam-camera.service",
            {
                ("Service", "ExecStart"): "/usr/bin/libcamera-vid",
                ("Unit", "Requires"): "camjam-control.service",
            },
        ),
        (
            SYSTEMD_DIR / "camjam-diagnostics.service",
            {
                ("Service", "ExecStart"): "/opt/camjam/bin/diagnostics.sh",
                ("Service", "Type"): "oneshot",
            },
        ),
    ],
)
def test_systemd_units_have_expected_configuration(
    unit_file: Path, required_options: dict[tuple[str, str], str]
) -> None:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.read(unit_file)
    for (section, option), expected_substring in required_options.items():
        assert parser.has_option(section, option)
        assert expected_substring in parser.get(section, option)


def _write_fake_systemctl(tmp_path: Path, inactive_service: str | None) -> Path:
    script_path = tmp_path / "systemctl"
    script_contents = """#!/usr/bin/env bash
set -euo pipefail

if [[ "$1" == "is-active" ]]; then
  shift
  if [[ "$1" == "--quiet" ]]; then
    shift
  fi
  svc="$1"
  if [[ "${svc}" == "{inactive_service}" ]]; then
    exit 3
  fi
  exit 0
fi

if [[ "$1" == "list-unit-files" ]]; then
  echo "camjam-tls-renew.timer enabled"
  exit 0
fi

if [[ "$1" == "daemon-reload" ]]; then
  exit 0
fi

if [[ "$1" == "enable" ]]; then
  exit 0
fi

if [[ "$1" == "start" ]]; then
  exit 0
fi

exit 0
"""
    script_path.write_text(
        script_contents.replace("{inactive_service}", inactive_service or ""),
        encoding="utf-8",
    )
    script_path.chmod(stat.S_IRWXU)
    return script_path


def _run_check_services(
    tmp_path: Path, inactive_service: str | None
) -> subprocess.CompletedProcess[str]:
    _write_fake_systemctl(tmp_path, inactive_service)
    env = {"PATH": f"{tmp_path}:{os.environ.get('PATH', '')}"}
    script = SCRIPTS_DIR / "check_services.sh"
    return subprocess.run(
        ["bash", str(script)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_check_services_script_reports_healthy(tmp_path: Path) -> None:
    result = _run_check_services(tmp_path, inactive_service=None)
    assert result.returncode == 0, result.stderr
    for service in (
        "camjam-control.service",
        "camjam-camera.service",
        "camjam-diagnostics.service",
        "pigpiod.service",
    ):
        assert service in result.stdout


def test_check_services_script_detects_failure(tmp_path: Path) -> None:
    result = _run_check_services(tmp_path, inactive_service="camjam-camera.service")
    assert result.returncode != 0
    assert "inactive" in result.stderr


def test_tls_timer_templates_exist() -> None:
    service = SYSTEMD_DIR / "camjam-tls-renew.service"
    timer = SYSTEMD_DIR / "camjam-tls-renew.timer"
    assert service.exists()
    assert timer.exists()


@pytest.mark.parametrize(
    "script_name",
    ["check_services.sh", "diagnostics.sh", "tls_renew.sh"],
)
def test_provisioning_scripts_are_executable(script_name: str) -> None:
    script = SCRIPTS_DIR / script_name
    assert script.exists()
    mode = script.stat().st_mode
    assert mode & stat.S_IXUSR


def test_provisioning_script_references_all_units() -> None:
    provision = (DEPLOY_DIR / "provision_camjam.sh").read_text()
    for unit in (
        "camjam-control.service",
        "camjam-camera.service",
        "camjam-diagnostics.service",
    ):
        assert unit in provision
    assert "pins.yaml" in provision


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Systemd scripts are Linux-specific")
def test_systemd_units_loadable() -> None:
    """Ensure the systemd unit files can be parsed by ConfigParser without errors."""
    for unit_file in SYSTEMD_DIR.glob("*.service"):
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.read(unit_file)
        assert parser.sections(), f"{unit_file.name} did not parse correctly"
