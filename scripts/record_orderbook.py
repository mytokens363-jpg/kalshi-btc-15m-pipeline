#!/usr/bin/env python3
"""Record live Kalshi KXBTC15M orderbook snapshots to JSONL for backtesting.

Runs continuously, polls every 30s, writes to data/ob_YYYY-MM-DD.jsonl
"""
from __future__ import annotations

import json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kalshi_bot.kalshi_auth import KalshiKey
from kalshi_bot.collectors.kalshi_rest import KalshiRestConfig, get_json
from kalshi_bot.paper_mm import pick_active_market

KEY_ID   = "ca30aa24-7fbb-4f8c-abbe-2bbc6d6bc48c"
KEY_PATH = "/root/.secrets/kalshi_prod.pem"
INTERVAL = 30  # seconds


def day_key() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def main() -> None:
    key = KalshiKey(access_key_id=KEY_ID, private_key_path=KEY_PATH)
    cfg = KalshiRestConfig(env="prod")
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(exist_ok=True)

    print(f"[recorder] Starting — polling every {INTERVAL}s")
    while True:
        try:
            market = pick_active_market(cfg, key, min_minutes_to_close=0)
            if not market:
                print("[recorder] No active market — sleeping 60s")
                time.sleep(60)
                continue

            ob = get_json(cfg=cfg, key=key, path=f"/trade-api/v2/markets/{market}/orderbook")
            record = {
                "ts": int(time.time()),
                "market_ticker": market,
                "orderbook": ob.get("orderbook", {}),
            }

            out = data_dir / f"ob_{day_key()}.jsonl"
            with open(out, "a") as f:
                f.write(json.dumps(record) + "\n")

            print(f"[recorder] {market} snapshot saved → {out.name}")
        except Exception as e:
            print(f"[recorder] Error: {e}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
