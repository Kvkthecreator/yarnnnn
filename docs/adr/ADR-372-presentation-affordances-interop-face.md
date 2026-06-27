# ADR-372 — Presentation Affordances on the Interop Face

> **Status**: Proposed (2026-06-26)
> **Authors**: KVK, Claude
> **Supersedes / amends**: amends **ADR-310** (one moat, two faces → grows a presentation *dimension* on the interop face), **ADR-368** (the memory-first verbs gain optional rich rendering — the recall bright-line is extended, not violated). Preserves ADR-075 (OAuth/transport), ADR-371 (self-contained auth boundary), ADR-311 (deferred raw primitives).
> **Related**: ADR-209 (authored revision chain — what the first widget renders), ADR-222 (kernel boundary — the adapter never touches the kernel), ADR-168 (primitives matrix — widgets call the same gated tools).
> **Canonical feature doc**: [`docs/features/mcp/presentation.md`](../features/mcp/presentation.md).

---

## 1. The correction this ADR ratifies

A recurring question: *"ChatGPT now has the Apps SDK — do we abandon MCP and build a ChatGPT app?"* The premise is backwards. The OpenAI Apps SDK does **not** replace MCP — it is a UI layer **on top of** MCP, and the patterns it pioneered were folded into the open **MCP Apps spec (SEP-1865, ratified 2026-01-26)**. OpenAI's own published guidance: *build around the MCP Apps standard for portability, then layer ChatGPT extensions on top.*

So the work is not "support ChatGPT." The work is: **the interop face (MCP) grows an optional presentation dimension**, declared per-tool as data, served by the MCP server's own resource surface, rendered by hosts that can and ignored by hosts that can't — with the kernel and the core service untouched. ChatGPT is the first consumer of this dimension, not its definition.

This ADR ratifies that framing so no future session re-frames it as a vendor feature and couples the kernel to a host.

## 2. The model — one moat, three faces

ADR-310 established **one moat, two faces**: the *cockpit* (operator, in-app) and the *interop face* (foreign LLM, via MCP, text). This ADR grows the interop face a **rendering axis**:

```
                  ONE MOAT (judged substrate)
                           │
        ┌──────────────────┼──────────────────────────┐
   COCKPIT FACE       INTEROP FACE
   (web/, in-app)     (MCP)
                           │
                  ┌────────┴─────────┐
            TEXT RENDERING      RICH RENDERING
            (default; every     (host runs a widget WE author,
             host; the host      over the SAME returned data)
             narrates)
```

The rich-rendering axis is **not a third product and not a third moat.** It is the interop face described to a host that can do more than print text. The substrate, the primitives, the gating, the audit trail — all unchanged. A widget is a *renderer of returned substrate*, hosted on the foreign surface.

## 3. The honest constraints (named so the decision is real)

### C1 — Rich rendering risks re-introducing what ADR-368 deliberately rejected
ADR-368's load-bearing rule: `recall` **returns** substrate, it does not **synthesize** an answer, because the host LLM explains in its own voice over its own conversation context. A widget *is* rendering-on-the-host — superficially the thing we rejected. The reconciliation is **D3** below; getting it wrong silently undoes ADR-368.

### C2 — Host metadata shapes are vendor-controlled and will drift
`_meta.ui.resourceUri`, `text/html;profile=mcp-app`, `window.openai.*` are external surfaces. OpenAI's extensions sit beside the MCP Apps standard and both evolve. A framework that hardcodes today's keys inline across tools rots on the first vendor revision.

### C3 — The kernel boundary is sacred (ADR-222)
`execute_primitive()` and `api/services/*` must never learn that ChatGPT, widgets, or `_meta` exist. Any host-specific knowledge that leaks below the MCP-server module is the drift this ADR exists to prevent.

## D. Decisions

### D1 — Presentation is a per-tool **affordance declaration** (data, not code)
Each MCP tool MAY declare a neutral, host-agnostic presentation affordance — `{ widget: <id>, fallback: "text", interactive: bool }` — as data adjacent to the tool. A tool with no declaration is text-only. **Text-only is the default and is always valid on every host.** A tool opts into rich rendering by declaring, never by being rewired. (This is why the framework does not "fixate on the current three verbs": the verbs are subject to change; the affordance mechanism is the durable layer, and a new verb opts in with one data entry.)

