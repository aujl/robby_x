#!/usr/bin/env bash
set -euo pipefail

services=(
  camjam-control.service
  camjam-camera.service
  camjam-diagnostics.service
  pigpiod.service
)

healthy=1

for svc in "${services[@]}"; do
  if systemctl is-active --quiet "$svc"; then
    echo "$svc: active"
  else
    echo "$svc: inactive" >&2
    healthy=0
  fi
done

if [[ $healthy -eq 0 ]]; then
  exit 1
fi
