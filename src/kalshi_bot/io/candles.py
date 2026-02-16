from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover (py<3.9)
    from backports.zoneinfo import ZoneInfo  # type: ignore


NY_TZ = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class PriceTick:
    ts_ms: int
    mid: float
    provider: str
    symbol: str


@dataclass
class Candle5m:
    # candle_start is stored in UTC ms for stability; also emit local ISO for readability.
    candle_start_ms: int
    candle_start_local: str
    symbol: str

    open: float
    high: float
    low: float
    close: float

    # tick metadata
    ticks: int
    first_ts_ms: int
    last_ts_ms: int


def _floor_dt_to_5m(dt_local: datetime) -> datetime:
    # dt_local must be timezone-aware.
    minute = (dt_local.minute // 5) * 5
    return dt_local.replace(minute=minute, second=0, microsecond=0)


def candle_start_ms_utc(ts_ms: int, tz: ZoneInfo = NY_TZ) -> tuple[int, str]:
    """Return (candle_start_ms_utc, candle_start_local_iso) aligned to 5-min buckets in tz."""
    dt_utc = datetime.fromtimestamp(ts_ms / 1000.0, tz=ZoneInfo("UTC"))
    dt_local = dt_utc.astimezone(tz)
    start_local = _floor_dt_to_5m(dt_local)
    # Convert back to UTC for stable storage.
    start_utc = start_local.astimezone(ZoneInfo("UTC"))
    start_ms = int(start_utc.timestamp() * 1000)
    # Local label includes offset, which matters across DST.
    return start_ms, start_local.isoformat()


def parse_external_price_tick(line: str) -> Optional[PriceTick]:
    """Parse one JSONL line emitted by the external collectors.

    Expected shape:
      {"ts_ms": ..., "type": "EXTERNAL_PRICE", "payload": {"provider":...,"symbol":...,"mid":...}}

    Returns None for non-matching lines.
    """
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    if obj.get("type") != "EXTERNAL_PRICE":
        return None
    payload = obj.get("payload") or {}
    try:
        ts_ms = int(obj["ts_ms"])
        mid = float(payload["mid"])
        provider = str(payload.get("provider", ""))
        symbol = str(payload.get("symbol", ""))
    except (KeyError, TypeError, ValueError):
        return None

    return PriceTick(ts_ms=ts_ms, mid=mid, provider=provider, symbol=symbol)


def iter_ticks(paths: Iterable[Path]) -> Iterator[PriceTick]:
    for path in paths:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                tick = parse_external_price_tick(line)
                if tick is not None:
                    yield tick


def build_5m_candles(
    ticks: Iterable[PriceTick],
    tz: ZoneInfo = NY_TZ,
    symbol: str = "BTCUSDT",
) -> Iterator[Candle5m]:
    current: Optional[Candle5m] = None

    for t in ticks:
        if t.symbol and t.symbol != symbol:
            continue

        start_ms, start_local_iso = candle_start_ms_utc(t.ts_ms, tz=tz)

        if current is None or start_ms != current.candle_start_ms:
            if current is not None:
                yield current
            current = Candle5m(
                candle_start_ms=start_ms,
                candle_start_local=start_local_iso,
                symbol=symbol,
                open=t.mid,
                high=t.mid,
                low=t.mid,
                close=t.mid,
                ticks=1,
                first_ts_ms=t.ts_ms,
                last_ts_ms=t.ts_ms,
            )
            continue

        # update candle
        current.high = max(current.high, t.mid)
        current.low = min(current.low, t.mid)
        current.close = t.mid
        current.ticks += 1
        current.last_ts_ms = t.ts_ms

    if current is not None:
        yield current


def write_candles_jsonl(out_path: Path, candles: Iterable[Candle5m]) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    first_start: Optional[int] = None
    last_start: Optional[int] = None

    with out_path.open("w", encoding="utf-8") as f:
        for c in candles:
            n += 1
            if first_start is None:
                first_start = c.candle_start_ms
            last_start = c.candle_start_ms
            f.write(
                json.dumps(
                    {
                        "type": "CANDLE_5M",
                        "candle_start_ms": c.candle_start_ms,
                        "candle_start_local": c.candle_start_local,
                        "symbol": c.symbol,
                        "open": c.open,
                        "high": c.high,
                        "low": c.low,
                        "close": c.close,
                        "ticks": c.ticks,
                        "first_ts_ms": c.first_ts_ms,
                        "last_ts_ms": c.last_ts_ms,
                    },
                    separators=(",", ":"),
                )
                + "\n"
            )

    return {"out": str(out_path), "candles": n, "first": first_start, "last": last_start}
