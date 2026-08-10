"""ADR-543 regression gate — the file-native interop surface.

The memory ontology (remember / recall / trace, ADR-169→368) is retired IN
FULL; the surface is a binding of the kernel verb contract (ADR-512 D3):
open · list · search · save · history · share. This gate holds the re-cut:
the new verbs exist and behave file-natively, and the phantom-object
machinery cannot quietly return.

Pure-Python (no DB, no `mcp` package — composition-layer checks run live with
fakes; server.py is checked at source-text level). Roster == registered-tool-set
equality lives in test_adr533_participant_contract.py; the memory-verb absence
gate lives in test_adr512_open_verb.py #5 — neither is duplicated here.

Run: python3 test_adr543_file_native_surface.py  (from api/)

Asserts:
  1. compose_list EXISTS, accepts every root spelling as "the whole workspace",
     rejects malformed references, and returns workspace-relative paths with
     attribution (behavioral, faked substrate).
  2. compose_list reads WORKSPACE-scoped (_substrate_scope), never bare
     auth.user_id — the ADR-407/501 member read-path lesson.
  3. compose_search always emits `confidence` (even on a true miss) and every
     hit carries an open-able path + reference.
  4. compose_history is EXACT: malformed reference → invalid_reference;
     no revisions → found: false (never a fuzzy resolve).
  5. The retired machinery is absent (module-level tombstone).
"""

import asyncio
import inspect
import sys
import types


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


class _FakeResp:
    def __init__(self, data=None):
        self.data = data or []


class _FakeQuery:
    def __init__(self, store):
        self._store = store
        self._like = None

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def like(self, col, pat):
        self._like = pat
        return self

    def in_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def range(self, *a, **k):
        return self

    def execute(self):
        prefix = (self._like or "").rstrip("%")
        rows = [r for r in self._store if r["path"].startswith(prefix)]
        return _FakeResp(rows)


class _AdminUser:
    def __init__(self, name):
        self.user = types.SimpleNamespace(user_metadata={"full_name": name}, email=None)


class _FakeClient:
    def __init__(self, store):
        self._store = store
        # Principal display (2026-08-10): compose_list resolves member names
        # via the auth admin API; the fake resolves the one known member.
        self.auth = types.SimpleNamespace(
            admin=types.SimpleNamespace(
                get_user_by_id=lambda uid: _AdminUser("Kevin") if uid == "u-kvk"
                else (_ for _ in ()).throw(RuntimeError("no such user"))
            )
        )

    def table(self, name):
        return _FakeQuery(self._store)


