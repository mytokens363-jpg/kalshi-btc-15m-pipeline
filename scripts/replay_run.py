#!/usr/bin/env python3
from __future__ import annotations

import argparse

from kalshi_bot.sim.replay import ReplayEngine, ReplayConfig
from kalshi_bot.strategy.mm_baseline import on_event


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", required=True, help="Path to JSONL events file")
    args = ap.parse_args()

    eng = ReplayEngine(ReplayConfig())
    st = eng.run(args.events, lambda ev, st: on_event(ev, st))
    print("Replay finished")
    print(f"fair_prob={st.fair_prob} inv_yes={st.inv_yes} pnl_usd={st.pnl_usd}")


if __name__ == "__main__":
    main()
