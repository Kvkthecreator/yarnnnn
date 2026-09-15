"""Gate: an infrastructure fault never wears an authorization answer's clothes.

FOUND 2026-09-15, driving the beta-readiness pass. `principal_reaches_workspace`
returned False on ANY exception, and every caller renders False as "No active
grant into workspace X". The shared service client (`get_service_client`, an
`lru_cache`d singleton) hands one HTTP/2 connection pool to every threadpool
worker `get_user_client` runs in; under concurrency that pool throws
`httpx.ReadError: [Errno 11]` — 7 bursts across 5 instances on 2026-09-12→13,
including three 403s at 16:23:49Z.

So a member holding a perfectly valid grant was told they had none. They retry a
permissions problem that does not exist; the real transport fault is a warning
nobody reads. THREE separate claims must hold, and this gate drives all three
against the real functions rather than reading the source:

  1. UNDECIDABLE ≠ NO. A failed lookup raises ReachUndecidable, never False.
  2. DECIDED-NO STILL WORKS. A genuine absence of grant still returns False —
     the fix must not turn every denial into a 503.
  3. THE RETRY DISCRIMINATES. A transient transport fault is retried once and
     recovers; a REAL error (permission denied, missing relation) is raised on
     the first attempt with no wasted retry.

Run: python3 -B test_reach_undecidable_is_not_a_denial.py   (script-shaped —
read the printed count, not the exit code)
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import services.supabase as S  # noqa: E402

_passed = 0
_failed = 0


def check(label: str, ok: bool) -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"PASS  {label}")
    else:
        _failed += 1
        print(f"FAIL  {label}")


# ── 1. Undecidable is not a denial ───────────────────────────────────────────

def _boom(*_a, **_k):
    raise RuntimeError("httpx.ReadError: [Errno 11] Resource temporarily unavailable")


with patch.object(S, "resolve_owned_workspace_ids", _boom):
    try:
        result = S.principal_reaches_workspace("u1", "ws1")
        check(f"a failed lookup raises rather than returning {result!r}", False)
    except S.ReachUndecidable:
        check("a failed lookup raises ReachUndecidable, not False", True)
    except Exception as exc:  # noqa: BLE001
        check(f"a failed lookup raises ReachUndecidable (got {type(exc).__name__})", False)


# ── 2. A decided NO still returns False ──────────────────────────────────────

class _EmptyResult:
    data: list = []


class _Query:
    def select(self, *_a):
        return self

    def eq(self, *_a):
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        return _EmptyResult()


class _Client:
    def table(self, *_a):
        return _Query()


with patch.object(S, "resolve_owned_workspace_ids", lambda _u: set()), \
        patch.object(S, "get_service_client", lambda: _Client()):
    check(
        "a principal with no grant still returns False (not an exception)",
        S.principal_reaches_workspace("u1", "ws1") is False,
    )


# ── 3. The retry discriminates transient from real ───────────────────────────

for text, want_transient in (
    ("httpx.ReadError: [Errno 11] Resource temporarily unavailable", True),
    ("Server disconnected without sending a response", True),
    ("ConnectionResetError: [Errno 54]", True),
    ("RemoteProtocolError: illegal request line", True),
    ("permission denied for table principal_grants", False),
    ("relation \"principal_grants\" does not exist", False),
    ("invalid input syntax for type uuid", False),
):
    check(
        f"classified {'transient' if want_transient else 'real':9} — {text[:44]}",
        S._is_transient_transport_error(Exception(text)) is want_transient,
    )

_attempts = {"n": 0}


def _flaky():
    _attempts["n"] += 1
    if _attempts["n"] == 1:
        raise RuntimeError("httpx.ReadError: [Errno 11]")
    return "recovered"


check(
    "a transient fault is retried once and recovers",
    S._retry_once_on_transport(_flaky, what="gate") == "recovered" and _attempts["n"] == 2,
)

_real_attempts = {"n": 0}


def _real_error():
    _real_attempts["n"] += 1
    raise RuntimeError("permission denied for table principal_grants")


try:
    S._retry_once_on_transport(_real_error, what="gate")
    check("a real error is not retried", False)
except RuntimeError:
    check(
        "a real error raises on the FIRST attempt (no wasted retry)",
        _real_attempts["n"] == 1,
    )

_persistent = {"n": 0}


def _always_broken():
    _persistent["n"] += 1
    raise RuntimeError("httpx.ReadError: [Errno 11]")


try:
    S._retry_once_on_transport(_always_broken, what="gate")
    check("a persistent transient fault still raises", False)
except RuntimeError:
    check(
        "a persistent transient fault still raises after exactly 2 attempts",
        _persistent["n"] == 2,
    )


# ── 4. The callers answer 503, not 403 ───────────────────────────────────────
# Text-level, deliberately: these are FastAPI/MCP handlers whose construction
# needs a live request. The claim is narrow — each call site that catches
# ReachUndecidable answers with an unavailability status, never a grant claim.

_SITES = (
    ("services/supabase.py", "503"),
    ("routes/mcp.py", "503"),
    ("routes/shares.py", "503"),
    ("mcp_server/server.py", "reach_unavailable"),
)
_here = Path(__file__).resolve().parent
for rel, marker in _SITES:
    src = (_here / rel).read_text()
    idx = src.find("ReachUndecidable")
    # Every file that imports the exception must also HANDLE it.
    handles = "except ReachUndecidable" in src
    # ...and the handler's answer must appear after the catch, not anywhere.
    catch_at = src.find("except ReachUndecidable")
    answered = catch_at != -1 and marker in src[catch_at:catch_at + 700]
    check(f"{rel} catches ReachUndecidable and answers {marker}", idx != -1 and handles and answered)

# COMPLETENESS: the except clause must RAISE, never `return False` again.
# Bounded to the CONSTRUCT via the AST, not a character window — a fixed slice
# reaches into the neighbouring function and matches its code (the 2026-07-31
# lesson, BROWSER-CLICK-PASS-PLAYBOOK §5). The first cut of this very check
# sliced 2000 chars, fell short of the `raise`, and reported a false red.
import ast  # noqa: E402

_tree = ast.parse((_here / "services/supabase.py").read_text())
_fn = next(
    (n for n in ast.walk(_tree)
     if isinstance(n, ast.FunctionDef) and n.name == "principal_reaches_workspace"),
    None,
)
_handlers = [h for h in ast.walk(_fn) if isinstance(h, ast.ExceptHandler)] if _fn else []
check(
    "principal_reaches_workspace exists and has an except clause",
    _fn is not None and len(_handlers) == 1,
)
if _handlers:
    _body = _handlers[0].body
    _raises = any(isinstance(s, ast.Raise) for s in ast.walk(_handlers[0]))
    _returns_false = any(
        isinstance(s, ast.Return)
        and isinstance(s.value, ast.Constant)
        and s.value.value is False
        for s in ast.walk(_handlers[0])
    )
    check(
        "its except clause RAISES and never `return False`",
        _raises and not _returns_false,
    )

print("=" * 62)
print(f"reach-undecidable gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
print("=" * 62)
sys.exit(1 if _failed else 0)
