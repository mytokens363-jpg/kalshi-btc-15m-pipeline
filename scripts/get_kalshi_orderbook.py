#!/usr/bin/env python3
"""Fetch and print a Kalshi market orderbook via REST (v2).

Usage:
  python ./scripts/get_kalshi_orderbook.py --env demo --market-ticker KXBTC15M-... 

Env vars:
  KALSHI_ACCESS_KEY_ID
  KALSHI_PRIVATE_KEY_PATH
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kalshi_bot.kalshi_auth import KalshiKey
from kalshi_bot.collectors.kalshi_rest import KalshiRestConfig, get_json


def _env_required(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Missing env var: {name}")
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=["demo", "prod"], default="demo")
    ap.add_argument("--market-ticker", required=True)
    args = ap.parse_args()

    key = KalshiKey(
        access_key_id=_env_required("KALSHI_ACCESS_KEY_ID"),
        private_key_path=_env_required("KALSHI_PRIVATE_KEY_PATH"),
    )
    cfg = KalshiRestConfig(env=args.env)

    data = get_json(cfg=cfg, key=key, path=f"/trade-api/v2/markets/{args.market_ticker}/orderbook")

    ob = data.get("orderbook") or {}
    ob_fp = data.get("orderbook_fp") or {}

    def top(side: str):
        # Prefer integer cents ladders if present, otherwise dollars_fp
        levels = ob.get(side) or []
        levels_d = ob_fp.get(f"{side}_dollars") or ob.get(f"{side}_dollars") or []
        return levels[:5], levels_d[:5]

    for side in ("yes", "no"):
        lv, lvd = top(side)
        print(f"{side.upper()} levels (raw): {lv}")
        print(f"{side.upper()} levels ($):   {lvd}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
