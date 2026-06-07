"""ADR-322 regression gate — entity-layer pruning to the /proc core.

Asserts:
  (a) ENTITY_TYPES == {agent, platform, session, version} (document + task removed).
  (b) TABLE_MAP keys match — no document/task resolution.
  (c) _enrich_document_with_content is deleted.
  (d) SearchEntities scope enum is {agent, version, all} — no 'document'.
  (e) _search_document_content is deleted.
  (f) LookupEntity(ref='document:...') and ('task:...') return a redirect, not a
      raw parse error (the helpful steer ADR-322 D2 preserves).
  (g) EditEntity rejects document/task refs (not in TABLE_MAP).
  (h) grep gate — no live `document:` / `task:` entity-ref construction in the
      entity primitives (redirect-hint prose excepted).

Run: python -m pytest api/test_adr322_entity_pruning.py -q
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

API = Path(__file__).parent


def _read(*parts: str) -> str:
    return (API / Path(*parts)).read_text()


# ---------------------------------------------------------------------------
# (a) + (b) ENTITY_TYPES + TABLE_MAP = the /proc core
# ---------------------------------------------------------------------------

PROC_CORE = {"agent", "platform", "session", "version"}


def test_entity_types_is_proc_core():
    from services.primitives.refs import ENTITY_TYPES
    assert set(ENTITY_TYPES) == PROC_CORE, (
        f"ENTITY_TYPES must be the /proc core {PROC_CORE} (ADR-322 removed "
        f"document + task); got {set(ENTITY_TYPES)}"
    )


def test_table_map_matches_proc_core():
    from services.primitives.refs import TABLE_MAP
    assert set(TABLE_MAP) == PROC_CORE, (
        f"TABLE_MAP keys must match the /proc core; got {set(TABLE_MAP)}"
    )
    assert "document" not in TABLE_MAP and "task" not in TABLE_MAP


# ---------------------------------------------------------------------------
# (c) + (e) deleted enrichment / search helpers
# ---------------------------------------------------------------------------

def test_enrich_document_with_content_deleted():
    from services.primitives import refs
    assert not hasattr(refs, "_enrich_document_with_content"), (
        "_enrich_document_with_content must be deleted (ADR-322 — documents are files)."
    )


def test_search_document_content_deleted():
    from services.primitives import search
    assert not hasattr(search, "_search_document_content"), (
        "_search_document_content must be deleted (ADR-322 — use SearchFiles on uploads/)."
    )


# ---------------------------------------------------------------------------
# (d) SearchEntities scope enum drops document
# ---------------------------------------------------------------------------

def test_search_entities_scope_enum_drops_document():
    from services.primitives.search import SEARCH_ENTITIES_TOOL
    enum = SEARCH_ENTITIES_TOOL["input_schema"]["properties"]["scope"]["enum"]
    assert "document" not in enum, "SearchEntities scope must not include 'document' (ADR-322)."
    assert set(enum) == {"agent", "version", "all"}, (
        f"SearchEntities scope enum must be {{agent, version, all}}; got {enum}"
    )


# ---------------------------------------------------------------------------
# (f) LookupEntity redirects document:/task: refs (D2 helpful steer)
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_lookup_entity_task_ref_returns_redirect():
    from services.primitives.read import handle_lookup_entity
    auth = SimpleNamespace(user_id="u", client=None)
    res = _run(handle_lookup_entity(auth, {"ref": "task:weekly-brief"}))
    assert res["success"] is False
    assert res["error"] == "not_an_entity_type"
    # Steers to Schedule + the YAML paths, not a raw "Unknown entity type".
    assert "Schedule" in res["message"] and "_spec.yaml" in res["message"]


def test_lookup_entity_document_ref_returns_redirect():
    from services.primitives.read import handle_lookup_entity
    auth = SimpleNamespace(user_id="u", client=None)
    res = _run(handle_lookup_entity(auth, {"ref": "document:abc-123"}))
    assert res["success"] is False
    assert res["error"] == "not_an_entity_type"
    # Steers to SearchFiles/ReadFile on uploads/.
    assert "uploads/" in res["message"] and "ReadFile" in res["message"]


# ---------------------------------------------------------------------------
# (g) EditEntity rejects document/task (not in TABLE_MAP)
# ---------------------------------------------------------------------------

def test_edit_entity_rejects_non_proc_types():
    # parse_ref raises for unknown types now; EditEntity surfaces that cleanly.
    from services.primitives.refs import parse_ref
    import pytest
    for bad in ("document:abc", "task:weekly"):
        with pytest.raises(ValueError):
            parse_ref(bad)


# ---------------------------------------------------------------------------
# (h) grep gate — no live document:/task: entity-ref CONSTRUCTION in primitives
# ---------------------------------------------------------------------------

def test_no_live_document_or_task_ref_construction():
    # Scan the entity primitives for `f"document:{...}"` / `f"task:{...}"`
    # ref-construction (the old result-emit pattern). Redirect-hint prose that
    # NAMES the dissolved types is allowed (it steers the model away).
    import re
    offenders = []
    for parts in [
        ("services", "primitives", "search.py"),
        ("services", "primitives", "refs.py"),
        ("services", "primitives", "list.py"),
    ]:
        src = _read(*parts)
        # f-string ref construction: f"document:{...}" or f"task:{...}"
        if re.search(r'f"document:\{|f"task:\{|"ref": f"document:|"ref": f"task:', src):
            offenders.append("/".join(parts))
    assert not offenders, (
        f"These files still CONSTRUCT document:/task: entity refs (ADR-322 removed "
        f"the types): {offenders}"
    )
