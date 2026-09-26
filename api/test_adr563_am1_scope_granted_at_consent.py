"""ADR-563 Amendment 1 — the MCP scope is granted at consent, never defaulted.

ADR-563 made the tiers real, but two defaults decided the grant instead of the
operator:

- the SDK registered every client at `files:read`, and it refuses an authorize
  request above the registered scope — so ChatGPT, which asks for exactly what
  it registered with, could never be granted write, however often it reconnected;
- a missing scope fell to `"read"` — the legacy full-access grant — so Claude,
  which asks for nothing, got delete and share on every new connection.

This gate DRIVES the path rather than reading it: the real MCP server app
(`/register`, `/authorize`, `/token`) and the real API consent router
(`/api/mcp/oauth-consent`, `/api/mcp/oauth-callback`) run in one process over
one in-memory stand-in for the service tables, so a code minted by the MCP
server is the code the API binds and the token endpoint exchanges.

Run with the MCP venv: `.venv-mcp/bin/python test_adr563_am1_scope_granted_at_consent.py`
(it re-execs itself there when started under an interpreter without the `mcp`
SDK). Script-shaped: it prints a count, and exits non-zero on any failure.
"""

import base64
import hashlib
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MCP_PY = os.path.join(HERE, ".venv-mcp", "bin", "python")

try:
    import mcp  # noqa: F401
except ModuleNotFoundError:
    if os.path.exists(MCP_PY) and os.path.realpath(sys.executable) != os.path.realpath(MCP_PY):
        os.execv(MCP_PY, [MCP_PY, os.path.abspath(__file__)])
    print("ADR-563 am.1 gate: 0/1 passed — the mcp SDK is not importable; nothing was driven")
    sys.exit(1)

os.chdir(HERE)
sys.path.insert(0, HERE)
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "gate")
os.environ.setdefault("MCP_SERVER_URL", "https://mcp.example.com")

FAILURES: list = []
RUN = 0


def _check(label, cond):
    global RUN
    RUN += 1
    if cond:
        logging.info("✓ %s", label)
    else:
        logging.error("✗ %s", label)
        FAILURES.append(label)
    return bool(cond)


# ── One in-memory stand-in for the service tables, shared by both services ──

class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table):
        self.db, self.table, self.filters = db, table, []
        self.op, self.payload = "select", None

    def select(self, *_a, **_k):
        return self

    def insert(self, row):
        self.op, self.payload = "insert", dict(row)
        return self

    def update(self, patch):
        self.op, self.payload = "update", dict(patch)
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, _n):
        return self

    def _match(self, row):
        return all(row.get(k) == v for k, v in self.filters)

    def execute(self):
        rows = self.db.setdefault(self.table, [])
        if self.op == "insert":
            rows.append(self.payload)
            return _Result([self.payload])
        hit = [r for r in rows if self._match(r)]
        if self.op == "update":
            for r in hit:
                r.update(self.payload)
        elif self.op == "delete":
            self.db[self.table] = [r for r in rows if not self._match(r)]
        return _Result(hit)


class _Service:
    def __init__(self):
        self.db = {}

    def table(self, name):
        return _Query(self.db, name)


class _Member:
    user_id = "00000000-0000-0000-0000-00000000a563"
    email = "gate@example.com"


