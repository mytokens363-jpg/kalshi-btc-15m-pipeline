from __future__ import annotations

"""Kalshi venue connector (skeleton).

Phase 0: define the minimal interface we need.

We intentionally do NOT implement auth here until you provide:
- which Kalshi API (REST + websocket?)
- how auth works (key + signature, OAuth, etc.)
- which market type (CLOB vs RFQ-like)
"""

import time
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any

from ..types import Event


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class KalshiConfig:
    env: str = "prod"  # or "demo" if they provide sandbox
    market_ticker: Optional[str] = None


class KalshiVenue:
    def __init__(self, cfg: KalshiConfig):
        self.cfg = cfg

    def run_marketdata(self, emit: Callable[[Event], None]) -> None:
        """Stream order book + trades, emitting VENUE_BOOK / VENUE_TRADE events."""
        raise NotImplementedError("Need Kalshi API details to implement")

    def submit_order(self, order: Dict[str, Any]) -> str:
        """Submit an order and return venue order id."""
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> None:
        raise NotImplementedError
