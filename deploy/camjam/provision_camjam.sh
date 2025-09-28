#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="${SCRIPT_DIR}/systemd"
CONFIG_DIR="${SCRIPT_DIR}/config"
SCRIPTS_DIR="${SCRIPT_DIR}/scripts"
PIN_CONFIG="${CONFIG_DIR}/pins.yaml"

CALIBRATE=0

usage() {
  cat <<USAGE
Usage: $0 [--calibrate]

Installs CamJam runtime dependencies, deploys configuration files, and enables
systemd services for control, camera streaming, and diagnostics.

Options:
  --calibrate   Launch servo calibration workflow after provisioning completes.
USAGE
}

if [[ ${EUID} -ne 0 ]]; then
  echo "This script must be run as root (use sudo)." >&2
  exit 1
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --calibrate)
      CALIBRATE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

log() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

ensure_directories() {
  install -d -m 0755 /opt/camjam/bin
  install -d -m 0755 /etc/camjam
  install -d -m 0750 /var/lib/camjam
}

install_packages() {
  log "Installing apt dependencies"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y \
    git \
    python3 \
    python3-venv \
    python3-pip \
    python3-pigpio \
    pigpio \
    pigpiod \
    libcamera-apps \
    tmux \
    jq
}

deploy_pin_config() {
  log "Applying CamJam pin mappings"
  install -m 0644 "${PIN_CONFIG}" /etc/camjam/pins.yaml
}

install_scripts() {
  log "Installing helper scripts"
  install -m 0755 "${SCRIPTS_DIR}/check_services.sh" /opt/camjam/bin/check_services.sh
  install -m 0755 "${SCRIPTS_DIR}/diagnostics.sh" /opt/camjam/bin/diagnostics.sh
  install -m 0755 "${SCRIPTS_DIR}/tls_renew.sh" /opt/camjam/bin/tls_renew.sh
}

install_systemd_units() {
  log "Deploying systemd units"
  for unit in "${SYSTEMD_DIR}"/*.{service,timer}; do
    [[ -e "${unit}" ]] || continue
    install -m 0644 "${unit}" "/etc/systemd/system/$(basename "${unit}")"
  done
  systemctl daemon-reload
  systemctl enable pigpiod.service
  systemctl enable camjam-control.service
  systemctl enable camjam-camera.service
  systemctl enable camjam-diagnostics.service
  if systemctl list-unit-files | grep -q '^camjam-tls-renew.timer'; then
    systemctl enable camjam-tls-renew.timer
  fi
}

run_calibration() {
  if [[ ${CALIBRATE} -eq 0 ]]; then
    return
  fi

  log "Starting servo calibration routine"
  if ! systemctl is-active --quiet pigpiod.service; then
    systemctl start pigpiod.service
  fi

  python3 - <<'PY'
import json
import pathlib
import time

TARGET_PATH = pathlib.Path('/var/lib/camjam/servos.yaml')

print('Centre the pan/tilt assembly, then press Enter to record offsets...')
input()

default_offsets = {'pan_offset': 0, 'tilt_offset': 0, 'timestamp': time.time()}
TARGET_PATH.write_text(json.dumps(default_offsets, indent=2))
print(f'Calibration complete. Offsets saved to {TARGET_PATH}.')
PY
}

main() {
  ensure_directories
  install_packages
  deploy_pin_config
  install_scripts
  install_systemd_units
  run_calibration
  log "Provisioning complete"
}

main "$@"
