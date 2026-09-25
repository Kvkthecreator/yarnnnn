"""ADR-669 — the database transport is bounded: HTTP/1.1, one socket per
request, fifteen seconds per call, one builder for every client.

Run: cd api && python3 test_adr669_the_database_transport_is_bounded.py

Script-shaped (the house form): prints each check, a count, exits 1 on any
failure. The stall arm is DRIVEN: a local socket that accepts and never
answers, and the bounded client giving up on it in words the once-retry
recognises. The rest reads the built client and the source.
"""

from __future__ import annotations

import os
import re
import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-placeholder")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "service-placeholder")

import httpx  # noqa: E402

from services import supabase as S  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {('— ' + detail) if detail else ''}")


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


SRC = read("api/services/supabase.py")

# ═════════════════════════════════════════════════════════════════════════════
print("D1 one builder — every client in every service passes client_options()")
# ═════════════════════════════════════════════════════════════════════════════
_deployed = [
    p for tree in ("api/services", "api/routes", "api/jobs", "api/mcp_server")
    for p in (ROOT / tree).rglob("*.py")
] + [ROOT / "api/main.py"]
_bare: list[str] = []
_opts_outside: list[str] = []


def _call_args(src: str, start: int) -> str:
    """The balanced argument text of the call whose '(' is at `start`."""
    depth, i = 0, start
    while i < len(src):
        if src[i] == "(":
            depth += 1
        elif src[i] == ")":
            depth -= 1
            if depth == 0:
                return src[start + 1:i]
        i += 1
    return src[start + 1:]


def _code_only(src: str) -> str:
    """The source minus its docstrings and comments — a call is code, a mention is not."""
    src = re.sub(r'("""|\'\'\')(.*?)\1', "", src, flags=re.S)
    return re.sub(r"#[^\n]*", "", src)


for _p in _deployed:
    _s = _code_only(_p.read_text())
    for _m in re.finditer(r"\bcreate_client\(", _s):
        _args = _call_args(_s, _m.end() - 1)
        # A CALL has arguments; `create_client()` in a docstring or comment names the function.
        if not _args.strip():
            continue
        if "client_options()" not in _args:
            _bare.append(f"{_p.relative_to(ROOT)}: create_client({_args[:40]!r}…)")
    if _p.name != "supabase.py" and "ClientOptions(" in _s:
        _opts_outside.append(str(_p.relative_to(ROOT)))
check("every create_client in the deployed trees passes client_options()", not _bare, "; ".join(_bare))
check("ClientOptions is constructed in services/supabase.py and nowhere else", not _opts_outside, "; ".join(_opts_outside))
check("…and there, exactly once — inside client_options()",
      SRC.count("ClientOptions(") == 1 and "def client_options()" in SRC
      and SRC.index("def client_options()") < SRC.index("ClientOptions("))
check("the scheduler builds through the one builder — its private create_client is gone",
      "from supabase import create_client" not in read("api/jobs/unified_scheduler.py")
      and "get_service_client()" in read("api/jobs/unified_scheduler.py"))
check("the MCP server builds through the one builder",
      "get_service_client()" in read("api/mcp_server/auth.py") and "create_client(" not in read("api/mcp_server/auth.py").replace("no second create_client()", ""))

# ═════════════════════════════════════════════════════════════════════════════
print("\nD2/D3 the transport — HTTP/1.1, one socket per request, bounded")
# ═════════════════════════════════════════════════════════════════════════════
_opts = S.client_options()
_hc = _opts.httpx_client
check("the options carry an httpx client of our own", isinstance(_hc, httpx.Client))
check("no auth auto-refresh timer, no persisted session (the memory discipline stands)",
      _opts.auto_refresh_token is False and _opts.persist_session is False)
check("HTTP/1.1 — a dead socket takes down one request, never every request",
      getattr(_hc._transport._pool, "_http2", None) is False, str(getattr(_hc._transport._pool, "_http2", "?")))
check("fifteen seconds per call, five to connect",
      _hc.timeout == httpx.Timeout(S.DB_CALL_TIMEOUT_S, connect=S.DB_CONNECT_TIMEOUT_S)
      and S.DB_CALL_TIMEOUT_S == 15.0 and S.DB_CONNECT_TIMEOUT_S == 5.0, str(_hc.timeout))
