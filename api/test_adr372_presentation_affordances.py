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
        "1 trace has an affordance; remember/recall do not (D1 — opt-in declaration)",
        aff.affordance_for("trace") is not None
        and aff.affordance_for("remember") is None
        and aff.affordance_for("recall") is None))

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

    # ---- Wire-shape assertions (need `mcp`) --------------------------------
    try:
        import asyncio
        from mcp.types import CallToolResult
        import mcp_server.server as s
    except Exception as exc:  # noqa: BLE001
        _skip("7-11 wire-shape assertions", f"(mcp unavailable: {exc})")
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

    # D4: no-affordance tools pass through unchanged (text-only default)
    results.append(_check(
        "9 remember/recall pass through as bare dict — unchanged text path (D1 default)",
        s._present("recall", sample) is sample and s._present("remember", sample) is sample))

    async def _wire():
        tools = {t.name: t for t in await s.mcp.list_tools()}
        # D2: trace tool DEFINITION carries _meta; remember does not
        def_ok = (tools["trace"].meta or {}).get("ui", {}).get("resourceUri", "").startswith("ui://") \
            and tools["remember"].meta is None
        # widget resource registered + serves the bundle with the right MIME
        res = {str(r.uri) for r in await s.mcp.list_resources()}
        served_ok = "ui://yarnnn/trace-timeline.html" in res
        blob = list(await s.mcp.read_resource("ui://yarnnn/trace-timeline.html"))[0]
        bundle_ok = blob.mime_type == registry.RESOURCE_MIME and "result.history" in blob.content
        return def_ok, served_ok, bundle_ok

    def_ok, served_ok, bundle_ok = asyncio.run(_wire())
    results.append(_check(
        "10 trace DEFINITION carries _meta (host registers template); remember has none (D2)",
        def_ok))
    results.append(_check(
        "11 widget served at ui:// with text/html;profile=mcp-app, binds history[] (§3/§7)",
        served_ok and bundle_ok))

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
