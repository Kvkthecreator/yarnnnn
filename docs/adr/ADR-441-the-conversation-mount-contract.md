# ADR-441 — The conversation-mount contract: one thread renderer per altitude, citations resolve in the renderer

> **Status**: **Accepted + Implemented** (2026-07-11, operator-commissioned audit
> 2026-07-10). The ADR-436 move — one frame-agnostic renderer, N mounts that own
> their frames — applied to **conversation threads** and to the **HTML-artifact
> render path**. Derivation: `docs/analysis/the-conversation-mounts-audit-2026-07-11.md`
> (full inventory + receipts).

**Date**: 2026-07-11
**Dimension**: Channel (Axiom 6 — where conversations and artifacts render)

**Extends / builds on**: ADR-436 (renderer/mount split — the lens), ADR-411/412
(lanes + the three chromes — the altitude seam this ratifies), ADR-440 (the
Studio — the second lane mount + the reference projection this relocates),
ADR-408 D2 (A1/A2 altitudes), ADR-245 (three-layer rendering).

**Amends**: ADR-440 D5 (the projection pass is re-homed: a property of the Web
Viewer renderer, not of the Studio canvas mount), ADR-411 gate
(`test_adr411_lanes.py` cost assertion reconciled with ADR-439's ratified
BYOK override).

**Preserves**: mutation-through-chat (ADR-236); window = surface; the ADR-412
chrome homes (rail = A1, /chat = A2, /agents = A3); the lane wire protocol and
mechanics (ADR-411) byte-identical; read-purity (projection never writes pins —
ADR-440 D5 as amended).

---

## 1. The problem

The chat panel accreted mounts while the layer under it was redesigned. Four
symptoms, from the audit:

1. `LanePanel` grew four optional mount-specific props across two days
   (`onArtifactWrite`, `emptyState`, `suggestions`, `composerSeed`) with no
   named contract — the next mount adds prop 8 ad hoc.
2. A Studio artifact renders **differently in the chat card and on the canvas**:
   `ArtifactCard → FileBody → WebViewer` injects raw `srcDoc` (broken
   `data-ref` images), while `StudioCanvas` runs `resolveArtifactHtml` first.
   Same file, two pixels. FileOpenModal and the Files detail share the defect.
3. Three hand-written copies of the same SSE transport loop
   (`NarrativeContext.tsx:710-724`, `client.ts:244-260`,
   `useContentRefinement.ts:90-106` — the third dead).
4. A fossil narrative surface (`feed-surface/` + `feed/`, 7 files, zero
   importers) survives from the pre-ADR-415 era.

## 2. D1 — Two thread renderers, ratified along the altitude seam; never merged

The audit measured the two live thread stacks and found the A1/A2 split is a
**wire-protocol split**, not a styling preference: the steward stream carries
`stream_start` attribution, `tool_use`/`tool_result` objects, `ui_action`
dispatch (clarify/setup/navigation), and reviewer-progress phases; the lane
stream carries `text_delta`/`tool`/`artifact`/`done`. Neither vocabulary is a
subset of the other.

**Decision**: exactly **one thread renderer per altitude** —
`ConversationPanel` (A1, mounted once: the steward rail) and `LanePanel` (A2,
mounted N times behind the D2 contract). Merging them would put two protocols
behind a mode flag inside one component — the renderer fork ADR-436 refuses.
A future third altitude chrome (persona-agent seats, ADR-382) gets its own
renderer *only* if its protocol genuinely differs; otherwise it mounts
`LanePanel`.

## 3. D2 — The lane mount contract, named

`LanePanel` is **the** lane-thread renderer: frame-agnostic (the mount owns
the column/header/frame around it), one per ADR-408 Altitude 2. Mounts
configure it through a **named slots contract** (`LaneMountSlots`, exported
beside the component):

| Slot | What the mount declares | Adopters today |
|---|---|---|
| `emptyState` | teach the mount's act in the mount's words | Studio (teaching state); /chat falls to the lane-contract default |
| `suggestions` | starter chips while the transcript is empty | Studio (per-template) |
| `composerSeed` | seed/append composer text (pointing, insert menu) | Studio (v1.1) |
| `onArtifactWrite` | a write landed — refresh the mount's view of the file | Studio (canvas reload) |

The rules the contract carries (mirror of ADR-436 §5):

