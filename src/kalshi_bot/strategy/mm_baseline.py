from __future__ import annotations

"""Baseline market-making strategy (skeleton).

Phase 1: implement inventory-aware quoting once venue is wired.
For now, we only compute a placeholder fair probability.
"""

from dataclasses import dataclass
from typing import List, Dict, Any

from ..types import Event
from ..state import BotState


@dataclass
class MMConfig:
    base_fair: float = 0.50

    # very simple quoting params (YES contract in cents)
    edge_cents: int = 2
    size: int = 1


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def decide_orders(ev: Event, st: BotState, cfg: MMConfig) -> List[Dict[str, Any]]:
    """Return ORDER_SUBMIT intents (paper/sim).

    This is intentionally simple: quote around fair_prob whenever we see a venue book.
    """
    if st.fair_prob is None:
        st.fair_prob = cfg.base_fair

    if ev.type == "EXTERNAL_PRICE":
        # TODO: derive fair_prob from BTC move / momentum.
        return []

    if ev.type != "VENUE_BOOK":
        return []

    fair_cents = int(round(_clamp(st.fair_prob, 0.01, 0.99) * 100))
    bid = max(1, fair_cents - cfg.edge_cents)
    ask = min(99, fair_cents + cfg.edge_cents)

    return [
        {"side": "buy", "price": bid, "qty": cfg.size, "contract": "YES"},
        {"side": "sell", "price": ask, "qty": cfg.size, "contract": "YES"},
    ]


def on_event(ev: Event, st: BotState, cfg: MMConfig = MMConfig()) -> None:
    """Backward-compatible handler used by old scripts.

    Side-effect: updates st.fair_prob, may append order intents to st.open_orders.
    """
    intents = decide_orders(ev, st, cfg)
    for i, intent in enumerate(intents):
        st.open_orders[f"intent:{ev.ts_ms}:{i}"] = intent
