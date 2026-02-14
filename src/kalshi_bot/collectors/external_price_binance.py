from __future__ import annotations

"""Binance BTCUSDT top-of-book collector.

Priority feed for external price reference.

Uses Binance Futures bookTicker stream (very high update rate):
- wss://fstream.binance.com/ws/btcusdt@bookTicker

Message example:
{
  "u": 400900217,
  "s": "BTCUSDT",
  "b": "50208.69000000",
  "B": "0.36900000",
  "a": "50208.70000000",
  "A": "0.17800000"
}

We record EXTERNAL_PRICE events with bid/ask/mid.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Callable, Optional

import websockets

from ..types import Event


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class BinanceConfig:
    symbol: str = "btcusdt"
    stream: str = "bookTicker"
    url: str = "wss://fstream.binance.com/ws"

    @property
    def ws_url(self) -> str:
        return f"{self.url}/{self.symbol}@{self.stream}"


class BinanceTopOfBookCollector:
    def __init__(self, cfg: BinanceConfig):
        self.cfg = cfg

    async def run(self, emit: Callable[[Event], None]) -> None:
        url = self.cfg.ws_url
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    backoff = 1.0
                    async for msg in ws:
                        try:
                            data = json.loads(msg)
                            bid = float(data.get("b"))
                            ask = float(data.get("a"))
                            if bid <= 0 or ask <= 0:
                                continue
                            ev = Event(
                                ts_ms=now_ms(),
                                type="EXTERNAL_PRICE",
                                payload={
                                    "provider": "binance",
                                    "symbol": data.get("s"),
                                    "bid": bid,
                                    "ask": ask,
                                    "mid": (bid + ask) / 2.0,
                                },
                            )
                            emit(ev)
                        except Exception:
                            continue
            except Exception:
                # Reconnect with capped exponential backoff
                await asyncio.sleep(min(30.0, backoff))
                backoff = min(30.0, backoff * 1.8)
