#!/usr/bin/env python3
"""Backtest the MM strategy against recorded Kalshi orderbook data.

Reads JSONL files from data/ directory and replays through paper_mm logic.

Usage:
    python scripts/backtest_mm.py
    python scripts/backtest_mm.py --data-dir /path/to/data
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kalshi_bot.paper_mm import (
    QuoteConfig, _best_level, _now_day_key, choose_quote_price,
    load_state, save_state,
)


def run_backtest(data_dir: Path, qcfg: QuoteConfig, cash: float = 250.0) -> None:
    files = sorted(data_dir.glob("*.jsonl"))
    if not files:
        print(f"No data found in {data_dir} — run collector first")
        return

    print(f"Found {len(files)} data files in {data_dir}")
    st: dict = {"cash_cents": int(cash * 100), "positions": {}, "open_orders": {}, "daily": {}}

    total_ticks = 0
    total_fills = 0
    realized_pnl_cents = 0

    for f in files:
        with open(f) as fh:
            for line in fh:
                try:
                    record = json.loads(line.strip())
                except Exception:
                    continue

                market = record.get("market_ticker") or record.get("ticker")
                ob = record.get("orderbook") or record.get("ob") or {}
                yes_levels = ob.get("yes") or []
                no_levels = ob.get("no") or []
                if not market or (not yes_levels and not no_levels):
                    continue

                total_ticks += 1

                for side, levels in (("yes", yes_levels), ("no", no_levels)):
                    best = _best_level(levels)
                    if not best:
                        continue
                    best_px, best_sz = best
                    quote_px = choose_quote_price(best_px, qcfg)
                    if quote_px < 1 or quote_px > 99:
                        continue

                    oo = st.setdefault("open_orders", {}).setdefault(market, {})
                    existing = oo.get(side)

                    # Simulate fill: if size at our price decreased, we got filled
                    if existing:
                        prev_sz = existing.get("prev_sz_at_px", best_sz)
                        px = existing["price"]
                        cur_sz = next((float(s) for p, s in levels if int(p) == px), None)
                        if cur_sz is not None and cur_sz < prev_sz:
                            fills = min(int(prev_sz - cur_sz), existing.get("remaining", 0))
                            if fills > 0:
                                total_fills += fills
                                cost = fills * px
                                pos = st.setdefault("positions", {}).setdefault(market, {
                                    "yes_qty": 0, "yes_cost_cents": 0,
                                    "no_qty": 0, "no_cost_cents": 0
                                })
                                pos[f"{side}_qty"] += fills
                                pos[f"{side}_cost_cents"] += cost
                                st["cash_cents"] -= cost
                                existing["remaining"] = max(0, existing["remaining"] - fills)
                        # Update prev size
                        existing["prev_sz_at_px"] = cur_sz if cur_sz is not None else best_sz
                    else:
                        # Place new quote
                        cur_sz = next((float(s) for p, s in levels if int(p) == quote_px), best_sz)
                        oo[side] = {
                            "price": quote_px,
                            "remaining": qcfg.quote_size,
                            "prev_sz_at_px": cur_sz,
                        }

    # Final P&L estimate (mark positions at 50c for simplicity)
    unrealized = 0
    for pos in st.get("positions", {}).values():
        unrealized += int(pos.get("yes_qty", 0)) * (50 - int(pos.get("yes_cost_cents", 0) / max(1, pos.get("yes_qty", 1))))
        unrealized += int(pos.get("no_qty", 0)) * (50 - int(pos.get("no_cost_cents", 0) / max(1, pos.get("no_qty", 1))))

    starting_cash = int(cash * 100)
    ending_cash = st.get("cash_cents", starting_cash)
    pnl_cents = ending_cash - starting_cash + unrealized

    print(f"\n{'='*50}")
    print(f"BACKTEST RESULTS")
    print(f"{'='*50}")
    print(f"Ticks processed:  {total_ticks:,}")
    print(f"Total fills:      {total_fills:,}")
    print(f"Starting cash:    ${cash:.2f}")
    print(f"Ending cash:      ${ending_cash/100:.2f}")
    print(f"Unrealized P&L:   ${unrealized/100:.2f}")
    print(f"Total P&L:        ${pnl_cents/100:.2f}")
    print(f"Return:           {pnl_cents/starting_cash*100:.2f}%")
    print(f"{'='*50}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data", help="Directory with JSONL orderbook files")
    ap.add_argument("--tight", action="store_true")
    ap.add_argument("--cash", type=float, default=250.0)
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    qcfg = QuoteConfig(tight=args.tight, quote_size=1)
    run_backtest(data_dir, qcfg, args.cash)


if __name__ == "__main__":
    main()
