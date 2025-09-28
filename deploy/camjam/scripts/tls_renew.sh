#!/usr/bin/env bash
set -euo pipefail

CERTBOT_ARGS=(
  renew
  --deploy-hook "systemctl reload camjam-control.service"
)

if command -v certbot >/dev/null 2>&1; then
  certbot "${CERTBOT_ARGS[@]}"
else
  echo "certbot not installed; skipping TLS renewal" >&2
fi
