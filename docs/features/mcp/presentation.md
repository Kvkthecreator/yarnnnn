# MCP Presentation — Host-Negotiated Rich Rendering on the Interop Face

> **Status**: Proposed. **Governed by** [ADR-372](../../adr/ADR-372-presentation-affordances-interop-face.md). Sibling to [README.md](README.md) (framing), [tool-contracts.md](tool-contracts.md) (signatures), [workflows.md](workflows.md) (dynamics), [architecture.md](architecture.md) (dispatch/primitive mapping).
> **Updated**: 2026-06-26
> **Authors**: KVK, Claude

---

## 1. What this is (and what it is not)

The interop face (MCP) returns text today. Some hosts can render an **interactive widget** instead — ChatGPT (OpenAI Apps SDK), and any host implementing the open **MCP Apps spec** (SEP-1865, 2026-01-26). This doc defines how YARNNN serves rich rendering to those hosts **without** building a ChatGPT-specific product, coupling the kernel to a vendor, or violating the ADR-368 memory-first contract.

**It is NOT:**
- a separate "OpenAI Apps" product, directory, or service — an "app" is *this MCP server* + widget metadata, viewed through ChatGPT's lens;
- a replacement for MCP — the Apps SDK is a UI layer *on top of* MCP;
- a change to the moat, the substrate, the primitives, or the gate.

**It IS:** a per-tool, data-declared *presentation affordance*, served by the MCP server's resource surface, with one host-adapter at the edge. The third face of the one moat (ADR-372 §2).

> **The single most important rule (ADR-372 D3):** a widget renders the **returned substrate** — it never composes an answer, opinion, or judgment the server did not return. `recall`/`trace` still return material; the host (prose **and/or** widget) explains it — and the host LLM still narrates in prose even when a widget renders (the widget is additive, not a replacement). Break this and you silently undo ADR-368.

---

## 2. The affordance model (D1) — declaration, not code

Presentation is declared as data adjacent to each tool. A tool with no declaration is **text-only — the default, valid on every host.**

```python
# api/mcp_server/presentation/affordances.py  (proposed)
# Neutral, host-agnostic. No OpenAI/ChatGPT names appear here.

AFFORDANCES: dict[str, Affordance] = {
    # tool name → affordance
    "trace": Affordance(
        widget="trace-timeline",     # registry id → ui:// resource
        fallback="text",             # always; text path is never removed
        interactive=True,            # widget may call back into tools (D6)
    ),
    # "recall": Affordance(widget="recall-cards", fallback="text", interactive=False),
    # "remember": (none) — a fire-and-forget write; text confirmation is correct.
}
```

`Affordance` is a frozen dataclass. **Why data, not inline `_meta`:** the three verbs are subject to change (README §"Why these three verbs"); the affordance *mechanism* is the durable layer. A new verb opts in with one dict entry; a removed verb drops one. No tool body is rewired, and the vendor `_meta` shape is generated downstream (§4), never authored here.

---

## 3. The widget registry + bundle location (D5)

Widget bundles are **frontend artifacts** (HTML/JS, typically React), built independently and **served by the MCP server's resource surface** — never importing kernel Python.

```
api/mcp_server/
├── server.py                 # tools + resource registration (existing)
├── presentation/             # ← NEW: the whole presentation layer (interop face)
│   ├── affordances.py        # the AFFORDANCES declaration (§2)
│   ├── registry.py           # widget id → ui:// uri, mime, csp/domain meta
│   └── adapters/
│       ├── mcp_apps.py       # PRIMARY: open MCP Apps spec _meta shape (D2)
│       └── openai.py         # OVERLAY: ChatGPT _meta sugar (D2); window.openai
│                             #          feature-detection lives in the widget
└── widgets/                  # ← NEW: a mini-web/, its OWN build (npm + esbuild)
    ├── package.json
    ├── build.mjs            # esbuild → single self-contained .html per widget
    ├── tsconfig.json
    ├── src/trace-timeline/  # the first widget (§7): index.tsx, TraceTimeline.tsx,
    │                        #   types.ts, useToolResult.ts, styles.ts
    └── dist/                # built bundles, COMMITTED + served as ui:// resources
        └── trace-timeline.html
```

The registry maps a widget id to its served resource:

```python
# registry.py (proposed)
RESOURCE_MIME = "text/html;profile=mcp-app"   # MCP Apps standard MIME

WIDGETS = {
    "trace-timeline": Widget(
        uri="ui://yarnnn/trace-timeline.html",
        bundle_path="widgets/dist/trace-timeline.html",
        # served-resource _meta.ui — domain + CSP are required for ChatGPT submission
        domain="https://mcp.yarnnn.com",
        csp_connect=["https://mcp.yarnnn.com"],
    ),
}
```

