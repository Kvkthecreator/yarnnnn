# ADR-443 — The artifact-write render slot: a mount declares how a lane's writes render

**Status**: **Accepted + Implemented** (2026-07-12, operator-ratified — "studio is none because we're looking at the very thing we're working on"). A one-slot extension to the ADR-441 `LaneMountSlots` contract. Doc-first with its code in the same pass.

> **Amended (2026-07-15, the seam-contract spine — operator-ratified in the chat(think)
> three-axes discourse):** the `'card'` mode gains a TYPE-dispatched depth rule — **preview
> depth follows ownership**. For a file whose format is claimed by a surface-owning app
> (ADR-451 `resolveSurfaceApplication` — v1: `.html` → Studio), the card renders
> **Quick-Look-grade**: title, bounded first-viewport preview, attribution, and the owning
> app as the celebrated primary action ("Open in Studio") — never a full working render.
> Chat *glances* at another app's file; it doesn't bench it. Files with no surface-owning
> claimant (`.md` briefs, notes, distillates — chat's own working material) keep the full
> render: reading the asset inline IS thinking-work (the ADR-454 asset/dividend seam). The
> dispatch lives at the file-TYPE altitude inside the card renderer — consistent with §3's
> discipline (mounts declare card-vs-none; the card's internal depth per type is not a mount
> concern, exactly as projection is a type property). **Implemented same day** —
> `ArtifactCard.tsx` consults `resolveSurfaceApplication`: owned formats get the
> QUICKLOOK_MAX_PX glance (no in-place expansion) + "Open in ‹app›" primary (header +
> footer strip); unclaimed formats byte-identical. Capture:
> `docs/analysis/chat-think-three-axes-discourse-2026-07-15.md` §11.
**Date**: 2026-07-12
**Dimension**: Channel (Axiom 6 — how a conversation renders the artifacts it produces)
**Extends / amends**: **ADR-441 D2** (the lane mount contract — this adds the fifth named slot it pre-authorized: "new mount need → new named slot, never a branch inside LanePanel"). Builds on ADR-436 (renderer/mount split), ADR-440 (the Studio — the mount that fully owns the artifact view), ADR-408 D2 (A1/A2 altitudes).
**Derivation**: `docs/analysis/chat-rendering-per-context-and-the-artifact-write-slot-2026-07-12.md`

---

## 1. Context

In Studio, the bound lane rendered every assistant artifact write as a full inline
`ArtifactCard` **while the same artifact was rendered full-size on the canvas
beside it** — a duplicate render of the very file the operator is authoring.

ADR-441 already did the systematic consolidation this question reaches for — one
`chat_sessions` model, one `sse.ts` transport, two renderers split on altitude
(`ConversationPanel` A1 / `LanePanel` A2) behind the declarative `LaneMountSlots`
contract. It even flagged the Studio duplicate (§1 symptom 2) — but scoped its fix
to the *pixel mismatch* (card showed broken `data-ref` images; canvas showed them
resolved). D3 made the two renders **identical** — which, by making them match,
made the *redundancy* more visible, not less. Whether the card should render **at
all** when the mount owns the view was never on ADR-441's table.

`LanePanel` rendered the card **unconditionally** (`LanePanel.tsx:374-385`) with no
slot to govern it. That is the gap: a missing slot, not missing systematization.

## 2. Decision

Add a fifth named slot to `LaneMountSlots`:

```ts
artifactWrite?: 'card' | 'link' | 'none';   // default 'card'
```

- **`'card'` (default)** — the full `ArtifactCard` preview. For a mount with **no
  other view** of the artifact (`/chat`). Byte-identical to pre-ADR-443.
- **`'link'`** — a compact "wrote {file}" citation line. For a mount that
  **references** the artifact but doesn't render it inline. (No adopter today;
  in the enum so the principle is complete and a future mount needn't re-open it.)
- **`'none'`** — suppress entirely. For a mount that **fully owns** the artifact
  view, where an inline render is a duplicate. **Studio passes `'none'`.**

**Studio is `'none'`, not `'link'` (operator ruling).** The rationale sharpens the
model: in Studio the canvas *is* the artifact view, rendered live as it's edited.
A transcript breadcrumb pointing at the file you're already staring at is a
citation to the present — noise. The authoring trail that matters (which turn
changed what) is served by the artifact's own revision history (`trace`), not by
transcript lines. So `'none'` makes the transcript **pure conversation** — the
honest state for a mount that owns the view.

The three-way principle: **`'card'` when the mount has no other view · `'none'`
when it fully owns the view · `'link'` for referenced-but-not-shown.**

## 3. Why a slot, not the alternatives (from the derivation §6)

- **NOT a `variant`/`mode` enum on `LanePanel` ('studio'|'chat'|…).** That is the
  surface-specific branch ADR-441 D2 forbids — it couples the renderer to the
  *identity* of its mounts. A slot couples it only to a *behavior* the mount
  declares; a fourth layout needs no new enum value + internal branch.
- **NOT in the projection layer** (`viewers/projection.ts`). Projection is a
  property of the file TYPE's renderer (ADR-441 D3); its only per-mount axis is
  `opts.pointer`. "Card vs suppress" is a MOUNT concern decided one layer up, in
  `LanePanel`. Locating it in projection would be the exact altitude error
  ADR-436/441 prevent.
- **NOT a separate `StudioLanePanel`.** The over-engineering wall — re-forks
  transport/transcript for one slot's difference.
- **NOT auto-detecting the bound lane** (`context_metadata.artifact_path`). That
  makes the renderer *infer* mount intent from session metadata — the "renderer
  reaches into context" coupling the contract bans. The mount **declares**, the
  renderer never **guesses**. (A bound lane in a *different* future layout might
  still want the card.)

## 4. Implementation

- `LaneMountSlots` gains `artifactWrite?: 'card' | 'link' | 'none'`; `LanePanel`
  defaults it to `'card'` and gates the render block: `'none'` → the block is
  null; `'link'` → a one-line `FileText` citation; `'card'` → the existing
  `ArtifactCard` (unchanged).
- `StudioSurface` passes `artifactWrite="none"` on its `LanePanel` mount.
- **Byte-identical for every existing mount** — `/chat` omits the slot → `'card'`.
  Only Studio changes.

## 5. What this does NOT do

- No change to the session model, the transport, or the A1/A2 renderer split
  (ADR-441 D1/D4 stand).
- No change to projection / citation resolution (ADR-441 D3 stands).
- No new renderer, no `LanePanel` fork, no per-layout chat stack. The set of chat
  layouts can grow: each new mount that owns its artifact view declares
  `artifactWrite: 'none'`; each that references one declares `'link'`; each with
  no other view gets the default. The renderer never forks — the ADR-441 rule,
  applied once more.

## 6. Gate

`test_lane_artifacts.py` (asserts `ArtifactCard` present in `LanePanel` + the
lane-artifact contract) stays green — the import + the `'card'` path are unchanged;
`test_adr412_chat_surface.py` unaffected. The slot is additive with a `'card'`
default, so N=existing-mounts is byte-identical (the ADR-441 discipline).
