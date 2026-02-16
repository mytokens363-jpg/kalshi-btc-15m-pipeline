#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import os
import sys

# Allow running as a script without installing the package
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kalshi_bot.collectors.kalshi_ws_marketdata import KalshiWsConfig, run_kalshi_ws_marketdata
from kalshi_bot.io.recorder import JsonlRecorder
from kalshi_bot.kalshi_auth import KalshiKey


def _env_required(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Missing env var: {name}")
    return v


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect Kalshi WS v2 marketdata (read-only) to JSONL")
    ap.add_argument("--env", choices=["demo", "prod"], default="demo")
    ap.add_argument("--channels", default="ticker,trade", help="Comma-separated channels (e.g., ticker,trade,orderbook_delta)")
    ap.add_argument("--market", action="append", default=[], help="Market ticker (repeatable). If omitted, subscribe to all markets for the channel.")
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--public-only",
        action="store_true",
        help="Do not authenticate (no headers). Useful for testing public channels like ticker/trade.",
    )
    args = ap.parse_args()

    access_key_id = None
    private_key_path = None
    if not args.public_only:
        access_key_id = _env_required("KALSHI_ACCESS_KEY_ID")
        private_key_path = _env_required("KALSHI_PRIVATE_KEY_PATH")

    if args.env == "demo":
        ws_host = os.getenv("KALSHI_WS_HOST", "demo-api.kalshi.co")
    else:
        ws_host = os.getenv("KALSHI_WS_HOST", "api.elections.kalshi.com")

    out = args.out or f"state/recordings/kalshi_ws_{args.env}_{dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"
    rec = JsonlRecorder(out)

    channels = tuple([c.strip() for c in args.channels.split(",") if c.strip()])

    cfg = KalshiWsConfig(
        ws_host=ws_host,
        channels=channels,
        market_tickers=tuple(args.market),
    )

    # Kalshi docs: these channels require auth
    private_channels = {"orderbook_delta", "fill", "market_positions", "communications", "order_group_updates"}
    if args.public_only and any(c in private_channels for c in channels):
        raise SystemExit(f"--public-only cannot be used with private channels: {sorted(set(channels) & private_channels)}")

    key = None if args.public_only else KalshiKey(access_key_id=access_key_id, private_key_path=private_key_path)

    print(f"Connecting to Kalshi WS ({args.env}) wss://{cfg.ws_host}{cfg.ws_path} auth={'off' if args.public_only else 'on'}")
    print(f"Recording to: {out}")
    if cfg.market_tickers:
        print(f"Markets: {cfg.market_tickers}")
    print(f"Channels: {cfg.channels}")

    def emit(obj: dict) -> None:
        # Recorder expects Event-like shape; we already provide ts_ms/type/payload.
        rec.path.parent.mkdir(parents=True, exist_ok=True)
        with rec.path.open("a", encoding="utf-8") as f:
            import json

            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    asyncio.run(run_kalshi_ws_marketdata(cfg, key, emit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