def main():
    results = []
    from services import mcp_composition as m

    store = [
        {"path": "/workspace/operation/reports/q3.md", "content_bytes": 812,
         "updated_at": "2026-08-01T00:00:00Z",
         "workspace_file_versions": {"authored_by": "operator", "author_identity_uuid": "u-kvk", "created_at": "2026-08-01T00:00:00Z"}},
        {"path": "/workspace/inbound/uploads/deck.pdf", "content_bytes": 90210,
         "updated_at": "2026-07-20T00:00:00Z",
         "workspace_file_versions": {"authored_by": "yarnnn:mcp:claude.ai", "created_at": "2026-07-20T00:00:00Z"}},
    ]
    auth = types.SimpleNamespace(user_id="u", client=_FakeClient(store))

    # _substrate_scope resolves the caller's workspace via the DB; stub it for
    # the behavioral checks (the scoping DISCIPLINE is asserted structurally in 2).
    saved_scope = m._substrate_scope
    m._substrate_scope = lambda a: ("user_id", "u")
    try:
        # 1a — every root spelling lists the whole workspace
        roots = ["", "/", "/workspace", "/workspace/", "workspace",
                 "yarnnn://workspace/", None]
        root_ok = True
        for r in roots:
            res = asyncio.run(m.compose_list(auth, reference=r))
            if not (res.get("success") and res.get("count") == 2):
                root_ok = False
        results.append(_check(
            "1a every root spelling enumerates the whole workspace",
            root_ok))

        # 1b — a folder reference narrows; paths come back workspace-relative;
        # attribution is the RESOLVED display (2026-08-10 identity pass —
        # never the raw ledger string, never a UUID).
        res = asyncio.run(m.compose_list(auth, reference="operation"))
        files = res.get("files") or []
        results.append(_check(
            "1b folder reference narrows + paths are workspace-relative with resolved attribution",
            res.get("count") == 1
            and files[0]["path"] == "operation/reports/q3.md"
            and files[0]["authored_by"] == "Kevin"
            and files[0]["author_class"] == "member"
            and files[0]["reference"].startswith("yarnnn://workspace/")))

        # 1c — malformed references rejected, honest empty for a missing folder
        bad = asyncio.run(m.compose_list(auth, reference="https://x.com/a"))
        empty = asyncio.run(m.compose_list(auth, reference="no-such-folder"))
        results.append(_check(
            "1c foreign scheme rejected; missing folder returns an honest empty",
            bad.get("error") == "invalid_reference"
            and empty.get("success") and empty.get("count") == 0
            and "explanation" in empty))
    finally:
        m._substrate_scope = saved_scope

    # 2 — compose_list queries under _substrate_scope, never a bare user_id eq
    list_src = inspect.getsource(m.compose_list)
    results.append(_check(
        "2 compose_list reads workspace-scoped (_substrate_scope, not bare user_id)",
        "_substrate_scope" in list_src and '"user_id"' not in list_src))

    # 3 — compose_search: confidence ALWAYS present; hits carry path + reference
    import services.primitives.registry as preg

    async def _search_case(fake_result):
        saved = preg.execute_primitive

        async def fake_exec(auth_, name, args):
            return fake_result

        preg.execute_primitive = fake_exec
        try:
            return await m.compose_search(auth, query="alpha strategy")
        finally:
            preg.execute_primitive = saved

    miss = asyncio.run(_search_case({"success": True, "results": [], "count": 0}))
    hit = asyncio.run(_search_case({"success": True, "count": 1, "results": [
        {"path": "/workspace/operation/reports/q3.md", "content_preview": "text",
         "updated_at": "t", "similarity": 0.9}]}))
    results.append(_check(
        "3 search: confidence present on miss AND hit; hits carry path + reference",
        miss.get("confidence") == "none" and miss.get("results") == []
        and hit.get("confidence") in ("high", "ambiguous", "weak")
        and hit["results"][0]["path"] and hit["results"][0]["reference"].startswith("yarnnn://")))

    # 4 — compose_history is exact
    async def _history_case(reference, fake_lr=None):
        saved = preg.execute_primitive

        async def fake_exec(auth_, name, args):
            return fake_lr if fake_lr is not None else {"success": True, "revisions": []}

        preg.execute_primitive = fake_exec
        try:
            return await m.compose_history(auth, reference=reference)
        finally:
            preg.execute_primitive = saved

    bad_hist = asyncio.run(_history_case("https://x.com/a"))
    empty_hist = asyncio.run(_history_case("operation/nope.md"))
    results.append(_check(
        "4 history: malformed reference → invalid_reference; no revisions → found: false",
        bad_hist.get("error") == "invalid_reference"
        and empty_hist.get("success") and empty_hist.get("found") is False))

    # 5 — the tombstone: retired machinery absent from the module
    survivors = [n for n in (
        "dispatch_remember_this", "resolve_remember_path", "resolve_memory_path",
        "resolve_trace_path", "compose_recall", "compose_trace",
        "stamp_provenance", "DOMAIN_ALIASES",
    ) if hasattr(m, n)]
    results.append(_check(
        "5 retired memory machinery absent (ADR-543 tombstone)",
        not survivors, f"survivors={survivors}"))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} ADR-543 assertions pass")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
