# ADR-289: Feed and Conversation Surfaces — Invocation as the Grouping Primitive

**Status**: Phase 1 BE Implemented 2026-05-18 — Phase 2 FE Proposed
**Date**: 2026-05-18
**Dimensional classification**: **Channel** (Axiom 6) primary — defines surface rendering shape; **Substrate** (Axiom 1) secondary — re-anchors the narrative `invocation_id` envelope field to its canonical source row; **Identity** (Axiom 2) tertiary — clarifies which actor classes render in which surface.

**Supersedes**:
- ADR-219 D5 visual rendering policy (chat-bubble-everywhere for material weight). The two-tier weight enum and pulse vocabulary survive intact; the rendering primitives change.

**Amends**:
- ADR-237 (Chat Role-Based Design System) — the four-shape MessageDispatch grammar (`user-bubble | reviewer-bubble | agent-bubble | system-activity`) survives but applies ONLY in the Conversation surface. The Feed surface uses typed event rows, not bubbles.
- ADR-258 revised (Reviewer-as-personified-feed-mode-operator) — per-action Reviewer narration via `surface_reviewer_actions` survives unchanged on the substrate side; only how the rendered rows group changes.
- ADR-259 (Feed Surface vocabulary rename) — completes the rename's structural arc. ADR-259 said "operations timeline, not chat history"; this ADR makes the rendering grammar match.
- ADR-272 D2 (chat narrative collapses to 4 shapes) — the four shapes survive but get scoped to the Conversation surface only.
- ADR-277 (Feed emission policy) — emission policy unchanged; what changes is how surviving emissions render.

**Preserves**:
- FOUNDATIONS Axiom 1 (Substrate), Axiom 2 (Identity), Axiom 4 (Trigger / pulse), Axiom 6 (Channel), Axiom 9 (Invocation + Narrative).
- ADR-194 v2 Reviewer substrate.
- ADR-209 Authored Substrate (attribution unchanged).
- ADR-250 Phase 2 / Migration 165 `execution_events` substrate table (this ADR makes it load-bearing for narrative grouping).
- ADR-258 D2 InteractiveModal chip→modal pattern for proposals.
- ADR-277 emission policy (mechanical-fire silence at source).
- Migration 161 narrative envelope (`metadata.invocation_id`, `pulse`, `weight`, `task_slug`, `summary`, `provenance`).

---

## 1. Context

Production audit on kvk's alpha-trader workspace surfaced two layered problems with how the feed surface renders:

1. **Visual conflation.** Reviewer-directed action narrations ("Firing recurrence on Reviewer's direction. SyncPlatformState: 1 written, 0 unchanged") render as chat bubbles visually identical to operator–Reviewer conversation. The surface treats orchestration plumbing and conversation as the same shape.

2. **Bundle structure destroyed at the substrate boundary.** A single Reviewer trigger cycle ("wake") produces N action narration rows + 1 verdict row in `session_messages`. The bundle exists in memory in `reviewer_agent.actions_taken: list[dict]` but is flattened to N independent rows at the surfacing boundary (`services/reviewer_chat_surfacing.py::surface_reviewer_actions`). The FE has no way to group them.

Operator observed both symptoms simultaneously: "10:46 / 10:48 / 10:50 PM" stacks of identical-looking rows with no anchor, in a chat-bubble grammar that makes every event read as conversation.

### Why prior framings were insufficient

WORKSPACE.md §4 already names the intent (*"operations timeline, not chat history"*). ADR-259 renamed chat→feed in May. ADR-272 collapsed seven bubble shapes to four. Each step was correct vocabulary-wise but did not reach the rendering primitives — the four surviving shapes are all bubble-shaped (`bg-muted rounded-2xl rounded-bl-md max-w-[92%]`), and every `session_messages` row maps to one bubble regardless of whether it's part of a conversation or part of an autonomous wake.

The deeper observation: chat bubbles are the right shape for conversation between an operator and a counterpart. They are the wrong shape for autonomous operations activity. The two surfaces have been conflated under one component.

### Why "wake_id" was the wrong instinct

A first-pass proposal added `wake_id` as a new envelope field to group Reviewer trigger cycles in the FE. This ADR rejects that approach because:

