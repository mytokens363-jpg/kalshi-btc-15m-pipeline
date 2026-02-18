#!/usr/bin/env python3
from __future__ import annotations

import argparse

from kalshi_bot.sim.replay import ReplayEngine, ReplayConfig
from kalshi_bot.sim.paper import PaperExecutor
from kalshi_bot.strategy.mm_baseline import decide_orders, MMConfig
from kalshi_bot.types import Event


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", required=True, help="Path to JSONL events file")
    args = ap.parse_args()

    eng = ReplayEngine(ReplayConfig())
    execu = PaperExecutor()
    cfg = MMConfig()

    def on_event(ev: Event, st):
        if ev.type == "VENUE_BOOK":
            execu.on_marketdata(ev)

        intents = decide_orders(ev, st, cfg)
        for intent in intents:
            execu.submit_intent(intent, st, emit=lambda e: None, ts_ms=ev.ts_ms)

    st = eng.run(args.events, on_event)
    print("Replay finished")
    print(f"fair_prob={st.fair_prob} inv_yes={st.inv_yes} pnl_usd={st.pnl_usd} open_orders={len(st.open_orders)}")


if __name__ == "__main__":
    main()
