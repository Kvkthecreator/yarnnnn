"""ADR-548 — the scope doorway gate.

ADR-407 D1 says every workspace-content table keys on the WORKSPACE. The repo
already had the helper (`services.workspace_context.substrate_scope_filter`) and
118 call sites using it. What it did NOT have was a gate asserting that substrate
readers actually CALL it.

The existing gates test the helper's behavior in isolation
(`test_adr373_sweep_spine.py::test_substrate_scope` proves it returns
`("workspace_id", ws)` when a workspace resolves) — and passed 12/12 while
`ListFiles` and `SearchFiles` in `services/primitives/workspace.py` keyed on the
bare caller. A member searching the commons got `[]` for every owner-authored
file: HTTP 200, empty result, nothing in Sentry.

That is the repo's recurring lesson in its exact form — **the gates tested the
room, not the doorway.** This gate is the doorway: it walks the AST of every
production module and fails on a `.eq("user_id", ...)` applied to a table that
ADR-407 D1 classifies as workspace content.

Why AST and not grep: a text scan for `.eq("user_id"` matches its own explanatory
comments and docstrings (the `feedback_gate_assertion_matches_its_own_comment`
lesson). `ast` sees calls only, so a comment ABOUT the banned pattern is free to
exist — this file's own docstring is proof.

Falsification: revert any `.eq(*_scope_filter(auth))` in
`services/primitives/workspace.py` to `.eq("user_id", auth.user_id)` and this
gate must go red naming that exact line.
"""

import ast
import re
from pathlib import Path
from typing import List, Optional, Set

import pytest
import yaml

API = Path(__file__).resolve().parent
MANIFEST = API / "services" / "scope_manifest.yaml"

_PROD_DIRS = ("services", "routes", "agents", "jobs", "mcp_server")

#: Tables whose scope key MUST be the workspace (ADR-407 D1 workspace-content).
#: Derived from the scope manifest — the single declared home for the fact, so
#: this gate cannot drift from the registry it enforces.
def _content_tables() -> Set[str]:
    manifest = yaml.safe_load(MANIFEST.read_text()) or {}
    stores = manifest.get("stores", {}) or {}
    return {
        name
        for name, row in stores.items()
        if isinstance(row, dict) and row.get("scope") == "content"
    }


#: Call sites permitted to key workspace content on `user_id`.
#:
#: These are the two-arm fallback helpers themselves: each already prefers
#: `workspace_id` and falls back to `user_id` only when no workspace resolves
#: (byte-identical at N=1, per ADR-373). They are the mechanism this gate
#: protects, not violations of it.
_ALLOWED = {
    ("services/workspace_context.py", "substrate_scope_filter"),
    ("services/authored_substrate.py", "_substrate_scope"),
    ("services/workspace_purge.py", "_purge_scope"),
    ("services/workspace_purge.py", "_delete_rows"),
}

