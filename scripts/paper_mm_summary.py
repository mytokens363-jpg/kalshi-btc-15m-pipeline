#!/usr/bin/env python3
"""Summarize internal paper-MM results from state/paper_mm_state.json.

This is read-only and does not call Kalshi.

Usage:
  python ./scripts/paper_mm_summary.py --state state/paper_mm_state.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="state/paper_mm_state.json")
    ap.add_argument("--last", type=int, default=8, help="show last N fills/realized entries")
    args = ap.parse_args()

    p = Path(args.state)
    if not p.exists():
        print("No state file yet.")
        return 0

    st = json.loads(p.read_text())

    cash_cents = int(st.get("cash_cents", 0))
    cash = cash_cents / 100.0

    daily = st.get("daily", {}) or {}
    day_keys = sorted(daily.keys())
    today_key = day_keys[-1] if day_keys else None
    filled_today = int(daily.get(today_key, {}).get("filled", 0)) if today_key else 0

    realized = st.get("realized", []) or []
    realized_pnl_cents = sum(int(x.get("pnl_cents", 0)) for x in realized)

    positions = st.get("positions", {}) or {}
    open_markets = len(positions)

    print(f"Kalshi PAPER-MM summary")
    print(f"- cash: ${cash:.2f}")
    print(f"- realized PnL (all-time): ${realized_pnl_cents/100.0:.2f} (n={len(realized)})")
    if today_key:
        print(f"- filled today ({today_key} UTC): {filled_today}")
    print(f"- open markets: {open_markets}")

    if open_markets:
        print("- positions (by market):")
        for mkt, pos in list(positions.items())[:12]:
            yq = int(pos.get("yes_qty", 0))
            nq = int(pos.get("no_qty", 0))
            yc = int(pos.get("yes_cost_cents", 0))
            nc = int(pos.get("no_cost_cents", 0))
            print(f"  • {mkt}: YES {yq} (cost ${yc/100:.2f}) | NO {nq} (cost ${nc/100:.2f})")
        if open_markets > 12:
            print(f"  … +{open_markets-12} more")

    if realized:
        print("- last realized:")
        for r in realized[-args.last:]:
            print(
                f"  • {r.get('market')} result={r.get('result')} pnl=${int(r.get('pnl_cents',0))/100:.2f} "
                f"(payout=${int(r.get('payout_cents',0))/100:.2f} cost=${int(r.get('cost_cents',0))/100:.2f})"
            )

    fills = st.get("fills", []) or []
    if fills:
        print("- last fills:")
        for f in fills[-args.last:]:
            print(f"  • {f.get('market')} {f.get('side')} {f.get('qty')} @ {f.get('px')}c")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
