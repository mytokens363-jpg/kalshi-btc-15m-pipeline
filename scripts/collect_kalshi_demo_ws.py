#!/usr/bin/env python3
from __future__ import annotations

"""Collect Kalshi DEMO WebSocket messages and record to JSONL.

Phase 0 collector.
- Starts with public channels (ticker, trade)
- Later we will add authenticated headers + orderbook_delta once API keys are on the VPS.

Usage (VPS):
  cd /root/kalshi-btc-5min-bot
  source .venv/bin/activate
  PYTHONPATH=./src python scripts/collect_kalshi_demo_ws.py --channels ticker,trade

Optionally filter by market tickers:
  --markets "KXFUT24-LSV,OTHER..."
"""

import argparse
import asyncio
import datetime as dt
import json
import time
from typing import Any, Dict, List

import os
import websockets

from kalshi_bot.io.recorder import JsonlRecorder
from kalshi_bot.types import Event
from kalshi_bot.kalshi_auth import KalshiKey, ws_auth_headers


def now_ms() -> int:
    return int(time.time() * 1000)


WS_URL_DEMO = "wss://demo-api.kalshi.co/trade-api/ws/v2"
WS_PATH = "/trade-api/ws/v2"


def _emit(rec: JsonlRecorder, etype: str, payload: Dict[str, Any]) -> None:
    rec.append(Event(ts_ms=now_ms(), type=etype, payload=payload))


async def main_async() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="Output JSONL path")
    ap.add_argument(
        "--channels",
        default="ticker,trade",
        help="Comma-separated channels (default: ticker,trade)",
    )
    ap.add_argument(
        "--markets",
        default="",
        help="Comma-separated market tickers to filter (optional)",
    )
    ap.add_argument("--ws", default=WS_URL_DEMO, help="WebSocket URL")
    ap.add_argument("--auth", action="store_true", help="Force authenticated websocket headers")
    args = ap.parse_args()

    chans: List[str] = [c.strip() for c in args.channels.split(",") if c.strip()]
    markets: List[str] = [m.strip() for m in args.markets.split(",") if m.strip()]

    out = args.out or f"state/recordings/kalshi_demo_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    rec = JsonlRecorder(out)

    print(f"Recording Kalshi demo WS to: {out}")
    print(f"WS: {args.ws}")
    print(f"channels={chans} markets={markets or 'ALL'}")

    # Auth (demo currently returns 401 even for public channels in our tests; support auth by default if env vars exist)
    key_id = os.environ.get("KALSHI_ACCESS_KEY")
    key_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH")

    headers = None
    if args.auth or (key_id and key_path):
        if not (key_id and key_path):
            raise SystemExit("Missing KALSHI_ACCESS_KEY or KALSHI_PRIVATE_KEY_PATH env vars")
        headers = ws_auth_headers(KalshiKey(access_key_id=key_id, private_key_path=key_path), ws_path=WS_PATH)
        print("Using authenticated websocket headers (KALSHI-ACCESS-KEY/SIGNATURE/TIMESTAMP).")

    backoff = 1.0
    while True:
        try:
            async with websockets.connect(args.ws, ping_interval=20, ping_timeout=20, additional_headers=headers) as ws:
                backoff = 1.0

                sub: Dict[str, Any] = {
                    "id": 1,
                    "cmd": "subscribe",
                    "params": {"channels": chans},
                }
                if markets:
                    sub["params"]["market_tickers"] = markets

                await ws.send(json.dumps(sub))
                _emit(rec, "CONNECTION", {"status": "connected", "sub": sub})

                async for msg in ws:
                    try:
                        data = json.loads(msg)
                    except Exception:
                        continue

                    mtype = data.get("type")
                    payload = data.get("msg") if isinstance(data.get("msg"), dict) else data

                    if mtype == "trade":
                        _emit(rec, "VENUE_TRADE", payload)
                    elif mtype == "ticker":
                        # ticker contains bid/ask-like fields; store it as VENUE_BOOK for now
                        _emit(rec, "VENUE_BOOK", payload)
                    else:
                        # Keep unknown types for debugging
                        _emit(rec, "VENUE_BOOK", {"type": mtype, "raw": payload})

        except Exception as e:
            _emit(rec, "CONNECTION", {"status": "disconnected", "error": str(e)})
            await asyncio.sleep(min(30.0, backoff))
            backoff = min(30.0, backoff * 1.8)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
