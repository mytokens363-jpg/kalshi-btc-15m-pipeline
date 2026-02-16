#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Test Kalshi REST auth against /trade-api/v2/portfolio/balance")
    ap.add_argument("--env", choices=["demo", "prod"], default="demo")
    args = ap.parse_args()

    access_key_id = _env_required("KALSHI_ACCESS_KEY_ID")
    private_key_path = _env_required("KALSHI_PRIVATE_KEY_PATH")

    base = "https://demo-api.kalshi.co" if args.env == "demo" else "https://api.elections.kalshi.com"
    path = "/trade-api/v2/portfolio/balance"
    url = base + path

    key = KalshiKey(access_key_id=access_key_id, private_key_path=private_key_path)
    headers = rest_auth_headers(key, method="GET", path=path)

    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print("HTTP", resp.status)
            try:
                print(json.dumps(json.loads(body), indent=2))
            except Exception:
                print(body)
            return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print("HTTP", e.code)
        print(body)
        return 2
    except Exception as e:
        print("ERROR", repr(e))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
