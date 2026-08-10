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

> **The single most important rule (ADR-372 D3):** a widget renders the **returned substrate** — it never composes an answer, opinion, or judgment the server did not return. `search`/`history` still return material; the host (prose **and/or** widget) explains it — and the host LLM still narrates in prose even when a widget renders (the widget is additive, not a replacement). Break this and you silently undo the retrieval-not-delegation line.

---

## 2. The affordance model (D1) — declaration, not code

Presentation is declared as data adjacent to each tool. A tool with no declaration is **text-only — the default, valid on every host.**

```python
# api/mcp_server/presentation/affordances.py  (proposed)
# Neutral, host-agnostic. No OpenAI/ChatGPT names appear here.

AFFORDANCES: dict[str, Affordance] = {
    "history":  Affordance(widget="history-timeline", fallback="text", interactive=True),
    "search":   Affordance(widget="search-results",    fallback="text", interactive=False),
    # ADR-533 D4 (2026-08-07) — the file verbs join the roster:
    "save":     Affordance(widget="save-receipt",      fallback="text", interactive=False),
    "open":     Affordance(widget="file-header",       fallback="text", interactive=False),
}

TEXT_ONLY: dict[str, str] = {          # ADR-533 D4 — a DECLARED decision, not a gap
    "share": "the result is a link + a reach level — one line the host relays verbatim",
}
```

> **ADR-533 D4 — why the roster was incomplete, and the rule that keeps it honest.**
> Until 2026-08-07 the roster held only the three MEMORY verbs; the three ADR-512 FILE
> verbs (`open`/`save`/`share`) had no entries. On ChatGPT — the only host with
> `renders_widgets=True` — the memory verbs rendered rich and the file verbs rendered
> bare text, so the OpenAI Apps face still presented yarnnn as a *memory* product, the
> costume ADR-512 §10 declared ended. **Not every verb earns a widget** (text-only has
> always been valid here) — but a deliberate text-only decision and an unfinished one are
> indistinguishable in an empty map. So every rostered verb must now appear in
> `AFFORDANCES` **or** `TEXT_ONLY` *with its reason* — exactly one, never both, never
> neither — asserted by `test_adr533_participant_contract.py`, which also fails if a
> declared widget's `dist/` bundle was never built.

The widgets, by display intent:
- **`history-timeline`** — the revision chain as a provenance-colored vertical timeline with click-to-expand inline diffs (the differentiator).
- **`search-results`** — ranked matches as scannable cards: each with a timestamp, the excerpt, and the openable source path.
- **`save-receipt`** (ADR-533) — exists for the **conflict**: on `stale_write`/`base_required` it shows who holds the head, when, what they called their change, and that nothing was overwritten. The success path is a small receipt.
- **`file-header`** (ADR-533) — the opened file's **identity**: name, provenance chip for whose version it is, timestamp, revision count. Deliberately **not** the content — the host renders text better, and the attribution is what a storage connector cannot show.

All are **display-only** (no buttons / no callbacks in v1) — pure presentation of returned substrate (D3), which keeps zero new action surface and zero review-risk. Shared widget code lives in `widgets/src/shared/` (the `useToolResult` reader, provenance bucketing, the `yz-` stylesheet); each widget is `widgets/src/<name>/`.

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
    ├── src/history-timeline/  # the flagship widget (§7): index.tsx, HistoryTimeline.tsx,
    │                        #   types.ts, useToolResult.ts, styles.ts
    └── dist/                # built bundles, COMMITTED + served as ui:// resources
        └── history-timeline.html
```

The registry maps a widget id to its served resource:

```python
# registry.py (proposed)
RESOURCE_MIME = "text/html+skybridge"   # ChatGPT's required widget MIME (§4 live-finding)

WIDGETS = {
    "history-timeline": Widget(
        uri="ui://yarnnn/history-timeline.html",
        bundle_path="widgets/dist/history-timeline.html",
        # served-resource _meta.ui — domain + CSP are required for ChatGPT submission
        domain="https://mcp.yarnnn.com",
        csp_connect=["https://mcp.yarnnn.com"],
    ),
}
```

Served via the existing SDK (confirmed available, mcp 1.28.0):

```python
# server.py (proposed addition)
@mcp.resource("ui://yarnnn/history-timeline.html", mime_type=RESOURCE_MIME)
def history_timeline_widget() -> str:
    return (WIDGETS["history-timeline"].bundle_path).read_text()  # the built HTML/JS
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

**The data is always in the text channel** (the ADR-368 invariant, unchanged). The **widget pointer is now allow-listed** (`presentation/hosts.py`): a host in `WIDGET_RENDERING_HOSTS` (today: `chatgpt`) gets it; everything else gets the same full result **without** the pointer — a **text-safe default**, so the worst case is "no widget," never "broken render." The gate keys on the same client id the MCP layer already derives (`mcp_composition.derive_client_name*`); a new rendering host opts in with one entry, verified end-to-end first. The served resource stays OpenAI-shaped (correct — only a host that got the pointer ever fetches it, and post-gate only ChatGPT does).

