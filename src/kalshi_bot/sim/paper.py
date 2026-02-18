from __future__ import annotations

"""Paper/sim execution engine.

This converts strategy ORDER_SUBMIT intents into simulated acks/fills.

For now we implement a very naive fill model:
- If intent is a BUY at price >= current best ask (if known) -> fill.
- If intent is a SELL at price <= current best bid -> fill.
- Otherwise leave as open.

If no best bid/ask are known from marketdata, we do not fill.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional

from ..types import Event
from ..state import BotState


@dataclass
class PaperConfig:
    fill_on_cross: bool = True


class PaperExecutor:
    def __init__(self, cfg: PaperConfig = PaperConfig()):
        self.cfg = cfg
        self.best_bid: Optional[int] = None
        self.best_ask: Optional[int] = None
        self._next_id = 1

    def on_marketdata(self, ev: Event) -> None:
        # Attempt to parse best bid/ask from raw venue payload.
        raw = (ev.payload or {}).get("raw") if isinstance(ev.payload, dict) else None
        if not isinstance(raw, dict):
            return

        # Heuristic: some messages include bid/ask fields in cents.
        for k_bid, k_ask in (("bid", "ask"), ("best_bid", "best_ask"), ("yes_bid", "yes_ask")):
            if k_bid in raw and k_ask in raw:
                try:
                    self.best_bid = int(raw[k_bid])
                    self.best_ask = int(raw[k_ask])
                    return
                except Exception:
                    pass

    def submit_intent(self, intent: Dict[str, Any], st: BotState, emit: Callable[[Event], None], ts_ms: int) -> str:
        oid = f"paper:{self._next_id}"
        self._next_id += 1

        st.open_orders[oid] = dict(intent)
        emit(Event(ts_ms=ts_ms, type="ORDER_ACK", payload={"order_id": oid, "intent": intent}))

        if not self.cfg.fill_on_cross:
            return oid

        side = intent.get("side")
        price = int(intent.get("price"))
        qty = float(intent.get("qty", 0))

        crossed = False
        if self.best_bid is not None and self.best_ask is not None:
            if side == "buy" and price >= self.best_ask:
                crossed = True
            if side == "sell" and price <= self.best_bid:
                crossed = True

        if crossed:
            # fill immediately
            st.open_orders.pop(oid, None)
            emit(Event(ts_ms=ts_ms, type="ORDER_FILL", payload={"order_id": oid, "price": price, "qty": qty}))

        return oid
