#!/usr/bin/env python3

"""End-to-end Kalshi smoke test.

Steps:
1) REST auth: GET /trade-api/v2/portfolio/balance
2) REST list markets: GET /trade-api/v2/markets?series_ticker=...&status=open
3) WS connect + subscribe (ticker/trade) for optional market ticker

Env vars:
- KALSHI_ACCESS_KEY_ID
- KALSHI_PRIVATE_KEY_PATH

Example:
  ./scripts/smoke_kalshi_e2e.py --env demo --series-ticker KXBTC15M --market-ticker KXBTC15M-26FEB18-1700
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Allow running as script
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kalshi_bot.kalshi_auth import KalshiKey
from kalshi_bot.collectors.kalshi_rest import KalshiRestConfig, get_json
from kalshi_bot.collectors.kalshi_ws_marketdata import KalshiWsConfig, run_kalshi_ws_marketdata


def _env_required(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Missing env var: {name}")
    return v


async def _ws_once(cfg: KalshiWsConfig, key: KalshiKey | None, n: int) -> None:
    got = 0

    def emit(obj: dict) -> None:
        nonlocal got
        t = obj.get("type")
        payload = obj.get("payload")
        print("WS", t, payload if isinstance(payload, dict) else "")
        got += 1

    stop = asyncio.Event()

    async def runner():
        await run_kalshi_ws_marketdata(cfg, key, emit, stop_event=stop)

    task = asyncio.create_task(runner())
    # wait for some messages
    while got < n:
        await asyncio.sleep(0.2)
    stop.set()
    await asyncio.sleep(0.2)
    task.cancel()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=["demo", "prod"], default="demo")
    ap.add_argument("--series-ticker", default="KXBTC15M")
    ap.add_argument("--market-ticker", default="")
    ap.add_argument("--ws-messages", type=int, default=3)
    args = ap.parse_args()

    key = KalshiKey(
        access_key_id=_env_required("KALSHI_ACCESS_KEY_ID"),
        private_key_path=_env_required("KALSHI_PRIVATE_KEY_PATH"),
    )

    rest_cfg = KalshiRestConfig(env=args.env)

    bal = get_json(cfg=rest_cfg, key=key, path="/trade-api/v2/portfolio/balance")
    print("BALANCE keys:", list(bal.keys()))

    mkts = get_json(
        cfg=rest_cfg,
        key=key,
        path="/trade-api/v2/markets",
        params={"limit": 5, "series_ticker": args.series_ticker, "status": "open"},
    )
    print("MARKETS keys:", list(mkts.keys()))
    print("MARKETS sample count:", len(mkts.get("markets", [])))

    ws_host = "demo-api.kalshi.co" if args.env == "demo" else "api.elections.kalshi.com"
    ws_cfg = KalshiWsConfig(
        ws_host=ws_host,
        channels=("ticker", "trade"),
        market_tickers=(args.market_ticker,) if args.market_ticker else (),
    )

    print("Connecting WS…")
    asyncio.run(_ws_once(ws_cfg, key, n=args.ws_messages))

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
