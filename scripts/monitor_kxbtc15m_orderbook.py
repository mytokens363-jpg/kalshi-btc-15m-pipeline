#!/usr/bin/env python3
"""Read-only monitor for Kalshi BTC 15m (KXBTC15M) demo orderbook liquidity.

Goal: alert only when BOTH sides have liquidity (YES and NO non-empty) for the
nearest active market ticker AND a spread exists.

This script is intentionally read-only (no orders).

Env vars:
  KALSHI_ACCESS_KEY_ID
  KALSHI_PRIVATE_KEY_PATH

State:
  ./state/monitor_kxbtc15m.json (to avoid duplicate alerts)

Usage:
  python ./scripts/monitor_kxbtc15m_orderbook.py --env demo --min-spread-cents 1
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from kalshi_bot.kalshi_auth import KalshiKey
from kalshi_bot.collectors.kalshi_rest import KalshiRestConfig, get_json

STATE_PATH = Path(__file__).resolve().parents[1] / "state" / "monitor_kxbtc15m.json"
SERIES = "KXBTC15M"


def _env_required(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Missing env var: {name}")
    return v


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def _save_state(st: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=2, sort_keys=True))
    tmp.replace(STATE_PATH)


def _pick_active_market(cfg: KalshiRestConfig, key: KalshiKey) -> str | None:
    # Ask for open markets; API returns a list. We pick the earliest in the list.
    data = get_json(
        cfg=cfg,
        key=key,
        path="/trade-api/v2/markets",
        params={"limit": 50, "series_ticker": SERIES, "status": "open"},
    )
    markets = data.get("markets") or []
    if not markets:
        return None
    # Prefer ACTIVE if status field exists; otherwise take first.
    for m in markets:
        if (m.get("status") or "").lower() == "active":
            return m.get("ticker") or m.get("market_ticker")
    m0 = markets[0]
    return m0.get("ticker") or m0.get("market_ticker")


def _best_level(levels: list) -> tuple[int, float] | None:
    # levels like [[price_cents, size], ...]
    if not levels:
        return None
    price, size = levels[0]
    return int(price), float(size)


def _top_n(levels: list, n: int = 3) -> list[tuple[int, float]]:
    out: list[tuple[int, float]] = []
    for row in (levels or [])[:n]:
        try:
            p, s = row
            out.append((int(p), float(s)))
        except Exception:
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=["demo", "prod"], default="demo")
    ap.add_argument("--min-spread-cents", type=int, default=1)
    args = ap.parse_args()

    key = KalshiKey(
        access_key_id=_env_required("KALSHI_ACCESS_KEY_ID"),
        private_key_path=_env_required("KALSHI_PRIVATE_KEY_PATH"),
    )
    cfg = KalshiRestConfig(env=args.env)

    mkt = _pick_active_market(cfg, key)
    if not mkt:
        return 0

    ob = get_json(cfg=cfg, key=key, path=f"/trade-api/v2/markets/{mkt}/orderbook")
    book = ob.get("orderbook") or {}

    yes_levels = book.get("yes") or []
    no_levels = book.get("no") or []

    yes = _best_level(yes_levels)
    no = _best_level(no_levels)

    # Alert condition: both sides present.
    if not yes or not no:
        return 0

    yes_px, yes_sz = yes
    no_px, no_sz = no

    yes_top3 = _top_n(yes_levels, 3)
    no_top3 = _top_n(no_levels, 3)

    # Define a simple "spread" in cents between the two best offers.
    # This is heuristic; for binary markets, yes+no near 100 indicates tightness.
    spread = abs((yes_px + no_px) - 100)

    if spread < args.min_spread_cents:
        # Very tight / essentially crossed; still liquidity exists, but user asked for spread appears.
        # We'll treat spread>=min as "spread appears".
        return 0

    st = _load_state()
    last_alert = st.get("last_alert", {})
    if last_alert.get("market_ticker") == mkt and last_alert.get("yes_px") == yes_px and last_alert.get("no_px") == no_px:
        return 0

    st["last_alert"] = {
        "ts": int(time.time()),
        "market_ticker": mkt,
        "yes_px": yes_px,
        "yes_sz": yes_sz,
        "no_px": no_px,
        "no_sz": no_sz,
        "spread": spread,
        "yes_top3": yes_top3,
        "no_top3": no_top3,
    }
    _save_state(st)

    fmt = lambda lv: ",".join([f"{p}x{int(s)}" for p, s in lv])
    print(
        f"KALSHI DEMO KXBTC15M liquidity: {mkt} | YES {yes_px}x{yes_sz:g} (top3:{fmt(yes_top3)}) | "
        f"NO {no_px}x{no_sz:g} (top3:{fmt(no_top3)}) | spreadMetric={spread}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
