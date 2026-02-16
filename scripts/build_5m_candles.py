#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import sys

# Allow running as a script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kalshi_bot.io.candles import NY_TZ, build_5m_candles, iter_ticks, write_candles_jsonl


def main() -> int:
    ap = argparse.ArgumentParser(description="Build 5-minute candles (America/New_York buckets) from external price JSONL")
    ap.add_argument("--in", dest="inp", required=True, help="Input JSONL file or directory (recordings)")
    ap.add_argument("--out", dest="out", required=True, help="Output JSONL path")
    ap.add_argument("--symbol", default="BTCUSDT")
    args = ap.parse_args()

    in_path = Path(args.inp).expanduser()
    if in_path.is_dir():
        paths = sorted(in_path.glob("*.jsonl"))
    else:
        paths = [in_path]

    ticks = iter_ticks(paths)
    candles = build_5m_candles(ticks, tz=NY_TZ, symbol=args.symbol)
    meta = write_candles_jsonl(Path(args.out).expanduser(), candles)
    print(meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