### D2 — Target the **open MCP Apps spec** as primary; ChatGPT extensions are a thin overlay
Widgets are authored against the ratified MCP Apps standard (SEP-1865): `ui://` resource scheme, `text/html;profile=mcp-app` MIME, `_meta.ui.resourceUri` linkage, JSON-RPC-over-`postMessage` bridge for callbacks. ChatGPT-specific niceties (`window.openai.*`, `openai/widgetDescription`) are layered on **only inside one host-adapter**, and the *widget* feature-detects them at runtime (graceful degradation), per OpenAI's own published posture: *build with the MCP Apps standard keys + bridge by default; use `window.openai` only when you need ChatGPT-specific capabilities, and feature-detect before calling.* Portability first; vendor sugar at the edge, detected widget-side. This makes Gemini / any future MCP-Apps host reuse the same widget bundles for free.

### D3 — The recall bright-line is **extended, not violated**: a widget renders returned substrate; the model still narrates
The ADR-368 rule moves from *"the host explains in prose"* to:

> **The host explains the returned material — in prose, or as an interactive view of that same returned material. A widget MUST NOT compose an answer, an opinion, or a judgment the server did not return.**

A `trace` timeline widget draws the revision chain the server already returns and adds *interaction* (click a revision → see the diff). It adds no opinion. The moat-defended judgment stays server-side; the widget is presentation of judged output.

**The model does not go silent when a widget renders.** A widget is *additive*, not a replacement for the host's narration: the host LLM still narrates the evolution in its own voice over its own conversation context, exactly as ADR-368 requires, *and* the timeline renders alongside. This is deliberate tiered redundancy — the same instinct as ADR-367 (macOS Control-Center / tiered-access): the glanceable view and the spoken explanation co-exist, neither demotes the other. (It also keeps cross-LLM consistency: a text-only host shows the prose narration of the *same* returned substrate, so no host is worse off, only differently rendered.)

### D4 — The text channel **always** carries the data; widget `_meta` is attached **only to a host that renders widgets** (AMENDED 2026-06-27)

> **Amendment (2026-06-27) — the original "attach `_meta` unconditionally" was falsified live.** The premise below (point 2, struck through) was that a non-rendering host *ignores* `_meta` harmlessly because it is "non-semantic to a host that does not read it." **claude.ai does not ignore it.** Its connector reads the widget pointer, fetches the pointed-at resource (served `text/html+skybridge` with `openai/*` keys — the OpenAI-Apps shape ChatGPT requires), tries to render it, and fails with **"Unsupported UI resource content format."** The tool's underlying write/read still succeeded, but the host surfaced a rendering error as a tool error. The OpenAI-Apps render path had leaked into the Claude path because nothing decided *per host* whether to send the pointer.
>
> **Resolved design (the gate):** the **result data stays unconditionally in the text channel** for every host (that, unchanged, is the ADR-368 invariant). The **widget `_meta` pointer is now gated** on host rendering-capability via `presentation/hosts.py::renders_widgets(client_name)`. It is an **allow-list with a text-safe default**: a host in `WIDGET_RENDERING_HOSTS` (today: `chatgpt` only) gets the pointer; every other host — claude.ai, the opaque-client_id case, any unidentified/new host — gets the bare text path, which every host renders. So the failure mode is "no widget" (always safe), never "broken UI." The host id reuses the one the MCP layer already derives (`mcp_composition.derive_client_name*`); a new rendering host opts in with one entry. This is exactly the "reliable server-side capability signal → opt into suppressing `_meta` for text-only hosts" escape hatch the original D4 anticipated (last paragraph) — the resolved client id is reliable enough to be that signal. The served resource stays OpenAI-shaped, which is correct: only a host that received the pointer ever fetches it, and post-gate only ChatGPT receives it.

The framework's guarantee, restated:

1. **The tool always returns the full, model-readable result in `content` / `structuredContent`** — the text path is *unconditionally* intact. This, not detection, is what protects the ADR-368 invariant.
2. ~~**The tool also attaches widget `_meta`** when the tool has an affordance (D1). A host that renders widgets (ChatGPT, MCP-Apps hosts) uses it; a host that does not (claude.ai today, plain clients) ignores it — `_meta` is non-semantic to a host that does not read it, so nothing degrades.~~ **(falsified — see amendment above)** The tool attaches widget `_meta` only when the tool has an affordance (D1) **AND** the calling host is in `WIDGET_RENDERING_HOSTS`. A non-widget host gets the **same full-result `CallToolResult`, minus the widget pointer** — *not* a bare dict (a bare dict trips the lowlevel `outputSchema` validation; see the second live finding below).

