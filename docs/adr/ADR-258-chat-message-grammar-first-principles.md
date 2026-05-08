# ADR-258: Chat Message Grammar — First Principles Rewrite

> **Status**: **Implemented** (2026-05-08)
> **Date**: 2026-05-08
> **Authors**: KVK, Claude
> **Supersedes**: ADR-237 (Chat Role-Based Design System — the color-based grammar it defined)
> **Amends**: ADR-215 §Chat tab contracts, SURFACE-CONTRACTS.md Chat section
> **Dimensional classification**: **Channel** (Axiom 6) primary

---

## Context

ADR-237 established a dispatch table for chat message rendering, but made two structural errors:

1. **Color as identity marker.** Reviewer entries got a rose-tinted bubble background; System Agent got a muted background; proposals got a border-colored card. Color became the primary differentiator, not typography or position. This is backwards — color should carry semantic state (approved/rejected), not participant identity.

2. **Cards as participants.** The Reviewer card, ProposalCard, and ReviewerBanner inside ProposalCard each evolved independently into styled widgets with their own color conventions. This fractured the grammar: there was no unified model for what a "chat entry" looks like.

The operator's observation: three things need to be true simultaneously:
- The Reviewer is the primary conversational voice
- Proposals and documents are interactive — one unified style
- The System Agent should feel like a message, not a widget
- Each participant's bubble owns its own secondary status chrome, not the row wrapper

---

## Decisions

### D1 — Three participants, one bubble shape

The chat stream has exactly three speaking participants:

| Participant | Position | Label | Identity marker |
|---|---|---|---|
| **Operator** | right-aligned | "You" | position only |
| **Reviewer** | left-aligned | persona name (from IDENTITY.md) | label, not color |
| **System Agent** | left-aligned | "System Agent" | label, typographic de-emphasis |

All three use the same bubble shape: `rounded-2xl px-3 py-2 bg-muted`. No participant gets a different background color. Color enters only on semantic state chips (approved = emerald, rejected = red) as inline elements inside the bubble, never as bubble background.

System events (`role='system'`) and external events (`role='external'`) are not participants — they're ambient log entries. They keep their dim one-liner treatment at reduced opacity.

### D2 — Proposals are inline cards, not participant bubbles

Proposals are actionable objects in the stream — they are not a participant speaking. They render as a self-contained card distinct from any bubble:

- Uniform border, muted background, no color-coding on the card frame
- Reviewer verdict (approved/deferred/rejected) shown as a compact status chip inside the card
- Approve/Reject buttons inline
- No separate `ReviewerBanner` colored component — status is text + icon chip only

This is the "alert → action" pattern: the card is the notification that an action is staged; the inline buttons are the response affordance. No modal needed — the card is already compact and self-contained. A modal would be appropriate only if the operator needs to drill into full substrate context (decisions trail, performance history) — that links out to `/work?tab=decisions`.

### D3 — Participant status chrome lives inside the bubble

Each participant's bubble can carry secondary status information below the content text. This is participant-owned, not row-wrapper-owned:

- **Reviewer bubble**: below content — confidence chip (low/medium/high) + directive dispatched indicator (`→ fired signal-evaluation`) if action_instruction was executed
- **System Agent bubble**: below content — primitive executed (`ManageRecurrence · pause`) + output file chip if produced
- **Operator bubble**: no chrome

The row wrapper (MessageRow) retains only:
- Weight gating (material/routine/housekeeping)
- Authorship chip for recurrence-tagged entries
- "Run on a schedule" affordance

It does NOT own Reviewer section dividers. Those are deleted entirely.

### D4 — No section dividers for any participant

The `— Simons —` centered section divider added in ADR-237 for Reviewer verdicts is deleted. The Reviewer is a chat participant, not a gate announcement. The label on the bubble ("Simons") is sufficient identity. A divider is appropriate only for structural section breaks in a document, not in a conversation stream.

### D5 — Typographic hierarchy, not color hierarchy

Reviewer bubbles de-emphasize the label slightly more than System Agent bubbles to signal the Reviewer is speaking *about* the operation rather than operating it, but both use `text-muted-foreground`. The Reviewer's *content* is given prominence through normal text size and markdown rendering. System Agent narration uses the same size but shorter content — its brevity is the de-emphasis signal, not color.

---

## What changes

| Component | Change |
|---|---|
| `ReviewerCard.tsx` | Remove all rose tinting. Uniform `bg-muted` bubble. Status chip (approved/deferred/rejected) as inline element, not banner. Confidence chip below content. |
| `MessageDispatch.tsx` | `renderReviewerBubble` replaces `ReviewerVerdictRenderer` — no longer delegates to ReviewerCard for addressed mode; ReviewerCard retained only for proposal verdicts. Actually simplify: one reviewer renderer, always same bubble shape. |
| `MessageRow.tsx` | Delete all Reviewer section divider logic. Reviewer entries are just `MaterialRow` with no special casing beyond skipping the authorship chip. |
| `ProposalCard.tsx` | Remove `ReviewerBanner` component (colored). Replace with compact status chip: `{personaName} · Approved` in emerald text, `{personaName} · Deferred` in muted text, `{personaName} · Rejected` in muted-red text. No colored border panels. |

---

## Impact radius

- `web/components/tp/MessageDispatch.tsx` — reviewer renderer simplified
- `web/components/tp/MessageRow.tsx` — Reviewer section divider deleted
- `web/components/tp/ReviewerCard.tsx` — rose tint removed, status chip replaces verdict badge
- `web/components/tp/ProposalCard.tsx` — ReviewerBanner deleted, compact status chip added
- `docs/design/SURFACE-CONTRACTS.md` — Chat tab section updated
- `docs/adr/ADR-237-chat-role-based-design-system.md` — superseded note added

---

## What does NOT change

- Weight gating (material/routine/housekeeping) — preserved
- Proposal inline card pattern — preserved (not moved to modal)
- `ProposalCard` approve/reject buttons — preserved
- Workspace file path chips — preserved
- "Run on a schedule" affordance — preserved
- Observation entries (dim Eye icon line) — preserved
- System event / external event dim lines — preserved
