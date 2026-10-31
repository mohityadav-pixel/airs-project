"""One shared, pooled HTTP client for every upstream provider.

Opening a fresh client per request means a fresh DNS lookup and TCP/TLS
handshake every time. With 270 cities that is hundreds of lookups a minute,
and macOS's resolver starts answering "nodename nor servname provided" —
which looked like the internet going down. A pooled client reuses
connections, and a short retry rides out the occasional failed lookup.
"""
from __future__ import annotations

import threading
import time

import httpx

_client: httpx.Client | None = None
_lock = threading.Lock()


def client() -> httpx.Client:
    global _client
    with _lock:
        if _client is None or _client.is_closed:
            _client = httpx.Client(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10,
                                    keepalive_expiry=60.0),
                follow_redirects=True)
        return _client


def get(url: str, *, params: dict | None = None, headers: dict | None = None,
        timeout: float | None = None, retries: int = 2) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return client().get(url, params=params, headers=headers,
                                timeout=timeout if timeout else httpx.USE_CLIENT_DEFAULT)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout,
                httpx.RemoteProtocolError) as exc:
            last = exc
            time.sleep(0.6 * (attempt + 1))
    assert last is not None
    raise last