> **Second live finding (2026-06-27) — the envelope must be a `CallToolResult` on both paths.** The first cut returned a bare dict for non-widget hosts, which tripped a *different* claude.ai error: **"Output validation error: outputSchema defined but no structured output returned."** The three tools advertise an `outputSchema` (`_attach_output_schemas`), and the vendored `mcp` lowlevel handler rejects a schema-bearing tool's return when it carries no structured content. A `CallToolResult` short-circuits that check; a bare dict survives it only when FastMCP's `convert_result` produced `structuredContent`, which it does only when `fn_metadata.output_schema` is set — but our attach lands on the tool *instance attribute* (the override that drives `list_tools`), not on `fn_metadata`. So a bare-dict text return reached the host as unstructured-only → validation error. The break was masked before the gate because every tool always returned a `CallToolResult` (the unconditional-`_meta` path). **Resolution:** `_present()` returns a `CallToolResult` (both channels) on every affordance-bearing path; only the widget `_meta` is gated. The advertised `outputSchema` is now satisfied on every host.
3. **Capability detection, where it happens at all, is widget-side** (`window.openai` feature-detection inside the bundle, D2) **and now also server-side** (the host allow-list gate above — the per-request decision of *whether to send the pointer at all*).

The invariant "we never degrade the text experience" holds because the data is *always* in the text channel — and now the widget pointer never reaches a host that cannot render it, so a non-rendering host shows clean text instead of a rendering error.

### D5 — All presentation code lives in `api/mcp_server/`; one adapter per host scheme
The affordance model, the widget registry, the resource-serving, and the host adapters live **entirely in the MCP-server module** (the interop face). A host name (`openai`, future others) appears in code in exactly one place: its adapter. The kernel and `api/services/*` are untouched (C3). Widget *bundles* are frontend artifacts with their own build (a mini-`web/` under `api/mcp_server/widgets/`), **served by** the MCP server's resource surface but never importing Python kernel code.

### D6 — The widget↔kernel contract IS the existing gated tool
A widget that calls back (`tools/call` over the bridge) calls the **same** `remember`/`recall`/`trace` tools, through the **same** `execute_primitive()` gate and the **same** ADR-307 permission taxonomy and audit trail. No new privileged path. A widget cannot reach substrate a tool call couldn't.

## 4. What this supersedes / amends

- **Amends ADR-310**: "two faces" → the interop face carries a text/rich rendering axis. No new moat.
- **Amends ADR-368**: the three verbs gain optional affordances; the recall bright-line is restated per D3.
- **Preserves**: ADR-075 (OAuth/transport carry forward unchanged — mcp 1.28.0 already serves resources via `FastMCP.resource()` / `custom_route()`, no SDK change), ADR-371 (auth boundary), ADR-222 (kernel boundary), ADR-307 (one gate), ADR-209 (the chain `trace` renders).

## 5. Implementation sequencing

Doc-first per CLAUDE.md. (1) This ADR. (2) [`presentation.md`](../features/mcp/presentation.md) — canonical feature doc with the affordance model, registry, the always-attach `_meta` + always-text-channel contract (D4), adapter pattern, and the worked `trace`-widget slice. (3) README pointer + `architecture.md` `## Presentation` section. (4) Implementation slice: the `trace` timeline widget (the differentiator) as the first and reference affordance. No code until this ADR ratifies.

**First implementation checkpoint (validate before building any widget):** the `trace` tool returns its full `history[]` in `content`/`structuredContent` *and* attaches widget `_meta`, then connect from ChatGPT (developer mode) and confirm the widget renders while a text-only host (claude.ai) shows the unchanged text. This proves the always-attach/always-text contract end-to-end before a single line of React is styled. If ChatGPT does not pick up the `_meta` at all, that is the real blocker to surface — not the widget's visual design.

## 6. Rejected alternatives

- **"Build a ChatGPT app" (treat Apps SDK as the unit).** Rejected — couples to a vendor shape (C2), contradicts OpenAI's own portability advice, and frames a UI layer as a product. Targeting the open spec (D2) is strictly more durable.
- **A dedicated `/apps/openai/` directory or a separate service.** Rejected — there is no separate artifact; an "app" is this MCP server + widget metadata. A new directory implies a second product and invites kernel-coupling.
- **Widgets compose answers (richer, "smarter" UI).** Rejected — violates D3 / ADR-368; reintroduces per-host synthesis divergence and moves judgment off the seat.
- **Hardcode `_meta.ui` inline in each tool.** Rejected — rots on the first vendor revision (C2); D1 + D5 isolate the shape in declarations + one adapter.
