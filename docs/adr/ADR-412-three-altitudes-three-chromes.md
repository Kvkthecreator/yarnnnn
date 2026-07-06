# ADR-412: Three Altitudes, Three Chromes — the AI-interaction IA

**Status**: Accepted (2026-07-06, operator-ratified in discourse — "this fully matches, let's proceed"). Rewritten in place: this file's first commit (`08e75f0`) carried the viewer-parameter draft, which over-weighted the multi-viewer correctness pass; the discourse re-centered on the single user's mental model over the new AI landscape. The viewer-parameter material survives, demoted, as D6.
**§10 step 1 Implemented (2026-07-06)** — D3 + D2 core: the `chat` kernel surface (primary tier, second after Home; registry + `desk.ts` union + array + SurfaceRegistry; the redirect stub replaced by `ChatSurface`), work-first recents (updated_at-desc, model chip + filter facet, `chat.lane` window-namespaced param), `LanePanel` relocated `shell/chrome/` → `components/chat-surface/`, the drawer purified to steward-only (lane strip/state/create-form deleted). Gate `api/test_adr412_chat_surface.py` 25/25; ADR-411 mechanics gate PASS untouched; ADR-297 phase-1 gate 168/0 (two stale `feed`-era assertions fixed in the same commit); launcher gates (ADR-349 35/0, ADR-340 P3 20/0) updated to the new primary set; `tsc --noEmit` clean. The D2 steward-thread TAIL (session-boundary legibility, history surfacing, per-workspace drawer behavior) remains open within step 1.
**§10 step 2 Implemented (2026-07-06)** — D5, with one honest widening vs this ADR's text: ADR-387 §6.4 had homed **five** registry panes on the roster (identity · principles · autonomy · budget · expected-output), not just autonomy — the reversal re-homes all five (`pane_of: workspace-settings`, one flattened **System Agent** pane group) plus the two local panes (capabilities · activity). The Freddie card + `ReviewerDetail` + the ADR-387 pane shell leave `/agents` (the roster filters the freddie class; stale `?agent=freddie` deep-links fall to list mode); the governor frame line lands (ADR-381 D5); pane bodies extract to `web/components/agents/SystemAgentPanes.tsx` (Singular Implementation — Workspace Settings mounts it; the ADR-387 `MOVED_TO_FREDDIE` net deletes, so pre-387 bookmarks resolve again); the five route stubs retarget `/workspace-settings?workspace-settings.pane=…`; the overlay Activity link + comment sweep ride along. Gate extended to 52/52 ((c)+(d) blocks); the ADR-387-era placement assertions in `test_adr341`/`test_adr347`/`test_adr340_p2` re-pointed to the D5 state (46/0 · 32/0 · 95/0); `tsc --noEmit` clean.
**Date**: 2026-07-06
**Dimension**: Channel (Axiom 6 — where each kind of AI lives in the shell) + Identity (Axiom 2 — the three altitudes made legible by placement)
**Relates to**: ADR-408 D2 (the three altitudes — this ADR is their chrome), ADR-411 (lanes — their windowed home lands here), ADR-410 (attention rework — stands as-is; D6 rides its build session), ADR-340/349 (launcher IA — one primary tile added for a new capability, not a re-sort), ADR-316 (chat as dockable rail — the rail is confirmed and purified), ADR-381 (Freddie — D5 governor framing carried onto the roster)
**Amends**: ADR-411 (the lane strip leaves the chat drawer; the Chat surface becomes the lanes' home), ADR-387 §6.4 (the autonomy pane re-homes from Freddie's roster pane to Workspace Settings — reversal stated honestly in D5), ADR-214/251 (Freddie/systemic card leaves the Agents roster), ADR-259/385 lineage (the `/chat` redirect stub retires; the slug is reclaimed as a real surface), ADR-408 D5 (the first-cut relocation list is superseded by this partition)

---

## 1. Context — the mix-up is in the chrome, not the canon

ADR-408 D2 named three kinds of AI with different relationships to identity,
autonomy, and persona. The canon is clean; the chrome contradicts it in two
places, observed live:

1. **Freddie renders in two homes**: a card on the `/agents` roster (with its
   config panes — `foregroundSurface('autonomy')` resolves to a Freddie pane
   there per ADR-387 §6.4) *and* the first chip in the chat drawer.