Served via the existing SDK (confirmed available, mcp 1.28.0):

```python
# server.py (proposed addition)
@mcp.resource("ui://yarnnn/trace-timeline.html", mime_type=RESOURCE_MIME)
def trace_timeline_widget() -> str:
    return (WIDGETS["trace-timeline"].bundle_path).read_text()  # the built HTML/JS
```

No new Render service, no SDK upgrade — `FastMCP.resource()` and `custom_route()` are both present in the vendored mcp 1.28.0.

---

## 4. The adapter layer (D2, D5) — one host name per file

The neutral affordance is translated to a vendor `_meta` shape **at response-serialization time, by an adapter.** The `_meta` is attached *unconditionally* (D4 — there is no server-side host handshake to gate on; a non-rendering host simply ignores it). A host name appears in code in exactly one place: its adapter file. Which adapter to use can default to the open-spec shape and overlay the OpenAI sugar always (it is additive and ignored elsewhere), or be selected by a best-effort `clientInfo` sniff purely as an optimization — never as a correctness dependency.

```python
# adapters/mcp_apps.py — PRIMARY (open spec)
def tool_meta(affordance: Affordance) -> dict:
    w = WIDGETS[affordance.widget]
    return {"ui": {"resourceUri": w.uri}}   # the ratified MCP Apps linkage
```

```python
# adapters/openai.py — OVERLAY (thin, ChatGPT-only sugar over the primary)
def tool_meta(affordance: Affordance) -> dict:
    meta = mcp_apps.tool_meta(affordance)            # start from the open shape
    meta["openai/widgetDescription"] = "..."         # vendor nicety, additive
    meta["ui"]["visibility"] = ["model", "app"]
    return meta
```

When MCP Apps standardizes a key OpenAI currently does its own way, the open adapter gains it and the overlay shrinks. **The blast radius of any vendor revision is one adapter file.**

---

## 5. The invariant guard (D4) — always-attach `_meta`, always-text-channel

