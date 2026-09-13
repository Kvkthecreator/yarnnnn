"""ADR-548 D1 — a substrate WRITE must land in the workspace it was authorized against.

The defect this gate closes
---------------------------
The sibling of `test_adr548_purge_honors_binding.py`, on the write path
instead of the destructive one, and it shipped for the same reason: the rule
("the explicit binding must be PASSED, not inferred") had no gate on this
door. The ratchet ADR-548 D2 named — `test_adr548_primitive_scope_doorway.py`
— was deleted as collateral by the ADR-632 steward retirement (85c4f7b) while
four docs went on citing it, so the class had NO enforcement at all.

`write_revision(...)` takes `workspace_id` as an OPTIONAL kwarg. Omitted, the
write resolves through `effective_workspace_id`, whose rung 2 is a contextvar
that — per `workspace_context`'s own docstring — does NOT survive into an
async route handler (`get_user_client` is a sync generator, so FastAPI runs it
in a threadpool and the handler reads a different context). Resolution then
falls to rung 3: **owner-resolution, which returns the caller's OLDEST owned
workspace** — not the one they are operating.

So for an owner pinned into their SECOND workspace via `X-Workspace-Id`:
    the read     -> workspace B (the pin, via _substrate_scope_filter(auth))
    the WRITE    -> workspace A (owner-resolved, the oldest)
    the read-back-> workspace B, and 404s

Receipted on prod 2026-09-13 (yarnnn-api logs, one second apart):

    04:51:34  PATCH  ... workspace_id=eq.d5b9029b ... "File edited"
    04:51:35  GET    ... workspace_id=eq.9dc80079 ... 404 Not Found

The member saw "Nothing exists at operation/ideas.md — it may have been moved
or never written" in the Text editor, while the file sat intact in their other
workspace. HTTP 200 on the write, a plausible empty state on the read: the
ADR-561 incorrect-success class again, on the create gesture of a core app.

Falsified against the real pre-fix source before landing (reverting any one of
the six call sites reddens this gate naming that function).

Run: python3 test_adr548_writes_honor_binding.py   (script-style, like its
neighbours — note `pytest` reports "no tests ran" on these files.)
"""
import ast
import asyncio
import inspect
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


# -- 1. the mechanism: the contextvar really is lost in an async handler -----
# The fact the whole gate rests on. Asserted, not trusted: if a future
# FastAPI/anyio change propagates context, this says so rather than going
# quietly stale.
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
    f"got {_in_handler!r} — if this now propagates, revisit ADR-548 D1",
)
record(
    "an explicit workspace_id is honored over any fallback",
    effective_workspace_id("user-1", "WS-B-PINNED") == "WS-B-PINNED",
)

# -- 2. write_revision still ACCEPTS a binding ------------------------------
from services.authored_substrate import write_revision  # noqa: E402

_wr_params = list(inspect.signature(write_revision).parameters)
record(
    "write_revision accepts a workspace_id binding",
    "workspace_id" in _wr_params,
    f"signature is ({', '.join(_wr_params)}) — a route cannot pass its pin",
)

# -- 3. every UserClient route that writes PASSES its binding ---------------
# The composition check: not "does a spelling appear somewhere in the file"
# but "does each write_revision call inside a request-scoped handler receive a
# workspace_id keyword". AST, not grep — a text scan matches this gate's own
# explanatory comments, the failure mode this repo has hit before (ADR-548 D2).
#
# Membership is ASSERTED, not merely iterated: when a sibling gate listed a
# function that no longer existed, the loop skipped it and reported a
# confident green over nothing.
WRITE_DOORS = {
    "routes/workspace.py": {"edit_workspace_file"},
    "routes/studio.py": {
        "set_default_design_system_route",
        "write_artifact",
        "_retitle_to",
        "create_artifact",
    },
    "routes/images.py": {"export_png"},
}

for rel, expected in sorted(WRITE_DOORS.items()):
    path = os.path.join(REPO, rel)
    if not os.path.exists(path):
        record(f"{rel} exists", False, "file is gone — re-point or delete this entry")
        continue
    tree = ast.parse(open(path).read())
    fns = {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for name in sorted(expected):
        fn = fns.get(name)
        record(f"{rel}:{name} exists", fn is not None, "named function not found")
        if fn is None:
            continue
        calls = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and getattr(n.func, "id", None) == "write_revision"
        ]
        record(
            f"{rel}:{name} writes through write_revision",
            bool(calls),
            "no write_revision call found — re-point this entry",
        )
        for c in calls:
            kwargs = {k.arg for k in c.keywords if k.arg}
            record(
                f"{rel}:{name} passes its request binding to write_revision",
                "workspace_id" in kwargs,
                "called without workspace_id — the write owner-resolves to the "
                "caller's OLDEST workspace while the read used the pin",
            )

print("=" * 62)
print(f"ADR-548 D1 write-binding gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
print("=" * 62)
sys.exit(1 if _failed else 0)