2. **Lanes render as the steward's siblings**: the ADR-411 lane strip puts
   the steward chip and lane chips in one row of one drawer.

Same chrome implies same kind. A user reading the drawer concludes "Freddie
is one of my chats"; a user reading the roster concludes "Freddie is one of
my agents." Both are false (ADR-408 D2), and no labeling fixes what
placement asserts. The fix is not pedagogy — it is giving each altitude the
chrome that matches a category users already hold: the OS assistant
(Siri/Spotlight), your chats (the ChatGPT/Claude-app shape), and staff.

## 2. D1 — The taxonomy is carried by chrome; placement is the pedagogy

| Altitude | Kind | Chrome home | Never appears as |
|---|---|---|---|
| 1 | **Freddie** — the system agent | **The rail only** (the chat drawer, ADR-316): part of the shell, summonable everywhere | a window, a launcher tile, a roster card, a chat among chats |
| 2 | **Lanes** — the member's model-pinned helpers | **The Chat surface** (D3): a windowed workbench of the member's conversations | chips beside the steward; a principal |
| 3 | **Agents** — persona agents + user-authored domain agents | **`/agents`** — the judgment roster | conflated with either of the above |

Each altitude gets exactly one chrome home. Cross-references are links, not
co-presence: the rail can deep-link to Freddie's Settings group; the Chat
surface can deep-link to Files where a lane wrote; the roster frame names
Freddie without seating him.

## 3. D2 — The rail purifies to the steward

The lane strip leaves the chat drawer (amending ADR-411's placement — the
strip was the right v1 mount, wrong permanent home). The drawer becomes
**Freddie only**: one thread per member per workspace (ADR-407 Phase 4),
the OS terminal. The drawer header is Freddie's identity and deep-links to
the Workspace Settings System-Agent group (D5).

The **steward single-thread tail** (session-boundary legibility, history
surfacing, per-workspace drawer behavior — the polish ADR-408 D6 named as
prerequisite) rides this purification: it is rail work, owned by D2's build.

## 4. D3 — Chat: the lanes surface

A new windowed kernel surface: **slug `chat`, route `/chat`** (the ADR-308
redirect stub to Notifications retires — the slug's third life; old
narrative bookmarks land on Chat, an accepted minor break), launcher tier
**primary** (Workspace group). Scope: **member experience** — it lists the
viewer's own lanes in the acting workspace (ADR-407 D6; lanes are private
threads, the commons is where their work lands).

