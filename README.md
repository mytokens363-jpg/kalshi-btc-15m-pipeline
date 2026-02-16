# Kalshi BTC 15-minute Bot (Kalshi-first)

Goal: Build a strategy for Kalshi BTC **15-minute** up/down markets (`kxbtc15m`).

**Principles**
- Start with **sim/paper** (no live orders) until data + fills + fees are validated.
- Hard risk controls from day 1 (max loss/day, max notional, kill switch).
- Full audit logging (every decision + quote + order attempt).

## Roadmap (phased)

### Phase 0 — Infrastructure (no trading)
- Kalshi demo WebSocket collector (ticker/trade now; orderbook_delta once keys are on VPS)
- Kalshi connector (auth, market discovery, order book snapshots)
- Price feed adapter (Binance Futures bookTicker primary; Coinbase ticker fallback)
- Clock + 5-min candle alignment
- Local state store + logs

### Phase 1 — Simulator
- Deterministic replay (recorded order book + price feed)
- Fill model: spread + fees + partial fills + latency

### Phase 2 — Live small (opt-in)
- Start tiny size + strict caps
- Circuit breaker + auto-stop

## Running (Phase 0)

### External price collector (Binance primary, Coinbase fallback)

```bash
cd ~/.openclaw/workspace/kalshi-btc-5min-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/collect_external_failover.py
```

Recordings are written to `state/recordings/*.jsonl`.

### Build 15-minute candles (NY time buckets)

```bash
source .venv/bin/activate
python scripts/build_15m_candles.py --in state/recordings --out state/candles/btc_15m.jsonl --symbol BTCUSDT
```

### Streaming 15-minute candles (hybrid: in-memory + write-on-close)

This consumes ticks from stdin and maintains the current NY-aligned 15-minute candle in memory,
while also writing:
- append-only candle closes to `--out`
- a small `--latest` snapshot file updated every tick

```bash
source .venv/bin/activate
python scripts/collect_external_failover.py --out /tmp/ext.jsonl

# Example: stream from a file (or pipe from a live collector)
cat /tmp/ext.jsonl | python scripts/live_15m_candles.py \
  --out state/candles/btc_15m_live.jsonl \
  --latest state/candles/btc_15m_latest.json \
  --symbol BTCUSDT
```

### One-command runner (collector → live candles)

```bash
source .venv/bin/activate
./scripts/run_live_15m_pipeline.sh
```

### Kalshi WS marketdata (read-only)

Kalshi WS v2 requires an authenticated connection even for public marketdata channels.
Set env vars:
- `KALSHI_ACCESS_KEY_ID`
- `KALSHI_PRIVATE_KEY_PATH` (PEM file)

Demo host defaults to `demo-api.kalshi.co`, prod to `api.elections.kalshi.com`.

```bash
source .venv/bin/activate
export KALSHI_ACCESS_KEY_ID="..."
export KALSHI_PRIVATE_KEY_PATH="/path/to/kalshi_private_key.pem"

# Demo, ticker+trade (all markets)
python scripts/collect_kalshi_ws_marketdata.py --env demo --channels ticker,trade

# Filter to one market ticker (repeatable --market)
python scripts/collect_kalshi_ws_marketdata.py --env demo --channels ticker,trade --market kxbtc15m-26feb152015
```

### Supervisor (health monitor + auto-restart)

This wraps the pipeline, writes logs to `state/logs/`, and restarts if:
- the pipeline exits, or
- the `btc_15m_latest.json` snapshot stops updating (stale file age)

```bash
source .venv/bin/activate
./scripts/run_live_15m_supervisor.sh
```

Notes:
- `btc_15m_latest.json` updates every tick.
- `btc_15m_live.jsonl` appends on candle close (and on clean EOF).

## Safety
- Never store secrets in repo.
- Use env vars or OS keychain on the node.