```
one renderer, N mounts — the mount owns its frame, never the thread internals
slots are DECLARATIVE — a mount never reaches into messages/transport
transcript + transport live in the renderer (no headless split: both mounts
  consume the identical full thread; a data/view split has no second consumer)
new mount needs → new named slot in the contract, never a surface-specific
  branch inside LanePanel
```

## 4. D3 — Citations resolve in the renderer: the projection moves into the Web Viewer app

ADR-436: *"an app owns file types and draws their content."* Drawing an HTML
file that cites the commons **includes resolving its citations** — exactly as
the Image Viewer's signed-blob fetch is part of drawing an image. The
reference projection (ADR-440 D5) is therefore a property of the **type's
renderer**, not of the Studio mount that shipped it first.

**Decision**:

- `resolveArtifactHtml` relocates `components/studio/` →
  `components/workspace/viewers/projection.ts` (the viewers layer — beside the
  apps that consume it). Content unchanged, including the v1.1 pointer
  runtime behind `opts.pointer`.
- **`WebViewer` runs the projection** whenever the content carries `data-ref`
  (async, with the raw content as the pre-projection fallback). Every
  `FileBody` mount — ArtifactCard, FileOpenModal, the Files detail — now
  renders citations identically to the Studio canvas. Zero mount changes:
  the fix lands in the renderer and every frame inherits it.
- `StudioCanvas` keeps its own iframe **only** for its mount-specific needs
  (full-bleed frame + the pointer runtime under `sandbox="allow-scripts"`),
  consuming the same relocated projection. One projection implementation,
  N render sites.
- Read-purity preserved: the projection never writes pins (ADR-440 D5 as
  amended — pins refresh on authoring turns only), so a read-only grant's
  card renders correctly too.

## 5. D4 — One SSE transport, two protocols

The byte-identical transport loop (`getReader` + `TextDecoder` + buffer split
on `\n` + `data: ` prefix + `JSON.parse`) extracts to **one helper**,
`web/lib/sse.ts::readSseStream(body, onEvent)`. Both live readers adopt it;
their **event vocabularies stay separate** (D1 — the protocols are the
altitude seam). The dead third copy dies with its host (D5).

## 6. D5 — Deletions

| Dies | Why | Gate re-point (same commit) |
|---|---|---|
| `components/feed-surface/` (FeedSurface + WorkspaceContextOverlay) | fossil narrative surface; `/notifications` replaced it (ADR-415/410); zero importers | `test_adr340_d8_machinery_fold.py:128` (deep-link check inside the fossil) |
| `components/feed/` (5 files) | consumed only by FeedSurface | `test_authored_by_narrative.py:151-152` (badge adoption in two fossil rows) |
| `hooks/useContentRefinement.ts` | dead third SSE reader, zero importers | none |
| the two inline SSE loops | replaced by `lib/sse.ts` (D4) | none |

**Not dying**: `components/tp/*` — all 13 components verified live on the
steward-rail path. The `tp` slug is historical; retained per the GLOSSARY
relabel-keep-slug discipline (a directory rename is churn, refused).

## 7. D6 — The ADR-411 gate reconcile

`test_adr411_lanes.py:198` (`"cost" not in keys`) predates ADR-439, which
ratified `cost_override_usd` on lane metering (BYOK rounds record
cost-to-us = 0). The assertion re-encodes its intent honestly: the **only**
cost-named key permitted is `cost_override_usd`, and it must be `None` on
managed-key turns. The metering behavior itself is untouched.

## 8. Consequences

- **Positive**: artifacts render identically in every frame (the operator's
  broken-glyph receipt closes); the lane thread has a named contract the next
  mount adopts instead of growing; 7 fossil files + 2 duplicated transport
  loops die; the A1/A2 renderer split is ratified so it stops being
  re-litigated at each new mount.
- **Cost**: one relocation (`projection.ts`), one new small module
  (`lib/sse.ts`), two gate-test re-points.
- **Risk**: low — FE-only; the projection path is already live on the canvas;
  non-`data-ref` HTML renders byte-identically (the projection short-circuits).

## 9. The one-line statement

**Conversations get the ADR-436 treatment: one thread renderer per altitude
(steward and lane, never merged — the altitude seam is a wire-protocol seam),
the lane renderer behind a named mount-slots contract instead of accreting
props, the reference projection re-homed from the Studio mount into the Web
Viewer renderer so every frame draws citations identically, one shared SSE
transport under two separate protocols, and the fossil feed surface deleted.**
