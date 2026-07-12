# Chat rendering per context — the artifact-write slot, and why it's one slot, not three chat stacks

**Date**: 2026-07-12
**Status**: Discourse → **ratified as [ADR-443](../adr/ADR-443-the-artifact-write-render-slot.md)** (2026-07-12, Implemented). The `artifactWrite` slot was added to `LaneMountSlots`; Studio passes `'none'` (operator ruling — the canvas is the artifact view, so the transcript stays pure conversation). This doc is the derivation record. Receipts-backed; NOT a new chat stack.
**Author**: Claude (collaborator) + KVK (operator)
**Trigger**: Operator screenshot — in Studio, the bound lane renders `deck.html` as an inline `ArtifactCard` bubble *while the same artifact is rendered full-size on the canvas beside it*. "Displaying the render in the chat while we're working on the file seems wrong." Plus the meta-concern: handle per-context chat display **without over-engineering a separate chat layout stack**, systematically, since the set of layouts may grow.

---

## 1. The two failure modes to steer between

The operator named both walls precisely:

- **Under-abstraction (what the screenshot shows):** one renderer shows an artifact card *everywhere*, including where the mount already renders that artifact by other means → duplication. The renderer doesn't know its mount's context.
- **Over-abstraction (the stated worry):** three chat stacks — a StudioChat, a SurfaceChat, a FreddieChat — each re-implementing session/transport/streaming, diverging over time. N-way maintenance, the thing to avoid.

The right answer lives between them: **one engine, one message model, one transport — and a single declarative seam where a mount configures how a turn renders.** The audit's finding is that this seam **already exists** (ADR-441, landed 2026-07-11) — it just doesn't yet carry the axis the screenshot needs.

## 2. What is already shared (the good news — most of it)

The 2026-07-11 conversation-mount work (ADR-441) already did the hard consolidation. Verified:

| Layer | State | Receipt |
|---|---|---|
| **Session model** | ONE table. A lane is a `chat_sessions` row (`session_type='lane'`), scoped `(workspace, principal)` like every session. Studio's "bound lane" is just a lane whose `context_metadata.artifact_path` names the artifact. | `api/routes/lanes.py:11, 76-79, 162, 42-45` |
| **Transport** | ONE helper. The byte-level SSE loop is `web/lib/sse.ts::sseEvents`; both live readers (lane + steward) consume it. | `web/lib/sse.ts:1-14`, `client.ts:246`, `NarrativeContext.tsx` |
| **Renderers** | TWO, split on **altitude** (a wire-protocol split, not a style pref): `ConversationPanel` (A1 steward rail) and `LanePanel` (A2 lanes + Studio). Merging them = the renderer fork ADR-436 refuses. | ADR-441 D1 (`ADR-441…md:47-63`) |
| **Mount contract** | ONE named-slots contract, `LaneMountSlots` — a mount configures `LanePanel` declaratively (`emptyState`, `suggestions`, `composerSeed`, `onArtifactWrite`) and **never reaches into messages/transport**. | `LanePanel.tsx:90-104`, ADR-441 D2 |

So "three chat stacks" is already NOT the world we're in, and the operator's over-engineering fear is largely already answered by canon. Studio mounts the *exact same* `LanePanel` /chat mounts (`StudioSurface.tsx:27, 330-352`).

## 3. What is NOT yet shared — the gap the screenshot exposes

**`LanePanel` renders an `ArtifactCard` for every assistant turn that carries an artifact write, unconditionally — there is no slot to change or suppress it.**

- `LanePanel.tsx:374-385` — `{m.role === 'assistant' && m.artifacts?.length ? <ArtifactCard … /> …}`. No prop, flag, or slot gates it.
- The `artifacts` array is populated from the lane stream regardless of mount (`LanePanel.tsx:205-243`).
- Studio passes the full `LaneMountSlots` (`StudioSurface.tsx:331-351`) but **none of the slots controls the card** — no `showArtifactCard` / `variant` / `renderMode` exists anywhere in `LanePanelProps` or `LaneMountSlots`.

**Why this is precisely a gap, not a Studio bug:** Studio already consumes the write signal via `onArtifactWrite` to bump `reloadKey` so the **canvas** re-renders (`StudioSurface.tsx:206-217`). The same write drives *both* the canvas render (wanted) and the transcript card (redundant). The duplication is structural — Studio has no lever to say "I already show this artifact; don't also card it in the transcript."

**ADR-441 half-closed this and made it more visible.** Its own §1 problem statement (`ADR-441…md:37-40`) flags the Studio duplicate as symptom #2 — but scoped the fix to the *pixel mismatch* (the card rendered broken `data-ref` images while the canvas rendered them resolved). D3 re-homed the projection so the card and canvas now render **identically**. That closed "two pixels" — and, by making them identical, arguably made the *redundancy* more obvious, not less. The *should-the-card-exist-here-at-all* question was never on ADR-441's table (confirmed: the derivation audit `the-conversation-mounts-audit-2026-07-11.md:77` treats only render-consistency).

So the screenshot is a genuinely new, orthogonal observation on top of fresh canon.

## 4. Where the systematic answer lives — and where it does NOT

