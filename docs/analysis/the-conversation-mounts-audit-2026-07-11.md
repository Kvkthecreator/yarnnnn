# The conversation-mount audit — chat panels against the ADR-436 lens

**Date**: 2026-07-11 (operator-commissioned 2026-07-10, the first Studio session)
**Hat**: A (system audit; the fix ADR is ADR-441)
**Method**: full inventory of every conversation-thread render path + the artifact
render paths they mount, receipts under every claim. The question the operator
posed: the chat panel is now mounted in multiple places while the filesystem +
modal layer evolved underneath it (ADR-427 blobs, ADR-436 apps/mounts, ADR-440
reference projection) — has the chat layer accreted rather than been designed,
and does ADR-436's "one renderer, N mounts" move apply to conversations?

---

## 1. Inventory — every thread render path and its mount

A "thread" = a scrollable message list + a composer. There are **two live
thread renderers** (not four "chat panels" — two of the four suspected mounts
share one renderer, and one suspected mount does not exist), plus one fossil.

### Renderer 1 — the steward thread (Altitude 1)

| | Receipt |
|---|---|
| Renderer | `web/components/tp/ConversationPanel.tsx` — message list at :252-260 (`filterAddressedMessages(messages).map → MessageRow`), composer form at :341-392 |
| Mount (the ONLY one) | the chat drawer rail: `ChatDrawer.tsx:290-297`, registered as chrome `chat-drawer` (`ChromeRegistry.tsx:31,38`), region `main-rail` (`ShellCompositor.tsx:129,150-153`) |
| Transcript state | `useNarrative()` — the global `contexts/NarrativeContext.tsx` provider |
| Streaming | SSE loop inside `NarrativeContext.sendMessage` (`NarrativeContext.tsx:710-999`), protocol `/api/feed` (`chatTransport.ts:29`) |
| Bubble grammar | `MessageRow.tsx` → `MessageDispatch.tsx` (ADR-237 role dispatch) → InlineToolCall / FreddieCard / ToolResultCard / ProposalCard |

### Renderer 2 — the lane thread (Altitude 2)

| | Receipt |
|---|---|
| Renderer | `web/components/chat-surface/LanePanel.tsx` — message list :292+, composer :373+ |
| Mount A: /chat workbench | `ChatSurface.tsx:308-313` — passes the 3 required props only (`laneId`, `laneName`, `modelLabel`) |
| Mount B: the Studio's left pane | `StudioSurface.tsx` (workbench state) — passes the full set incl. `onArtifactWrite`, `emptyState`, `suggestions`, `composerSeed` |
| Transcript state | per-lane local state via `api.lanes.messages(laneId)` (`LanePanel.tsx:108-133`) |
| Streaming | `api.lanes.sendStream` (`client.ts:222-276`), protocol `/api/lanes/{id}/messages` |
| Bubble grammar | inline user/assistant bubbles + `MarkdownRenderer` + `ArtifactCard` (`LanePanel.tsx:292-360`) |

### The two suspected mounts that are NOT separate render paths

- **"Agent chats"** — there is no agent-conversation thread renderer.
  `/agents` detail renders `AgentContentView` (a detail view, not a chat;
  `agents/page.tsx:89`); `/agents/[id]` is a pure redirect shim
  (`agents/[id]/page.tsx:32-38`). Conversing near an agent flows through the
  steward rail with `surfaceOverride` (`ChatDrawer.tsx:146-148,291`).
  `MessageDispatch`'s `agent-bubble` role renders authored-agent messages
  *inside the steward transcript*, not a separate thread.
- **"The Freddie rail" vs "/chat lanes"** — genuinely two renderers, but each
  is the ONE renderer for its altitude (ADR-412 D1: one chrome home per
  altitude). The Studio did not add a fourth chrome — it added a second
  *mount* of Renderer 2.

### The fossil

