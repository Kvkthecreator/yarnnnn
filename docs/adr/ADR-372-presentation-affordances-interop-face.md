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

### D4 — The server **always** attaches `_meta`; the text channel **always** carries the data; non-rendering hosts ignore `_meta` harmlessly
There is **no documented server-side host-capability handshake** in the MCP Apps ecosystem (verified 2026-06-26 against OpenAI's docs + the Apps SDK examples: servers attach `_meta.ui.resourceUri` *unconditionally* and the host renders it or ignores it). So the framework does **not** gate `_meta` on `initialize` detection — that mechanism does not exist to rely on. Instead:

1. **The tool always returns the full, model-readable result in `content` / `structuredContent`** — the text path is *unconditionally* intact. This, not detection, is what protects the ADR-368 invariant.
2. **The tool also attaches widget `_meta`** when the tool has an affordance (D1). A host that renders widgets (ChatGPT, MCP-Apps hosts) uses it; a host that does not (claude.ai today, plain clients) ignores it — `_meta` is non-semantic to a host that does not read it, so nothing degrades.
3. **Capability detection, where it happens at all, is widget-side** (`window.openai` feature-detection inside the bundle, D2), not server-side.

The invariant "we never degrade the text experience" holds because the data is *always* in the text channel — a strictly simpler and safer guarantee than negotiation. (Should a reliable server-side capability signal later standardize, the framework can opt into suppressing `_meta` for text-only hosts as an optimization, but it must never become the thing the text path *depends on*.)

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
