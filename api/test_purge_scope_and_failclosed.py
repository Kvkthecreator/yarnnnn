"""The purge acts on the workspace it was ASKED about, and fails CLOSED.

Three defects this pins, all found by tracing the Danger Zone end-to-end
(2026-08-20) and none of them visible to any existing gate:

1. `purge_workspace(client, user_id, workspace_id)` received the workspace being
   purged and then called `purge_l2_workspace(client, user_id)` — a function
   that re-resolved the CALLER's home workspace. Phases 2 and 3 used the
   argument correctly, so the content phase could wipe a different workspace's
   files than the row that got deleted. Latent only while everyone had one
   workspace; deliberate genesis made multiple workspaces normal.

2. `resolve_purge_workspace` swallowed a resolution FAILURE into the same `None`
   that means "this user has no workspace". `None` reads as "N=1, allow" at the
   authority gate and as "scope to user_id" at the delete — so one transient
   error both granted owner-grade authority and silently narrowed the blast
   radius. Fail-open on permission, fail-quiet on scope.

3. The stats side counted `action_proposals` with `optional=True` (swallowing a
   missing table and reporting 0) while the delete raised. The UI promised a
   no-op and the clear 500'd.
"""

import ast
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.dirname(os.path.abspath(__file__))
_results = []


def record(name, ok, detail=""):
    _results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail if not ok else ''}")
    return ok


def _src(rel):
    with open(os.path.join(REPO, rel)) as fh:
        return fh.read()


def run() -> int:
    # ---- 1. the workspace argument is HONORED, not re-resolved ----------
    from services.workspace_purge import purge_l2_workspace

    sig = inspect.signature(purge_l2_workspace)
    record(
        "purge_l2_workspace accepts the workspace it should act on",
        "workspace_id" in sig.parameters,
        f"params: {list(sig.parameters)}",
    )

    delete_src = _src("services/workspace_delete.py")
    tree = ast.parse(delete_src)
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "purge_workspace"
    )
    # Find the call and check the workspace_id argument is threaded through.
    threaded = False
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "purge_l2_workspace":
            names = [a.id for a in node.args if isinstance(a, ast.Name)]
            threaded = "workspace_id" in names
    record(
        "the lifecycle purge passes the workspace it was asked to purge",
        threaded,
        "purge_l2_workspace(...) must receive workspace_id, not re-resolve it",
    )

    # ---- 2. resolution FAILURE denies; genuine absence still allows -----
    from services.workspace_purge import (
        WorkspaceResolutionError,
        resolve_purge_workspace,
    )
    import services.workspace_context as wc

    real = wc.effective_workspace_id
    try:
        wc.effective_workspace_id = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("db down")
        )
        raised = False
        try:
            resolve_purge_workspace("u1")
        except WorkspaceResolutionError:
            raised = True
        record(
            "a resolution FAILURE raises rather than collapsing into None",
            raised,
            "None would read as 'N=1, allow' at the authority gate",
        )

        wc.effective_workspace_id = lambda *a, **k: None
        record(
            "a genuine absence still returns None (the real N=1 case)",
            resolve_purge_workspace("u1") is None,
        )
    finally:
        wc.effective_workspace_id = real

    acct = _src("routes/account.py")
    # Re-anchored 2026-08-20: this counted the literal `_resolve_or_deny(user_id)`,
    # a SPELLING that ADR-548 D8 correctly changed — the destructive paths must
    # now pass their request binding as a second argument. Counting the call by
    # AST asserts the PROPERTY (they route through the fail-closed resolver)
    # instead of pinning one argument list. Falsified by deleting a call site.
    import ast as _ast
    _calls = [
        n for n in _ast.walk(_ast.parse(acct))
        if isinstance(n, _ast.Call) and getattr(n.func, "id", None) == "_resolve_or_deny"
    ]
    record(
        "the destructive paths route through the fail-closed resolver",
        "def _resolve_or_deny(" in acct and len(_calls) >= 3,
        f"_resolve_or_deny call sites: {len(_calls)}",
    )
    stats_i = acct.index("def get_danger_zone_stats")
    record(
        "the READ-ONLY stats preview degrades instead of 500ing",
        "except WorkspaceResolutionError" in acct[stats_i : stats_i + 1200],
        "a preview must not fail the pane on a resolve error",
    )
    docs = _src("routes/documents.py")
    record(
        "the documents clear-gate is fail-closed too (same shape)",
        "WorkspaceResolutionError" in docs,
    )

    # ---- 3. count and delete tolerate the same things -------------------
    purge = _src("services/workspace_purge.py")
    ap = purge.index('deleted["action_proposals"]')
    record(
        "action_proposals: the delete tolerates what the count tolerates",
        "optional=True" in purge[ap : ap + 220],
        "count uses optional=True; a raising delete 500s a clear the UI called a no-op",
    )

    print("=" * 60)
    ok = sum(1 for _, o, _ in _results if o)
    print(f"purge scope + fail-closed gate: {ok}/{len(_results)} passed")
    print("=" * 60)
    return 0 if ok == len(_results) else 1


if __name__ == "__main__":
    sys.exit(run())