> Why an allow-list, not a deny-list: claude.ai's OAuth `client_id` is an opaque registration UUID and its User-Agent contains no "claude" — so it may resolve late or to "unknown." A deny-list would leak the widget to any host it failed to recognize. An allow-list with a text-safe default fails closed: an unrecognized host gets text, which every host renders. When MCP standardizes a real per-request rendering-capability bit, `renders_widgets()` is the one function to swap.

> **Second live finding (2026-06-27): the envelope is a `CallToolResult` on BOTH paths — not a bare dict for the text path.** The first cut returned a bare dict for non-widget hosts. That tripped a *different* live error on claude.ai: **"Output validation error: outputSchema defined but no structured output returned."** Cause: the three tools advertise an `outputSchema` (`_attach_output_schemas`), and the vendored `mcp` lowlevel handler rejects a return that has no structured content when a schema is declared. A `CallToolResult` short-circuits that check (lowlevel `server.py:546`); a bare dict only survives it if FastMCP's `convert_result` produced `structuredContent` — which it does **only when `fn_metadata.output_schema` is set**, and our schema attach lands on the tool's instance attribute (the override that takes effect for `list_tools`), *not* on `fn_metadata`. So a bare-dict text return reached the host as unstructured-only → `structuredContent=None` → the validation error. This latent break was masked before the gate because every tool *always* returned a `CallToolResult` (the unconditional-`_meta` path). The fix: `_present()` returns a `CallToolResult` (both channels populated) on **every** affordance-bearing path; only the widget `_meta` is gated. Net effect — the advertised `outputSchema` is now actually satisfied on every host, not just the (former) ChatGPT path.

---

## 5.1 Host Profiles — the interop-reach registry (ADR-379)

The `renders_widgets()` gate (§5) is one slice of a larger truth: **a host is a driver, not a code branch.** Reach — N LLM hosts (Gemini, Cursor, Copilot, Perplexity, …) connecting to the same three verbs over the same substrate — is the product (ADR-310, "one memory for every AI you use"). ADR-379 makes the host a **data entry**, not a code change.

A host varies from the core on **exactly four dimensions**, and only four:

| # | Dimension | Varies | Status |
|---|-----------|--------|--------|
| 1 | **Identity** | OAuth `client_id` / UA / registered name → short id | `HostProfile.match` (the registry is the single resolver) |
| 2 | **Auth** | OAuth 2.1 dynamic-registration vs static bearer | **already host-agnostic** (`oauth_provider.py`) — zero new code per host |
| 3 | **Render** | (a) renders widgets? (b) which dialect? | (a) `HostProfile.renders_widgets` (§5 gate); (b) `HostProfile.widget_dialect` (§4 deferred) |
| 4 | **Quirks** | per-host workarounds (e.g. Claude Desktop JSON-string coercion) | a profile field *only when a real quirk is found* — never speculative |

Everything else — verbs, substrate, `user_id`, provenance mechanism, the ADR-307 gate — is identical. **The de-risking fact:** dimensions 2 and the *text path* of 3 are already host-agnostic, so a spec-compliant MCP client gets clean text responses with **zero new code** (proven live 2026-06-27). The registry doesn't *unlock* reach — reach is already there — it makes reach **attributed and safe** instead of **accidental and `"unknown"`**.

`presentation/hosts.py` is the registry: a `HostProfile` table + three resolvers (`resolve_host_id`, `renders_widgets`, `widget_dialect`). `_normalize_client_id` (in `mcp_composition.py`) delegates to `resolve_host_id` — one resolver, the substring chain gone. **Adding Gemini is one line** (`HostProfile("gemini", ("gemini", "google"))`): it connects (auth, free), gets text (free), and attributes as `yarnnn:mcp:gemini` in `history` (the one thing the entry adds). When a host ships a widget spec, flip `renders_widgets=True` + set `widget_dialect`, and §4's multi-dialect serving renders it.

> **Ordering caveat (preserved):** substring match is **first-wins by registry order**. The specific Claude variants (`claude_desktop`, `claude_code`) must be tested such that they win over the bare `anthropic`/`claude.ai` match. The CI gate (`test_adr379_host_profiles.py`) freezes the known disambiguations so the ordering can never silently regress.

> **The structural guarantee:** the CI gate asserts (1) no host-name literal appears outside the registry in the MCP layer (`openai` survives only inside its adapter, per D5); (2) every `renders_widgets=True` profile declares a dialect; (3) the known disambiguations resolve; (4) the ADR-372 gate contract holds. That gate is what keeps the Nth host a *data entry* — a leaked host name fails the build.

