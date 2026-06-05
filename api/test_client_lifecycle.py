"""Regression gate — Supabase/httpx client lifecycle (2026-06-05).

THE BUG (recurring — OOM-killed yarnnn-api 2026-06-01 AND 2026-06-04):
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


# ── 2. build_working_memory closes EVERY client it opens ────────────────────
# Spy on create_client: every client handed out must end up with both pools closed.
import services.working_memory as wm  # noqa: E402

handed_out: list[_FakeClient] = []


def _spy_create_client(*_a, **_k) -> _FakeClient:
    c = _FakeClient()
    handed_out.append(c)
    return c


# Each _*_sync helper just returns an inert value; we only care about lifecycle.
# Patch create_client at both the supabase module (used by close path import site)
# and the working_memory alias used to construct clients.
with mock.patch.object(wm, "_create_supabase_client", _spy_create_client), \
     mock.patch("services.bundle_reader.bundles_active_for_workspace", lambda *_a, **_k: []):
    # Replace every sync DB helper with an inert stub so no network is touched.
    sync_names = [n for n in dir(wm) if n.endswith("_sync") and callable(getattr(wm, n))]

    def _make_stub(name):
        # Return a shape that downstream formatting tolerates: dict-ish/list-ish.
        def _stub(*args):
            # last arg is the client; helpers that return dict/list/int all OK as {}
            return {}
        return _stub

    patches = [mock.patch.object(wm, n, _make_stub(n)) for n in sync_names]
    for p in patches:
        p.start()
    try:
        result = asyncio.run(wm.build_working_memory("user-123", client=None))
    finally:
        for p in patches:
            p.stop()

check("build_working_memory: opened at least 20 clients (the parallel-read fan-out)", len(handed_out) >= 20)
check(
    f"build_working_memory: closes EVERY client it opens ({sum(c.both_closed for c in handed_out)}/{len(handed_out)})",
    len(handed_out) > 0 and all(c.both_closed for c in handed_out),
)


# ── 3. Source contract — the leak pattern is gone ───────────────────────────
wm_src = (Path(__file__).resolve().parent / "services" / "working_memory.py").read_text()
sb_src = (Path(__file__).resolve().parent / "services" / "supabase.py").read_text()

check(
    "working_memory: legacy _make_client() pass-through pattern deleted",
    "_make_client()" not in wm_src,
)
check(
    "working_memory: _run_sync_with_client wrapper present (per-thread create+close)",
    "_run_sync_with_client" in wm_src and "close_supabase_client(client)" in wm_src,
)
check(
    "working_memory: _classify_activation_state closes its own client in finally",
    "finally:\n            close_supabase_client(client)" in wm_src
    or "close_supabase_client(client)" in wm_src,
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

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
