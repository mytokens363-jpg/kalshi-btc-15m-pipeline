#!/usr/bin/env python3
from __future__ import annotations

"""Collector runner (stub).

When venue + external price collectors are implemented, this will:
- connect to both
- record unified Event stream to state/recordings/<date>.jsonl
"""

import argparse
import datetime as dt

from kalshi_bot.io.recorder import JsonlRecorder


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out = args.out or f"state/recordings/{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    rec = JsonlRecorder(out)
    print(f"Recording to: {out}")
    print("Collectors not implemented yet. This is a placeholder.")


if __name__ == "__main__":
    main()