def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    svc = _Service()

    # The MCP server's provider and the API route both reach the service client;
    # both get the SAME stand-in, so the path is one path.
    from mcp_server import oauth_provider
    oauth_provider.YarnnnOAuthProvider._client = lambda self: svc
    oauth_provider._ensure_foreign_llm_grant = lambda *a, **k: None

    import routes.mcp as consent_routes
    consent_routes.get_service_client = lambda: svc
    import services.supabase as supa
    supa.resolve_workspace_for_principal = lambda _uid: None

    from fastapi import FastAPI
    from starlette.testclient import TestClient
    from mcp_server.server import mcp as mcp_app
    from services.mcp_scopes import GRANTABLE_TIERS, DEFAULT_GRANT, REGISTRATION_SCOPES

    mcp_client = TestClient(mcp_app.streamable_http_app())
    api = FastAPI()
    api.include_router(consent_routes.router, prefix="/api/mcp")
    api.dependency_overrides[supa.get_user_client] = lambda: _Member()
    api_client = TestClient(api)

    verifier = "v" * 50
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    redirect = "https://chatgpt.com/connector/oauth/cb"

    def register():
        r = mcp_client.post("/register", json={
            "client_name": "ChatGPT", "redirect_uris": [redirect],
            "token_endpoint_auth_method": "none",
        })
        return r

    def authorize(client_id, scope=None):
        params = {
            "response_type": "code", "client_id": client_id, "redirect_uri": redirect,
            "code_challenge": challenge, "code_challenge_method": "S256", "state": "st",
        }
        if scope is not None:
            params["scope"] = scope
        r = mcp_client.get("/authorize", params=params, follow_redirects=False)
        loc = r.headers.get("location", "")
        code = loc.split("code=", 1)[1].split("&", 1)[0] if "/mcp/authorize?code=" in loc else None
        return r, loc, code

    def exchange(client_id, code):
        return mcp_client.post("/token", data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect,
            "client_id": client_id, "code_verifier": verifier,
        })

    def code_row(code):
        return next((r for r in svc.db.get("mcp_oauth_codes", []) if r["code"] == code), None)

    # ── A. Registration is a ceiling ────────────────────────────────────────
    r = register()
    client_id = r.json().get("client_id") if r.status_code == 201 else None
    _check(
        "A. a client registering with no scope is registered for every grantable tier",
        r.status_code == 201
        and sorted(r.json().get("scope", "").split()) == sorted(GRANTABLE_TIERS),
    )
    _check(
        "A. the ceiling is exactly the grantable tiers — the legacy `read` is not offered",
        REGISTRATION_SCOPES == GRANTABLE_TIERS and "read" not in GRANTABLE_TIERS,
    )

    # ── B. A client asking above the old default reaches consent ────────────
    # This is the ChatGPT defect: registered at files:read, the SDK answered a
    # request for files:write with error=invalid_scope and never reached consent.
    r, loc, code = authorize(client_id, "files:write")
    _check(
        "B. /authorize for files:write redirects to the consent screen, not invalid_scope",
        r.status_code == 302 and code is not None and "invalid_scope" not in loc,
    )
    row = code_row(code) or {}
    _check(
        "B. the pending code carries NO scope — the bind is its one writer",
        code is not None and row.get("scope") is None,
    )

    # ── C. Consent offers the choice, preselecting write ────────────────────
    r = api_client.get("/api/mcp/oauth-consent", params={"code": code})
    body = r.json() if r.status_code == 200 else {}
    tiers = [t.get("scope") for t in body.get("tiers", [])]
    _check(
        "C. the consent screen offers exactly the grantable tiers, weakest first",
        tiers == GRANTABLE_TIERS,
    )
    _check(
        "C. write is preselected",
        body.get("default_scope") == DEFAULT_GRANT == "files:write",
    )
    grants = {t["scope"]: t.get("grants", []) for t in body.get("tiers", [])}
    _check(
        "C. each tier's sentences nest (read ⊂ write ⊂ share)",
        len(grants) == 3
        and set(grants["files:read"]) < set(grants["files:write"]) < set(grants["files:share"]),
    )

    # ── D. The bind writes what the operator chose, and only a tier ─────────
    r = api_client.post("/api/mcp/oauth-callback", params={"code": code, "scope": "read"})
    _check(
        "D. binding the legacy `read` is refused (honoured on old tokens, never minted)",
        r.status_code == 400 and (code_row(code) or {}).get("user_id") is None,
    )
    r = api_client.post("/api/mcp/oauth-callback", params={"code": code, "scope": "files:write"})
    row = code_row(code) or {}
    _check(
        "D. the bind writes the chosen tier onto the code",
        r.status_code == 200 and row.get("scope") == "files:write"
        and row.get("user_id") == _Member.user_id,
    )

    # ── E. The token carries the granted tier ───────────────────────────────
    r = exchange(client_id, code)
    tok = r.json() if r.status_code == 200 else {}
    stored = [t for t in svc.db.get("mcp_oauth_access_tokens", []) if t.get("client_id") == client_id]
    _check(
        "E. the exchanged token carries files:write — the ChatGPT connection can save",
        r.status_code == 200 and tok.get("scope") == "files:write"
        and len(stored) == 1 and stored[0].get("scopes") == ["files:write"],
    )

    # ── F. A client asking for nothing gets the operator's pick, not `read` ─
    # This is the Claude defect: no scope at /authorize became legacy full access.
    r, loc, code2 = authorize(client_id)
    api_client.post("/api/mcp/oauth-callback", params={"code": code2})
    r = exchange(client_id, code2)
    _check(
        "F. no requested scope + no pick → the preselected tier, never legacy `read`",
        r.status_code == 200 and r.json().get("scope") == DEFAULT_GRANT,
    )

    # ── G. A bound code with no granted scope is refused, never guessed ─────
    _r, _loc, code3 = authorize(client_id, "files:read")
    for row in svc.db.get("mcp_oauth_codes", []):
        if row["code"] == code3:
            row["user_id"] = _Member.user_id  # bound by something that chose nothing
    r = exchange(client_id, code3)
    _check(
        "G. a bound code carrying no scope does not exchange",
        r.status_code == 400,
    )

    print(
        f"\nADR-563 am.1 scope-granted-at-consent gate: "
        f"{RUN - len(FAILURES)}/{RUN} passed, {len(FAILURES)} failed"
    )
    for f in FAILURES:
        print(f"  ✗ {f}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(run())
