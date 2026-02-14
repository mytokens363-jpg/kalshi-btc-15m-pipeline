# Kalshi BTC 5-minute Bot (Kalshi-first)

Goal: Build a high-frequency style strategy for 5-minute BTC up/down markets.

**Principles**
- Start with **sim/paper** (no live orders) until data + fills + fees are validated.
- Hard risk controls from day 1 (max loss/day, max notional, kill switch).
- Full audit logging (every decision + quote + order attempt).

## Roadmap (phased)

### Phase 0 — Infrastructure (no trading)
- Kalshi connector (auth, market discovery, order book snapshots)
- Price feed adapter (Coinbase/Binance via websocket)
- Clock + 5-min candle alignment
- Local state store + logs

### Phase 1 — Simulator
- Deterministic replay (recorded order book + price feed)
- Fill model: spread + fees + partial fills + latency

### Phase 2 — Live small (opt-in)
- Start tiny size + strict caps
- Circuit breaker + auto-stop

## Safety
- Never store secrets in repo.
- Use env vars or OS keychain on the node.
