"""The desktop host's minimum version — ADR-663 D3.

The desktop app is the website in a native window (D1): the page is always
current, and the only installed, versioned thing is the host around it. The page
names that host on every API request (`X-Yarnnn-Client: desktop/X.Y.Z`, the
shape of Claude Code's `claude-cli/X.Y.Z`), and this module refuses a host older
than `DESKTOP_MIN_VERSION` with 426 `desktop_update_required`, which the page
turns into a notice (`web/components/shell/UpdateNotice.tsx`).

A browser sends no header and is never refused. Raising the minimum is how a
host change that the website depends on is rolled out: ship the new host, then
raise this.

Per-feature minimums (Claude Code's `tengu_bridge_min_version` pattern) sit
beside the global one: a feature that needs a newer host names its own floor
and is simply not offered below it — the host is never refused for it.
`BROWSER_MIN_VERSION` (ADR-662 D15, the relay to the extension) is the first.
"""

from __future__ import annotations

import json
import re
from typing import Optional

DESKTOP_MIN_VERSION = "0.2.0"

#: ADR-662 D15 — the first host that relays the browser tools to the yarnnn
#: Chrome extension. 0.3.x carried the retired pane and is not offered them;
#: below this the app still works, without the browser.
BROWSER_MIN_VERSION = "0.4.0"

CLIENT_HEADER = b"x-yarnnn-client"

_DESKTOP = re.compile(r"^desktop/(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def _parse(version: str) -> tuple[int, int, int]:
    major, minor, patch = (int(p) for p in version.split(".")[:3])
    return major, minor, patch


def refuses(header: Optional[str]) -> bool:
    """True when the request comes from a desktop host below the minimum.

    No header → a browser → never refused. A `desktop/` header that does not
    parse is refused: it cannot be vouched for, and a real host always sends
    `desktop/X.Y.Z`.
    """
    if not header or not header.startswith("desktop/"):
        return False
    m = _DESKTOP.match(header.strip())
    if not m:
        return True
    return tuple(int(g) for g in m.groups()) < _parse(DESKTOP_MIN_VERSION)


_BODY = json.dumps({
    # The API's one error shape (`_error_body` in main.py).
    "error": {
        "code": "desktop_update_required",
        "message": "This version of the yarnnn desktop app is out of date.",
        "hint": {"min_version": DESKTOP_MIN_VERSION},
    }
}).encode()


def host_version(header: Optional[str]) -> Optional[tuple[int, int, int]]:
    """The desktop host's version from `X-Yarnnn-Client`, or None for a
    browser (no header) or a header that does not parse."""
    if not header:
        return None
    m = _DESKTOP.match(header.strip())
    return tuple(int(g) for g in m.groups()) if m else None  # type: ignore[return-value]


def host_meets(header: Optional[str], minimum: str) -> bool:
    """True when the request comes from a desktop host at or above `minimum` —
    the per-feature check. A browser never meets it."""
    version = host_version(header)
    return version is not None and version >= _parse(minimum)


class DesktopMinVersionMiddleware:
    """Pure ASGI, so streaming responses (lane turns) pass through untouched.

    Registered INSIDE the CORS middleware: a refusal must carry CORS headers,
    or the browser reports a network error and the page never sees the 426.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            raw = dict(scope.get("headers") or []).get(CLIENT_HEADER)
            if raw is not None and refuses(raw.decode("latin-1")):
                await send({
                    "type": "http.response.start",
                    "status": 426,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(_BODY)).encode()),
                    ],
                })
                await send({"type": "http.response.body", "body": _BODY})
                return
        await self.app(scope, receive, send)
