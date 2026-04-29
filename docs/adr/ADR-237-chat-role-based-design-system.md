# ADR-237: Chat Role-Based Design System — One Dispatch Table, One Grammar

> **Status**: **Implemented** (2026-04-29, single commit). Round 2 of the ADR-236 frontend cockpit coherence pass — the second Tier 1 sub-ADR. Test gate `api/test_adr237_chat_role_grammar.py` 7/7 passing. TypeScript typecheck clean. Cross-ADR regression check 57/57 across six gates (231 + 233 P1 + 233 P2 + 234 + 237 + 238). CHANGELOG entry `[2026.04.29.10]` recorded.
> **Date**: 2026-04-29
> **Authors**: KVK, Claude
> **Dimensional classification**: **Channel** (Axiom 6) primary — a shared formal grammar for chat-message rendering across roles. **Identity** (Axiom 2) secondary — the grammar is keyed on `TPMessage.role`, which is the chat-surface projection of FOUNDATIONS Axiom 2's identity layer.
> **Builds on**: ADR-189 (TP→YARNNN rename — Implemented), ADR-216 (Orchestration vs Judgment vocabulary — Implemented), ADR-219 (Invocation + Narrative implementation — Implemented), ADR-235 (UpdateContext Dissolution + ManageRecurrence + ManageAgent.create sunset — Implemented 2026-04-29 commit `9156db9`), ADR-236 (Frontend Cockpit Coherence Pass — Round 1 closed 2026-04-29), ADR-238 (Autonomy-Mode FE Consumption — Implemented 2026-04-29 commit `c769e64`).
> **Composition note for future sub-ADRs**: ADR-239 (Round 3 trader cockpit) will reuse the role-component dispatch when surfacing Reviewer / Agent / System cards inside cockpit faces — `MoneyTruthFace` and `TrackingFace` currently roll their own; the dispatch table this ADR ships becomes the substrate. ADR-240 (Round 4 onboarding-as-activation) consumes the role grammar for first-conversation rendering — operator's first turn sees the same components the steady-state chat does, no special onboarding path. Items 8.2 + 9 + 10 (Round 5 mop-up) all consume this surface.
> **Amends**: ADR-023 (Supervisor Desk — `TPMessages.tsx` retired as the legacy surface).
> **Preserves**: FOUNDATIONS axioms 1–9, ADR-141 (execution layers), ADR-156 (single intelligence layer), ADR-159 (filesystem-as-memory), ADR-194 v2 (Reviewer substrate), ADR-205 (chat-first triggering), ADR-209 (Authored Substrate attribution).

---

## Context

ADR-236's audit (2026-04-29) named "chat role-based design system" as Item 1 — the first Tier 1 architectural item. The diagnosis was: chat-role components were authored per ADR (ADR-193 ProposalCard, ADR-194 ReviewerCard, ADR-219 narrative weights, ADR-238 autonomy chip) without a coordinating grammar, and the dispatch logic for which-component-renders-which-role lives **inline inside `ChatPanel.tsx`'s `NarrativeMessage` function** as hand-rolled JSX with `msg.role` switching at multiple call sites.

### What's there today (verified 2026-04-29)

The chat surface has **eight role-component files** under `web/components/tp/`:

| File | LOC | Triggered by | Status |
|---|---|---|---|
| `SystemCard.tsx` | 161 | `msg.role === 'system'` (in NarrativeMessage) | Active |
| `ReviewerCard.tsx` | 107 | `msg.role === 'reviewer'` (in NarrativeMessage) | Active |
| `ProposalCard.tsx` | 255 | Specific narrative kinds (proposal-emit, etc.) | Active |
| `NotificationCard.tsx` | 38 | `msg.notification` payload | Active |
| `InlineActionCard.tsx` | 126 | `msg.actionCard` payload | Active |
| `InlineToolCall.tsx` | 309 | `msg.toolHistory` payload | Active |
| `ToolResultCard.tsx` | 438 | tool-result rendering | Active |
| `TPMessages.tsx` | 75 | **Zero imports — dead code** (legacy ADR-023 surface) | **Dead** |

