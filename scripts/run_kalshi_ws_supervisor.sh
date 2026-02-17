#!/usr/bin/env bash
set -euo pipefail

# Supervisor for Kalshi WS marketdata collector.
# - Restarts on failure
# - Rotates output file per run
# - Basic health check: output file mtime must keep updating
#
# Usage:
#   cd /root/.openclaw/workspace/kalshi-btc-5min-bot
#   source /root/.secrets/kalshi.env
#   ./scripts/run_kalshi_ws_supervisor.sh
#
# Config (env vars):
#   KALSHI_ENV=prod|demo                     (default: prod)
#   KALSHI_CHANNELS=ticker,trade             (default: ticker,trade)
#   KALSHI_MARKETS=KXBTC-...,...             (optional; comma-separated)
#   PUBLIC_ONLY=1                            (optional; sets --public-only)
#   RESTART_SLEEP_SEC=2
#   HEALTH_GRACE_SEC=10
#   HEALTH_MAX_STALE_SEC=20
#   VENV_PY=./.venv/bin/python
#   LOG_DIR=state/logs
#   OUT_DIR=state/recordings

KALSHI_ENV="${KALSHI_ENV:-prod}"
KALSHI_CHANNELS="${KALSHI_CHANNELS:-ticker,trade}"
KALSHI_MARKETS="${KALSHI_MARKETS:-}"
PUBLIC_ONLY="${PUBLIC_ONLY:-0}"

VENV_PY="${VENV_PY:-./.venv/bin/python}"
LOG_DIR="${LOG_DIR:-state/logs}"
OUT_DIR="${OUT_DIR:-state/recordings}"

RESTART_SLEEP_SEC="${RESTART_SLEEP_SEC:-2}"
HEALTH_GRACE_SEC="${HEALTH_GRACE_SEC:-10}"
HEALTH_MAX_STALE_SEC="${HEALTH_MAX_STALE_SEC:-20}"

mkdir -p "$LOG_DIR" "$OUT_DIR"

stamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

file_age_sec() {
  local p="$1"
  if [[ ! -f "$p" ]]; then
    echo 999999
    return
  fi
  python3 - <<PY
import os, time
p=os.path.expanduser("$p")
print(int(time.time() - os.path.getmtime(p)))
PY
}

build_args() {
  local args=("--env" "$KALSHI_ENV" "--channels" "$KALSHI_CHANNELS")

  if [[ "$PUBLIC_ONLY" == "1" ]]; then
    args+=("--public-only")
  fi

  if [[ -n "$KALSHI_MARKETS" ]]; then
    IFS=',' read -r -a mkts <<<"$KALSHI_MARKETS"
    for m in "${mkts[@]}"; do
      m="${m//[[:space:]]/}"
      [[ -z "$m" ]] && continue
      args+=("--market" "$m")
    done
  fi

  printf '%q ' "${args[@]}"
}

run_once() {
  local run_id out log_file args
  run_id="$(date -u +%Y%m%d_%H%M%S)"
  out="$OUT_DIR/kalshi_ws_${KALSHI_ENV}_${run_id}.jsonl"
  log_file="$LOG_DIR/kalshi_ws_${KALSHI_ENV}_${run_id}.log"

  args="$(build_args)"

  echo "[$(stamp)] starting kalshi ws collector (run_id=$run_id)" | tee -a "$log_file"
  echo "[$(stamp)] out=$out" | tee -a "$log_file"
  echo "[$(stamp)] args=$args" | tee -a "$log_file"

  # Run in background so we can health-check.
  ( OUT="$out" \
      "$VENV_PY" scripts/collect_kalshi_ws_marketdata.py \
        --out "$out" \
        ${args} \
      >>"$log_file" 2>&1 ) &
  local pid=$!

  sleep "$HEALTH_GRACE_SEC"

  while kill -0 "$pid" 2>/dev/null; do
    local age
    age="$(file_age_sec "$out")"
    if [[ "$age" -gt "$HEALTH_MAX_STALE_SEC" ]]; then
      echo "[$(stamp)] HEALTH: output stale age=${age}s -> restarting pid=$pid" | tee -a "$log_file"
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      return 1
    fi
    sleep 5
  done

  wait "$pid" || return $?
  return 0
}

while true; do
  if run_once; then
    echo "[$(stamp)] collector exited cleanly; restarting in ${RESTART_SLEEP_SEC}s" | tee -a "$LOG_DIR/kalshi_ws_supervisor.log"
  else
    echo "[$(stamp)] collector failed/restarted; sleeping ${RESTART_SLEEP_SEC}s" | tee -a "$LOG_DIR/kalshi_ws_supervisor.log"
  fi
  sleep "$RESTART_SLEEP_SEC"
done