- "Wake" is a Reviewer-shaped concept. The moment user-authored Agents fire cycles, specialists run sub-invocations, or MCP write-backs land, the term does not fit. We would end up with `wake_id` + `agent_run_id` + `specialist_run_id` + future variants doing the same job under divergent vocabulary.
- FOUNDATIONS Axiom 9 names **invocation** as the atom of action. Every cycle through the six dimensions is one invocation, regardless of actor class. The grouping primitive should be invocation, not wake.
- `metadata.invocation_id` already exists in the narrative envelope (per ADR-219 Commit 2 / Migration 161). It currently links to `agent_runs.id`, which is the wrong substrate row post-ADR-261/271 sweep (the task-pipeline `agent_runs` write path is dead; Reviewer wakes do not produce `agent_runs` rows). The field exists, the link is broken — fixing the link is the correct move.

---

## 2. Decisions

### D1 — Two surfaces, two render grammars

The cockpit has exactly two surfaces that render `session_messages` rows. Both consume the same substrate; their rendering grammars are structurally different.

**Surface 1: The Feed** (`/feed`)

The workspace-wide operations timeline. Renders:
- **Invocation cards** — one card per `metadata.invocation_id` group. Card header reads from the linked `execution_events` row (shape, status, trigger, duration, model). Card body shows the verdict row (the persona-bearing actor's `role` row with reasoning). Constituent actions nest inside the card, collapsed by default, expandable.
- **Operator event markers** — rows with `role='user'`, rendered as compact marker lines (not right-aligned bubbles). When the user message opened an addressed exchange, the marker includes a pointer "opened conversation with Reviewer →" linking into the Conversation drawer scrolled to that invocation.
- **File events / capability events** — `role='system'` rows with no `invocation_id` group, or rows tagged as standalone substrate events. Compact typed-row treatment, not bubbles.
- **Day separators** — derived at render time from `created_at`. The Feed is asynchronous and multi-day; date anchors are required for legibility.
- **Proposal chips** — interactive chip→modal pattern (ADR-258 D2). Unchanged.

The chat-bubble grammar is retired on this surface entirely. Bubbles imply conversation. The Feed is not a conversation.

**Surface 2: The Conversation** (drawer on `/feed`, right panel on `/work`, `/agents`, `/context`, `/workspace`)

The chat-shaped exchange between operator and a counterpart. Renders:
- **Bubble grammar per ADR-237 + ADR-272** — `user-bubble`, `reviewer-bubble`, `agent-bubble`. The `system-activity` shape from ADR-272 D2 is dropped from this surface — system activity is not conversation. (It remains a valid substrate role on `session_messages`; it just doesn't render in the Conversation surface.)
- **Render filter**: rows where `metadata.pulse = 'addressed'`. Autonomous wakes (periodic / reactive / heartbeat triggers) do not appear in the Conversation surface — they belong to the Feed.
- **Action pointers** nested under the counterpart's bubble when the counterpart performed actions during the addressed turn. Format: `↳ Wrote /workspace/...`, `↳ Proposed AAPL 30sh`. These are read from the same `actions_taken` substrate that the Feed renders as nested rows under the invocation card. Same data, two render contexts.

The two surfaces share substrate. They differ in grouping shape and rendering primitives.

### D2 — `metadata.invocation_id` re-anchored to `execution_events.id`

The narrative envelope's `invocation_id` field — established by Migration 161, currently documented in `services/narrative.py` as pointing to `agent_runs.id` — is re-anchored to `execution_events.id`.

Rationale:
- `agent_runs` is the legacy task-pipeline audit table (Migration 098). The task pipeline as a separate execution path was dissolved by ADR-261. Reviewer wakes do not produce `agent_runs` rows. The current field link is broken in practice.
- `execution_events` (Migration 165, ADR-250 Phase 2) is the canonical authoritative record of every invocation attempt: one row per invocation, always written regardless of outcome. Shape, trigger_type, status, cost, tokens, duration. This IS the substrate row for Axiom 9's invocation atom.
- Re-anchoring the link makes the narrative envelope's invocation pointer agree with the canonical substrate row. The grouping primitive on the FE becomes "rows sharing `metadata.invocation_id`," and that ID resolves to a substrate row carrying invocation header data.

No envelope schema change — the field exists. No new column on `session_messages` — the JSONB envelope already holds the field. The change is at the write sites (which value gets stamped) and at the consumer (what the field resolves to).

Legacy data: rows on `main` with `metadata.invocation_id` pointing at `agent_runs.id` are pre-users and will be wiped during the standard alpha reset cycle. No coercion layer is added.

### D3 — Addressed cycles become first-class invocations

Today, scheduler-fired and reactive-trigger invocations write `execution_events` rows. Operator-addressed cycles in `routes/feed.py` do not — the addressed turn produces narrative rows but no invocation row.

This ADR commits to writing an `execution_events` row for every addressed cycle. Specifically:
- `routes/feed.py::dispatch_addressed_turn` (or its equivalent named site) writes an `execution_events` row at the start of the cycle with `trigger_type='addressed'`, `shape='addressed'` (or a stable equivalent), `status='in_progress'`, captures the returned `id`.
- The captured `execution_event_id` flows into `reviewer_agent.invoke_reviewer()` as a new `invocation_id` parameter.
- Reviewer threads the ID into every entry in `actions_taken`.
- The cycle's narrative writes — operator user row, Reviewer reply row, action narrations — all stamp `metadata.invocation_id` with that ID.
- On cycle completion, the `execution_events` row is finalized with `status`, `tool_rounds`, token usage, `duration_ms`.

Net effect: every actor class — Reviewer scheduler-fired, Reviewer reactive, Reviewer addressed, future user-authored Agents, future specialist sub-invocations, future MCP write-backs — produces invocations under a single substrate vocabulary. The narrative envelope's invocation pointer is universal across actors.

### D4 — `reviewer_agent.invoke_reviewer` accepts and propagates `invocation_id`

The Reviewer loop is the LLM cycle. Its caller (the dispatcher) generates the `execution_events` row; the Reviewer receives the row's ID and propagates it.

Signature change: `invoke_reviewer(trigger, context, invocation_id: str, ...)` — required parameter, not optional. Threading the ID through `actions_taken` entries lets `surface_reviewer_actions` stamp it on every narration row without re-deriving from caller context.

The `ReviewerOutput` dataclass gains `invocation_id` for symmetry with `actions_taken[*].invocation_id`. The verdict-row write at cycle close stamps the same ID.

### D5 — `surface_reviewer_actions` stamps `metadata.invocation_id` on every emitted row

`services/reviewer_chat_surfacing.py::surface_reviewer_actions` already iterates `actions_taken` and writes one `system_agent`-role narration row per consequential action. This ADR adds: each emitted row stamps `metadata.invocation_id` with the ID from the action record (or from the function's new `invocation_id` parameter as fallback).

`narrate_reviewer_action` is unchanged — it's a pure body-text composer. The substrate write at line 244 (`write_narrative_entry(... extra_metadata=meta)`) gains `invocation_id` in `meta`.

The verdict row write (currently in `invocation_dispatcher` after the Reviewer loop completes) stamps the same ID.

### D6 — FE grouping primitive is `metadata.invocation_id`

`FeedPanel.tsx` (or its successor in the Feed surface) groups `session_messages` by `metadata.invocation_id` to render invocation cards. Rows without `invocation_id` (operator standalone messages, certain system events) render as standalone typed-event rows.

The Conversation surface filter is independent: `WHERE metadata.pulse = 'addressed'`. Within the Conversation, grouping by `invocation_id` is still useful (so the addressed-turn's operator question + Reviewer reply + nested action pointers are one visual unit), but the filter itself is pulse-driven.

### D7 — Surface deployment topology

| Route / context | Surface rendered | Grouping primitive | Filter |
|---|---|---|---|
| `/feed` (center) | Feed | `metadata.invocation_id` | All rows in workspace session |
| `/feed` drawer (when operator engages a conversation) | Conversation | `metadata.invocation_id` (intra-conversation) | `pulse='addressed'` |
| `/work` right panel | Conversation | same | `pulse='addressed'` |
| `/agents` right panel | Conversation | same | `pulse='addressed'` |
| `/context` right panel | Conversation | same | `pulse='addressed'` |
| `/workspace` right panel | Conversation | same | `pulse='addressed'` |

The Feed surface exists in exactly one route. The Conversation surface exists in all chat-mounted panel contexts. The previous behavior — `FeedPanel` rendering the entire workspace history identically across every page's right panel — is retired.

### D8 — Composer scoping

The composer (text input + send) appears in:
- `/feed` bottom — defaults to addressing the Reviewer (current behavior). Submission produces a `pulse='addressed'` invocation cycle.
- Right-panel Conversation — same submission semantics, with `surfaceOverride` informing YARNNN's prompt context.

The composer's submission shape is unchanged. What changes is what the resulting messages render as on each surface (Feed: marker row pointing at the conversation; Conversation: addressed bubble exchange).

### D9 — `system-activity` shape is retired on the Conversation surface

ADR-272 D2 established four message shapes including `system-activity` (ambient orchestration narration). This ADR scopes that shape to the Feed surface only — system activity is part of operations, not conversation. The Conversation surface renders only the three actor-bubble shapes: `user-bubble`, `reviewer-bubble`, `agent-bubble`.

Substrate-level role values on `session_messages` are unchanged. Only the render dispatch differs by surface.

### D10 — Singular Implementation discipline

`web/components/tp/MessageDispatch.tsx` + `web/components/tp/MessageRow.tsx` together implement today's single rendering path. This ADR splits the responsibility:

- **Conversation surface** retains the bubble grammar. `MessageDispatch.tsx` becomes Conversation-only.
- **Feed surface** gets a new rendering path with typed-event row components: `InvocationCard`, `OperatorEventMarker`, `FileEventRow`, `CapabilityEventRow`, `DaySeparator`, `ProposalChip`.
- **`MessageRow.tsx`** is split — its row-wrapper concerns split into `ConversationRow` (the row wrapper for bubbles, retains weight gating + authorship chip + Make-Recurring affordance) and the Feed-side render is a different shape that doesn't need a row wrapper.

The single-path discipline is honored by surface, not by component reuse: one surface has exactly one render path; two surfaces have two paths. No conditional branching on "are we in the Feed or the Conversation" inside a shared component — each surface has its own renderers.

Code deletions:
- `web/components/tp/MessageDispatch.tsx::renderSystemActivity` deleted (the Conversation surface doesn't render system rows; the Feed surface uses typed event components).
- The flat `messages.map(msg => <NarrativeMessage />)` in `FeedPanel.tsx` is replaced. The legacy `FeedPanel` is split:
  - `FeedPanel` → `ConversationPanel` (handles the right-panel and drawer cases; consumes pulse-filtered, invocation-grouped messages).
  - New `FeedTimeline` component for the `/feed` center surface, consuming all messages grouped by `invocation_id`.
- `ThreePanelLayout.tsx::chat` prop renames to `conversation` to reflect the surface it now mounts. The `chat?: {...}` prop block migrates to `conversation?: {...}`. All four call sites (`/work`, `/agents`, `/context`, `/workspace`) update. The `/feed` page stops mounting a right-panel chat — the Feed IS the chat-adjacent surface, no glue chat panel is needed.

---

## 3. What this ADR does NOT do

- **No schema changes.** `session_messages.metadata` is JSONB; the envelope field exists. `execution_events` exists (Migration 165). No new tables, no new columns, no migrations.
- **No primitive registry changes.** The primitive matrix is unchanged. No new primitives, no renames.
- **No prompt changes** beyond a docstring fix in `api/services/narrative.py` (the `invocation_id` doc string says "agent_runs.id" and needs to say "execution_events.id").
- **No vocabulary divergence.** "Wake" is rejected as a substrate concept. The atom is "invocation" per Axiom 9.
- **No backward-compat shim.** Pre-ADR-289 rows with `invocation_id` pointing at `agent_runs.id` are dead-link data; pre-users, will be wiped on reset. No coercion layer.
- **No new actor class.** This ADR does not introduce user-authored Agents, specialists, or MCP write-backs as new surfaces — they are anticipated as future invocation classes that inherit this ADR's grouping primitive for free.
- **No mobile design.** Mobile is current default — small screens navigate to `/feed` and don't show right-panel Conversation. Post-Phase-2 question.
- **No realtime subscription change.** `useSessionMessagesRealtime` is unchanged; both surfaces consume from the same realtime stream and apply their own filter/grouping at render.
- **No Reviewer prompt content change.** The Reviewer's persona, tool surface, and verdict shape are unchanged. Only the dispatcher's writes change.

---

## 4. Implementation phases

**Phase 1 — Substrate alignment (BE, single atomic commit) — Implemented 2026-05-18**

1. ✓ `routes/feed.py` addressed-cycle dispatch site writes an `execution_events` row at cycle close with `slug="addressed"`, `mode="judgment"`, `trigger_type="addressed"`. Pre-generates `invocation_id` in `response_stream`, threads through `_dispatch_reviewer_turn`. Failure branch writes `status="failed"`, `error_reason="exception"`.
2. ✓ `reviewer_agent.invoke_reviewer()` accepts required `invocation_id: str` keyword parameter; threads it into every `actions_taken` entry and the final `ReviewerOutput`. `ReviewerOutput` TypedDict declares the field. Operator-cancellation early return stamps it.
3. ✓ `services/invocation_dispatcher.py` judgment dispatch pre-generates `invocation_id = str(uuid.uuid4())`; passes to `invoke_reviewer(invocation_id=...)`; stamps `id=invocation_id` on both success and failure `record_execution_event` calls.
4. ✓ `services/reviewer_chat_surfacing.py::surface_reviewer_actions` reads `action.get("invocation_id")` from each action record and passes through `write_narrative_entry(invocation_id=...)`.
5. ✓ `write_reviewer_message` accepts optional `invocation_id` and passes through to `write_narrative_entry`.
6. ✓ `routes/feed.py` operator user message `append_message` stamps `metadata.invocation_id`. Both progress-drain and post-loop drain system_agent narrations also stamp it.
7. ✓ `services/narrative.py` docstring re-anchored: `invocation_id` documented as `execution_events.id` (canonical invocation atom per FOUNDATIONS Axiom 9). Pre-ADR-289 wording about `agent_runs.id` removed.
8. ✓ `services/telemetry.py::record_execution_event` accepts optional caller-supplied `id` parameter and returns the inserted row id (or None on failure). Pre-ADR-289 callers (no `id`) continue to work — Postgres generates the UUID.
9. ✓ `services/review_proposal_dispatch.py::_run_ai_reviewer` pre-generates `invocation_id`, passes to `invoke_reviewer`, stamps on every `write_reviewer_message` site (advisory + defer + observe-only fallback). `_execute_reviewer_directives` accepts + threads `invocation_id`. `_write_observation` accepts + stamps.
10. ✓ Test gate `api/test_adr289_invocation_id_anchoring.py` (25/25 PASS) asserts every wiring point above.

**Deferred to Phase 1B**: proposal-arrival reactive cycles do not yet write a finalized `execution_events` row. `_run_ai_reviewer` has 7+ exit branches; finalizing the audit row across all of them is its own refactor. Narrative grouping by invocation_id works for proposal-arrival rows today (Reviewer + action narrations share the id); the audit-row coverage gap is forensic-substrate only. Schedule Phase 1B when a) proposal-arrival cycle audit becomes load-bearing, or b) we refactor `_run_ai_reviewer` for another reason and can fold this in.

Net delta: ~100 LOC across 7 files. Zero behavioral change on the FE (still renders flat — Phase 2 picks up the grouping).

**Phase 2 — Feed surface rendering (FE, single atomic commit)**

1. New components: `web/components/feed/FeedTimeline.tsx`, `InvocationCard.tsx`, `OperatorEventMarker.tsx`, `FileEventRow.tsx`, `CapabilityEventRow.tsx`, `DaySeparator.tsx`.
2. `/feed` page rewires: replaces the FeedSurface→FeedPanel chain with FeedSurface→FeedTimeline at the center; the drawer mounts `ConversationPanel`.
3. `web/components/tp/FeedPanel.tsx` renames to `ConversationPanel.tsx` (operator-facing semantics align with the surface it serves). All identifier references update in the same commit.
4. `web/components/tp/MessageDispatch.tsx::renderSystemActivity` deleted. The 4-shape grammar collapses to 3 actor shapes for the Conversation surface.
5. `web/components/tp/MessageRow.tsx` retains its weight gating + cross-cutting wrappers, scoped to Conversation use.
6. `web/components/shell/ThreePanelLayout.tsx::chat` prop renames to `conversation`. Four call sites (`/work`, `/agents`, `/context`, `/workspace`) update atomically.
7. `/feed` page removes the right-panel chat mount — the Feed surface stands alone; conversation engagement opens a drawer over the Feed.
8. Day separator, invocation card grouping, operator event marker pointer-into-conversation all wired.

Net delta: ~700 LOC additions, ~300 LOC deletions, ~10 files renamed.

**Phase 3 — Doc-radius cascade (same commit as Phase 2)**

1. `docs/design/WORKSPACE.md` Tab 4 (Feed) rewritten — typed event rows replace bubble grammar; Conversation surface contract added.
2. `docs/architecture/FOUNDATIONS.md` Axiom 9 derived-principle note updated — invocation is the cockpit's grouping primitive across surfaces.
3. `docs/architecture/invocation-and-narrative.md` updated — `execution_events` named as the canonical substrate row.
4. `docs/adr/ADR-219-invocation-narrative-implementation.md` D5 visual-rendering banner pointing here.
5. `docs/adr/ADR-237-chat-role-based-design-system.md` banner — four-shape grammar scoped to Conversation.
6. `docs/adr/ADR-258-reviewer-as-personified-chat-mode-operator.md` (or its `feed-mode` variant) banner — per-action narration substrate unchanged; rendering layer collapses into invocation cards.
7. `docs/adr/ADR-259-feed-surface.md` banner — rendering grammar arc closed.
8. `docs/adr/ADR-272-identity-collapse-system-agent-and-specialist.md` D2 amendment note — four-shape grammar scoped to Conversation; Feed uses typed events.
9. `docs/adr/ADR-277-feed-emission-policy.md` cross-reference — emission policy unchanged; render shape changes.
10. `CLAUDE.md` Architecture section entries for ADR-289.
11. `api/prompts/CHANGELOG.md` entry.

---

## 5. The rule of thumb (canon)

Surfaced for future ADRs that add new actor classes or rendering surfaces:

> **Invocation is the atom. `execution_events` is its substrate row. `metadata.invocation_id` is its narrative envelope link.**
>
> Any new actor class that produces narrative rows MUST write an `execution_events` row for its cycle and stamp `metadata.invocation_id` on the narrative rows it emits. No new vocabulary for grouping — the atom is universal.
>
> Rendering grammar splits by surface, not by actor: the Feed renders typed-event rows for operations activity; the Conversation renders bubbles for `pulse='addressed'` exchanges. The four-shape bubble grammar from ADR-237/272 belongs to the Conversation surface.

---

## 6. Acceptance criteria

**Phase 1 (BE) — landed 2026-05-18:**
- [x] Every addressed cycle in `routes/feed.py` writes an `execution_events` row.
- [x] Every Reviewer scheduler-fired cycle's `execution_events.id` propagates into `invoke_reviewer` and stamps `metadata.invocation_id` on every emitted narrative row.
- [x] `services/narrative.py` docstring documents `invocation_id` as `execution_events.id`.
- [x] Test gate `api/test_adr289_invocation_id_anchoring.py` passes (25/25).

**Phase 2 (FE) — pending:**
- [ ] `/feed` renders invocation cards, operator event markers, file events, capability events, day separators — no chat bubbles for non-addressed rows.
- [ ] `/feed` drawer renders the Conversation surface with bubble grammar when operator engages an addressed exchange.
- [ ] `/work`, `/agents`, `/context`, `/workspace` right-panel render the Conversation surface (bubble grammar, `pulse='addressed'` filter).
- [ ] `ThreePanelLayout::chat` prop renamed to `conversation` at all four call sites.
- [ ] `MessageDispatch::renderSystemActivity` deleted.
- [ ] `FeedPanel` renamed to `ConversationPanel` (or equivalent — operator-facing semantics align with Conversation, not Feed).
- [ ] Doc-radius cascade applied in same commit as Phase 2.

**Phase 1B (proposal-arrival audit row) — deferred:**
- [ ] `_run_ai_reviewer` writes a finalized `execution_events` row across all exit branches.

---

## 7. Discourse log

This ADR resolves a multi-turn architectural discourse session (2026-05-18):

1. Operator observation: feed surface renders Reviewer-directed mechanical-mirror narrations as chat bubbles indistinguishable from operator–Reviewer conversation. Initial framing was "noise filter / ADR-277 extension."
2. Reframe to design surface gap: WORKSPACE.md §4 already names "operations timeline, not chat history" as the Feed's intent; the rendering grammar never followed.
3. Sketch round: ASCII mockups of typed-event Feed + Conversation drawer. Operator aligned on direction.
4. Audit caught: `FeedPanel` mounts in five places (one center, four right-panel). The two surfaces had been conflated under one component across the cockpit.
5. Refinement: Feed exists at `/feed` only; Conversation is the right-panel surface on every other page AND the drawer on `/feed`. Two genuinely separate components.
6. Substrate question: is `wake_id` the right grouping primitive?
7. Resolution: no. Invocation is the axiomatic atom; `execution_events` is its substrate row; `metadata.invocation_id` is the envelope link (already exists, currently misaligned). Re-anchoring the link is the structural answer.
8. Addressed-cycle gap surfaced: today's addressed cycles don't write `execution_events` rows. Closing that gap makes invocation universal across actor classes.
9. ADR drafted.

---

**End of ADR-289. Phase 1 BE implementation deferred to a follow-on commit per the standard discipline (ADR ratify first, code follows).**
