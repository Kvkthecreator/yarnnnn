"""ADR-476 — Purge is workspace-scoped, and its surfaces say so.

  D1  the purge predicate keys on `workspace_id` (the substrate's binding unit
      since ADR-373/474), falling back to `user_id` only at N=1
  D2  clearing shared content is owner-grade — owner-default plus the
      extensible `workspace:clear` grant scope, never a role enum (ADR-405)
  D3  the workspace-content purges live on the workspace surface; the account
      surface keeps only genuinely account-scoped actions

The load-bearing one is D1: before this, a purge in a multi-member workspace
deleted only the rows the purging user authored, so every other member's files
survived a "clear workspace" — and were unreachable by any purge at all.

Run with `python3 test_adr476_purge_scope.py` (NOT pytest — check() gates print
✗ but a pytest run reports PASS; see MEMORY.md).
"""

import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_passed = 0
_failed = 0


def record(name: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        logger.info(f"✓ {name}" + (f": {detail}" if detail else ""))
    else:
        _failed += 1
        logger.error(f"✗ {name}" + (f": {detail}" if detail else ""))


class _Q:
    """Records the filters a purge query would apply."""

    def __init__(self, sink: Dict[str, Any]) -> None:
        self.sink = sink

    def eq(self, col: str, val: Any) -> "_Q":
        self.sink.setdefault("eq", {})[col] = val
        return self

    def like(self, *_a: Any) -> "_Q":
        return self

    def select(self, *_a: Any, **_k: Any) -> "_Q":
        return self

    def delete(self) -> "_Q":
        return self


def run() -> None:
    from services.workspace_purge import _purge_scope, resolve_purge_workspace

    WS = "wwwwwwww-0000-0000-0000-000000000000"
    UID = "uuuuuuuu-0000-0000-0000-000000000000"

    # -- D1: the predicate ---------------------------------------------------
    sink: Dict[str, Any] = {}
    _purge_scope(_Q(sink), UID, WS)
    record(
        "D1. with a workspace, the purge scopes on workspace_id",
        sink.get("eq") == {"workspace_id": WS},
        f"filters={sink.get('eq')}",
    )

    sink = {}
    _purge_scope(_Q(sink), UID, None)
    record(
        "D1. without a workspace, it falls back to user_id (N=1, byte-identical)",
        sink.get("eq") == {"user_id": UID},
        f"filters={sink.get('eq')}",
    )

    # -- D1: no `user_id` scoping left on the workspace-content tables -------
    purge_src = open(os.path.join(REPO, "api/services/workspace_purge.py")).read()

    # Every workspace-scoped delete must route through _purge_scope. A literal
    # `.eq("user_id", …)` outside the fallback helper is the regression.
    # Comments are stripped first — a source-grep that matches prose is the
    # false-positive class MEMORY.md warns about (gates grep text, not code).
    def _code_lines(src: str) -> List[str]:
        """Source with comments AND docstrings removed.

        Blanking docstrings matters: this module's own docstrings quote the
        `.eq("user_id", …)` pattern they describe fixing, and a naive grep
        matches the prose and reports a defect that isn't in the code.
        """
        import ast as _ast
        import io as _io
        import tokenize as _tok

        # Blank out every string-expression statement (docstrings) by line.
        drop: set = set()
        try:
            tree = _ast.parse(src)
            for node in _ast.walk(tree):
                if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Constant):
                    if isinstance(node.value.value, str):
                        drop.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
        except SyntaxError:
            pass

        out = []
        for i, ln in enumerate(src.splitlines(), start=1):
            if i in drop:
                continue
            out.append(ln.split("#", 1)[0])
        return out

    stray = [
        ln.strip()
        for ln in _code_lines(purge_src)
        if '.eq("user_id"' in ln and "return query.eq" not in ln
    ]
    record(
        "D1. no stray user_id filter survives in the purge service",
        not stray,
        f"stray={stray}" if stray else "all deletes route through _purge_scope",
    )

    # -- D1: the ADR-474 blob regression is fixed ----------------------------
    # Slice the code-only rendering of the WHOLE module (so docstrings are
    # already blanked), then take this function's span.
    purge_code = "\n".join(_code_lines(purge_src))
    i = purge_code.index("def _collect_blob_shas")
    body = purge_code[i : i + 1200]
    record(
        "D1. _collect_blob_shas is workspace-scoped (ADR-474 regression fixed)",
        "_purge_scope(" in body and '.eq("user_id"' not in body,
        "collected only the purging user's blobs before ADR-476",
    )

    # -- D1: the orchestrator resolves the workspace ONCE --------------------
    record(
        "D1. purge_l2_workspace resolves the workspace and threads it",
        "resolve_purge_workspace(user_id)" in purge_src
        and "workspace_id=ws" in purge_src,
        "",
    )

    # -- D1: user-scoped tables stay user-scoped -----------------------------
    # A member's notifications and MCP tokens are THEIRS (ADR-431); clearing the
    # workspace must not revoke another member's connectors.
    for table in ("mcp_oauth_access_tokens", "notifications", "event_trigger_log"):
        line = next(
            (ln for ln in purge_src.splitlines() if f'"{table}"' in ln and "_delete_rows" in ln),
            "",
        )
        record(
            f"D1. {table} stays user-scoped (a member's own)",
            "workspace_id=ws" not in line,
            line.strip()[:80],
        )

    # -- D2: the gate --------------------------------------------------------
    from services.principal_grants import (
        WORKSPACE_CLEAR_SCOPE,
        has_workspace_clear_authority,
    )

    record(
        "D2. the clear authority is a grant SCOPE, not a role enum (ADR-405)",
        WORKSPACE_CLEAR_SCOPE == "workspace:clear",
        WORKSPACE_CLEAR_SCOPE,
    )

    grants_src = open(os.path.join(REPO, "api/services/principal_grants.py")).read()
    fn = grants_src[grants_src.index("def has_workspace_clear_authority") :][:2000]
    record(
        "D2. owner-default is the ground truth (owner_id, not the owner grant)",
        'select("owner_id")' in fn,
        "two legacy workspaces have an owner with no owner-grant row",
    )
    record(
        "D2. the gate fails closed on lookup error",
        "return False" in fn.split("except")[-1],
        "",
    )

    acct_src = open(os.path.join(REPO, "api/routes/account.py")).read()
    for route in ("clear_work_history", "clear_workspace"):
        # Window must clear the long route docstrings — clear_workspace's gate
        # sits ~60 lines past the def.
        seg = acct_src[acct_src.index(f"async def {route}") :][:8000]
        record(
            f"D2. {route} gates on workspace-clear authority",
            "_require_workspace_clear_authority(" in seg,
            "",
        )

    # -- D3: the surfaces ----------------------------------------------------
    ws_page = open(
        os.path.join(REPO, "web/app/(authenticated)/workspace-settings/page.tsx")
    ).read()
    record(
        "D3. Workspace Settings mounts the danger zone",
        "WorkspaceDangerZone" in ws_page and '"danger"' in ws_page,
        "",
    )

    acct_page = open(
        os.path.join(REPO, "web/app/(authenticated)/settings/page.tsx")
    ).read()
    # Singular Implementation: the purge CARDS must not be duplicated here.
    record(
        "D3. Account settings no longer renders the L1/L2 purge buttons",
        'initiateDangerAction("work-history")' not in acct_page
        and 'initiateDangerAction("workspace")' not in acct_page,
        "the cards live only in WorkspaceDangerZone",
    )
    record(
        "D3. Account settings links across to the workspace door",
        "/workspace-settings?pane=danger" in acct_page,
        "",
    )

    dz = open(
        os.path.join(REPO, "web/components/workspace-concepts/WorkspaceDangerZone.tsx")
    ).read()
    record(
        "D3. the surface warns that clearing affects every member",
        "other member" in dz and "not just yours" in dz,
        "ADR-476 §4 falsifier made visible in the copy",
    )

    # -- live: the gate against real data ------------------------------------
    try:
        from services.supabase import get_service_client

        c = get_service_client()
        rows = (
            c.table("principal_grants")
            .select("principal_id, workspace_id, role")
            .eq("status", "active")
            .in_("role", ["owner", "member"])
            .execute()
        ).data or []
        by_ws: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            by_ws.setdefault(r["workspace_id"], []).append(r)
        multi = {w: g for w, g in by_ws.items() if len(g) > 1}

        if not multi:
            logger.warning("live gate check skipped — no multi-member workspace")
        for ws_id, grants in multi.items():
            owner_row = (
                c.table("workspaces").select("owner_id").eq("id", ws_id).execute()
            ).data
            if not owner_row:
                continue
            owner = str(owner_row[0]["owner_id"])
            record(
                f"D2 LIVE. owner may clear {ws_id[:8]}",
                has_workspace_clear_authority(owner, ws_id),
                "",
            )
            for g in grants:
                pid = str(g["principal_id"])
                if pid == owner:
                    continue
                record(
                    f"D2 LIVE. non-owner member {pid[:8]} may NOT clear",
                    not has_workspace_clear_authority(pid, ws_id),
                    "",
                )
    except Exception as exc:  # noqa: BLE001 — live checks are env-gated
        logger.warning(f"live checks skipped (no DB env): {exc}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        logger.exception("suite crashed")
        record("SUITE", False, f"crashed: {exc}")
    print("\n" + "=" * 60)
    print(f"ADR-476 purge-scope gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
    print("=" * 60)
    sys.exit(1 if _failed else 0)
