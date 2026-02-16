from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

import websockets

from ..kalshi_auth import KalshiKey, ws_auth_headers


@dataclass(frozen=True)
class KalshiWsConfig:
    # Production: api.elections.kalshi.com
    # Demo: demo-api.kalshi.co
    ws_host: str
    ws_path: str = "/trade-api/ws/v2"
    use_tls: bool = True

    # subscriptions
    channels: tuple[str, ...] = ("ticker", "trade")
    market_tickers: tuple[str, ...] = ()

    # ops
    ping_interval_sec: float = 20.0  # client-side keepalive (server also pings)
    reconnect_backoff_sec: float = 2.0
    max_reconnect_backoff_sec: float = 30.0


def _ws_url(cfg: KalshiWsConfig) -> str:
    scheme = "wss" if cfg.use_tls else "ws"
    return f"{scheme}://{cfg.ws_host}{cfg.ws_path}"


def _subscribe_frame(cfg: KalshiWsConfig) -> dict:
    # AsyncAPI indicates `cmd` + `params`.
    params: dict = {"channels": list(cfg.channels)}
    if cfg.market_tickers:
        params["market_tickers"] = list(cfg.market_tickers)
    return {"cmd": "subscribe", "params": params}


async def run_kalshi_ws_marketdata(
    cfg: KalshiWsConfig,
    key: KalshiKey,
    emit: Callable[[dict], None],
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """Connect to Kalshi WS v2, subscribe to channels, and emit raw JSON messages.

    Emits dicts shaped like:
      {"ts_ms":..., "type":"KALSHI_WS", "payload": {"channel":..., ...raw...}}

    This is read-only marketdata wiring.
    """

    url = _ws_url(cfg)
    backoff = cfg.reconnect_backoff_sec

    while True:
        if stop_event is not None and stop_event.is_set():
            return

        headers = ws_auth_headers(key, ws_path=cfg.ws_path)

        try:
            # websockets>=16 uses additional_headers (extra_headers was removed)
            async with websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=cfg.ping_interval_sec,
                ping_timeout=cfg.ping_interval_sec,
                close_timeout=5,
                max_queue=1000,
            ) as ws:
                # subscribe
                await ws.send(json.dumps(_subscribe_frame(cfg), separators=(",", ":")))

                async for msg in ws:
                    if stop_event is not None and stop_event.is_set():
                        return

                    ts_ms = int(time.time() * 1000)
                    try:
                        obj = json.loads(msg)
                    except json.JSONDecodeError:
                        obj = {"raw": msg}

                    emit({"ts_ms": ts_ms, "type": "KALSHI_WS", "payload": obj})

            backoff = cfg.reconnect_backoff_sec

        except Exception as e:
            emit({
                "ts_ms": int(time.time() * 1000),
                "type": "KALSHI_WS_ERROR",
                "payload": {"error": repr(e), "url": url},
            })
            await asyncio.sleep(backoff)
            backoff = min(cfg.max_reconnect_backoff_sec, backoff * 1.5)
