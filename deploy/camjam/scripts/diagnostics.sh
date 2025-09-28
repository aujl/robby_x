#!/usr/bin/env bash
set -euo pipefail

LOG_DIR=/var/log/camjam
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/diagnostics.log"

read_battery_voltage() {
  if command -v vcgencmd >/dev/null 2>&1; then
    vcgencmd measure_volts
  else
    echo "volts=5.00" # Placeholder when running off-target
  fi
}

read_cpu_temp() {
  if command -v vcgencmd >/dev/null 2>&1; then
    vcgencmd measure_temp
  else
    echo "temp=45.0'C" # Placeholder
  fi
}

{
  date --iso-8601=seconds
  read_battery_voltage
  read_cpu_temp
  /opt/camjam/bin/check_services.sh || echo "Service check failed"
} >> "${LOG_FILE}" 2>&1
