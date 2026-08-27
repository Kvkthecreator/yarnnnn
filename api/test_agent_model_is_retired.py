"""The pre-ADR-596 agent model is retired, in code and in schema (2026-08-26).

WHAT THIS GUARDS
ADR-109 modelled an agent as a per-workspace DB row (`agents`) with a run
ledger (`agent_runs`), versions, quality scores and a review queue. ADR-596/600
replaced it: an agent is a BEING, one row in `services/agents_registry.AGENTS`,
static kernel data. Two models for one word is the ambiguity Singular
Implementation exists to prevent.

The retirement happened in two commits — the router + ManageAgent (083d25d),
then every remaining reader plus migration 248 (this one). This gate holds it:
a future session that reintroduces a table read, a deleted module, or one of
the retired primitives fails here rather than shipping a second model.

WHY IT CHECKS SOURCE TEXT AND NOT BEHAVIOUR
The tables are DROPPED. There is no live call to observe — a behavioural test
would need the schema it exists to assert the absence of. So the assertions are
over the source: no production module may query the tables, and the deleted
modules may not reappear.

⚠️ `routes/account.py`, `services/workspace_delete.py` and
`services/workspace_purge.py` are the interesting exemption that ISN'T one: a
purge must cover a table regardless of its row count, so they legitimately
listed these tables for as long as the tables existed. They no longer exist, so
those references are gone too — and this gate asserts that, because a purge
naming a dropped table raises rather than no-ops.

Run: python3 api/test_agent_model_is_retired.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent

_passed = 0
_failed = 0


def check(cond, msg):
    global _passed, _failed
    if cond:
        print(f"  ok   {msg}")
        _passed += 1
    else:
        print(f"  FAIL {msg}")
        _failed += 1


#: Directories that ship. Tests and one-shot scripts may still NAME the tables
#: in prose; production code may not query them.
_PROD_DIRS = ("services", "routes", "jobs", "agents", "mcp_server", "integrations")

#: The retired model's relations. SEVEN TABLES and ONE VIEW — the distinction
#: matters here and not only in the migration: `DROP TABLE` on a view is an
#: ERROR, so a gate that demanded `DROP TABLE agent_role_metrics` would be
#: demanding a statement that cannot run. Both this list and the migration were
#: written from a PostgREST roster, which does not report relkind; --dry-run is
#: what surfaced it (2026-08-26).
_RETIRED_TABLES = (
    "agents",
    "agent_runs",
    "agent_context_log",
    "agent_export_preferences",
    "agent_proposals",
    "agent_source_runs",
    "agent_validation_results",
)

#: The one VIEW, dropped with `DROP VIEW` and BEFORE the tables it reads.
_RETIRED_VIEWS = ("agent_role_metrics",)

#: SQL functions over the retired model. They split around the table drops:
#: a function taking/returning a table's ROW TYPE must go BEFORE it, while a
#: TRIGGER function must go AFTER the table carrying its trigger. That is why
#: the migration has four steps — see its step 2 / step 4 comments.
_RETIRED_FUNCTIONS = (
    "fill_agent_run_workspace_id",
    "get_agent_domain",
    "get_agent_export_history",
    "get_due_pulse_agents",
    "get_next_run_number",
    "get_suggested_agent_runs",
)

#: Modules deleted with the model. Reintroducing one means reintroducing the
#: model, so their ABSENCE is the assertion.
_DELETED_MODULES = (
    "routes/agents.py",
    "services/agent_creation.py",
    "services/working_memory.py",
    "services/feedback_distillation.py",
    "services/feedback_actuation.py",
    "services/feedback_engine.py",
    "services/primitives/coordinator.py",
    "services/primitives/search.py",
)

#: Primitives retired with it. Each was a tool an LLM could call against an
#: empty table — SearchEntities answered "Found 0 result(s)" to every query.
_RETIRED_PRIMITIVES = (
    "ManageAgent",
    "SearchEntities",
    "DiscoverAgents",
    "ReadAgentFile",
)


def _prod_files():
    for d in _PROD_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            yield p


def main() -> int:
    # 1. No production module queries a retired table.
    _all_relations = _RETIRED_TABLES + _RETIRED_VIEWS
    table_re = re.compile(
        r'\.(?:table|from_)\(\s*["\'](' + "|".join(_all_relations) + r')["\']\s*\)'
    )
    offenders = []
    scanned = 0
    for p in _prod_files():
        scanned += 1
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            m = table_re.search(line)
            if m:
                offenders.append(f"{p.relative_to(ROOT)}:{i} ({m.group(1)})")
    # Guard against a silent no-op scan (the gate-saw-nothing failure mode).
    check(scanned > 100, f"scanned {scanned} production modules")
    check(
        not offenders,
        "no production module queries a retired agent table"
        + (f" — FOUND: {offenders}" if offenders else ""),
    )

    # 2. The deleted modules stay deleted.
    for rel in _DELETED_MODULES:
        check(not (ROOT / rel).exists(), f"{rel} stays deleted")

    # 3. The retired primitives are off every roster and every handler map.
    sys.path.insert(0, str(ROOT))
    try:
        from services.primitives.registry import (  # noqa: E402
            CHAT_PRIMITIVES,
            FREDDIE_PRIMITIVES,
            HANDLERS,
            HEADLESS_PRIMITIVES,
        )
    except Exception as exc:  # pragma: no cover - import failure is the finding
        check(False, f"primitive registry imports ({exc})")
        return 1

    for label, roster in (
        ("chat", CHAT_PRIMITIVES),
        ("headless", HEADLESS_PRIMITIVES),
        ("freddie", FREDDIE_PRIMITIVES),
    ):
        names = {t["name"] for t in roster}
        present = sorted(n for n in _RETIRED_PRIMITIVES if n in names)
        check(
            not present,
            f"{label} roster carries no retired primitive"
            + (f" — FOUND: {present}" if present else ""),
        )
        # Every tool on a roster must still have a handler — the coherence a
        # partial removal breaks.
        missing = sorted(n for n in names if n not in HANDLERS)
        check(
            not missing,
            f"{label} roster: every tool has a handler"
            + (f" — MISSING: {missing}" if missing else ""),
        )

    handler_present = sorted(n for n in _RETIRED_PRIMITIVES if n in HANDLERS)
    check(
        not handler_present,
        "no retired primitive has a handler"
        + (f" — FOUND: {handler_present}" if handler_present else ""),
    )

    # 4. The entity layer no longer addresses agents.
    from services.primitives.refs import ENTITY_TYPES, TABLE_MAP  # noqa: E402

    check("agent" not in ENTITY_TYPES, "`agent` is not an entity type")
    check("version" not in ENTITY_TYPES, "`version` is not an entity type")
    check("agent" not in TABLE_MAP, "TABLE_MAP has no `agent` row")
    check("version" not in TABLE_MAP, "TABLE_MAP has no `version` row")
    # ⚠️ The two literals must agree — a type in one but not the other either
    # raises "No table mapping" or becomes silently unaddressable.
    check(
        set(ENTITY_TYPES) == set(TABLE_MAP),
        f"ENTITY_TYPES == TABLE_MAP keys (types={sorted(ENTITY_TYPES)}, "
        f"tables={sorted(TABLE_MAP)})",
    )

    # 5. Migration 248 exists and drops all eight tables.
    mig = REPO / "supabase" / "migrations" / "248_retire_the_pre_adr596_agent_model.sql"
    check(mig.exists(), "migration 248 exists")
    if mig.exists():
        sql = mig.read_text(encoding="utf-8")
        for t in _RETIRED_TABLES:
            check(
                re.search(rf"DROP TABLE IF EXISTS {t}\b", sql) is not None,
                f"migration 248 drops table `{t}`",
            )
        for v in _RETIRED_VIEWS:
            check(
                re.search(rf"DROP VIEW IF EXISTS {v}\b", sql) is not None,
                f"migration 248 drops VIEW `{v}` (not DROP TABLE — that errors)",
            )
        for fn in _RETIRED_FUNCTIONS:
            check(
                re.search(rf"DROP FUNCTION IF EXISTS {fn}\(", sql) is not None,
                f"migration 248 drops function `{fn}`",
            )
        # The ordering is load-bearing and was established by --dry-run: the
        # row-type functions precede the table drops, the trigger function
        # follows them. Assert the split rather than trusting the comment.
        _i_rowtype = sql.find("DROP FUNCTION IF EXISTS get_due_pulse_agents")
        _i_tables = sql.find("DROP TABLE IF EXISTS agents;")
        _i_trigger = sql.find("DROP FUNCTION IF EXISTS fill_agent_run_workspace_id")
        check(
            -1 < _i_rowtype < _i_tables < _i_trigger,
            "the function drops SPLIT around the table drops "
            f"(rowtype={_i_rowtype} tables={_i_tables} trigger={_i_trigger})",
        )
        # The dangling FK columns on LIVE tables are the reason this is a
        # migration and not a bare drop.
        for tbl, col in (
            ("chat_sessions", "agent_id"),
            ("execution_events", "agent_run_id"),
            ("export_log", "agent_run_id"),
            ("action_proposals", "agent_slug"),
        ):
            check(
                re.search(rf"ALTER TABLE {tbl}\s+DROP COLUMN IF EXISTS {col}", sql)
                is not None,
                f"migration 248 drops {tbl}.{col}",
            )

    # 6. NO LIVE WRITER STILL SENDS A DROPPED COLUMN.
    #
    # The gap this closes, found by DRIVING production (2026-08-27): §5 proved
    # migration 248 DROPS `action_proposals.agent_slug`, and every check passed
    # — while `_insert_proposal_row` still put `"agent_slug": …` in its insert
    # dict. PostgREST refuses the WHOLE statement on an unknown column, so every
    # gated substrate write funnelling through that one path returned
    # `execution_error`, and a member's Rewrite silently could not land.
    #
    # "0 non-null rows" (what 248 measured) says nothing about whether a WRITER
    # still names the column. A dropped column needs BOTH halves asserted: the
    # DDL removes it, and no live payload mentions it.
    #
    # DRIVEN, not grepped: the row builder is executed and its KEYS inspected.
    # A grep over the module would pass on a renamed local or a commented line;
    # only the dict that actually reaches `.insert()` is the column set.
    _dropped_cols = {
        "chat_sessions": "agent_id",
        "execution_events": "agent_run_id",
        "export_log": "agent_run_id",
        "action_proposals": "agent_slug",
        "session_messages": "thread_agent_id",
    }
    try:
        import asyncio
        from types import SimpleNamespace

        import services.primitives.propose_action as _pa

        _captured: dict = {}

        class _Table:
            def __init__(self, name): self.name = name
            def insert(self, row):
                _captured["table"] = self.name
                _captured["row"] = dict(row)
                raise _Stop()

        class _Stop(Exception):
            pass

        class _Client:
            def table(self, name): return _Table(name)

        _auth = SimpleNamespace(user_id="00000000-0000-0000-0000-000000000000",
                                client=_Client())
        try:
            asyncio.new_event_loop().run_until_complete(
                _pa.enqueue_gated_action(
                    _auth, primitive="EditFile", inputs={}, family="substrate",
                    decision_context={}, source=None, task_slug=None, ttl_hours=1,
                )
            )
        except _Stop:
            pass

        _row = _captured.get("row")
        check(_row is not None, "the proposal row builder (enqueue_gated_action) was driven")
        check(_captured.get("table") == "action_proposals",
              f"it inserts into action_proposals (got {_captured.get('table')!r})")
        if _row is not None:
            _bad = sorted(
                k for k, v in _dropped_cols.items()
                if _captured.get("table") == k and v in _row
            ) or ([_dropped_cols["action_proposals"]]
                  if "agent_slug" in _row else [])
            check(
                not _bad,
                "the action_proposals insert names no DROPPED column "
                f"(offending keys: {_bad}; row keys={sorted(_row)})",
            )
    except Exception as exc:  # noqa: BLE001
        check(False, f"could not drive the proposal row builder ({exc!r})")

    # The dead auth field goes with the column — 0 readers, and a field that
    # only ever fed a dropped column is not "unused", it is retired.
    _fa = (ROOT / "agents" / "freddie_agent.py")
    check(
        "agent_slug" not in _fa.read_text(encoding="utf-8"),
        "freddie_agent.py carries no agent_slug on the auth namespace",
    )

    print()
    print("=" * 66)
    print(f"agent-model retirement gate: {_passed} passed, {_failed} failed")
    print("=" * 66)
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