The dispatch is in [`ChatPanel.tsx`'s `NarrativeMessage` function](../../web/components/tp/ChatPanel.tsx) (lines ~403–560), which:

1. Reads `msg.narrative?.weight` (material / routine / housekeeping) and branches.
2. Reads `msg.role` and branches inside `weight === 'material'`.
3. Reads `msg.role === 'user'` for the speech-bubble treatment.
4. Reads `msg.role === 'assistant'` for `inlineFireHint` derivation.
5. Reads `msg.notification`, `msg.actionCard`, `msg.toolHistory` from message payload.
6. Imports each role-component directly and threads ad-hoc props (`data`, `content`, `config`, etc.).

There are **six role values** declared at [`web/types/desk.ts:117`](../../web/types/desk.ts):

```ts
role: 'user' | 'assistant' | 'system' | 'reviewer' | 'agent' | 'external';
```

### Why this is debt — three concrete symptoms

**Symptom 1 — dead code persists.** `TPMessages.tsx` (75 LOC) has zero imports anywhere in the repo. It's a legacy ADR-023 "Supervisor Desk" surface that pre-dates the current rendering path. Singular Implementation says it goes; nothing in the audit caught it because no umbrella ADR was looking.

**Symptom 2 — props are hand-rolled, not normalized.** Every role-component receives a different prop shape:
- `<ReviewerCard data={msg.reviewer ?? {}} content={msg.content} />` — two-prop split between metadata and body
- `<SystemCard event={msg.system!} />` — single payload prop
- `<ProposalCard proposal={...} />` — own payload type
- `<NotificationCard notification={msg.notification} />` — own payload type
- `<InlineActionCard config={actionCard} onSelect onDismiss />` — config + handlers
- `<InlineToolCall ... />` — many specific props

Each new ADR (ADR-238 chip, future ADR-239 Reviewer-in-cockpit reuse) has to learn each shape independently. A role grammar would normalize them.

**Symptom 3 — no place to attach autonomy / authorship / weight as cross-cutting concerns.** ADR-238 added an autonomy chip *outside* the message render (above the form) because there was no row-level extension point. ADR-219's narrative weight (material/routine/housekeeping) is read inline at four different call sites in `NarrativeMessage`. ADR-209's `authored_by` attribution is rendered inline in `NarrativeMessage` only when `taskSlug` is set (line 437–442). Each new cross-cutting concern wedges into `NarrativeMessage` with its own conditional. Without a row-level abstraction, this metastasizes.

---

## Decision

ADR-237 codifies a **chat-message dispatch grammar** that consolidates the inline `msg.role` switching into one table-driven render path. Six role values, six rendering "shapes," one dispatch table. No new components introduced; the existing six active role-components survive (TPMessages.tsx deleted). Cross-cutting concerns (weight, authorship, autonomy posture) become row-level wrappers that compose around the dispatched component, not conditionals inside it.

### D1 — One dispatch table at `web/components/tp/MessageDispatch.tsx`

A new module exposes:

```ts
export type MessageShape =
  | 'user-bubble'        // role: 'user' — speech bubble, right-aligned
  | 'yarnnn-bubble'      // role: 'assistant' — speech bubble, left-aligned, YARNNN voice
  | 'system-event'       // role: 'system' — SystemCard
  | 'reviewer-verdict'   // role: 'reviewer' — ReviewerCard, full-width
  | 'agent-bubble'       // role: 'agent' — bubble with agent attribution chip
  | 'external-event'     // role: 'external' — muted-tone bubble (MCP / external write-back)
  ;

export function resolveMessageShape(msg: TPMessage): MessageShape;
export function MessageRenderer(props: { msg: TPMessage; ...rowProps }): JSX.Element;
```

`resolveMessageShape(msg)` is a pure function returning one of the six shapes from `msg.role`. `MessageRenderer` is the dispatch component — it calls `resolveMessageShape`, picks the right per-shape renderer, and applies row-level wrappers (weight, authorship chip, future autonomy hooks).

The six per-shape renderers live in the same module as small internal functions (or in a `web/components/tp/shapes/` folder if the file grows past ~400 LOC during implementation; the structural choice is implementation-time per-shape sizing, not an ADR-level decision).

### D2 — Cross-cutting concerns become row-level wrappers, not inline conditionals

Three cross-cutting concerns currently live inside `NarrativeMessage`:

- **Weight** (material / routine / housekeeping) — controls overall row visibility / styling
- **Authorship attribution chip** ("from {slug}" / "ran inline") — controls a small chip above the bubble
- **Make-recurring affordance** — controls a small button below user material messages

ADR-237 lifts each into a row-level wrapper applied **around** the dispatched shape:

```tsx
<MessageRow msg={msg} weight={weight} authorshipChip={authorshipChip} ...>
  <MessageRenderer msg={msg} ... />
</MessageRow>
```

`MessageRow` is the wrapper that handles the cross-cutting concerns. The shape renderers know nothing about weight or authorship — they render their content; `MessageRow` decides whether to show them at all (housekeeping is hidden), how to chrome them (with attribution), and what affordances surround them (Make Recurring).

This is the extension point ADR-238 needed and didn't have. Future autonomy-aware row treatments (e.g., a Reviewer verdict rendering differently when AUTONOMY = `bounded_autonomous`) compose into `MessageRow`'s prop surface, not into the per-role components.

### D3 — Per-role component prop normalization (selective, not exhaustive)

The six role components retain their existing prop interfaces — **with the explicit decision NOT to force a single uniform shape**. Forcing every role-component into a single prop signature would introduce abstraction churn for no real consumer-facing payoff. Singular Implementation says one grammar, not one shape.

But two normalizations land in this ADR because they reduce real friction:

- **`SystemCard.tsx`, `ReviewerCard.tsx`, `ProposalCard.tsx`, `NotificationCard.tsx`** — all four currently destructure `msg`-derived data via different paths. The dispatch wrapper extracts the right payload from `msg` and threads it; each component receives its own typed payload. **Net behavior: dispatch site cleans; components unchanged.**
- **`InlineActionCard.tsx`, `InlineToolCall.tsx`, `ToolResultCard.tsx`** — these are not role-components; they're **inline affordances** within an assistant or user bubble. They stay as their own surfaces; the dispatch wrapper does not touch them. The grammar applies to message-level rendering, not to per-content tool-result rendering.

This split (role-shape vs inline-affordance) is the structural insight the inline NarrativeMessage code was missing.

### D4 — `TPMessages.tsx` deleted

Verified zero imports across the repo (grep confirms). Per Singular Implementation Rule 7 of ADR-236: dead code goes when its replacement is verified. ADR-023 reference noted in this ADR's `Amends` header.

### D5 — `NarrativeMessage` collapses to a thin wrapper

`ChatPanel.tsx`'s `NarrativeMessage` function (lines 403–560 today, ~150 LOC of inline rendering) shrinks to:

```tsx
function NarrativeMessage({ msg, isLoading, onMakeRecurring }: ...) {
  return <MessageRow msg={msg} isLoading={isLoading} onMakeRecurring={onMakeRecurring}>
    <MessageRenderer msg={msg} isLoading={isLoading} />
  </MessageRow>;
}
```

All inline switching disappears. The `narrativeFilterMatches` function above it stays (the filter is independent of the render path).

### D6 — Autonomy chip composition (closes ADR-238 R2)

ADR-238's autonomy chip is currently rendered above the form in `ChatPanel.tsx` (composer-level). It stays there in this ADR — the chip is a workspace-level posture, not a per-message concern. **What changes:** the prop surface that future Reviewer / Proposal renderings can use to *also* render an autonomy badge inline. ADR-237 ships the substrate; ADR-237's first non-cockpit consumer (the Reviewer verdict shape) gets an optional `autonomy?: AutonomyLevel` prop threaded through `MessageRow`. Future ADRs (ADR-239 Reviewer-in-cockpit) can opt-in to display.

This is the explicit ADR-238 composition note operationalized: ADR-237 doesn't move ADR-238's chip; it threads autonomy state into the row-level grammar so per-shape renderers can compose with it without re-fetching.

---

## Resulting chat surface

### Components after ADR-237

| File | Status |
|---|---|
| `MessageDispatch.tsx` | **NEW** — `resolveMessageShape`, `MessageRenderer`, six per-shape internal renderers |
| `MessageRow.tsx` | **NEW** — row-level wrapper for weight/authorship/affordances/autonomy |
| `SystemCard.tsx` | Unchanged |
| `ReviewerCard.tsx` | Unchanged (gains optional autonomy prop in a follow-up ADR) |
| `ProposalCard.tsx` | Unchanged |
| `NotificationCard.tsx` | Unchanged |
| `InlineActionCard.tsx` | Unchanged (inline affordance, not role-shape) |
| `InlineToolCall.tsx` | Unchanged (inline affordance) |
| `ToolResultCard.tsx` | Unchanged (inline affordance) |
| `TPMessages.tsx` | **DELETED** (dead code, ADR-023 legacy) |
| `ChatPanel.tsx` | `NarrativeMessage` shrinks ~150 LOC → ~10 LOC; autonomy chip stays at composer level |

Net: `+2` new files, `−1` deleted, one large function shrinks, total LOC delta is approximately neutral (~+150 in new modules / ~−150 in `NarrativeMessage` / `−75` from `TPMessages`).

### What this enables for Round 2+

- **ADR-239 (Round 3 trader cockpit)** can render Reviewer / Agent / System cards inside cockpit faces by importing `MessageRenderer` directly. No re-deriving role-switching JSX inside `MoneyTruthFace` / `TrackingFace`.
- **ADR-240 (Round 4 onboarding)** uses the same grammar for first-conversation rendering — no special onboarding render path.
- **Item 8.2 (Make Recurring rework)** — the affordance is now a `MessageRow` prop that any consumer surface can opt-in/out without forking `NarrativeMessage`.
- **Item 9 (Agents tab refactor)** — agent-detail tabs render Reviewer decisions / agent feedback as `MessageRenderer` calls, not inline JSX duplication.
- **Item 10 (Cockpit ↔ snapshot convergence)** — `SnapshotModal`'s "Recent" tab can render the last-N narrative entries via `MessageRenderer`; the snapshot agrees with chat by construction.

---

## What this ADR does NOT do

- **Does not introduce a single uniform per-role component prop signature.** Singular Implementation says one grammar; forcing one shape across six structurally-different roles is over-abstraction. Each component keeps its prop surface.
- **Does not move autonomy chip rendering.** ADR-238's chip stays at composer level. ADR-237 only threads autonomy state into row-level prop surface for opt-in by per-shape renderers.
- **Does not refactor `InlineActionCard`, `InlineToolCall`, `ToolResultCard`.** These are inline affordances, not message-level renderers. They live inside bubbles; ADR-237 grammar is at message-level.
- **Does not change `TPMessage` shape.** Type-level changes propagate through too many call sites; ADR-237 reads existing `TPMessage` fields, doesn't add new ones.
- **Does not change `narrativeFilterMatches`.** The filter is independent of the render path. Item 8.1 verification confirmed wiring is correct; ADR-237 leaves it alone.
- **Does not introduce a JS test runner.** Same as ADR-238: regression gate is a Python script per ADR-236 Rule 3 + the ADR-238 precedent.
- **Does not change `TPContext.tsx` message-loading or tool-result handling.** That layer fills `TPMessage` payloads; ADR-237 only touches the rendering of those payloads.
- **Does not unify `narrative.weight` semantics across recurrence shapes.** Weight is a per-message concern; ADR-237's grammar consumes whatever weight a message carries.

---

## Implementation

### Files created (3)

- `web/components/tp/MessageDispatch.tsx` (~250 LOC)
  - `MessageShape` type union (6 values).
  - `resolveMessageShape(msg)` pure function.
  - Six per-shape internal render functions: `renderUserBubble`, `renderYarnnnBubble`, `renderSystemEvent`, `renderReviewerVerdict`, `renderAgentBubble`, `renderExternalEvent`.
  - `MessageRenderer({ msg, isLoading })` — the dispatch component.
  - Imports the six per-role components (`SystemCard`, `ReviewerCard`, etc.) verbatim.
- `web/components/tp/MessageRow.tsx` (~120 LOC)
  - `MessageRowProps` interface (msg, weight, authorshipChip, makeRecurringHandler, autonomy?, children).
  - Row-level wrapping: weight gating (housekeeping → hidden), authorship chip rendering (extracted from `NarrativeMessage`), Make-Recurring button rendering, optional autonomy badge slot for future opt-in by inner shape.
- `api/test_adr237_chat_role_grammar.py` — Python regression gate.

### Files modified (1)

- `web/components/tp/ChatPanel.tsx`
  - Delete inline `NarrativeMessage` body (~150 LOC of role-switching JSX).
  - `NarrativeMessage` shrinks to a thin `<MessageRow><MessageRenderer/></MessageRow>` wrapper.
  - All `msg.role`/`msg.notification`/`msg.actionCard`/`msg.toolHistory` extraction inside the rendering branch moves to `MessageDispatch.tsx` and `MessageRow.tsx`.
  - The `narrativeFilterMatches` function above stays unchanged.
  - The autonomy chip above the form (ADR-238) stays unchanged.
  - Imports trim to the new dispatch + row modules.

### Files deleted (1)

- `web/components/tp/TPMessages.tsx` — verified dead (zero imports). Its docblock referenced ADR-023; ADR-237 amends ADR-023 to retire this surface.

### Files NOT modified

- `web/components/tp/{SystemCard,ReviewerCard,ProposalCard,NotificationCard,InlineActionCard,InlineToolCall,ToolResultCard}.tsx` — unchanged. The dispatch threads payloads to them; their internals are out of scope.
- `web/types/desk.ts` — `TPMessage` shape unchanged.
- `web/contexts/TPContext.tsx` — message-load and tool-result handling unchanged.
- `web/lib/autonomy.ts` (ADR-238) — unchanged. ADR-237 imports `useAutonomy` for the optional row-level autonomy slot in `MessageRow`.
- `api/agents/prompts/*` — no prompt changes.
- All ADRs predating this one — Rule 2 (historical preservation).

### Test gate

`api/test_adr237_chat_role_grammar.py` asserts seven invariants. No JS test runner introduced.

1. `web/components/tp/MessageDispatch.tsx` exists and exports `MessageShape` type, `resolveMessageShape`, `MessageRenderer`.
2. `web/components/tp/MessageRow.tsx` exists and exports `MessageRow`.
3. `web/components/tp/TPMessages.tsx` does NOT exist (deletion regression guard).
4. `web/components/tp/ChatPanel.tsx` imports `MessageRenderer` and `MessageRow` from the new modules.
5. `web/components/tp/ChatPanel.tsx` no longer contains the string `if (msg.role === 'reviewer')` (regression guard against re-inlining the dispatch — the dispatcher owns role switching now).
6. The six role values from `web/types/desk.ts` are exhaustively handled in `MessageDispatch.tsx`'s `resolveMessageShape` (assertion checks each role string appears in the file).
7. `web/components/tp/ChatPanel.tsx` retains the autonomy chip render (ADR-238 R2 composition guard — confirms ADR-237 didn't accidentally move ADR-238's chip).

Combined gate target: 7/7 passing.

### Render parity

| Service | Affected | Why |
|---|---|---|
| API (yarnnn-api) | No | No backend code change. |
| Unified Scheduler | No | FE-only. |
| MCP Server | No | FE-only. |
| Output Gateway | No | Untouched. |

**No env var changes. No schema changes. No new services.**

### Singular Implementation discipline

- The role-switch dispatch lives in **one** module (`MessageDispatch.tsx`). The inline NarrativeMessage switch is deleted in the same commit, not parallel-paths-coexisting.
- Cross-cutting concerns (weight, authorship, Make Recurring) live in **one** wrapper (`MessageRow.tsx`). Pre-ADR-237 inline conditionals are deleted from `ChatPanel.tsx`.
- `TPMessages.tsx` is deleted — the legacy surface and the new grammar do not coexist.
- No deprecation period, no shim, no compatibility flag.

---

## Risks

**R1 — `NarrativeMessage` rewrite parity.** The current ~150-LOC inline render covers many edge cases (loading state, narrative chip linking, weight-based rendering). Mitigation: implementation walks the existing function line-by-line and maps each branch to either `MessageDispatch` or `MessageRow`; nothing gets dropped silently. Manual smoke required on at least the four operator-visible role shapes (user, assistant, reviewer, system) before commit.

**R2 — Hidden inline-affordance coupling.** `InlineActionCard` and `InlineToolCall` are rendered inside the assistant bubble's content, not at the row level. The dispatch must thread their payloads to the right shape's renderer. Mitigation: `renderYarnnnBubble` (for assistant) explicitly handles `msg.toolHistory`, `msg.actionCard`, and `msg.notification` — unchanged from current `NarrativeMessage`. Test gate assertion #5 catches forgotten handling by detecting if `msg.toolHistory` is referenced inline in `ChatPanel.tsx` (it should be in MessageDispatch only post-ADR).

**R3 — Future per-role variation.** ADR-239 may want a Reviewer verdict to render *differently* in the trader cockpit than in chat. Mitigation: that's a `MessageRow` prop concern, not a per-role component fork. ADR-237's row wrapper exposes a `surface?: 'chat' | 'cockpit'` prop slot that future ADRs opt into; ADR-237 itself ships only `'chat'` semantics.

**R4 — Test coverage thinness.** Python regression gate catches structural drift but not visual regressions. Mitigation: same as ADR-238 — operator manual smoke on the four primary role shapes is the visual gate. Future FE test runner scaffolding is a separate ADR if pressure surfaces.

**R5 — Vocabulary churn.** "Shape" appears in ADR-231 as `RecurrenceShape` (DELIVERABLE / ACCUMULATION / ACTION / MAINTENANCE) and in ADR-237 as `MessageShape` (six values). Mitigation: the contexts are orthogonal — recurrence shapes are work-classification, message shapes are render-shape; the type names live in different modules; no caller will collide. Documented in this ADR's risk section so future-me doesn't get confused on a re-read.

---

## Phasing

Single commit, sized medium. The dependency graph is linear: new dispatch + row modules → ChatPanel rewrite → TPMessages delete → test gate → CHANGELOG entry → commit.

1. Author `web/components/tp/MessageDispatch.tsx` (six per-shape renderers + dispatch component).
2. Author `web/components/tp/MessageRow.tsx` (row wrapper).
3. Rewrite `NarrativeMessage` in `ChatPanel.tsx` to thin shell.
4. Delete `web/components/tp/TPMessages.tsx`.
5. Author `api/test_adr237_chat_role_grammar.py` — 7 assertions.
6. Run all gates (ADR-231 invariants, ADR-233 P1+P2, ADR-234, ADR-235 17/17, ADR-237 7/7, ADR-238 6/6).
7. Manual smoke on the four primary role shapes in browser.
8. Add `[2026.04.29.N]` CHANGELOG entry.
9. Atomic commit + push.

---

## Closing

ADR-237 is the grammar codification Round 1 surfaced as needed. ADR-238 added an autonomy chip and explicitly recorded the absence of a row-level extension point as a known limitation; ADR-237 builds that point. Future Tier 1 sub-ADRs (Round 3 trader cockpit, Round 4 onboarding) compose with the dispatch table this ADR ships rather than re-deriving role-switching JSX in their own surfaces. The Item-1 design-system slop diagnosed by ADR-236 dissolves into a one-table dispatch + one-wrapper composition pattern; the existing six role-components survive their roles and gain a coordinating frame around them.
