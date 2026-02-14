from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class BotState:
    # inventory in YES contracts (positive=long YES)
    inv_yes: float = 0.0

    # cash PnL in USD (sim)
    pnl_usd: float = 0.0

    # last known fair probability (0..1)
    fair_prob: Optional[float] = None

    # outstanding orders (sim)
    open_orders: Dict[str, dict] = field(default_factory=dict)
