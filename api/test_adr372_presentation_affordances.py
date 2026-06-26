"""ADR-372 regression gate — presentation affordances on the interop face.

Asserts the always-attach `_meta` + always-text-channel contract (ADR-372 D4),
the per-tool affordance declaration (D1), the open-spec-primary `_meta` shape
(D2), and the kernel-boundary invariant (D5: presentation imports nothing from
`api/services/*`).

Run in the MCP venv (where `mcp` is installed):
    .venv-mcp/bin/python test_adr372_presentation_affordances.py

The two structural assertions (affordance map + no-kernel-import) run without
`mcp`; the wire-shape assertions need it. If `mcp` is absent the wire checks are
SKIPPED (reported), not failed — same posture as test_adr368_memory_surface.py.
"""

import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def _skip(label, detail=""):
    print(f"SKIP  {label}  {detail}")


def main():
    results = []

    # ---- D1: per-tool affordance declaration (data) ------------------------
    from mcp_server.presentation import affordances as aff
    results.append(_check(
        "1 all three memory verbs declare a widget affordance (D1 — opt-in declaration)",
        aff.affordance_for("trace") is not None
        and aff.affordance_for("recall") is not None
        and aff.affordance_for("remember") is not None))

    results.append(_check(
        "2 trace affordance → trace-timeline widget, interactive, text fallback (D1/D3)",
        (lambda a: a.widget == "trace-timeline" and a.fallback == "text" and a.interactive)(
            aff.affordance_for("trace"))))

    # ---- D5: kernel-boundary — presentation imports nothing from services/ --
    import inspect
    from pathlib import Path
    from mcp_server.presentation import registry
    from mcp_server.presentation.adapters import mcp_apps, openai as openai_adapter
    pres_dir = Path(aff.__file__).resolve().parent
    srcs = "\n".join(p.read_text() for p in pres_dir.rglob("*.py"))
    no_kernel_import = ("from services" not in srcs) and ("import services" not in srcs)
    results.append(_check(
        "3 presentation layer imports NOTHING from api/services/* (D5 kernel boundary)",
        no_kernel_import))

    # ---- D5: no vendor COUPLING in the primary adapter ---------------------
    # The invariant is "no vendor keys/logic in the open-spec adapter" — a prose
    # mention of the overlay in a docstring is fine. Check for the actual
    # coupling: OpenAI `_meta` key prefixes and overlay calls.
    # The real coupling signal is an OpenAI `_meta` key prefix as a string LITERAL
    # in the primary adapter (a prose mention of the overlay in a docstring is fine).
    primary_src = inspect.getsource(mcp_apps)
    vendor_coupling = ('"openai/' in primary_src) or ("'openai/" in primary_src)
    results.append(_check(
        "4 the open-spec PRIMARY adapter emits no OpenAI `_meta` key (D5 — one host per file)",
        not vendor_coupling))

    # ---- D2: open-spec-primary `_meta` shape -------------------------------
    def_meta = registry.tool_definition_meta("trace-timeline")
    resp_meta = registry.tool_response_meta("trace-timeline")
    served = registry.served_resource_meta("trace-timeline")
    results.append(_check(
        "5 _meta uses the open MCP Apps linkage ui.resourceUri → ui:// (D2)",
        def_meta.get("ui", {}).get("resourceUri", "").startswith("ui://")
        and resp_meta.get("ui", {}).get("resourceUri", "").startswith("ui://")))
    results.append(_check(
        "6 served-resource _meta carries domain + CSP (host submission requirement)",
        "domain" in served.get("ui", {}) and "csp" in served.get("ui", {})))

    # ---- ChatGPT binding (the live-finding fix): openai/outputTemplate ------
    # The open ui.resourceUri alone registered the template but ChatGPT rendered
    # text — ChatGPT binds via openai/outputTemplate on the tool DEFINITION
    # (verified against OpenAI's example server). Assert the load-bearing keys.
    results.append(_check(
        "6b tool-def _meta carries ChatGPT binding keys: openai/outputTemplate + widgetAccessible (live-finding fix)",
        def_meta.get("openai/outputTemplate", "").startswith("ui://")
        and def_meta.get("openai/widgetAccessible") is True))

    # ---- Wire-shape assertions (need `mcp`) --------------------------------
    try:
        import asyncio
        from mcp.types import CallToolResult
        import mcp_server.server as s
    except Exception as exc:  # noqa: BLE001
        _skip("7-12 wire-shape + diff-embed assertions", f"(mcp unavailable: {exc})")
        total, passed = len(results), sum(results)
        print(f"\n{passed}/{total} ADR-372 structural assertions pass (wire checks skipped)")
        sys.exit(0 if passed == total else 1)

    sample = {"subject": "x", "path": "/workspace/operation/x.md",
              "history": [{"authored_by": "operator", "when": "t", "change": "c", "revision_id": "r"}],
              "returned": 1, "explanation": "e"}

    # D4: trace result wraps to CallToolResult with _meta AND both text channels
    wrapped = s._present("trace", sample)
    results.append(_check(
        "7 trace result → CallToolResult with widget _meta attached (D4 always-attach)",
        isinstance(wrapped, CallToolResult)
        and wrapped.meta.get("ui", {}).get("resourceUri", "").startswith("ui://")))
    results.append(_check(
        "8 the full result is ALWAYS in the text channel — content + structuredContent (D4)",
        bool(wrapped.content) and wrapped.content[0].text
        and wrapped.structuredContent == sample))

    # D4: all three affordance tools wrap to CallToolResult with their OWN
    # widget binding; a tool with no affordance would pass through as a bare dict.
    from mcp_server.presentation import registry as _reg
    expected_uri = {
        "trace": "ui://yarnnn/trace-timeline.html",
        "recall": "ui://yarnnn/recall-cards.html",
        "remember": "ui://yarnnn/remember-receipt.html",
    }
    all_wrapped = True
    for n, uri in expected_uri.items():
        w = s._present(n, sample)
        ok = isinstance(w, CallToolResult) and bool(w.content) and w.structuredContent == sample \
            and (w.meta or {}).get("ui", {}).get("resourceUri") == uri
        if not ok:
            all_wrapped = False
            print(f"      [!] {n} did not wrap to its widget {uri}")
    results.append(_check(
        "9 each of remember/recall/trace wraps to CallToolResult with ITS OWN widget _meta (D1/D4)",
        all_wrapped))

    widget_uris = {
        "trace": "ui://yarnnn/trace-timeline.html",
        "recall": "ui://yarnnn/recall-cards.html",
        "remember": "ui://yarnnn/remember-receipt.html",
    }

    async def _wire():
        tools = {t.name: t for t in await s.mcp.list_tools()}
        # D2: ALL THREE tool DEFINITIONS carry the openai/outputTemplate binding.
        def_ok = all(
            (tools[n].meta or {}).get("openai/outputTemplate") == uri
            for n, uri in widget_uris.items()
        )
        # all three widget resources registered + serve a valid self-contained bundle.
        res = {str(r.uri) for r in await s.mcp.list_resources()}
        served_ok = all(uri in res for uri in widget_uris.values())
        bundle_ok = True
        for uri in widget_uris.values():
            blob = list(await s.mcp.read_resource(uri))[0]
            c = blob.content
            no_external = 'src="http' not in c and "src='http" not in c
            if not (
                blob.mime_type == registry.RESOURCE_MIME
                and c.lstrip().startswith("<!doctype html>")
                and no_external
                and "createRoot" in c
            ):
                bundle_ok = False
        return def_ok, served_ok, bundle_ok

    def_ok, served_ok, bundle_ok = asyncio.run(_wire())
    results.append(_check(
        "10 all three tool DEFINITIONS carry openai/outputTemplate (host registers each template; D2)",
        def_ok))
    results.append(_check(
        "11 all three widgets served at ui:// — self-contained HTML, React mount, skybridge MIME (§3/§7)",
        served_ok and bundle_ok))

    # ---- compose_trace embeds diffs server-side (zero-callback, ADR-372) ----
    from services import mcp_composition as mc
    import services.primitives.registry as preg

    async def _diff_embed():
        revisions = [
            {"id": "r3", "authored_by": "reviewer:ai", "created_at": "t3", "message": "tightened"},
            {"id": "r2", "authored_by": "operator", "created_at": "t2", "message": "edited"},
            {"id": "r1", "authored_by": "yarnnn:mcp", "created_at": "t1", "message": "created"},
        ]
        history = [{"authored_by": r["authored_by"], "when": r["created_at"],
                    "change": r["message"], "revision_id": r["id"]} for r in revisions]
        seen = []

        async def fake_diff(auth, name, args):
            seen.append((args["from_rev"], args["to_rev"]))
            return {"success": True, "diff": f"@@ {args['from_rev']}->{args['to_rev']}"}

        orig = preg.execute_primitive
        preg.execute_primitive = fake_diff
        try:
            await mc._embed_revision_diffs(None, "/workspace/operation/x.md", revisions, history)
        finally:
            preg.execute_primitive = orig
        # newest-first: r3 diffs vs r2, r2 vs r1, r1 (oldest) → None
        return (history[0]["diff"] and history[1]["diff"] and history[2]["diff"] is None
                and seen == [("r2", "r3"), ("r1", "r2")])

    results.append(_check(
        "12 compose_trace embeds each revision's diff-vs-predecessor; oldest is None (ADR-372 zero-callback)",
        asyncio.run(_diff_embed())))

    # ---- trace resolves to the file that IS the subject, not one that mentions it ----
    # Live finding: raw FTS top-hit picked 1-revision prose/report files over the
    # historied state file the subject names. resolve_trace_path does name-match
    # first, then history-weighted FTS. Structural + behavioral checks.
    import inspect as _inspect
    trace_src = _inspect.getsource(mc.compose_trace)
    results.append(_check(
        "13 compose_trace resolves via resolve_trace_path (name-match-first), not raw FTS top-hit",
        "resolve_trace_path" in trace_src and "resolve_memory_path" not in trace_src))

    # behavioral: a fake client where the subject's named file (SPY.yaml, 14 revs)
    # exists alongside a mention-file; name-match must win over any FTS path.
    class _FakeResp:
        def __init__(self, data=None, count=None):
            self.data = data or []
            self.count = count

    class _FakeQuery:
        def __init__(self, table, store):
            self._t, self._store, self._filters, self._ilike = table, store, {}, None
        def select(self, *a, **k): return self
        def eq(self, col, val): self._filters[col] = val; return self
        def in_(self, *a, **k): return self
        def ilike(self, col, pat): self._ilike = pat; return self
        def order(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            if self._t == "workspace_files":
                import re as _re
                # emulate SQL ILIKE: case-insensitive, % = any chars. Build the
                # regex by splitting on % and escaping the literal segments (so
                # `.` stays literal) — re.escape does NOT escape % in 3.11, so a
                # naive replace would leave the % in the pattern.
                pat = self._ilike or ""
                rx = _re.compile(
                    "^" + ".*".join(_re.escape(seg) for seg in pat.split("%")) + "$",
                    _re.IGNORECASE,
                )
                hits = [{"path": p} for p in self._store["files"] if rx.match(p)]
                return _FakeResp(data=hits)
            if self._t == "workspace_file_versions":
                path = self._filters.get("path")
                return _FakeResp(count=self._store["revs"].get(path, 0))
            return _FakeResp()

    class _FakeClient:
        def __init__(self, store): self._store = store
        def table(self, name): return _FakeQuery(name, self._store)

    class _FakeAuth:
        def __init__(self, store): self.client, self.user_id = _FakeClient(store), "u"

    def _resolve_behavior():
        store = {
            "files": ["/workspace/operation/trading/SPY.yaml",
                      "/workspace/operation/specs/regime-state.md"],
            "revs": {"/workspace/operation/trading/SPY.yaml": 14,
                     "/workspace/operation/specs/regime-state.md": 1},
        }
        # name-match for "SPY" should pick SPY.yaml (the file that IS the subject),
        # never regime-state.md (which merely mentions SPY).
        got = asyncio.run(mc.resolve_trace_path(_FakeAuth(store), "SPY"))
        return got == "/workspace/operation/trading/SPY.yaml"

    results.append(_check(
        "14 resolve_trace_path name-match picks the file the subject NAMES (SPY → SPY.yaml, not a mention-file)",
        _resolve_behavior()))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} ADR-372 assertions pass")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:  # noqa: BLE001
        pass
    main()
