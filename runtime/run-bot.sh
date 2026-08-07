#!/usr/bin/env bash
set -uo pipefail

CONFIG="/workspace/bot.config"
ENV_FILE="/workspace/.env"

load_config() {
  BOT_WORKDIR="/workspace/bot"
  BOT_COMMAND=""

  if [ -f "$CONFIG" ]; then
    while IFS='=' read -r raw_key raw_value || [ -n "${raw_key:-}" ]; do
      key="$(printf '%s' "${raw_key:-}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
      [ -z "$key" ] && continue
      case "$key" in
        \#*) continue ;;
      esac
      value="${raw_value:-}"
      value="$(printf '%s' "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
      case "$key" in
        BOT_WORKDIR) BOT_WORKDIR="$value" ;;
        BOT_COMMAND) BOT_COMMAND="$value" ;;
      esac
    done < "$CONFIG"
  fi
}

load_env() {
  if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a
  fi
}

while true; do
  load_config

  if [ -z "$BOT_COMMAND" ]; then
    echo "[$(date '+%F %T')] BOT_COMMAND が未設定です。"
    echo "Web CMDで: nano /workspace/bot.config"
    sleep 3600
    continue
  fi

  if [ ! -d "$BOT_WORKDIR" ]; then
    echo "[$(date '+%F %T')] BOT_WORKDIR がありません: $BOT_WORKDIR" >&2
    sleep 30
    continue
  fi

  load_env
  cd "$BOT_WORKDIR" || {
    sleep 30
    continue
  }

  echo "[$(date '+%F %T')] Bot starting"
  echo "workdir=$BOT_WORKDIR"
  echo "command=$BOT_COMMAND"

  # 実際のBotプロセス。終了したらsupervisorがこのwrapperを再起動します。
  exec /bin/bash -lc "$BOT_COMMAND"
done
