#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

# Allow running as a script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kalshi_bot.io.candles import NY_TZ, Candle15m, PriceTick, build_15m_candles, parse_external_price_tick


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, separators=(",", ":")) + "\n")


def _write_latest(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def tick_to_pricetick(line: str) -> Optional[PriceTick]:
    t = parse_external_price_tick(line)
    if t is None:
        return None
    return t


def candle_to_record(c: Candle15m) -> dict:
    return {
        "type": "CANDLE_15M",
        "candle_start_ms": c.candle_start_ms,
        "candle_start_local": c.candle_start_local,
        "symbol": c.symbol,
        "open": c.open,
        "high": c.high,
        "low": c.low,
        "close": c.close,
        "ticks": c.ticks,
        "first_ts_ms": c.first_ts_ms,
        "last_ts_ms": c.last_ts_ms,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Stream 15-minute NY-time candles from external price JSONL (stdin)")
    ap.add_argument("--out", required=True, help="Append-only candles JSONL output")
    ap.add_argument("--latest", required=True, help="Latest candle snapshot JSON file")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--stats-every-seconds", type=int, default=30)
    args = ap.parse_args()

    out_path = Path(args.out).expanduser()
    latest_path = Path(args.latest).expanduser()

    current: Optional[Candle15m] = None
    last_stats = time.time()
    ticks_seen = 0
    last_tick_ms: Optional[int] = None

    for raw in sys.stdin:
        pt = tick_to_pricetick(raw)
        if pt is None:
            continue
        if pt.symbol and pt.symbol != args.symbol:
            continue

        ticks_seen += 1
        last_tick_ms = pt.ts_ms

        # Use the same candle builder logic by feeding one tick at a time.
        # We replicate the update logic for performance/clarity.
        from kalshi_bot.io.candles import candle_start_ms_utc

        start_ms, start_local_iso = candle_start_ms_utc(pt.ts_ms, tz=NY_TZ)

        if current is None or start_ms != current.candle_start_ms:
            if current is not None:
                _append_jsonl(out_path, candle_to_record(current))
            else:
                # Create the file early so downstream tooling can detect it.
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.touch(exist_ok=True)
            current = Candle15m(
                candle_start_ms=start_ms,
                candle_start_local=start_local_iso,
                symbol=args.symbol,
                open=pt.mid,
                high=pt.mid,
                low=pt.mid,
                close=pt.mid,
                ticks=1,
                first_ts_ms=pt.ts_ms,
                last_ts_ms=pt.ts_ms,
            )
        else:
            current.high = max(current.high, pt.mid)
            current.low = min(current.low, pt.mid)
            current.close = pt.mid
            current.ticks += 1
            current.last_ts_ms = pt.ts_ms

        # Update latest snapshot every tick (small file)
        _write_latest(latest_path, candle_to_record(current))

        now = time.time()
        if now - last_stats >= args.stats_every_seconds:
            stats = {
                "type": "STATS",
                "ts_ms": int(now * 1000),
                "ticks_seen": ticks_seen,
                "last_tick_ms": last_tick_ms,
                "current_candle_start_ms": current.candle_start_ms if current else None,
                "current_candle_ticks": current.ticks if current else 0,
            }
            # stderr so stats show up even when stdout is piped to something that closes early
            print(json.dumps(stats), file=sys.stderr, flush=True)
            last_stats = now

    # Flush the last candle on EOF
    if current is not None:
        _append_jsonl(out_path, candle_to_record(current))

    # Emit final stats line
    final = {
        "type": "STATS_FINAL",
        "ts_ms": int(time.time() * 1000),
        "ticks_seen": ticks_seen,
        "last_tick_ms": last_tick_ms,
        "final_candle_start_ms": current.candle_start_ms if current else None,
        "final_candle_ticks": current.ticks if current else 0,
    }
    print(json.dumps(final), file=sys.stderr, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
