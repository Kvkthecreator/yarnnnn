"""What a browser sees at the connector URL.

The protocol is served at the root (ADR-370 Slice 2), so `https://mcp.yarnnn.com`
is both the URL a member pastes into a connector AND a link on /developers.
Every unauthenticated request to `/` answered 401 JSON — correct for an MCP
client (the 401 + `WWW-Authenticate` is how it discovers OAuth), wrong for a
person who clicked the link (`{"error": "invalid_token"}`) and for a crawler
(Search Console, 2026-09-24: "Blocked due to unauthorized request (401)").

This middleware answers ONLY a browser's page load — GET/HEAD on `/`, no
`Authorization`, an `Accept` naming `text/html` and not `text/event-stream` —
with a short noindex page saying what the URL is for. An MCP client never sends
that shape (the spec has it POST JSON-RPC, or GET with `text/event-stream`), so
every protocol and OAuth path is untouched and still reaches the SDK.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

CONNECTOR_URL = "https://mcp.yarnnn.com"
DEVELOPERS_URL = "https://www.yarnnn.com/developers"

_PAGE = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>yarnnn MCP connector</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0; font: 16px/1.6 system-ui, -apple-system, sans-serif;
         background: #0f1419; color: #e6e6e6; }}
  main {{ max-width: 34rem; margin: 18vh auto; padding: 0 16px; }}
  h1 {{ font-size: 1.4rem; font-weight: 500; margin: 0 0 1rem; }}
  p {{ color: #a0a4a8; }}
  code {{ color: #e6e6e6; font-size: .95em; }}
  a {{ color: #de5a2b; }}
</style>
</head>
<body>
<main>
<h1>This is yarnnn's MCP connector.</h1>
<p>It's an address for your AI assistant, not a page to browse. In Claude,
ChatGPT or any MCP client, add a custom connector with the URL
<code>{CONNECTOR_URL}</code> and sign in with your yarnnn account.</p>
<p><a href="{DEVELOPERS_URL}">Connection steps and developer docs</a></p>
</main>
</body>
</html>
""".encode()


def _header(scope: Scope, name: bytes) -> str:
    for key, value in scope.get("headers") or []:
        if key.lower() == name:
            return value.decode("latin-1")
    return ""


def is_browser_page_load(scope: Scope) -> bool:
    if scope.get("type") != "http" or scope.get("path") != "/":
        return False
    if scope.get("method") not in ("GET", "HEAD"):
        return False
    if _header(scope, b"authorization"):
        return False
    accept = _header(scope, b"accept").lower()
    return "text/html" in accept and "text/event-stream" not in accept


class BrowserDoorMiddleware:
    """Serve the explainer page to a browser at `/`; pass everything else through."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not is_browser_page_load(scope):
            await self.app(scope, receive, send)
            return
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/html; charset=utf-8"),
                (b"content-length", str(len(_PAGE)).encode()),
                (b"x-robots-tag", b"noindex"),
                (b"cache-control", b"no-store"),
                (b"vary", b"Accept, Authorization"),
            ],
        })
        body = b"" if scope["method"] == "HEAD" else _PAGE
        await send({"type": "http.response.body", "body": body})
