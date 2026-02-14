from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any


EventType = Literal[
    "EXTERNAL_PRICE",      # e.g. BTC spot/perp top-of-book mid
    "VENUE_BOOK",          # venue order book snapshot / update
    "VENUE_TRADE",         # venue prints
    "ORDER_SUBMIT",        # our orders (intent)
    "ORDER_ACK",           # venue ack
    "ORDER_FILL",          # fills/partials
    "ORDER_CANCEL",        # cancels
    "CONNECTION",          # connect/disconnect/reconnect
]


@dataclass(frozen=True)
class Event:
    ts_ms: int
    type: EventType
    payload: Dict[str, Any]


@dataclass(frozen=True)
class TopOfBook:
    ts_ms: int
    bid: float
    ask: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0


@dataclass(frozen=True)
class Fill:
    ts_ms: int
    order_id: str
    price: float
    qty: float
    fee: Optional[float] = None