**It lives in the `LaneMountSlots` contract** (`LanePanel.tsx:90-104`) — the seam ADR-441 D2 built for exactly this. Its governing rule (`ADR-441…md:85-87`):

> *"new mount needs → new named slot in the contract, never a surface-specific branch inside LanePanel."*

The Studio-card need is textbook: a mount needs to configure the shared renderer → it becomes a **new named slot**, not an `if (isStudio)` branch. This is the operator's instinct, and ADR-441 pre-authorized it.

**It does NOT live in the projection layer** (`viewers/projection.ts`). Projection resolves an artifact's citations and is a property of the **file type's renderer** (ADR-441 D3) — its only per-mount axis is `opts.pointer` (does this mount allow deixis?). Projection governs *how the HTML draws once you've decided to draw it*; the card-vs-suppress decision is made one layer up, in `LanePanel`. Putting the suppression axis in projection would mis-locate it (a type concern vs a mount concern) — the exact category error ADR-436/441 exist to prevent.

## 5. The proposed slot

Add one declarative slot to `LaneMountSlots`:

```ts
/** How this mount renders an assistant turn's artifact writes.
 *  - 'card'  (default): the full ArtifactCard preview (/chat — no other view).
 *  - 'link'  : a compact "wrote {file} →" citation line (mount shows the
 *              artifact elsewhere but a breadcrumb aids scanning).
 *  - 'none'  : suppress entirely (the mount fully owns the artifact view). */
artifactWrite?: 'card' | 'link' | 'none';
```

- **Studio** passes `'link'` (recommended over `'none'`) — the canvas owns the render; the transcript keeps a one-line "wrote deck.html →" so the *authoring trail* stays legible (you can see which turn produced which write) without a redundant full card. `'none'` is available if even the line is unwanted.
- **/chat** omits it → `'card'` default (no canvas; the card IS the only view — unchanged, byte-identical).
- **A future A3 / persona-seat mount** picks per its layout — no new machinery.

This generalizes as the layout set grows (the operator's stated requirement): a new layout that shows artifacts its own way declares `artifactWrite: 'link' | 'none'`; a new layout that doesn't gets the default. The renderer never forks.

**On the A1 Freddie rail:** no change. `ConversationPanel` doesn't render `ArtifactCard`/`FileBody` at all — it uses `ToolResultCard` (a compact tool-result line already). The rail is *already* effectively `'link'`-shaped by construction, which incidentally validates the model: the "system agent narrates what it did, doesn't re-render the artifact" posture is the right default for a rail, and the slot lets A2 mounts opt into the same discipline when they own the view.

## 6. Why not other approaches (rejected)

- **A `variant`/`mode` enum on `LanePanel` ('studio' | 'chat' | …).** Rejected — that's the surface-specific branch ADR-441 D2 explicitly forbids ("never a branch inside LanePanel"). A `mode` enum couples the renderer to the *identity* of its mounts; a declarative `artifactWrite` slot couples it only to a *behavior* the mount declares. When a fourth layout appears, the enum needs a new value + internal branches; the slot needs nothing.
- **Suppress in the projection layer.** Rejected — §4: wrong altitude (type vs mount).
- **A separate StudioLanePanel.** Rejected — the over-engineering wall; re-forks transport/transcript for one slot's worth of difference.
- **Detect "artifact_path is bound" inside LanePanel and auto-suppress.** Tempting (Studio lanes carry `context_metadata.artifact_path`), but rejected — it makes the renderer infer mount intent from session metadata, which is exactly the "renderer reaches into context" coupling the contract bans. A bound lane in a *different* future layout might still want the card. The mount should *declare*, not have the renderer *guess*.

## 7. Scope + sequencing

- This is **one slot + one conditional in `LanePanel.tsx:374-385` + Studio passing `artifactWrite='link'`**. Small, additive, byte-identical for /chat.
- It amends **ADR-441 D2** (adds a slot to the named contract) — so it wants a short ADR (candidate **ADR-443**) or an ADR-441 amendment, per the discipline that `LaneMountSlots` changes are canon (ADR-441's own rule). Doc-first, one commit.
- **Design sub-question for ratification:** Studio default `'link'` (keep the authoring-trail breadcrumb) vs `'none'` (fully silent). Recommend `'link'` — the transcript is the *record of what the lane did*, and a write is a material act worth one legible line even when the canvas shows the result. `'none'` is a mount's choice, not the default.

## 8. The one-paragraph answer to the operator's question

Chat is *already* one engine — one `chat_sessions` model, one `sse.ts` transport, and (ADR-441) two renderers split cleanly on altitude with a declarative `LaneMountSlots` contract so mounts configure the shared A2 renderer without forking it. The Studio duplicate isn't a symptom of missing systematization; it's a **missing slot** in a contract built for exactly this. The fix is to add `artifactWrite: 'card' | 'link' | 'none'` to `LaneMountSlots`, have Studio pass `'link'` (the canvas owns the render; keep a one-line authoring breadcrumb), and leave /chat on the `'card'` default. That is the systematic approach the operator asked for: **new layout need → new named slot, never a per-layout chat stack and never a renderer branch** — the rule already on the books.