The original instinct here was to *negotiate*: detect a rich-render host at `initialize` and only then attach `_meta`. **The ecosystem does not support that** (verified 2026-06-26 against OpenAI's docs + the Apps SDK examples): MCP servers attach `_meta.ui.resourceUri` **unconditionally**, and the host renders it or ignores it. There is no documented server-side host-capability handshake to gate on. OpenAI's guidance is *feature-detect widget-side* (`window.openai` graceful degradation), not gate server-side.

So the invariant is protected by a simpler and stronger mechanism than negotiation:

```
tool returns
   │
   ├─ content / structuredContent  ← ALWAYS present (full, model-readable result)
   │                                  the text path is unconditionally intact
   │                                  → this is what protects the ADR-368 invariant
   │
   └─ _meta.ui.resourceUri         ← attached whenever the tool has an affordance
                                      ┌─ rich host (ChatGPT, MCP-Apps): renders the widget
                                      └─ text host (claude.ai, plain): ignores _meta harmlessly
                                         (_meta is non-semantic to a host that doesn't read it)
```

**The data is always in the text channel.** That is the contract — not detection. A text-only host is never worse off (it gets the full result as prose, exactly the ADR-368 path); a rich host gets the widget *in addition*. There is no "broken half-render" failure mode because the widget never *replaces* the text — it accompanies it (D3: the model still narrates).

> Optional optimization, not a dependency: a best-effort `clientInfo` sniff *may* select the OpenAI overlay vs the bare open-spec shape. But correctness must never depend on it — mis-identifying a host must, at worst, send a slightly-less-tailored but still-valid `_meta` that the host ignores or renders. Should a reliable server-side capability signal later standardize, the framework can opt into suppressing `_meta` for text-only hosts as a bandwidth optimization; it must never become the thing the text path *relies on*.

---

## 6. The widget↔tool callback contract (D6)

An interactive widget *may* call back via JSON-RPC `tools/call` over `postMessage` (MCP Apps bridge). When it does, it calls the **same** `remember`/`recall`/`trace` tools — through the **same** `execute_primitive()` gate, the **same** ADR-307 permission taxonomy, the **same** audit trail. There is no widget-only privileged path. A widget cannot reach substrate a normal tool call couldn't.

```javascript
// inside the widget bundle — e.g. fetch more revisions on scroll
window.parent.postMessage({
  jsonrpc: "2.0", id: 1, method: "tools/call",
  params: { name: "trace", arguments: { subject, limit: 30 } }
}, "*");
```

The result arrives back as a `ui/notifications/tool-result` message; the widget re-renders. Same data contract as the text path.

> **Prefer embedding over calling back when the data set is bounded.** The `trace` widget's click-to-diff needs the diff for each revision — but rather than a per-click `tools/call`, `compose_trace` **embeds each revision's diff inline** in the result (server-side, via the existing `DiffRevisions` primitive). The widget expands a diff with *zero* callback. This keeps the ADR-368 three-verb surface intact (no 4th MCP tool), works on every host (even ones without the callback bridge), and is more robust. Reserve the callback path for genuinely unbounded interaction (infinite scroll, search-within) where embedding the whole set is impractical.

---

## 7. The `trace` timeline widget (the reference affordance — IMPLEMENTED)

`trace` is the first widget because it is the differentiator (the ADR-209 authored revision chain a plain storage connector cannot show), and a who-changed-what-when timeline is inherently visual.

**The data `compose_trace` returns** (`api/services/mcp_composition.py`) — each revision now carries its embedded diff-vs-predecessor (§6); no kernel change:

```python
{
  "success": True, "subject": "...", "path": "/workspace/operation/...",
  "history": [                       # newest first
    {"authored_by": "reviewer:ai", "when": "2026-06-25T...", "change": "...",
     "revision_id": "...", "diff": "@@ -1 +1 @@\n-old\n+new"},     # diff vs predecessor
    {"authored_by": "yarnnn:mcp",  "when": "2026-06-24T...", "change": "...",
     "revision_id": "...", "diff": None},                          # oldest → no predecessor
  ],
  "returned": 2, "citations": ["/workspace/operation/..."], "explanation": "..."
}
```

**What the slice ships (all in `api/mcp_server/`, none in the kernel):**

1. `presentation/affordances.py` — the `"trace"` entry (§2).
2. `presentation/registry.py` — `"trace-timeline"` → `ui://yarnnn/trace-timeline.html` (§3).
3. `server.py` — `@mcp.resource(...)` serving the built bundle (§3); on `trace`'s return, attach `_meta` via the adapter (§4) unconditionally, with the full `history[]` always also in `content`/`structuredContent` (§5).
4. `compose_trace._embed_revision_diffs` — embeds each revision's diff inline server-side (§6), so click-to-diff needs zero callback.
5. `widgets/src/trace-timeline/` — a React (TS) bundle that:
   - renders `history[]` as a vertical timeline, newest first;
   - colors each node by `authored_by` bucket (`operator` / `reviewer` / `mcp` / `agent` / `system`) — the cross-LLM provenance made visual;
   - shows each revision's `change` message + timestamp, and a **show-changes** toggle that expands the embedded unified `diff` (added/removed lines colored), zero callback;
   - renders the `explanation` as a caption — **it does not author new prose** (D3).
6. `widgets/package.json` + `build.mjs` (esbuild) → single self-contained `widgets/dist/trace-timeline.html`.

### Building the widget

The bundle is built **locally / at dev time** and the single-file `dist/` output is **committed** (a `.gitignore` exception overrides the global `dist/` rule). The Python MCP service serves the committed file verbatim at runtime — **it does not run this build**, so a stale `dist/` ships a stale widget. Rebuild after editing `src/`:

```bash
cd api/mcp_server/widgets
npm install          # first time only
npx tsc --noEmit     # type-check
npm run build        # → dist/trace-timeline.html (React inlined, minified, self-contained)
```

**Return-shape contract:** the full result is in `structuredContent` *and* `content` (so a text host and the model still reason over it); the widget reads the same fields from the `ui/notifications/tool-result` bridge notification (with a `window.openai.toolOutput` fast-path for first paint). The widget is a *richer view of the returned `history[]`* — nothing more.

**What the slice deliberately does NOT do:** synthesize a narrative of the evolution (that's the host LLM's job, prose or not — D3), add a 4th MCP tool / second data path, or touch `execute_primitive`/`api/services/*`.

---

## 8. Future-proofing checklist (why this scales for the life of the service)

| Future event | What changes | What does NOT change |
|---|---|---|
| The three verbs change / a 4th is added | one `AFFORDANCES` dict entry | mechanism, registry, adapters, kernel |
| OpenAI revises `_meta.ui.*` | `adapters/openai.py` only | open-spec primary, affordances, kernel |
| MCP Apps spec revs a key | `adapters/mcp_apps.py` only | overlay shrinks, affordances, kernel |
| Gemini / new host adds widgets | one new adapter file | widget bundles reused as-is |
| A new widget (e.g. `recall-cards`) | one registry + one affordance entry + one bundle | every other tool |
| A server-side host-capability signal standardizes | opt into suppressing `_meta` for text-only hosts as an optimization | the always-text-channel contract (text path never depends on it) |
| The kernel/primitives evolve | nothing in presentation (tools call `execute_primitive` unchanged) | the whole presentation layer |

The invariants that must never erode: **text is the default and always valid (D1/D4); the kernel never learns a host exists (D5/C3); a widget renders returned substrate, never composed judgment (D3); a callback is the same gated tool (D6).**
