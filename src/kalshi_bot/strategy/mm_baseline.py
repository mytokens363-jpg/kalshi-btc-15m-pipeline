from __future__ import annotations

"""Baseline market-making strategy (skeleton).

Phase 1: implement inventory-aware quoting once venue is wired.
For now, we only compute a placeholder fair probability.
"""

from dataclasses import dataclass
from typing import Optional

from ..types import Event
from ..state import BotState


@dataclass
class MMConfig:
    base_fair: float = 0.50


def on_event(ev: Event, st: BotState, cfg: MMConfig = MMConfig()) -> None:
    # Placeholder: set fair prob from external price move logic later.
    if st.fair_prob is None:
        st.fair_prob = cfg.base_fair

    if ev.type == "EXTERNAL_PRICE":
        # TODO: compute short-horizon drift/imbalance -> fair_prob adjustment.
        pass

    # TODO: if venue book update, decide quotes (bid/ask) and create ORDER_SUBMIT intents.