§4's multi-dialect resource serving is the **only** new engineering, and it's **deferred** until a second rendering host exists (YAGNI). The registry shape anticipates it (`widget_dialect` is a field from day one) so the seam is pre-cut. Until then only `chatgpt` renders, only the `openai` dialect is served — identical to today.

---

## 6. The widget↔tool callback contract (D6)

An interactive widget *may* call back via JSON-RPC `tools/call` over `postMessage` (MCP Apps bridge). When it does, it calls the **same** interop tools — through the **same** `execute_primitive()` gate, the **same** ADR-307 permission taxonomy, the **same** audit trail. There is no widget-only privileged path. A widget cannot reach substrate a normal tool call couldn't.

```javascript
// inside the widget bundle — e.g. fetch more revisions on scroll
window.parent.postMessage({
  jsonrpc: "2.0", id: 1, method: "tools/call",
  params: { name: "history", arguments: { reference, limit: 30 } }
}, "*");
```

The result arrives back as a `ui/notifications/tool-result` message; the widget re-renders. Same data contract as the text path.

> **Prefer embedding over calling back when the data set is bounded.** The `history` widget's click-to-diff needs the diff for each revision — but rather than a per-click `tools/call`, `compose_history` **embeds each revision's diff inline** in the result (server-side, via the existing `DiffRevisions` primitive). The widget expands a diff with *zero* callback. This keeps the verb surface intact (no extra MCP tool), works on every host (even ones without the callback bridge), and is more robust. Reserve the callback path for genuinely unbounded interaction (infinite scroll, search-within) where embedding the whole set is impractical.

---

## 7. The `history` timeline widget (the reference affordance — IMPLEMENTED)

`history` carries the flagship widget because it is the differentiator (the ADR-209 authored revision chain a plain storage connector cannot show), and a who-changed-what-when timeline is inherently visual.

**The data `compose_history` returns** (`api/services/mcp_composition.py`) — each revision carries its embedded diff-vs-predecessor (§6); no kernel change:

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

1. `presentation/affordances.py` — the `"history"` entry (§2).
2. `presentation/registry.py` — `"history-timeline"` → `ui://yarnnn/history-timeline.html` (§3).
3. `server.py` — `@mcp.resource(...)` serving the built bundle (§3); on `history`'s return, attach `_meta` via the adapter (§4) **only when `hosts.renders_widgets(client_name)`** (§5, amended 2026-06-27), with the full `history[]` always also in `content`/`structuredContent` for every host.
4. `compose_history` + `_embed_revision_diffs` — embeds each revision's diff inline server-side (§6), so click-to-diff needs zero callback.
5. `widgets/src/history-timeline/` — a React (TS) bundle that:
   - renders `history[]` as a vertical timeline, newest first;
   - colors each node by `authored_by` bucket (`operator` / `reviewer` / `mcp` / `agent` / `system`) — the cross-LLM provenance made visual;
   - shows each revision's `change` message + timestamp, and a **show-changes** toggle that expands the embedded unified `diff` (added/removed lines colored), zero callback;
   - renders the `explanation` as a caption — **it does not author new prose** (D3).
6. `widgets/package.json` + `build.mjs` (esbuild) → single self-contained `widgets/dist/history-timeline.html`.

### Building the widget

The bundle is built **locally / at dev time** and the single-file `dist/` output is **committed** (a `.gitignore` exception overrides the global `dist/` rule). The Python MCP service serves the committed file verbatim at runtime — **it does not run this build**, so a stale `dist/` ships a stale widget. Rebuild after editing `src/`:

```bash
cd api/mcp_server/widgets
npm install          # first time only
npx tsc --noEmit     # type-check
npm run build        # → dist/history-timeline.html (React inlined, minified, self-contained)
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
| A new host CONNECTS (reach: Gemini, Cursor, Copilot, …) | one `HostProfile` entry in `hosts.py` (§5.1) | auth, verbs, substrate, kernel — text path is free |
| An existing host adds WIDGET rendering | flip `renders_widgets=True` + set `widget_dialect`; one dialect adapter if new (§4) | widget bundles reused as-is; the registry entry already exists |
| A new widget | one registry + one affordance entry + one bundle | every other tool |
| A server-side host-capability signal standardizes | opt into suppressing `_meta` for text-only hosts as an optimization | the always-text-channel contract (text path never depends on it) |
| The kernel/primitives evolve | nothing in presentation (tools call `execute_primitive` unchanged) | the whole presentation layer |

The invariants that must never erode: **text is the default and always valid (D1/D4); the kernel never learns a host exists (D5/C3); a widget renders returned substrate, never composed judgment (D3); a callback is the same gated tool (D6).**