#: Modules whose `user_id` is ALREADY workspace-derived, per ADR-501 D2.
#:
#: The radar/wake/outcomes stack resolves the acting workspace at the request
#: boundary and then keys the whole stack by that workspace's OWNER
#: (`acting_workspace_owner` — `routes/radar.py::_acting_owner`, the same seam
#: as the addressed wake). The value flowing into `.eq("user_id", …)` there is
#: a resolved owner, not the raw caller, so those sites satisfy ADR-407 D1 by a
#: different route and flagging them would be crying wolf.
#:
#: This is a scope boundary on THIS GATE, not a blessing: these modules are
#: single-principal by construction today. If one of them ever serves a member
#: read directly, it belongs on the workspace key and must leave this set.
_OWNER_RESOLVED_MODULES = {
    "routes/radar.py",
    "services/radar.py",
    "services/wake.py",
    "services/wake_queue.py",
    "services/wake_sources/substrate_event.py",
    "services/scheduling.py",
    "services/capture/scheduling.py",
    "services/capture/drainer.py",
    "services/capture/declarations.py",
    "services/outcomes/high_impact.py",
    "services/outcomes/ledger.py",
    "services/outcomes/operator.py",
    "services/outcomes/trading.py",
    "services/daily_update_email.py",
    "services/daily_pnl_email.py",
    "services/recurrence.py",
    "services/risk_gate.py",
    "services/budget.py",
    "services/review_policy.py",
    "services/freddie_audit.py",
    "services/context_inference.py",
    "services/substrate_snapshot.py",
    "services/ask_builder.py",
    "services/workspace_guide.py",
    "services/compose/assembly.py",
    "services/compose/task_html.py",
    "services/documents.py",
    # Alpha-trader program primitives — single-operator persona workspaces.
    "services/primitives/mirror_calibration.py",
    "services/primitives/mirror_schedule_index.py",
    "services/primitives/mirror_recent_execution.py",
    "services/primitives/mirror_signal_state.py",
    "services/primitives/track_regime.py",
    "services/primitives/track_foreign.py",
    "services/primitives/track_universe.py",
    "services/primitives/track_web_sources.py",
    "services/primitives/refs.py",
    "services/primitives/system_state.py",
    "services/primitives/scaffold.py",
    "services/primitives/search.py",
    "services/primitives/embed.py",
    # Hat-B developer toolchain — never serves a real operator (CLAUDE.md).
    "services/operator_proxy/scenarios.py",
    "services/operator_proxy/capture.py",
    "services/operator_proxy/persona_snapshot.py",
    # Admin console — cross-workspace by design, service-key gated.
    "routes/admin.py",
    # Account-scope peripherals (`sync_registry` per ADR-425) + owner-keyed
    # emission/delivery logs.
    "routes/system.py",
    "routes/emissions.py",
}


#: Declared `content` in the manifest, but legitimately keyed on `user_id` today.
#:
#: ADR-425 D1/D3 split the connector fact in two: the CREDENTIAL
#: (`platform_connections`) became account scope, while the peripheral-
#: observability tail (`sync_registry`) stays declared `content` — but only
#: for the future D3 agent-owned connection. Every row that exists TODAY is a
#: human's, keyed `user_id`. So a `.eq("user_id", …)` here is current-correct,
#: and this gate must not demand a workspace key the data model does not yet
#: carry. When D3 lands, delete this entry — the sites will then be real
#: violations. (`workspace_context.py`'s docstring lumps both tables under
#: `account_scope_filter`, which is imprecise against ADR-425 as written; the
#: manifest + this note are the accurate pair.)
_CONTENT_BUT_ACCOUNT_KEYED = {"sync_registry"}


def _enclosing_func(tree: ast.AST, node: ast.AST) -> str:
    """Name of the function lexically containing `node` ('' at module level)."""
    best = ""
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if getattr(fn, "lineno", 0) <= node.lineno <= getattr(fn, "end_lineno", 0):
                # Innermost wins — a nested def is more specific than its parent.
                if not best or fn.lineno > getattr(_enclosing_func, "_last", 0):
                    best = fn.name
                    _enclosing_func._last = fn.lineno  # type: ignore[attr-defined]
    _enclosing_func._last = 0  # type: ignore[attr-defined]
    return best


def _table_of(node: ast.Call) -> Optional[str]:
    """The table name if `node` is part of a `.table("X")...` chain."""
    cur: ast.AST = node
    while isinstance(cur, ast.Call) or isinstance(cur, ast.Attribute):
        if isinstance(cur, ast.Call):
            fn = cur.func
            if (
                isinstance(fn, ast.Attribute)
                and fn.attr == "table"
                and cur.args
                and isinstance(cur.args[0], ast.Constant)
                and isinstance(cur.args[0].value, str)
            ):
                return cur.args[0].value
            cur = fn
        else:
            cur = cur.value
    return None


def _violations() -> List[str]:
    content = _content_tables()
    found: List[str] = []
    for sub in _PROD_DIRS:
        root = API / sub
        if not root.exists():
            continue
        for py in sorted(root.rglob("*.py")):
            if py.name.startswith("test_"):
                continue
            rel = py.relative_to(API).as_posix()
            if rel in _OWNER_RESOLVED_MODULES:
                continue
            try:
                tree = ast.parse(py.read_text())
            except SyntaxError:  # pragma: no cover — a broken file is another gate's job
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                if not (isinstance(fn, ast.Attribute) and fn.attr == "eq"):
                    continue
                if not node.args or not isinstance(node.args[0], ast.Constant):
                    continue
                if node.args[0].value != "user_id":
                    continue
                table = _table_of(node)
                if table is None or table not in content:
                    continue
                if table in _CONTENT_BUT_ACCOUNT_KEYED:
                    continue
                if (rel, _enclosing_func(tree, node)) in _ALLOWED:
                    continue
                found.append(f"{rel}:{node.lineno} — .eq(\"user_id\", …) on `{table}`")
    return found