- `components/feed-surface/FeedSurface.tsx` + `WorkspaceContextOverlay.tsx`
  (imported only by FeedSurface, `FeedSurface.tsx:35`) + the entire
  `components/feed/` subtree (DaySeparator · FeedTimeline · InvocationCard ·
  OperatorEventMarker · StandaloneEventRow) — **zero importers outside
  themselves** (grep receipts 2026-07-11: no `from '@/components/feed/` and no
  `FeedSurface` import anywhere outside the two dirs; all remaining mentions
  are comments). The `/notifications` route replaced this body with
  `ActivityLedger` + `QueueBody` (`notifications/page.tsx:18-22,46-48`;
  ADR-415/410). The narrative timeline grammar it carried lives on in the
  Activity ledger, not in a chat surface.
- `hooks/useContentRefinement.ts` — a third hand-written SSE reader
  (`getReader()` at :90, `data: ` parse at :106) with **zero importers**.

## 2. The duplication map — same concern, N implementations

| Concern | Implementations | Verdict (argued in §3) |
|---|---|---|
| Thread (list+composer) | ConversationPanel (A1) · LanePanel (A2) | JUSTIFIED — the altitude seam is a protocol seam (see §3.1) |
| SSE transport loop | `NarrativeContext.tsx:710-724` · `client.ts:244-260` · `useContentRefinement.ts:90-106` (dead) | UNJUSTIFIED at the byte level — 3 copies of `getReader + TextDecoder + split('\n') + 'data: ' + JSON.parse`; extract ONE helper, delete the dead copy |
| Message-bubble grammar | MessageDispatch role-dispatch (A1) · LanePanel inline bubbles (A2) | JUSTIFIED — the A1 grammar carries proposals/tool-cards/reviewer streams the lane protocol does not emit; forcing one grammar imports A1 complexity into A2 |
| HTML artifact render | `StudioCanvas` → `resolveArtifactHtml` (resolves `data-ref`) · `WebViewer` raw `srcDoc` (`viewers/index.tsx:92-105`) | UNJUSTIFIED — the same artifact renders resolved on the canvas and broken in every `FileBody` mount (ArtifactCard, FileOpenModal, Files detail). The projection is a property of the FILE TYPE, not of the mount |
| Sandboxed-iframe primitive | `StudioCanvas.tsx` iframe · `WebViewer` iframe | Collapses with the row above |
| Composer seeding / empty state / write-hook | LanePanel optional props (`onArtifactWrite`, `emptyState`, `suggestions`, `composerSeed`) | The de-facto mount contract, grown 4 props in two days without a name — formalize, don't multiply |

## 3. The audit questions, answered

### 3.1 Should the lane thread become a frame-agnostic renderer behind a mount contract?

