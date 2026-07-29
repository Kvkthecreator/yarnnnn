"""Workspace-binding transport gate (ADR-373 sweep).

NOT an ADR — these are bug guards. The audit of 2026-07-29 found the acting
workspace could be lost or go stale on the frontend in several ways; this
pins the two that are silent and therefore cannot be caught by looking.

WHY SILENT MATTERS. `services/supabase.py::get_user_client` fails CLOSED only
when `X-Workspace-Id` is PRESENT and invalid (403). When the header is simply
ABSENT it falls back to the owner workspace with no error — so a write path
that forgets the header mis-scopes forever and looks perfectly healthy. The
live instance: the chat rail's transport hand-built its headers, so a member
acting in a GRANTED workspace had every turn (and the files those turns wrote)
land in their OWN workspace, while chat history — which used the shared
`request()` helper — read from the granted one.

Run: python3 test_workspace_binding_transport.py
"""

from __future__ import annotations

import pathlib
import re
import sys

WEB = pathlib.Path(__file__).parent.parent / "web"

_failures: list[str] = []


def _assert(cond: bool, msg: str) -> None:
    print(f"  {'✓' if cond else '✗'} {msg}")
    if not cond:
        _failures.append(msg)


def _read(p: pathlib.Path) -> str:
    return p.read_text() if p.exists() else ""


def _strip_comments(src: str) -> str:
    """Assert on CODE, not commentary — a comment that NAMES the anti-pattern
    (as these files now do, deliberately) must not trip the check."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return "\n".join(
        ln for ln in src.splitlines() if not ln.strip().startswith(("//", "*"))
    )


def test_every_api_transport_sends_the_binding() -> None:
    """Any module that calls fetch() against the API must carry the binding.

    The rule is structural, not per-file: either go through `getAuthHeaders()`
    (which attaches it) or attach `X-Workspace-Id` explicitly.
    """
    print("\nEvery API write transport carries X-Workspace-Id")
    transport = _strip_comments(_read(WEB / "lib" / "api" / "chatTransport.ts"))
    _assert(
        "X-Workspace-Id" in transport,
        "chatTransport attaches the acting-workspace binding",
    )
    _assert(
        "getActiveWorkspaceId" in transport,
        "it reuses the exported binding accessor (one source of truth)",
    )

    proxy = _strip_comments(_read(WEB / "app" / "api" / "feed-proxy" / "route.ts"))
    _assert(
        "x-workspace-id" in proxy.lower(),
        "the same-origin proxy FORWARDS the binding (its allowlist dropped it)",
    )


def test_no_new_handbuilt_api_fetch_without_binding() -> None:
    """Catch the NEXT instance of this shape.

    A module that builds an `Authorization: Bearer` header by hand and fetches
    the API is exactly the pattern that lost the binding. If one appears, it
    must also carry `X-Workspace-Id`.
    """
    print("\nNo hand-built API fetch omits the binding")
    offenders: list[str] = []
    for path in sorted((WEB / "lib").rglob("*.ts")) + sorted((WEB / "app" / "api").rglob("*.ts")):
        src = _strip_comments(_read(path))
        builds_auth = "Bearer ${" in src or 'get("authorization")' in src
        fetches = "fetch(" in src
        if builds_auth and fetches and "X-Workspace-Id" not in src and "x-workspace-id" not in src.lower():
            # client.ts is the source of truth — it DEFINES getAuthHeaders.
            if path.name != "client.ts":
                offenders.append(str(path.relative_to(WEB)))
    _assert(
        not offenders,
        f"no hand-built API transport lacks the binding (found: {offenders})",
    )


def test_workspace_scoped_module_caches_are_binding_keyed() -> None:
    """A module-level cache holding workspace-scoped data must invalidate when
    the acting workspace rebinds.

    The acting workspace can now change MID-SESSION without a reload (the
    stale-pin self-heal in `client.ts`), so `let x = null` at module scope
    outlives its binding. Both known caches key to it; this keeps them keyed.
    """
    print("\nWorkspace-scoped module caches invalidate on rebind")
    for rel in ("lib/workspace/viewer.ts", "lib/freddie-persona.ts"):
        src = _read(WEB / rel)
        _assert(
            "cacheBinding" in src and "getActiveWorkspaceId" in src,
            f"{rel} keys its module cache to the acting workspace",
        )


if __name__ == "__main__":
    print("Workspace-binding transport + cache guards")
    print("=" * 60)
    for fn in [
        test_every_api_transport_sends_the_binding,
        test_no_new_handbuilt_api_fetch_without_binding,
        test_workspace_scoped_module_caches_are_binding_keyed,
    ]:
        fn()
    print("\n" + "=" * 60)
    if _failures:
        print(f"FAIL: {len(_failures)} check(s)")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    print("PASS")
