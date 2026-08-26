"""Regression gate — Supabase + Anthropic httpx client lifecycle (2026-06-05, +2026-07-01).

THE BUG (recurring — OOM-killed yarnnn-api 2026-06-01, 2026-06-04, AND 2026-07-01):
  Every `create_client()` eagerly opens TWO httpx connection pools (postgrest +
  gotrue auth) and exposes NO unified close(). Per-request / per-thread callers
  that abandoned those pools accumulated RSS until the 512 MiB starter-plan cap
  OOM-killed the process.

  Two offenders:
    1. working_memory.build_working_memory — created ~23 clients per call (one
       per parallel read), closed NONE, and handed each client across threads
       (event-loop thread → worker thread). The bulk of the 2026-06-04 creep.
    2. supabase.get_user_client — the 2026-06-01 fix closed postgrest only; the
       gotrue auth pool kept leaking, which is why the OOM RECURRED.

THE FIX:
  - services.supabase.close_supabase_client(client) — the Singular teardown that
    closes BOTH pools. Every per-request/per-thread call site routes through it.
  - working_memory._run_sync_with_client(fn, *args) — builds the client INSIDE
    the worker thread, runs fn, closes both pools in finally. No cross-thread
    handoff, no leak. All ~23 reads go through it.
  - get_user_client's finally closes through close_supabase_client.
  - _classify_activation_state closes its own client in finally.

This gate locks: (a) the teardown helper closes both pools; (b) build_working_memory
closes every client it opens (counted via a create_client spy); (c) the source
no longer carries the leak pattern.

See docs/infrastructure/memory-and-client-lifecycle.md.

Run: api/venv/bin/python api/test_client_lifecycle.py
"""

from __future__ import annotations

import ast
import asyncio
import sys
import types
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

PASS = 0
FAIL = 0


def check(name: str, cond: bool) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")


# ── Fake Supabase client mirroring the two-pool shape (postgrest + gotrue auth) ──
class _FakeHttpClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakePostgrest:
    def __init__(self) -> None:
        self.session = _FakeHttpClient()


class _FakeAuth:
    def __init__(self) -> None:
        self._http_client = _FakeHttpClient()


class _FakeClient:
    """Mirrors the supabase.Client surface the teardown + helpers touch."""

    def __init__(self, *_a, **_k) -> None:
        self.postgrest = _FakePostgrest()
        self.auth = _FakeAuth()

    @property
    def both_closed(self) -> bool:
        return self.postgrest.session.closed and self.auth._http_client.closed


# ── 1. close_supabase_client closes BOTH pools ──────────────────────────────
from services.supabase import close_supabase_client  # noqa: E402

_c = _FakeClient()
check("close_supabase_client: postgrest pool open before", not _c.postgrest.session.closed)
check("close_supabase_client: auth pool open before", not _c.auth._http_client.closed)
close_supabase_client(_c)
check("close_supabase_client: closes postgrest pool", _c.postgrest.session.closed)
check("close_supabase_client: closes gotrue auth pool (the 06-01 fix MISSED this)", _c.auth._http_client.closed)

# Teardown is best-effort — a broken client must not raise.
class _Broken:
    @property
    def postgrest(self):
        raise RuntimeError("boom")

    @property
    def auth(self):
        raise RuntimeError("boom")

_raised = False
try:
    close_supabase_client(_Broken())
except Exception:
    _raised = True
check("close_supabase_client: best-effort — never raises on a broken client", not _raised)


# ── 2. (was: build_working_memory closes EVERY client it opens) ─────────────
# services/working_memory.py was DELETED 2026-08-26 — its two public entry
# points had zero production callers. The fan-out it guarded no longer exists.
# Sections 1, 3 and 4 below still guard LIVE lifecycle code and stay.

# ── 3. Source contract — the leak pattern is gone ───────────────────────────
sb_src = (Path(__file__).resolve().parent / "services" / "supabase.py").read_text()

