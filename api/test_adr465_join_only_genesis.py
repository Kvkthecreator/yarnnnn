"""ADR-465 D2 regression gate — join-only genesis (Phases B/C).

Ratified 2026-08-03 (operator delegation). Structural checks, no DB.

Run: python3 test_adr465_join_only_genesis.py  (from api/)

Asserts:
  1. Migration 233 retires the migration-106 auto-mint (trigger + function),
     and no later migration re-creates them.
  2. Owner-genesis is lazy + explicit: ensure_owner_workspace exists, is
     idempotent-shaped (uncached re-check before insert), clears the resolver
     cache on mint, and the ONLY route that calls it is the cold-user door
     (/workspace/state) guarded on "no workspace resolved".
  3. The zero-or-one tolerance fixes: workspace_context fallback,
     _resolve_caller_workspace, and the MCP oauth hook all use the
     member-aware resolver (resolve_workspace_for_principal), not the
     owner-only one.
  4. No accept path mints a workspace: workspace_shares has no workspaces
     insert; join-only is real.
"""

import inspect
import os
import re
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def main():
    results = []

    # 1. the trigger is retired and stays retired
    with open("../supabase/migrations/233_adr465_join_only_genesis.sql", encoding="utf-8") as f:
        mig = f.read()
    results.append(_check(
        "1a migration 233 drops trigger + function",
        "DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users" in mig
        and "DROP FUNCTION IF EXISTS public.handle_new_user()" in mig))
    recreators = []
    mig_dir = "../supabase/migrations"
    for name in sorted(os.listdir(mig_dir)):
        try:
            num = int(name.split("_")[0])
        except ValueError:
            continue
        if num <= 233 or not name.endswith(".sql"):
            continue
        with open(os.path.join(mig_dir, name), encoding="utf-8") as f:
            body = f.read()
        if re.search(r"CREATE\s+(OR\s+REPLACE\s+)?TRIGGER\s+on_auth_user_created", body, re.I) or \
           re.search(r"CREATE\s+(OR\s+REPLACE\s+)?FUNCTION\s+(public\.)?handle_new_user", body, re.I):
            recreators.append(name)
    results.append(_check(
        "1b no later migration re-creates the auto-mint", not recreators, str(recreators)))

    # 2. lazy explicit genesis
    from services import supabase as sb
    results.append(_check(
        "2a ensure_owner_workspace EXISTS", hasattr(sb, "ensure_owner_workspace")))
    src = inspect.getsource(sb.ensure_owner_workspace)
    results.append(_check(
        "2b idempotent-shaped (uncached re-check precedes the insert) + cache cleared on mint",
        src.index('.select("id").eq("owner_id"') < src.index(".insert(")
        and src.count("cache_clear()") >= 2))
    with open("routes/workspace.py", encoding="utf-8") as f:
        ws_route = f.read()
    results.append(_check(
        "2c the cold-user door: /workspace/state calls it, guarded on no-workspace",
        "if not auth.workspace_id:" in ws_route
        and "ensure_owner_workspace(auth.user_id)" in ws_route))
    # the only production caller is the state route (+ the definition itself)
    # RE-CUT 2026-08-18: this grepped for the NAME, so any file that merely
    # DISCUSSES the cold-user door (services/workspace_genesis.py's docstring
    # compares itself against it) read as a caller. Assert on actual CALL sites
    # via AST instead — the invariant is unchanged, the mechanism can now tell
    # code from documentation. Also drops the .pyc hits the -rl grep returned.
    import ast as _ast
    callers = []
    for _root, _dirs, _files in os.walk("."):
        if any(sk in _root for sk in ("__pycache__", "node_modules", ".git")):
            continue
        if not _root.startswith(("./routes", "./services", "./mcp_server", "./agents")):
            continue
        for _f in _files:
            if not _f.endswith(".py") or _f == "supabase.py":
                continue
            _p = os.path.join(_root, _f)
            try:
                _t = _ast.parse(open(_p, encoding="utf-8").read())
            except SyntaxError:
                continue
            for _n in _ast.walk(_t):
                if isinstance(_n, _ast.Call):
                    _fn = _n.func
                    _nm = getattr(_fn, "id", None) or getattr(_fn, "attr", None)
                    if _nm == "ensure_owner_workspace":
                        callers.append(_p.lstrip("./"))
                        break
    callers = sorted(set(callers))
    results.append(_check(
        "2d no other production CALLER (accept/invite paths never mint)",
        callers == ["routes/workspace.py"], str(callers)))

    # 3. member-aware tolerance at the three audited sites
    from services import workspace_context as wc
    wc_src = inspect.getsource(wc.effective_workspace_id)
    results.append(_check(
        "3a workspace_context fallback is member-aware",
        "resolve_workspace_for_principal" in wc_src
        and "resolve_owner_workspace_id" not in wc_src))
    m = re.search(r"def _resolve_caller_workspace.*?\n\n", ws_route, re.S)
    results.append(_check(
        "3b _resolve_caller_workspace is member-aware",
        m and "resolve_workspace_for_principal" in m.group(0)))
    with open("mcp_server/oauth_provider.py", encoding="utf-8") as f:
        oauth_src = f.read()
    results.append(_check(
        "3c MCP oauth grant hook is member-aware",
        "resolve_workspace_for_principal(user_id)" in oauth_src))

    # 4. join-only is real: no accept path mints a workspace (the grant insert
    # lives in principal_grants; accept itself only updates the share row).
    from services import workspace_shares as shares
    results.append(_check(
        "4 accept_share never inserts any row itself (no workspace mint)",
        ".insert(" not in inspect.getsource(shares.accept_share)))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
