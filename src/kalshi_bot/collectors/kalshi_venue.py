from __future__ import annotations

"""Kalshi venue connector.

Implements:
- Marketdata via WS v2 (kalshi_ws_marketdata)
- Orders via REST v2 (portfolio/orders)

This stays intentionally "thin": it emits generic VENUE_* events and returns raw
IDs/responses so the strategy layer can evolve without constant refactors.

Defaults to demo for safety.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from ..kalshi_auth import KalshiKey
from ..types import Event
from .kalshi_rest import KalshiRestConfig, delete_json, post_json
from .kalshi_ws_marketdata import KalshiWsConfig, run_kalshi_ws_marketdata


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class KalshiConfig:
    env: str = "demo"  # demo|prod

    # marketdata
    ws_host: str = "demo-api.kalshi.co"
    ws_path: str = "/trade-api/ws/v2"
    use_tls: bool = True
    market_tickers: tuple[str, ...] = ()
    channels: tuple[str, ...] = ("ticker", "trade")

    # orders
    rest_timeout_sec: float = 20.0


class KalshiVenue:
    def __init__(self, cfg: KalshiConfig, key: Optional[KalshiKey] = None):
        self.cfg = cfg
        self.key = key
        self.rest_cfg = KalshiRestConfig(env=cfg.env, timeout_sec=cfg.rest_timeout_sec)

    async def run_marketdata(self, emit: Callable[[Event], None], stop_event: Optional[asyncio.Event] = None) -> None:
        """Stream marketdata and emit VENUE_BOOK/VENUE_TRADE/CONNECTION.

        The WS collector emits raw Kalshi messages; we translate the common channels.
        Anything unknown is forwarded as VENUE_BOOK (raw) so we don't drop data.
        """

        ws_cfg = KalshiWsConfig(
            ws_host=self.cfg.ws_host,
            ws_path=self.cfg.ws_path,
            use_tls=self.cfg.use_tls,
            channels=self.cfg.channels,
            market_tickers=self.cfg.market_tickers,
        )

        def _on_raw(msg: dict) -> None:
            ts = msg.get("ts_ms") or now_ms()
            typ = msg.get("type")
            payload = msg.get("payload") or {}

            if typ == "KALSHI_WS_ERROR":
                emit(Event(ts_ms=int(ts), type="CONNECTION", payload={"status": "error", **payload}))
                return

            if typ != "KALSHI_WS":
                emit(Event(ts_ms=int(ts), type="CONNECTION", payload={"status": "unknown", "raw": msg}))
                return

            ch = payload.get("channel") or payload.get("type")
            # Kalshi v2 messages are not perfectly consistent across channels.
            # We preserve raw payload in every event.
            if ch in ("trade", "trades"):
                emit(Event(ts_ms=int(ts), type="VENUE_TRADE", payload={"raw": payload}))
            elif ch in ("orderbook", "book", "ticker"):
                emit(Event(ts_ms=int(ts), type="VENUE_BOOK", payload={"raw": payload}))
            else:
                emit(Event(ts_ms=int(ts), type="VENUE_BOOK", payload={"raw": payload}))

        await run_kalshi_ws_marketdata(ws_cfg, self.key, emit=lambda raw: _on_raw(raw), stop_event=stop_event)

    def submit_order(self, order: Dict[str, Any]) -> str:
        """Submit an order; returns venue order id.

        Uses (commonly referenced) endpoint:
          POST /trade-api/v2/portfolio/orders

        The exact schema can vary; we pass through the dict as JSON.
        """
        path = "/trade-api/v2/portfolio/orders"
        data = post_json(cfg=self.rest_cfg, key=self.key, path=path, body=order)
        # Most responses contain order_id; fall back to raw.
        oid = data.get("order_id") or data.get("id") or data.get("order", {}).get("order_id")
        if not oid:
            raise RuntimeError(f"Missing order id in response: {data}")
        return str(oid)

    def cancel_order(self, order_id: str) -> None:
        """Cancel an order.

        Common patterns in Kalshi:
          DELETE /trade-api/v2/portfolio/orders/{order_id}

        If this endpoint differs, adjust here.
        """
        path = f"/trade-api/v2/portfolio/orders/{order_id}"
        delete_json(cfg=self.rest_cfg, key=self.key, path=path)