# The three working_memory source checks are gone with the module. The
# relocated `classify_activation_state` keeps the same close-in-finally shape,
# asserted here against its new home so the lifecycle contract still has a gate.
br_src = (Path(__file__).resolve().parent / "services" / "bundle_reader.py").read_text()
check(
    "bundle_reader: classify_activation_state closes its own client in finally",
    "close_supabase_client(client)" in br_src and "finally:" in br_src,
)
check(
    "supabase: get_user_client routes teardown through close_supabase_client",
    "close_supabase_client(client)" in sb_src,
)
check(
    "supabase: hand-rolled postgrest.session.close() in get_user_client's finally is gone",
    "yield AuthenticatedClient" in sb_src
    and sb_src.count("client.postgrest.session.close()") == 1,  # only inside the helper now
)

# ── 4. Anthropic client lifecycle (the THIRD occurrence — OOM 2026-07-01) ────
# Same bug class as the Supabase pools above, on the un-audited Anthropic path:
# AsyncAnthropic() eagerly builds an httpx pool (max_connections=1000) and was
# constructed per-call in all 7 services/anthropic.py wrappers, never closed.
# The Reviewer/Freddie loop calls the tool wrappers once per tool ROUND, so one
# multi-round wake abandoned N pools → ~50 MB/hr RSS creep on flat traffic.
# Fix: every wrapper uses `async with get_anthropic_client()` (or try/finally
# close() for the long generator), releasing the pool on return / exception /
# GeneratorExit (client disconnect mid-stream — the runaway amplifier).
import os as _os

_os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

_ANTH_OPENED: list[int] = []
_ANTH_CLOSED: list[int] = []


class _FakeAnthMessages:
    async def create(self, **kw):
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="ok")],
            stop_reason="end_turn",
            usage=types.SimpleNamespace(
                input_tokens=1, output_tokens=1,
                cache_creation_input_tokens=0, cache_read_input_tokens=0,
            ),
        )

    def stream(self, **kw):
        return _FakeAnthStream()


class _FakeAnthStream:
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    @property
    def text_stream(self):
        async def _g():
            for t in ("a", "b"):
                yield t
        return _g()
    async def get_final_message(self):
        return await _FakeAnthMessages().create()


class _FakeAnthClient:
    def __init__(self, **kw):
        self._id = len(_ANTH_OPENED)
        _ANTH_OPENED.append(self._id)
        self.messages = _FakeAnthMessages()
        self.beta = types.SimpleNamespace(messages=_FakeAnthMessages())
    async def __aenter__(self): return self
    async def __aexit__(self, *a):
        await self.close(); return False
    async def close(self):
        _ANTH_CLOSED.append(self._id)


with mock.patch("anthropic.AsyncAnthropic", _FakeAnthClient):
    import importlib
    import services.anthropic as _A
    importlib.reload(_A)

    # `model` is REQUIRED on every wrapper (2026-08-21) — the six defaults that
    # used to spell the retired `claude-sonnet-4-6` are gone, so these drives
    # name a model explicitly like every production caller does.
    _M = "claude-sonnet-5"

    async def _drive_anthropic():
        await _A.chat_completion([{"role": "user", "content": "hi"}], "sys", _M)
        await _A.chat_completion_with_usage([{"role": "user", "content": "hi"}], "sys", _M)
        await _A.chat_completion_with_tools([{"role": "user", "content": "hi"}], "sys", [], _M)
        await _A.chat_completion_with_tools([{"role": "user", "content": "hi"}], "sys", [], _M, context_management={"edits": []})
        await _A.chat_completion_with_tools_stream([{"role": "user", "content": "hi"}], "sys", [], _M)
        async for _ in _A.chat_completion_stream([{"role": "user", "content": "hi"}], "sys", _M):
            pass
        # Disconnect mid-stream (the runaway amplifier — must still close).
        _gen = _A.chat_completion_stream([{"role": "user", "content": "hi"}], "sys", _M)
        await _gen.__anext__()
        await _gen.aclose()

        async def _noop(n, i): return {"success": True}
        async for _ in _A.chat_completion_stream_with_tools([{"role": "user", "content": "hi"}], "sys", [], _noop, _M):
            pass
        _gen2 = _A.chat_completion_stream_with_tools([{"role": "user", "content": "hi"}], "sys", [], _noop, _M)
        await _gen2.__anext__()
        await _gen2.aclose()

    asyncio.run(_drive_anthropic())
    # Reload with the real SDK restored so later imports are unaffected.
    importlib.reload(_A)