- **Body**: lane list (the relocated strip's data, `GET /api/lanes`) +
  the conversation panel (`LanePanel` relocates from the drawer chrome to
  the surface body) + inline lane creation. Streaming and deeper session
  management remain the ADR-411 additive path.
- **The guardrail**: Chat is a *workbench over the shared workspace*, not
  the product's center. Home stays the front page; the ADR-411 contract is
  restated on the surface itself (lanes are isolated conversations; the
  workspace is the shared memory) — the surface links outward to the
  commons (files a lane touched), never inward to other transcripts.
- **Launcher note**: adding one primary tile for a *new capability's home*
  is not the evidence-gated recomposition of D7 — no existing surface moves.
  At-rest Workspace tier becomes **Home · Chat · Channels · Files · Agents**
  (Notifications stays bell-fronted `search-only` per ADR-349 — corrected
  from this ADR's first print, which mislisted it in the tier).

## 5. D4 — Lanes organize by work, never by model

The Chat surface is **flat recents of named lanes**: recency-ordered, each
row carrying the lane's name (the work) with the pinned model as a **chip**,
plus a model **filter facet** for the by-engine view on demand. Model-first
folders are rejected on our own precedent — ADR-385 ruled *group by
relationship, never transport; transport is row metadata* — and on recall:
the user's memory key is "the landing-page thread," not "a Gemini
conversation." Model-first grouping also splits one thread of work across
folders the moment it spans two lanes on two models. The model is the
lane's *setting*, legible everywhere (chip on the row, header of the panel,
`via ‹model›` in attribution) — never the namespace.

## 6. D5 — The Agents roster purifies; Freddie's legibility re-homes

- **The Freddie card leaves `/agents`.** The roster is Altitude 3: domain
  agents today, persona agents when ADR-382 builds. The ADR-214/251
  systemic-card convention ends.
- **The governor frame stays** (ADR-381 D5 legibility): one line on the
  roster — agents are created and governed by Freddie — a frame, not a
  seat. Manager in the letterhead, not a card among staff.
- **Freddie's panes re-home to Workspace Settings** as a **System Agent
  group** (Autonomy [the ADR-366 Grant] · Activity · Capabilities). This
  honestly **reverses ADR-387 §6.4's** placement (autonomy `pane_of:
  agents` → `pane_of: workspace-settings`): §6.4 was right that autonomy
  is Freddie's grant, but Freddie's inspection surface belongs on the
  system layer, not the staff roster. Call sites stay pane-blind — pane
  resolution is registry-driven (ADR-340 P2), so `foregroundSurface('autonomy')`
  follows the registry row.

## 7. D6 — The viewer-parameter correctness pass (demoted, unchanged in substance)

The multi-viewer machinery from this file's first draft survives as a
compact correctness pass riding **ADR-410's build session** (it is a
prerequisite of ADR-410's own gate):

- **The viewer-resolution layer**: one FE context `{viewerPrincipalId,
  roster}` (from `GET /api/workspace/members`) + a viewer-aware resolver
  above the sync attribution labeler ("You" / "You via GPT-4o mini" /
  "‹member› via ‹model›") — one module, one added layer (ADR-388 D3).
- **Grant-derived affordances**: authoring/consequential affordances render
  per the viewer's grant coverage, never a role enum (the UI twin of
  ADR-405's no-species-law) — constitution band author-drafts, activation
  CTA, Workspace Settings constitutional panes (explicit read-only). Reads
  stay universal; FE gating is legibility, the server gate is enforcement.
- **Ambient context**: which-workspace indicator + a compact who's-here
  roster read (membership, not presence).
- A fresh member lands on `/home` unchanged — the same front page is the
  right landing once rendered honestly. No member onboarding flow, no
  member composition set, ever: the viewer is a parameter, never a fork.

## 8. D7 — Standing items confirmed

- **ADR-410 stands as-is** (ratified alongside; the attention chapter).
- **Recomposition stays evidence-gated**: launcher re-sorts of *existing*
  surfaces, Home re-weighting, member-shaped compositions — deferred on
  lived two-account use after the correctness pass (ADR-340 §9's launcher
  item stays CLOSED per ADR-349; D3's added tile is a new home, not a
  re-sort).
- **Per-actor / per-model Usage view**: held for ADR-409 (ledger columns
  make it buildable any time, DP29-derived).
- **FOUNDATIONS**: the viewer-parameter clause joins the owed ADR-407 D10
  cascade; the three-chromes mapping lands in GLOSSARY (Freddie / Lane /
  Agent entries gain their chrome-home line) in the same doc pass.

## 9. What this ADR does NOT do

- No change to the ADR-411 contract or mechanics (lanes stay isolated
  conversations over one shared memory; tool surface, attribution, metering
  untouched) — only the lane UI's home moves.
- No shared chatrooms, no presence, no realtime (standing rejections).
- No model-first grouping anywhere (D4).
- No new altitude, principal kind, or autonomy dial.
- No member-specific surface set (D6 forbids the fork).
- No pricing surfaces (ADR-409 demand-gated).
- No backend/gate/grant changes — this is Channel-dimension work; the one
  registry change is the pane re-home (D5) + the new `chat` surface row.

## 10. Sequencing

1. **D3 + D2 together** (one FE session): the Chat surface (slug reclaim,
   lane list + LanePanel relocation, work-first recents) and the drawer
   purification (strip removal + steward-thread tail polish) — they are two
   sides of one move.
2. **D5**: roster purification + Settings System-Agent group + pane
   re-home (registry change + redirect hygiene).
3. **D6 rides ADR-410's session** (unchanged; its §5 sequencing stands).
4. Doc cascade (GLOSSARY + FOUNDATIONS rider) with the last code commit.

Gate: FE source-guards per house style — (a) the drawer renders no lane
strip and exactly one steward thread; (b) `/chat` is a windowed surface
listing only the viewer's lanes, recency-first with model chips;
(c) `/agents` renders no Freddie card and carries the governor frame line;
(d) `foregroundSurface('autonomy')` resolves into Workspace Settings;
(e) ADR-411's gate stays green (lane mechanics untouched).
