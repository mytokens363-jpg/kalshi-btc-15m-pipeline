# kalshi-btc-5min-bot — agent notes

## Rules
- Default to **SIM/PAPER**. No live orders unless Darius explicitly approves.
- Log every decision and order lifecycle event.

## Phase 0/1 tasks
- Implement collectors:
  - external BTC price feed (Coinbase/Binance)
  - Kalshi market data feed (order book + trades)
- Record unified JSONL event stream
- Build replay simulator + basic fill model
