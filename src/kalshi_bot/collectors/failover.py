from __future__ import annotations

"""Simple failover helper.

Phase 0: choose provider priority order.
"""

from dataclasses import dataclass
from typing import Literal


Provider = Literal["binance", "coinbase"]


@dataclass(frozen=True)
class FailoverConfig:
    primary: Provider = "binance"
    fallback: Provider = "coinbase"
