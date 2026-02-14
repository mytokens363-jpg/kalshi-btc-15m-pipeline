from __future__ import annotations

"""Coinbase BTC-USD top-of-book collector (skeleton).

Phase 0: define a collector interface and message format.

Implementation note:
- We'll use Coinbase Advanced Trade websocket feed when you confirm the exact endpoint + auth needs.
- For now, this file contains a stub that can be filled in quickly.
"""

import time
from dataclasses import dataclass
from typing import Callable, Optional

from ..types import Event


@dataclass
class CoinbaseConfig:
    product_id: str = "BTC-USD"


def now_ms() -> int:
    return int(time.time() * 1000)


class CoinbaseTopOfBookCollector:
    def __init__(self, cfg: CoinbaseConfig):
        self.cfg = cfg

    def run(self, emit: Callable[[Event], None]) -> None:
        """Run forever and call emit(Event(...)) for each update.

        TODO: implement websocket connection + reconnect + heartbeat.
        """
        raise NotImplementedError("Collector not implemented yet; needs websocket endpoint + auth decision")