check("the pool is sized (the service client's pool is shared by every request in the process)",
      _hc._transport._pool._max_connections == S.DB_POOL_LIMITS.max_connections == 20)
_hc.close()

_svc = S.get_service_client()
check("the service client hands the ONE httpx client to postgrest, storage and auth",
      _svc.postgrest.session is _svc.options.httpx_client
      and _svc.auth._http_client is _svc.options.httpx_client
      and getattr(_svc.storage, "_client", None) is _svc.options.httpx_client)
check("…so the one teardown releases it in a single close",
      "first close below releases everything" in SRC and "ADR-669" in SRC[SRC.index("def close_supabase_client"):SRC.index("def close_supabase_client") + 1600])
check("get_user_client builds through the builder too",
      "client = create_client(url, key, client_options())" in SRC[SRC.index("def get_user_client"):])

# ═════════════════════════════════════════════════════════════════════════════
print("\nD4 driven — a stalled socket is cut at the bound, and the cut is the transient the once-retry answers")
# ═════════════════════════════════════════════════════════════════════════════
_srv = socket.socket(); _srv.bind(("127.0.0.1", 0)); _srv.listen(1)
_port = _srv.getsockname()[1]
_held: list[socket.socket] = []


def _accept_and_never_answer():
    try:
        conn, _ = _srv.accept()
        _held.append(conn)  # keep it open; send nothing — a stalled socket
        time.sleep(5)
    except Exception:  # noqa: BLE001
        pass


threading.Thread(target=_accept_and_never_answer, daemon=True).start()
_client = S.bounded_http_client(call_timeout_s=0.8)
_t0 = time.monotonic()
_exc: BaseException | None = None
try:
    _client.get(f"http://127.0.0.1:{_port}/rest/v1/workspaces")
except BaseException as e:  # noqa: BLE001
    _exc = e
_elapsed = time.monotonic() - _t0
check("⭐ a socket that accepts and never answers is given up at the bound, not at 120 s",
      isinstance(_exc, httpx.ReadTimeout) and _elapsed < 3.0, f"{type(_exc).__name__} after {_elapsed:.2f}s")
check("⭐ the cut reads as a transient transport fault — the once-retry answers it on a fresh socket",
      _exc is not None and S._is_transient_transport_error(_exc))
check("…while a database's own 'statement timeout' answer is NOT retried",
      not S._is_transient_transport_error(Exception("canceling statement due to statement timeout")))
_calls = {"n": 0}


def _flaky():
    _calls["n"] += 1
    if _calls["n"] == 1:
        raise httpx.ReadTimeout("stalled")
    return "answered"


check("the once-retry recovers from exactly one cut", S._retry_once_on_transport(_flaky, what="gate") == "answered" and _calls["n"] == 2)
_client.close()
for _c in _held:
    _c.close()
_srv.close()

# ═════════════════════════════════════════════════════════════════════════════
print("\nthe canon says so")
# ═════════════════════════════════════════════════════════════════════════════
_adr = read("docs/adr/ADR-669-the-database-transport-is-bounded.md")
check("the ADR exists, Accepted, and names this gate",
      "**Accepted**" in _adr and "test_adr669_the_database_transport_is_bounded.py" in _adr)
check("the retry helper no longer says the cure is owed to a future ADR",
      "with its own ADR" not in SRC and "The cure landed with ADR-669" in SRC)
check("the ledger has the row", "- **ADR-669**:" in read("docs/architecture/ADR-LEDGER.md"))
_life = read("docs/infrastructure/memory-and-client-lifecycle.md")
check("the client-lifecycle reference records the stall and the rule",
      "ADR-669" in _life and "client_options()" in _life and "2026-09-25" in _life)
check("ACCESS.md points operators at the builder", "client_options()" in read("docs/database/ACCESS.md"))

print("\n" + "=" * 70)
print(f"  {PASS} passed, {FAIL} failed")
print("=" * 70)
if FAIL:
    print("✗ ADR-669 gate RED")
    sys.exit(1)
print("✓ all ADR-669 checks passed")
