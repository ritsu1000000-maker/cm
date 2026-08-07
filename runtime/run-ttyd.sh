#!/usr/bin/env bash
set -euo pipefail

WEB_USER="${WEB_USER:-admin}"
WEB_PASSWORD="${WEB_PASSWORD:-}"

if [ -z "$WEB_PASSWORD" ]; then
  echo "WEB_PASSWORD が未設定です。console.env を設定してください。" >&2
  exit 1
fi

exec /usr/bin/ttyd \
  -W \
  -p 7681 \
  -i 0.0.0.0 \
  -c "${WEB_USER}:${WEB_PASSWORD}" \
  -t titleFixed="Discord Bot Virtual CMD" \
  -t cursorBlink=true \
  -t fontSize=15 \
  -t disableLeaveAlert=true \
  /bin/bash --rcfile "$HOME/.bashrc" -i
