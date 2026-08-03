"""Lightweight in-process rate limiting for the MCP auth surface.

Security audit (2026-08-03): the MCP OAuth endpoints (/token, /register,
/authorize) and the static-bearer check had NO rate limiting. That allowed
online guessing against MCP_BEARER_TOKEN (operator-chosen, entropy not
guaranteed) and unbounded row-spam into mcp_oauth_clients via the unauthenticated
/register.

Design: a fixed-window counter per (client-ip, path-bucket), held in process
memory. No Redis, no new dependency — consistent with YARNNN's all-inline
architecture (ADR-083). The MCP server is a single Render web service, so a
per-process limiter is sufficient; it is a throttle against abuse, not a
distributed quota. Fails OPEN on internal error (never blocks a legitimate
request because the limiter itself broke) but closed against the flood.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

# Per-path-bucket limits: (max requests, window seconds). Auth paths are tight;
# everything else is ungated here (the protocol itself is bearer-gated upstream).
_LIMITS: dict[str, tuple[int, int]] = {
    "/token": (30, 60),        # token exchange + refresh
    "/register": (10, 300),    # dynamic client registration (unauthenticated)
    "/authorize": (30, 60),    # authorization requests
}


def _bucket_for(path: str) -> str | None:
    for prefix in _LIMITS:
        if path == prefix or path.startswith(prefix + "/"):
            return prefix
    return None


class _FixedWindow:
    """(count, window_start) per key, pruned lazily on access."""

    def __init__(self) -> None:
        self._data: dict[str, list] = defaultdict(lambda: [0, 0.0])
        self._lock = Lock()

    def hit(self, key: str, limit: int, window: int, now: float) -> bool:
        """Return True if allowed, False if the window is exhausted."""
        with self._lock:
            entry = self._data[key]
            count, start = entry
            if now - start >= window:
                entry[0], entry[1] = 1, now
                return True
            if count >= limit:
                return False
            entry[0] = count + 1
            return True


class AuthRateLimitMiddleware:
    """ASGI middleware throttling the OAuth auth paths by client IP."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._window = _FixedWindow()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            path = scope.get("path", "")
            bucket = _bucket_for(path)
            if bucket is not None:
                limit, window = _LIMITS[bucket]
                client = scope.get("client")
                ip = client[0] if client else "unknown"
                key = f"{ip}:{bucket}"
                if not self._window.hit(key, limit, window, time.monotonic()):
                    response = JSONResponse(
                        {"error": "rate_limited", "detail": "Too many requests. Slow down."},
                        status_code=429,
                        headers={"Retry-After": str(window)},
                    )
                    await response(scope, receive, send)
                    return
        except Exception:
            # Fail open: a broken limiter must never take down the auth surface.
            pass

        await self.app(scope, receive, send)
