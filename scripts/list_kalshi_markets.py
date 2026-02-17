#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# Allow running as a script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kalshi_bot.kalshi_auth import KalshiKey, rest_auth_headers


def _env_required(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Missing env var: {name}")
    return v


def _http_get_json(url: str, headers: dict[str, str]) -> dict:
    req = urllib.request.Request(url, method="GET", headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body)


def main() -> int:
    ap = argparse.ArgumentParser(description="List Kalshi markets (prod/demo) and filter by ticker prefix")
    ap.add_argument("--env", choices=["demo", "prod"], default="prod")
    ap.add_argument("--prefix", default="", help="Filter: market ticker must start with this (case-insensitive)")
    ap.add_argument("--series-ticker", default="KXBTC15M", help="Filter by series_ticker (e.g., KXBTC15M)")
    ap.add_argument(
        "--status",
        default="open,unopened",
        help="Comma-separated market status filter(s): open,unopened,closed,settled (default: open,unopened)",
    )
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--json", action="store_true", help="Print full JSON records (one per line) instead of just tickers")
    args = ap.parse_args()

    access_key_id = _env_required("KALSHI_ACCESS_KEY_ID")
    private_key_path = _env_required("KALSHI_PRIVATE_KEY_PATH")

    base = "https://demo-api.kalshi.co" if args.env == "demo" else "https://api.elections.kalshi.com"
    path = "/trade-api/v2/markets"

    key = KalshiKey(access_key_id=access_key_id, private_key_path=private_key_path)

    prefix = args.prefix.lower().strip()
    statuses = [s.strip() for s in args.status.split(",") if s.strip()]
    cursor: str | None = None

    out: list[dict] = []

    # Kalshi API only supports ONE status filter per request, so we loop statuses.
    for st in statuses:
        cursor = None
        for _page in range(args.max_pages):
            params = {
                "limit": str(args.limit),
                "series_ticker": args.series_ticker,
                "status": st,
            }
            if cursor:
                params["cursor"] = cursor
            url = base + path + "?" + urllib.parse.urlencode(params)

            headers = rest_auth_headers(key, method="GET", path=path)
            data = _http_get_json(url, headers=headers)

            markets = data.get("markets", [])
            for m in markets:
                t = (m.get("ticker") or "").strip()
                if not t:
                    continue
                if prefix and (not t.lower().startswith(prefix)):
                    continue
                out.append(m)

            cursor = data.get("cursor")
            if not cursor:
                break

    # Sort for stable output
    out.sort(key=lambda m: (m.get("ticker") or ""))

    if args.json:
        for m in out:
            print(json.dumps(m, ensure_ascii=False))
    else:
        for m in out:
            print(m.get("ticker"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
