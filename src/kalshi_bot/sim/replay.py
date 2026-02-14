from __future__ import annotations

"""Replay engine skeleton.

Loads recorded JSONL events and replays them in timestamp order.

Strategy can subscribe to events and emit simulated orders.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from ..types import Event
from ..state import BotState
from ..io.recorder import read_jsonl


@dataclass
class ReplayConfig:
    speed: float = 50.0  # higher = faster-than-real-time


class ReplayEngine:
    def __init__(self, cfg: ReplayConfig):
        self.cfg = cfg

    def run(self, path: str, on_event: Callable[[Event, BotState], None]) -> BotState:
        events = read_jsonl(path)
        st = BotState()
        for ev in events:
            on_event(ev, st)
        return st
