#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import datetime as dt

from kalshi_bot.collectors.external_price_binance import BinanceConfig, BinanceTopOfBookCollector
from kalshi_bot.collectors.external_price_coinbase import CoinbaseConfig, CoinbaseTickerCollector
from kalshi_bot.io.recorder import JsonlRecorder


async def main_async():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="JSONL output path")
    ap.add_argument("--provider", default="binance", choices=["binance", "coinbase"], help="Which feed to run")
    args = ap.parse_args()

    out = args.out or f"state/recordings/external_{args.provider}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    rec = JsonlRecorder(out)

    def emit(ev):
        rec.append(ev)

    print(f"Recording external feed ({args.provider}) to: {out}")

    if args.provider == "binance":
        c = BinanceTopOfBookCollector(BinanceConfig())
        await c.run(emit)
    else:
        c = CoinbaseTickerCollector(CoinbaseConfig())
        await c.run(emit)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
