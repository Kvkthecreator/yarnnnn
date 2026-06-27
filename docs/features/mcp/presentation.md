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
    # tool name → affordance. All three memory verbs render (2026-06-26):
    "trace":    Affordance(widget="trace-timeline",    fallback="text", interactive=True),
    "recall":   Affordance(widget="recall-cards",      fallback="text", interactive=False),
    "remember": Affordance(widget="remember-receipt",  fallback="text", interactive=False),
}
```

The three widgets, by display intent:
- **`trace-timeline`** — the revision chain as a provenance-colored vertical timeline with click-to-expand inline diffs (the differentiator).
- **`recall-cards`** — ranked excerpts as scannable cards: each with a provenance chip, domain, timestamp, the excerpt, and the source path.
- **`remember-receipt`** — a compact confirmation: ✓ saved, where it was filed, and the attributed source (makes the durable write *legible*).

All three are **display-only** (no buttons / no callbacks in v1) — pure presentation of returned substrate (D3), which keeps zero new action surface and zero review-risk. Shared widget code lives in `widgets/src/shared/` (the `useToolResult` reader, provenance bucketing, the `yz-` stylesheet); each widget is `widgets/src/<name>/`.

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
RESOURCE_MIME = "text/html+skybridge"   # ChatGPT's required widget MIME (§4 live-finding)

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

The neutral affordance is translated to a vendor `_meta` shape **at response-serialization time, by an adapter.** The `_meta` is attached **only to a widget-rendering host** (D4, amended 2026-06-27 — `hosts.renders_widgets(client_name)`; a non-rendering host like claude.ai gets the bare text result, because it does *not* ignore a widget pointer harmlessly — it tries to render it and fails). A host name appears in code in exactly two places: its adapter file (the vendor `_meta` shape) and `hosts.py` (whether it renders). The adapter still defaults to the open-spec shape and overlays the OpenAI keys (additive); the *gate* — not the adapter — decides whether that `_meta` reaches the host at all.

```python
# adapters/mcp_apps.py — PRIMARY (open spec)
def tool_definition_meta(widget) -> dict:
    return {"ui": {"resourceUri": widget.uri}}   # the ratified MCP Apps linkage
```

```python
# adapters/openai.py — OVERLAY (ChatGPT keys; LOAD-BEARING for render, see below)
def overlay_definition(meta: dict, widget) -> dict:
    meta = {**meta}
    meta["openai/outputTemplate"] = widget.uri        # ← the key ChatGPT binds on
    meta["openai/widgetAccessible"] = True
    meta["openai/toolInvocation/invoking"] = "…"
    meta["openai/toolInvocation/invoked"] = "…"
    return meta
```

> **LIVE-FINDING reconciliation (2026-06-26) — the overlay is NOT "sugar" for ChatGPT.** ADR-372 D2's original framing ("open-spec primary, ChatGPT extensions a thin overlay") is structurally right but understated the overlay's role. A live test found the widget *registered* (it appeared in ChatGPT's Templates list via `ui.resourceUri`) yet rendered **text, not the widget** — because **ChatGPT's renderer binds a tool to its template via `openai/outputTemplate` on the tool definition, not `ui.resourceUri`** (verified against OpenAI's own example server). And the served resource must use MIME **`text/html+skybridge`**, not the generic `text/html;profile=mcp-app`. So today, on ChatGPT, the OpenAI overlay keys + the skybridge MIME are **load-bearing** — without them nothing paints. We keep the open `ui.resourceUri` too (portable, ignored by ChatGPT). As the open MCP Apps spec converges with these keys, the overlay shrinks. **The blast radius of any vendor revision is still one adapter file** — the principle holds; only the "thin/optional" characterization was corrected.

---

## 5. The invariant guard (D4) — always-text-channel; `_meta` gated to widget hosts (AMENDED 2026-06-27)

> **Falsified live (2026-06-27).** The original §5 below assumed a text-only host *ignores* `_meta` harmlessly. **claude.ai does not.** Its connector reads the widget pointer, fetches the resource (served `text/html+skybridge` + `openai/*` keys), and fails with **"Unsupported UI resource content format"** — the OpenAI-Apps render path leaked into the Claude path because nothing decided per host whether to send the pointer. The write succeeded; the host surfaced a *render* error as a tool error. The fix is the escape hatch the original §5 anticipated (the blockquote): the resolved client id is a reliable-enough server-side signal, so we now **gate the pointer** while keeping the text channel unconditional.

The contract has two halves, and only one is unconditional:

```
tool returns
   │
   ├─ content / structuredContent  ← ALWAYS present, EVERY host (full, model-readable result)
   │                                  the text path is unconditionally intact
   │                                  → this is what protects the ADR-368 invariant
   │
   └─ _meta.ui.resourceUri         ← attached only when the tool has an affordance (D1)
                                      AND hosts.renders_widgets(client_name) is True
                                      ┌─ widget host (chatgpt ∈ WIDGET_RENDERING_HOSTS): gets the pointer, renders the widget
                                      └─ every other host (claude.ai, unidentified, new): NO pointer → clean text path
```

**The data is always in the text channel** (the ADR-368 invariant, unchanged). The **widget pointer is now allow-listed** (`presentation/hosts.py`): a host in `WIDGET_RENDERING_HOSTS` (today: `chatgpt`) gets it; everything else gets the bare text path — a **text-safe default**, so the worst case is "no widget," never "broken render." The gate keys on the same client id the MCP layer already derives (`mcp_composition.derive_client_name*`); a new rendering host opts in with one entry, verified end-to-end first. The served resource stays OpenAI-shaped (correct — only a host that got the pointer ever fetches it, and post-gate only ChatGPT does).

> Why an allow-list, not a deny-list: claude.ai's OAuth `client_id` is an opaque registration UUID and its User-Agent contains no "claude" — so it may resolve late or to "unknown." A deny-list would leak the widget to any host it failed to recognize. An allow-list with a text-safe default fails closed: an unrecognized host gets text, which every host renders. When MCP standardizes a real per-request rendering-capability bit, `renders_widgets()` is the one function to swap.

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
3. `server.py` — `@mcp.resource(...)` serving the built bundle (§3); on `trace`'s return, attach `_meta` via the adapter (§4) **only when `hosts.renders_widgets(client_name)`** (§5, amended 2026-06-27), with the full `history[]` always also in `content`/`structuredContent` for every host.
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
