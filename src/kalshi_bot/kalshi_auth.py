from __future__ import annotations

import base64
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


@dataclass(frozen=True)
class KalshiKey:
    access_key_id: str  # KALSHI-ACCESS-KEY header (Key ID)
    private_key_path: str


def now_ms() -> int:
    return int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)


def load_private_key(path: str):
    p = Path(path).expanduser()
    data = p.read_bytes()
    return serialization.load_pem_private_key(data, password=None)


def sign_pss_sha256_b64(private_key: rsa.RSAPrivateKey, message: str) -> str:
    sig = private_key.sign(
        message.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(sig).decode("utf-8")


def rest_auth_headers(key: KalshiKey, method: str, path: str) -> Dict[str, str]:
    """Build Kalshi REST API auth headers.

    Docs: signature = sign( timestamp + METHOD + path_without_query ).
    Important: when signing, strip query params from `path`.
    """
    ts = str(now_ms())
    method_u = method.upper()
    path_no_q = path.split("?", 1)[0]
    msg = ts + method_u + path_no_q
    pk = load_private_key(key.private_key_path)
    sig = sign_pss_sha256_b64(pk, msg)
    return {
        "KALSHI-ACCESS-KEY": key.access_key_id,
        "KALSHI-ACCESS-SIGNATURE": sig,
        "KALSHI-ACCESS-TIMESTAMP": ts,
    }


def ws_auth_headers(key: KalshiKey, ws_path: str = "/trade-api/ws/v2") -> Dict[str, str]:
    """Build Kalshi websocket auth headers.

    Docs: timestamp + "GET" + ws_path, then RSA-PSS SHA256 sign, base64.
    """
    ts = str(now_ms())
    msg = ts + "GET" + ws_path
    pk = load_private_key(key.private_key_path)
    sig = sign_pss_sha256_b64(pk, msg)
    return {
        "KALSHI-ACCESS-KEY": key.access_key_id,
        "KALSHI-ACCESS-SIGNATURE": sig,
        "KALSHI-ACCESS-TIMESTAMP": ts,
    }