**It already is one — unnamed.** LanePanel is frame-agnostic (it renders
`flex-1 min-h-0` into whatever column mounts it; ChatSurface owns the lane-list
+ header frame, StudioSurface owns the workbench frame). The accretion smell
(4 optional props added across ADR-440 v1/v1.1) is not the props themselves —
each is a real mount need — it is that they accreted *without a named
contract*, so the next mount will add prop 8 ad hoc. The v1.1 batch itself
flagged this (`LanePanel.tsx` composerSeed docstring: "Slated to become a
mount-contract slot in the conversation-mount refactor").

The fix is **naming, not rebuilding**: the ADR-436 mount-contract move applied
to threads is a *declaration* — one renderer per altitude, mounts pass slots
from a named contract type, the renderer never learns which surface mounts it.
Extracting a headless `useLaneThread` hook was considered and rejected: both
mounts consume the identical full thread; a data/view split has no second
consumer and would be speculative structure.

### 3.2 Should ArtifactCard route previews through the reference projection?

**Yes — but the projection belongs one level lower, in the Web Viewer app.**
The operator's screenshot receipt (2026-07-10): a Studio artifact citing
`./assets/x.svg` shows a broken-image glyph in the chat card while the Studio
canvas renders it. Root cause chain: `ArtifactCard` → `FileBody` → `WebViewer`
→ `<iframe srcDoc={file.content}>` verbatim (`viewers/index.tsx:95-103`) —
the `data-ref` citations never resolve. Fixing it *in ArtifactCard* would
repeat the mistake at the next mount (FileOpenModal and the Files detail have
the same defect today, invisibly).

ADR-436's own words decide the home: *"an app owns file types and draws their
content."* Drawing an HTML file that cites the commons **includes resolving
its citations** — the projection is part of rendering the type, exactly as the
Image Viewer's signed-blob fetch is part of rendering an image. One projection
implementation in the renderer → every mount (card, modal, Files detail,
canvas) renders identical pixels, which is the ADR-436 promise.

Corollary: `resolveArtifactHtml` is currently homed in `components/studio/` —
the app that happened to need it first — and `StudioCanvas` duplicates the
sandboxed-iframe render around it. It relocates to the viewers layer; the
canvas keeps only its mount-specific addition (the pointer runtime, already an
`opts` flag post-v1.1).

### 3.3 Steward rail vs lane thread — how much duplication, and does the altitude split justify it?

Measured side by side:

| | Lane protocol | Steward protocol |
|---|---|---|
| Endpoint | `/api/lanes/{id}/messages` | `/api/feed` (+ proxy fallback) |
| Text delta | `text_delta` | `content` + `reviewer_progress.phase=text_delta` |
| Tools | `tool` (name only) | `tool_use`/`tool_result` objects + `ui_action` dispatch (OPEN_SURFACE, CLARIFY, SHOW_SETUP_CONFIRM, …) |
| Artifacts | `artifact {path, verb}` | none |
| Attribution | none (the lane IS the member's embodiment) | `stream_start.author_*` (ADR-124 multi-author) |
| State | per-lane local | global reducer + session continuity |

**The altitude split is a real protocol split** — the steward wire carries an
event vocabulary (proposals, clarify, reviewer streaming, author attribution)
that has no lane analogue, and the lane wire carries one (`artifact`) the
steward lacks. Merging the renderers would mean one component speaking two
protocols behind a mode flag — the "different renderer" fork ADR-436 warns
against, in reverse. What is NOT justified is the byte-identical ~25-line SSE
transport loop copied three times (`client.ts:218-220` even says "mirrors the
steward's NarrativeContext reader"). The transport extracts; the protocols
stay separate.

### 3.4 What dies (Singular Implementation)?

1. `components/feed-surface/` (2 files) + `components/feed/` (5 files) — the
   fossil narrative surface (§1). Two gate tests hold references and re-point
   in the same commit: `test_adr340_d8_machinery_fold.py:128` (a deep-link
   check inside the fossil) and `test_authored_by_narrative.py:151-152` (badge
   adoption in two fossil rows).
2. `hooks/useContentRefinement.ts` — the dead third SSE reader.
3. The two hand-rolled SSE transport loops (replaced by one shared helper).
4. `StudioCanvas`'s private iframe+projection duplication (becomes the shared
   renderer path + its pointer opt).
5. NOT dying: `components/tp/*` — all 13 components verified LIVE on the
   steward-rail path (importer receipts in §1; `MessageDispatch` is imported by
   `MessageRow.tsx:42`, MessageRow by ConversationPanel, ConversationPanel by
   ChatDrawer). The `tp` slug is historical (thinking-partner era) — retained
   per the GLOSSARY relabel-keep-slug exceptions; a directory rename is churn
   with no behavior change and is explicitly refused.

### 3.5 The ADR-411 gate reconcile

`test_adr411_lanes.py:198` asserts `"cost" not in " ".join(ev.keys())` — the
original no-second-pricing-path guard. ADR-439 intentionally added
`cost_override_usd` to the metering call (`lane_runner.py:399` — BYOK rounds
record cost-to-us = 0). The assertion's *intent* survives; its *letter* is
stale. Reconcile: the only cost-named key permitted is `cost_override_usd`,
and on managed-key turns it must be `None` (the pool draws normally). That
preserves the invariant and encodes the ratified exception.

## 4. What this feeds

**ADR-441** — the conversation-mount contract: (D1) two thread renderers
ratified along the altitude seam, never merged; (D2) the lane mount contract
named; (D3) the reference projection moves into the Web Viewer app; (D4) one
SSE transport helper; (D5) the fossil deletions; (D6) the gate reconcile.
