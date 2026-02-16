#!/usr/bin/env python3
from __future__ import annotations

"""External price collector with failover.

Priority: Binance Futures bookTicker.
Fallback: Coinbase ticker.

This is Phase 0: record external reference feed robustly.
"""

import argparse
import asyncio
import datetime as dt
import time

import os
import sys
import json

# Ensure we can import from ./src when running as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kalshi_bot.collectors.external_price_binance import BinanceConfig, BinanceTopOfBookCollector
from kalshi_bot.collectors.external_price_coinbase import CoinbaseConfig, CoinbaseTickerCollector
from kalshi_bot.io.recorder import JsonlRecorder


async def run_with_timeout(coro, seconds: int):
    return await asyncio.wait_for(coro, timeout=seconds)


async def main_async():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--stdout", action="store_true", help="Also emit JSONL events to stdout (for piping)")
    ap.add_argument("--binanceSeconds", type=int, default=0, help="If >0, run Binance for N seconds then exit (test)")
    ap.add_argument("--coinbaseSeconds", type=int, default=0, help="If >0, run Coinbase for N seconds then exit (test)")
    args = ap.parse_args()

    out = args.out or f"state/recordings/external_failover_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    rec = JsonlRecorder(out)

    def emit(ev):
        rec.append(ev)
        if args.stdout:
            # Mirror the recorder format for piping into downstream tools.
            sys.stdout.write(json.dumps({"ts_ms": ev.ts_ms, "type": ev.type, "payload": ev.payload}, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    if not args.stdout:
        print(f"Recording external feed (binance primary, coinbase fallback) to: {out}")

    binance = BinanceTopOfBookCollector(BinanceConfig())
    coinbase = CoinbaseTickerCollector(CoinbaseConfig())

    while True:
        # Try binance first
        try:
            if args.binanceSeconds > 0:
                await run_with_timeout(binance.run(emit), args.binanceSeconds)
                return
            await binance.run(emit)
        except Exception as e:
            # fall through to coinbase
            pass

        # Fallback
        try:
            if args.coinbaseSeconds > 0:
                await run_with_timeout(coinbase.run(emit), args.coinbaseSeconds)
                return
            await coinbase.run(emit)
        except Exception:
            await asyncio.sleep(2.0)
            continue


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
