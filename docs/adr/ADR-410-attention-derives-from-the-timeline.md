# ADR-410: Attention Derives From the Timeline — one derivation, peer-first

**Status**: Accepted (2026-07-06 — ratified alongside ADR-412 per its D5 clause). **§5 steps 1–4 Implemented same day** (+ the ADR-412 D6 viewer-resolution layer they require): D2 hygiene one-shot APPLIED to prod (`api/scripts/oneshot/adr410_d2_expire_stale_substrate_proposals.py` — 7/7 pre-D3 substrate zombies expired-with-reason, all `freddie:`-sourced 2026-07-03→05, receipt ids in the run log); D6 stable ids (`kind:natural-key:at`) + `actor_id` on `TimelineEntry`, **plus one widening the ADR's "no schema change" note missed**: `author_identity_uuid` was an existing-but-unpopulated column, so operator-class revisions were ambiguous between humans — the human-write routes (PATCH /workspace/file, memory, documents; `UserMemory.write` pass-through) now thread `auth.user_id`, no schema change; D1 bell re-source (chat.globalHistory derivation DELETED; ACTIVITY = timeline revisions+invocations, peer-first via `web/lib/workspace/viewer.ts` — `useWorkspaceRoster` + `resolveActorForViewer`, legacy identity-less operator rows resolve self-quiet; sub-minute invocation dedupe; badge = queue + unseen PEER acts); D2 TO DO honest labels (proposer badge + `proposalQueuedByDialLine`); D3 in_app writes RETIRED in `services/witness.py` (recipient derivation kept as the outbound seam; phase-2 gate re-pointed 8/8); D4 actor-first lines, enum words banned from render. Gate `api/test_adr410_attention.py` 30/30; affected suites green (407-P2/P3, 408-D5.1, 412, 411, 297, 340-P1 re-pointed). **Remaining: D5** (Notifications surface re-mount — trails per §5) + the ADR-412 D3/D4 affordance + ambient passes. Evidence: the operator's live bell screenshot (2026-07-06) + code audit below.
**Date**: 2026-07-06
**Dimension**: Channel (Axiom 6 — where attention routes) + Identity (Axiom 2 — whose acts a principal is shown)
**Relates to**: ADR-405 (witness dial — D3/D4 finally get their true rendering), ADR-408 (D5.1 timeline — the source this ADR makes singular; D1 coworking contract), ADR-407 (member_state cursor — Phase 3), ADR-340 (DP29 derived-never-stored — restored where Phase 2 bent it), ADR-367 (Home/Notifications tiering — preserved, re-sourced)
**Amends**: ADR-407 Phase 2 (the witness in_app emission rows are retired in favor of derivation — the emission helper survives for outbound transports only), ADR-219 (material-weight narrative stops being the attention source)

---

## 1. The audit — what the bell actually shows today, and why it's wrong

