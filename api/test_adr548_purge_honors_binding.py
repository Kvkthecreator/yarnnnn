"""ADR-548 D8 — a destructive act must target the workspace it was AUTHORIZED against.

The defect this gate closes
---------------------------
`resolve_purge_workspace(user_id)` called `effective_workspace_id(user_id, None)`.
Rung 2 of that chain is a contextvar which — per `workspace_context`'s own
docstring, receipted on prod 2026-08-11 — does NOT survive into an async route
handler: `get_user_client` is a SYNC generator, so FastAPI runs it in a
threadpool and the handler reads a different context. Resolution then fell to
rung 3, the caller's OWN workspace.

Meanwhile the authority gate and the pane header both read `auth.workspace_id`
(`routes/workspace.py`: `acting = auth.workspace_id or resolve_owner_...`).

So for an owner pinned into workspace B via `X-Workspace-Id`:
    can_clear  -> computed for B
    pane names -> B
    the WIPE   -> A

A real workspace, HTTP 200, a plausible message. Nothing errors, nothing logs:
the ADR-561 incorrect-success class, on the two most destructive endpoints in
the product.

Falsified against the real pre-fix source before landing.

Run: python3 test_adr548_purge_honors_binding.py   (script-style, like its
neighbours — note `pytest` reports "no tests ran" on these files.)
"""
import ast
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.abspath(__file__))

_passed = 0
_failed = 0


def record(name: str, ok: bool, why: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"PASS  {name}")
    else:
        _failed += 1
        print(f"FAIL  {name}  {why}")


# -- 1. the mechanism: prove the contextvar really is lost -------------------
# This is the fact the whole gate rests on; assert it rather than trust it,
# so if a future FastAPI/anyio change propagates context the gate says so.
from services.workspace_context import (  # noqa: E402
    effective_workspace_id,
    set_request_workspace,
)


async def _drive_contextvar_loss():
    loop = asyncio.get_event_loop()

    def sync_dependency():           # what get_user_client is
        set_request_workspace("WS-B-PINNED")
        return effective_workspace_id("user-1", None)

    in_dep = await loop.run_in_executor(None, sync_dependency)

    async def handler():             # what a route handler is
        return effective_workspace_id("user-1", None)

    return in_dep, await handler()


_in_dep, _in_handler = asyncio.run(_drive_contextvar_loss())
record(
    "the binding IS visible inside the sync dependency",
    _in_dep == "WS-B-PINNED",
    f"got {_in_dep!r}",
)
record(
    "the binding is LOST in the async handler (why passing it is mandatory)",
    _in_handler is None,
    f"got {_in_handler!r} — if this now propagates, revisit ADR-548 D8",
)

# -- 2. an EXPLICIT binding wins over owner-resolution -----------------------
record(
    "an explicit workspace_id is honored over any fallback",
    effective_workspace_id("user-1", "WS-B-PINNED") == "WS-B-PINNED",
)

# -- 3. resolve_purge_workspace must ACCEPT a binding ------------------------
import inspect  # noqa: E402

from services.workspace_purge import resolve_purge_workspace  # noqa: E402

params = list(inspect.signature(resolve_purge_workspace).parameters)
record(
    "resolve_purge_workspace accepts a workspace binding",
    len(params) >= 2,
    f"signature is ({', '.join(params)}) — a route cannot pass its pin",
)
if len(params) >= 2:
    record(
        "and it FORWARDS that binding (explicit beats owner-resolution)",
        resolve_purge_workspace("user-1", "WS-B-PINNED") == "WS-B-PINNED",
        "the binding was accepted then dropped",
    )

# -- 4. every destructive route PASSES its binding ---------------------------
# The composition check: not "does a spelling appear" but "does each call that
# resolves a purge scope receive a second argument".
src = open(os.path.join(REPO, "routes/account.py")).read()
tree = ast.parse(src)

DESTRUCTIVE = {
    "clear_work_history",
    "clear_workspace",
    "clear_integrations",
    "get_danger_zone_stats",   # the PREVIEW must count what the act deletes
}
RESOLVERS = {"_resolve_or_deny", "resolve_purge_workspace"}

for fn in ast.walk(tree):
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    if fn.name not in DESTRUCTIVE:
        continue
    calls = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and getattr(n.func, "id", None) in RESOLVERS
    ]
    record(f"{fn.name} resolves a purge scope", bool(calls), "no resolver call found")
    for c in calls:
        record(
            f"{fn.name} passes its request binding to {c.func.id}",
            len(c.args) >= 2,
            "called with user_id alone — falls back to the CALLER'S OWN "
            "workspace while the authority gate used the pin",
        )

print("=" * 62)
print(f"ADR-548 D8 purge-binding gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
print("=" * 62)
sys.exit(1 if _failed else 0)
