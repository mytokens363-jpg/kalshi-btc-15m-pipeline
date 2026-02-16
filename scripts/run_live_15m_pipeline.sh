#!/usr/bin/env bash
set -euo pipefail

# One-command runner:
# - Collect external ticks (binance primary, coinbase fallback)
# - Pipe them into the live 15m candle publisher
# - Still records ticks to disk for replay

SYMBOL="${SYMBOL:-BTCUSDT}"
REC_OUT="${REC_OUT:-state/recordings/external_failover_$(date +%Y%m%d_%H%M%S).jsonl}"
CANDLE_OUT="${CANDLE_OUT:-state/candles/btc_15m_live.jsonl}"
LATEST_OUT="${LATEST_OUT:-state/candles/btc_15m_latest.json}"

VENV_PY="${VENV_PY:-./.venv/bin/python}"

exec "$VENV_PY" scripts/collect_external_failover.py --out "$REC_OUT" --stdout \
  | "$VENV_PY" scripts/live_15m_candles.py --out "$CANDLE_OUT" --latest "$LATEST_OUT" --symbol "$SYMBOL"