Observed live (owner's bell, 2026-07-06, post-D3):

| Section | Shows | Source (code) | What's wrong under multi-user |
|---|---|---|---|
| TO DO | "Save a workspace change" ×4, "Edit a workspace file" | `api.proposals.list('pending')` (`AttentionCenter.tsx:168`) | **Stale**: pre-D3 substrate proposals that would auto-apply today linger as zombies. **Illegible**: family-generic titles — no target path, no proposer, no dial line (D5.2 shipped elsewhere but not here). |
| ACTIVITY | "Reviewer ADDRESSED" ×4 | `api.chat.globalHistory(1)` → material-weight narrative rows of MY chat session (`AttentionCenter.tsx:169,190-206`) | **Structurally obsolete**: post-ADR-407 Phase 4, the chat session is the caller's PRIVATE thread — so activity = *my own turns echoed back at me* (self-witness, which ADR-405 D4 says is trivially satisfied and should never notify), while **peer and agent acts in the commons are invisible**. Vocabulary leaks internal enums ("Reviewer", "ADDRESSED" = wake_source). |
| (parallel) | witness in_app rows | ADR-407 Phase 2 `notifications` inserts | Written before the timeline existed; now a SECOND source overlapping the derived view — the exact shape DP29 forbids. |
| (parallel) | Home Timeline slot | `GET /api/workspace/timeline` (ADR-408 D5.1) | Correct — but it's a fourth mechanism nobody unified. |

Net: **five mechanisms** (bell TO-DO, bell chat-derived activity, notifications
rows, Notifications surface, timeline) answering two questions ("what wants
me" / "what happened"), with the multi-user-correct source (the timeline)
wired into only one of them. The bell predates the coworking model and now
misinforms: it amplifies self-noise and hides peers.

## 2. The principle

**One derivation, N mounts.** The workspace has exactly two attention
questions, each with exactly one source:

- **"What wants me"** = the witness queue: pending proposals the caller has
  standing to witness. Source: `action_proposals` (workspace-scoped since
  ADR-407 Phase 1).
- **"What happened"** = the timeline: `GET /api/workspace/timeline` (ADR-408
  D5.1 — the three attributed ledgers), filtered per viewer.

Every attention surface — the bell, the Notifications workbench, the Home
slot, future push — is a *mount* of these two derivations with different
depth (the ADR-367 macOS tiering, preserved). Nothing else may feed an
attention surface.

## 3. Decisions

**D1 — The bell's ACTIVITY re-sources to the timeline, peer-first.**
`AttentionCenter` drops `chat.globalHistory` entirely and renders
`timeline WHERE actor != viewer AND at > cursor` (the member_state
`attention` cursor, already per-(workspace, principal) since ADR-407
Phase 3). Self-acts are excluded by construction (ADR-405 D4 — you don't
need to be told what you just did). Badge = witnessable TO-DO count +
unseen peer/agent timeline count.

**D2 — TO DO becomes the witness queue, honestly labeled.** Rows carry the
proposal's real target (path/primitive detail), the proposer's attribution,
and the D5.2 dial line ("Queued by ‹agent›'s autonomy setting"). Plus
hygiene: a one-shot sweep expires the stale pre-D3 pending substrate
proposals (post-D3 they'd apply directly; the zombies misrepresent the
queue) — expired-with-reason, auditable, not deleted.

**D3 — The `notifications` table returns to pure outbound transport.** The
ADR-407 Phase 2 in_app witness rows are retired (they were the bridge before
the timeline existed; keeping them makes a second store of what the ledgers
already say — the DP29 violation). `emit_after_witness` survives with its
recipient derivation, now writing ONLY for outbound channels (email/push,
when those fan-outs ship); in-app attention is derivation, never rows.

**D4 — Vocabulary pass.** Every attention row is actor-first through the
shared attribution module ("seulkim88 edited …", "Freddie derived …",
"ChatGPT (via MCP) contributed …"). Internal enums (`wake_source` values,
"Reviewer", "ADDRESSED", family slugs as titles) are banned from
operator-facing strings — the FE label layer owns the mapping.

**D5 — The Notifications surface re-mounts the same two derivations** as the
breadth workbench (filters by actor/kind/date, full history via the
timeline's `before` cursor), replacing its chat-narrative body. Bell =
glance, Notifications = workbench, Home slot = ambient — three depths, one
source.

**D6 — Timeline enrichment to carry the load** (the source must be good
enough to be singular): entries gain a stable `id` (for cursoring +
read-state), revision entries carry `message` verbatim (already do) + a
compact per-actor grouping hint is left to the FE; invocation entries
suppress sub-minute duplicates FE-side. No schema change — the endpoint
already derives everything needed except stable ids (derive as
`kind:natural-key:at`).

## 4. What this does NOT do

- No stored read-receipts / per-row read state (the cursor stays a single
  timestamp per (workspace, principal) — DP29).
- No push/email fan-out build (D3 keeps the seam; transport scaling stays
  the named ADR-405 §3 follow-on).
- No presence/live collaboration (ADR-373 rejection stands).
- No change to the witness/permission mechanics — this is rendering + source
  unification only.

## 5. Sequencing (next session)

1. D2 hygiene one-shot (stale pre-D3 proposals → expired-with-reason).
2. D6 timeline ids + D1 bell re-source (delete the globalHistory derivation).
3. D3 retire in_app emission writes (keep the helper + its tests for the
   outbound seam).
4. D4 vocabulary pass across bell + timeline + Notifications rows.
5. D5 Notifications surface re-mount (the largest piece; can trail).

Gate: a member and an owner each see (a) zero of their own acts in their
bell, (b) every peer/agent act since their cursor, (c) a TO DO that names
the target, the proposer, and the dial that queued it.