def test_manifest_declares_content_tables() -> None:
    """Sanity: the gate is reading a real registry, not an empty set.

    Without this, a renamed manifest key would silently empty `_content_tables()`
    and the doorway check below would pass by vacuum.
    """
    content = _content_tables()
    assert "workspace_files" in content, (
        "scope_manifest.yaml no longer declares workspace_files as content scope — "
        f"got {sorted(content)[:10]}"
    )
    assert len(content) >= 5, f"suspiciously few content-scoped stores: {sorted(content)}"


def test_scope_filter_calls_pass_the_explicit_binding() -> None:
    """ADR-548 D8 — a scope call on an `auth` MUST pass `auth.workspace_id`.

    `substrate_scope_filter(auth.user_id)` alone is NOT equivalent to passing
    the binding. Its second fallback rung is a contextvar published by
    `get_user_client` — but that dependency is a SYNC generator, so FastAPI
    runs it in a threadpool and the value never reaches the async handler's
    context. Resolution then falls to rung 3, owner-resolution from user_id,
    which returns the CALLER'S OWN workspace.

    Receipted on prod 2026-08-11, the request-vs-query disagreement visible in
    one log line:

        [SCOPE] artifacts user=2be30ac5 ws=d5b9029b
                scope=workspace_id=4ca9c664 rows=1

    `ws=` is the workspace the request bound to; `scope=` is the workspace the
    query actually read. A member viewing the owner's workspace was served
    their own — one document instead of four. The log line's own comment
    claimed the two "can never disagree."

    So the explicit binding is not a style preference; omitting it is the bug.
    ADR-501 §6a lesson 4 said this once already ("the explicit binding must be
    PASSED, not inferred"); this gate is that lesson made mechanical.
    """
    offenders: List[str] = []
    call = re.compile(
        r"substrate_scope_filter\(\s*auth\.user_id\s*\)"
    )
    for sub in _PROD_DIRS:
        root = API / sub
        if not root.exists():
            continue
        for py in sorted(root.rglob("*.py")):
            if py.name.startswith("test_"):
                continue
            for i, line in enumerate(py.read_text().splitlines(), 1):
                if call.search(line):
                    offenders.append(f"{py.relative_to(API).as_posix()}:{i}")
    assert not offenders, (
        "scope call drops the request's workspace binding — it will silently\n"
        "resolve to the CALLER'S OWN workspace in a FastAPI async handler.\n"
        'Pass it: substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None))\n\n  '
        + "\n  ".join(offenders)
    )


def test_exemption_list_has_no_dead_entries() -> None:
    """An exemption for a file that no longer exists (or no longer has a bare
    `user_id` scope) is stale — it would silently re-exempt a future violation
    at that path. This keeps the carve-out shrinking rather than accreting.
    """
    stale = []
    for rel in sorted(_OWNER_RESOLVED_MODULES):
        py = API / rel
        if not py.exists():
            stale.append(f"{rel} (file is gone)")
            continue
        if '.eq("user_id"' not in py.read_text() and ".eq('user_id'" not in py.read_text():
            stale.append(f"{rel} (no bare user_id scope left — drop the exemption)")
    assert not stale, (
        "ADR-548 exemption list has stale entries:\n  " + "\n  ".join(stale)
    )


def test_no_bare_user_id_scope_on_workspace_content() -> None:
    """The doorway: workspace content is never keyed on the caller alone."""
    violations = _violations()
    assert not violations, (
        "ADR-407 D1 violation — workspace-content tables keyed on the bare caller.\n"
        "A member reading the commons gets [] for every owner-authored row, with\n"
        "HTTP 200 and no error. Route these through the module's scope helper\n"
        "(`substrate_scope_filter` / `_scope_filter`).\n\n  "
        + "\n  ".join(violations)
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