_anth_leaked = set(_ANTH_OPENED) - set(_ANTH_CLOSED)
check(
    "anthropic: every wrapper opens a client (7 wrappers + 2 disconnect drives)",
    len(_ANTH_OPENED) >= 7,
)
check(
    f"anthropic: closes EVERY client it opens ({len(_ANTH_CLOSED)}/{len(_ANTH_OPENED)}) incl. mid-stream disconnect",
    len(_ANTH_OPENED) > 0 and not _anth_leaked,
)

# The FOURTH occurrence (OOM 2026-07-22, mid-SSE on a lane turn) got past the
# previous version of this gate because it read ONE file's text —
# services/anthropic.py — and counted occurrences in it. Two callers in OTHER
# files (services/primitives/web_search.py, services/recurrence_prompt_inference.py)
# were structurally invisible to it, and both leaked a pool per call for weeks.
# A gate that greps one file cannot see the call site that matters. So: walk the
# AST of EVERY api/ source, find every call to get_anthropic_client(), and
# require each one to be the context-expression of an `async with` — the single
# exception being the long-lived streaming generator that closes in a `finally`.
_ANTH_BARE: list[str] = []
_ANTH_GUARDED: list[str] = []
_API_ROOT = Path(__file__).resolve().parent


def _is_get_anth_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "get_anthropic_client"
    )


for _py in sorted(_API_ROOT.rglob("*.py")):
    rel = _py.relative_to(_API_ROOT).as_posix()
    # Skip vendored deps and the gates themselves (which name the call in prose).
    if rel.startswith((".venv", "venv")) or rel.startswith("test_"):
        continue
    try:
        _tree = ast.parse(_py.read_text())
    except SyntaxError:
        continue
    # Every call that sits directly under an `async with` header is guarded.
    _guarded_nodes: set[int] = set()
    for _n in ast.walk(_tree):
        if isinstance(_n, ast.AsyncWith):
            for _item in _n.items:
                if _is_get_anth_call(_item.context_expr):
                    _guarded_nodes.add(id(_item.context_expr))
    for _n in ast.walk(_tree):
        if _is_get_anth_call(_n):
            where = f"{rel}:{_n.lineno}"
            if id(_n) in _guarded_nodes:
                _ANTH_GUARDED.append(where)
            else:
                _ANTH_BARE.append(where)

# services/anthropic.py's streaming generator holds the client across yields, so
# it cannot use `async with`; it closes in a `finally` instead. That one bare
# call is the ONLY sanctioned exception, and it must still prove its teardown.
_ANTH_SANCTIONED = {
    w for w in _ANTH_BARE if w.startswith("services/anthropic.py")
}
_anth_src = (_API_ROOT / "services" / "anthropic.py").read_text()
check(
    f"anthropic: every call site outside the streaming generator uses `async with` "
    f"({len(_ANTH_GUARDED)} guarded, {len(_ANTH_BARE) - len(_ANTH_SANCTIONED)} bare)",
    not (set(_ANTH_BARE) - _ANTH_SANCTIONED),
)
check(
    "anthropic: the one sanctioned bare call (streaming generator) closes in a finally",
    len(_ANTH_SANCTIONED) <= 1 and "await client.close()" in _anth_src,
)
check(
    "anthropic: the gate actually SAW the call sites (guards against a silent no-op scan)",
    len(_ANTH_GUARDED) + len(_ANTH_BARE) >= 8,
)


print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
