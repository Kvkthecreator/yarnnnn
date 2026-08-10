"""ADR-545 regression gate — the interop binding completes.

edit · delete · move bind the ADR-337 kernel verbs; `list` gains the change
feed (`since`) + honest pagination; `save` refuses the truncated-read
overwrite shape without stated intent; the searchable surface flips to a
deny-list (governance/ + system/ excluded, everything else in).

Pure-Python (no DB, no `mcp` package). Roster == registered-tool-set equality
lives in test_adr533_participant_contract.py; the D4 rendering-story coverage
extends there automatically.

Run: python3 test_adr545_binding_completion.py  (from api/)
"""

import asyncio
import inspect
import sys
import types


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def main():
    results = []
    from services import mcp_composition as m
    import services.primitives.registry as preg

    auth = types.SimpleNamespace(user_id="u", client=None)

    def _with_primitive(fake_exec, coro):
        async def run():
            saved = preg.execute_primitive
            preg.execute_primitive = fake_exec
            try:
                return await coro
            finally:
                preg.execute_primitive = saved
        return asyncio.run(run())

    # ── D1: edit — the anchored write ─────────────────────────────────────────
    calls = []

    async def fake_edit_ok(auth_, name, args):
        calls.append((name, args))
        return {"success": True, "path": f"/workspace/{args['path']}", "replacements": 2}

    res = _with_primitive(fake_edit_ok, m.compose_edit(
        auth, reference="yarnnn://workspace/operation/notes.md",
        old="a", new="b", replace_all=True))
    results.append(_check(
        "1a edit binds EditFile with the parsed reference + anchor args",
        res.get("success") and res.get("replacements") == 2
        and calls[0][0] == "EditFile"
        and calls[0][1]["path"] == "operation/notes.md"
        and calls[0][1]["old_string"] == "a" and calls[0][1]["replace_all"] is True))

    async def fake_edit_miss(auth_, name, args):
        return {"success": False, "error": "old_string_not_found", "message": "not found."}

    miss = _with_primitive(fake_edit_miss, m.compose_edit(
        auth, reference="operation/notes.md", old="zzz", new="b"))
    results.append(_check(
        "1b a missing anchor fails LOUDLY with re-anchor guidance (never guesses)",
        not miss.get("success") and miss.get("error") == "old_string_not_found"
        and "re-open" in (miss.get("message") or "").lower()))

    bad = asyncio.run(m.compose_edit(auth, reference="https://x.com/a", old="a", new="b"))
    results.append(_check(
        "1c edit rejects a foreign-scheme reference",
        bad.get("error") == "invalid_reference"))

    # ── D2: delete + move ─────────────────────────────────────────────────────
    async def fake_delete(auth_, name, args):
        return {"success": True, "path": f"/workspace/{args['path']}",
                "tombstone_revision_id": "t-1"}

    dres = _with_primitive(fake_delete, m.compose_delete(
        auth, reference="operation/scratch.md", message="superseded"))
    results.append(_check(
        "2a delete returns the tombstone receipt + retention explanation",
        dres.get("success") and dres.get("tombstone_revision_id") == "t-1"
        and "retained" in (dres.get("explanation") or "")))

    async def fake_move(auth_, name, args):
        return {"success": True}

    mres = _with_primitive(fake_move, m.compose_move(
        auth, reference="operation/a.md", new_reference="deals/a.md"))
    results.append(_check(
        "2b move parses both references and reports from→to",
        mres.get("success") and mres.get("from_path") == "/workspace/operation/a.md"
        and mres.get("path") == "/workspace/deals/a.md"))

    # ── D3: list — since + pagination plumbing ────────────────────────────────
    list_src = inspect.getsource(m.compose_list)
    results.append(_check(
        "3 list threads since (gte on updated_at) + range pagination + next_offset",
        'q.gte("updated_at"' in list_src.replace("            ", "")
        and ".range(offset, offset + page)" in list_src
        and '"next_offset"' in list_src))

    # ── D4: the honest save (truncation guard) ────────────────────────────────
    class _SizeQuery:
        def __init__(self, rows_by_table, table):
            self._rows, self._t = rows_by_table, table
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def order(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            return types.SimpleNamespace(data=self._rows.get(self._t, []))

    class _SizeClient:
        def __init__(self, rows_by_table): self._rows = rows_by_table
        def table(self, name): return _SizeQuery(self._rows, name)

    big_client = _SizeClient({
        "workspace_file_versions": [{"id": "head-1", "authored_by": "operator",
                                     "author_identity_uuid": None,
                                     "created_at": "t", "message": "m"}],
        "workspace_files": [{"content_bytes": m.OPEN_CONTENT_CAP + 5_000}],
    })
    big_auth = types.SimpleNamespace(user_id="u", client=big_client)
    saved_scope = m._substrate_scope
    m._substrate_scope = lambda a: ("user_id", "u")
    try:
        refused = asyncio.run(m.compose_save(
            big_auth, reference="operation/big.md", content="tiny",
            base_revision="head-1"))
        results.append(_check(
            "4a save over a beyond-open-cap file is REFUSED without stated intent",
            refused.get("error") == "large_file_overwrite"
            and "edit" in (refused.get("message") or "")))

        async def fake_write(auth_, name, args):
            return {"success": True}

        allowed = _with_primitive(fake_write, m.compose_save(
            big_auth, reference="operation/big.md", content="tiny",
            base_revision="head-1", confirm_full_replace=True))
        results.append(_check(
            "4b confirm_full_replace=true states intent and the save proceeds",
            allowed.get("success") is True))
    finally:
        m._substrate_scope = saved_scope

    # ── D5: the searchable surface is a deny-list ─────────────────────────────
    from services.primitives.embed import is_embed_eligible, is_searchable_root
    results.append(_check(
        "5a meaning folders + root guides are searchable; machine substrate is not",
        is_searchable_root("/workspace/deals/meridian/thesis.md")
        and is_searchable_root("/workspace/_playbook.md")
        and is_searchable_root("/workspace/operation/reports/q3.md")
        and is_searchable_root("/workspace/inbound/uploads/deck.extracted.md")
        and not is_searchable_root("/workspace/governance/_budget.yaml")
        and not is_searchable_root("/workspace/system/manifest.json")))
    results.append(_check(
        "5b searchable ≠ embeddable — the PAID path keeps its allow-list (ADR-325)",
        is_embed_eligible("/workspace/deals/meridian/thesis.md")[0] is False
        and is_embed_eligible("/workspace/operation/reports/q3.md", "x" * 300)[0] is True))

    # ── identity discipline carries to edit (structural) ──────────────────────
    from services.primitives import workspace as wsprim
    edit_src = inspect.getsource(wsprim.handle_edit_file)
    results.append(_check(
        "6 EditFile stamps author_identity_uuid for human-traceable species",
        "author_identity_uuid=identity_uuid" in edit_src
        and 'startswith("yarnnn:mcp:")' in edit_src))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} ADR-545 assertions pass")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
