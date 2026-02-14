from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Optional

from ..types import Event


class JsonlRecorder:
    """Append-only JSONL recorder.

    Writes one Event per line. Safe for large files and easy replay.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, ev: Event) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts_ms": ev.ts_ms, "type": ev.type, "payload": ev.payload}, ensure_ascii=False))
            f.write("\n")

    def extend(self, events: Iterable[Event]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps({"ts_ms": ev.ts_ms, "type": ev.type, "payload": ev.payload}, ensure_ascii=False))
                f.write("\n")


def read_jsonl(path: str | Path) -> list[Event]:
    p = Path(path)
    out: list[Event] = []
    if not p.exists():
        return out
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out.append(Event(ts_ms=int(obj["ts_ms"]), type=obj["type"], payload=obj.get("payload") or {}))
    out.sort(key=lambda e: e.ts_ms)
    return out
