#!/usr/bin/env bash
set -euo pipefail

# Simple supervisor for the live pipeline.
# Restarts on failure, logs to state/logs, and checks that latest snapshot is updating.

SYMBOL="${SYMBOL:-BTCUSDT}"
REC_OUT="${REC_OUT:-state/recordings/external_failover_$(date +%Y%m%d_%H%M%S).jsonl}"
CANDLE_OUT="${CANDLE_OUT:-state/candles/btc_15m_live.jsonl}"
LATEST_OUT="${LATEST_OUT:-state/candles/btc_15m_latest.json}"

VENV_PY="${VENV_PY:-./.venv/bin/python}"

LOG_DIR="${LOG_DIR:-state/logs}"
mkdir -p "$LOG_DIR"

RESTART_SLEEP_SEC="${RESTART_SLEEP_SEC:-2}"
HEALTH_GRACE_SEC="${HEALTH_GRACE_SEC:-20}"
HEALTH_MAX_STALE_SEC="${HEALTH_MAX_STALE_SEC:-15}"

stamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

latest_mtime_age() {
  if [[ ! -f "$LATEST_OUT" ]]; then
    echo 999999
    return
  fi
  python3 - <<PY
import os, time
p = os.path.expanduser("$LATEST_OUT")
age = int(time.time() - os.path.getmtime(p))
print(age)
PY
}

run_once() {
  local run_id
  run_id="$(date -u +%Y%m%d_%H%M%S)"
  local log_file="$LOG_DIR/live_15m_${run_id}.log"

  echo "[$(stamp)] starting pipeline (run_id=$run_id)" | tee -a "$log_file"

  # Start pipeline in background so we can health-check.
  ( SYMBOL="$SYMBOL" REC_OUT="$REC_OUT" CANDLE_OUT="$CANDLE_OUT" LATEST_OUT="$LATEST_OUT" VENV_PY="$VENV_PY" \
      ./scripts/run_live_15m_pipeline.sh \
      >>"$log_file" 2>&1 ) &
  local pid=$!

  # Give it a moment to create/update latest.
  sleep "$HEALTH_GRACE_SEC"

  while kill -0 "$pid" 2>/dev/null; do
    local age
    age="$(latest_mtime_age)"
    if [[ "$age" -gt "$HEALTH_MAX_STALE_SEC" ]]; then
      echo "[$(stamp)] HEALTH: latest snapshot stale age=${age}s -> restarting pid=$pid" | tee -a "$log_file"
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
    echo "[$(stamp)] pipeline exited cleanly; restarting in ${RESTART_SLEEP_SEC}s" | tee -a "$LOG_DIR/supervisor.log"
  else
    echo "[$(stamp)] pipeline failed/restarted; sleeping ${RESTART_SLEEP_SEC}s" | tee -a "$LOG_DIR/supervisor.log"
  fi
  sleep "$RESTART_SLEEP_SEC"

  # Refresh REC_OUT filename on each run so recordings rotate
  REC_OUT="state/recordings/external_failover_$(date +%Y%m%d_%H%M%S).jsonl"
done
