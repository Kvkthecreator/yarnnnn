# Notifications Layer-1 comprehensiveness audit (2026-08-25)

**Hat**: B (audit — recommends; the scope ratification lands in ADR-593 §6).
**Question**: which event classes that deserve a member's attention are
derived internally (in-app), with the right weight, per (workspace,
principal), with a clearing story — and which are not? Run after the
ADR-605 opt-in flip (`fca4281`) made the outbound side quiet by default;
"Layer 1" = the internal derived surfaces that must be comprehensive and
stable BEFORE outbound expansion (operator ruling, recorded in ADR-605's
amendment).

## Covered and verified (the stable core)

| Event class | Derivation | Mounts | Receipt |
|---|---|---|---|
| Decisions (witness) | `action_proposals`, always material | bell To-do · QueueBody | prod: 0 pending |
| Mentions (of humans, from humans or agents on the lane path) | write-time stamp → per-viewer derivation, resolution ≠ scroll-by | bell To-do · MentionQueue · badge | click-passed live (run record 2026-08-25); prod: 2 stamped rows |
| Peer/agent substrate acts | timeline (3 ledgers), weight-classified, peer-first, self-excluded | bell Activity (material) · workbench (lenses) | ADR-410/489 gates; live bell observed in-pass |
| Run receipts + failures | `execution_events` → invocation entries; failed = material and READS failed (destructive style + status line, `timeline-rows.tsx:39,98-100`) | bell Activity · workbench Runs lens | prod 30d: 357 invocations, 1 failed |
| Inbound arrivals | `revision_kind='observation'` = routine — workbench yes, bell no (deliberate) | workbench "What matters" | prod 30d: 99 observation revisions |
| Balance runway | limits read, authority-aware copy | bell warning row | observed in-pass |
| Scoping + cursor | per (workspace, principal); cross-device via `member_state['attention']` | all mounts | observed in-pass |

## Gaps (the Layer-1 work list, ordered)

**G1 — the mention stamp covers ONE of six conversation writers.**
`write_narrative_entry` is called from `routes/lanes.py` (stamps),
`routes/feed.py`, `services/freddie_chat_surfacing.py`, `services/wake.py`,
`services/narrative.py` self-callers, and `mcp_server/server.py` (none
stamp). An MCP-authored conversation message is live in prod (the
click-pass DM's seq-21 `role=external` row) — an @mention written by a
connected AI today routes nowhere, which re-opens the exact "theatre" gap
ADR-605 closed, for non-lane writers. Fix shape: stamp at the ONE
narrative-write chokepoint (or one shared helper), never per caller — the
chokepoint discipline that just paid for itself in the wrong-client fix.

**G2 — membership changes are invisible.** `accept_invite`
(`services/workspace_invites.py:208`) writes the grant + invite status and
touches none of the three timeline ledgers, so "X joined the workspace"
reaches no attention surface — in a commons product, a basic internal
notification. The timeline's source list is CLOSED (ADR-410 §2), so adding
a grants-derived source is an ADR-level widening, not a patch.

**G3 — freshness: the bell is a 60s poll** (`AttentionCenter.tsx`,
`REFRESH_INTERVAL_MS`), so a mention can take a minute to badge. Realtime
bell is ADR-593's named phase 4; the reusable realtime primitive exists
(`use-session-messages-realtime`, ADR-575's second-tenant pattern).

**G4 — mention polish** (from the click-pass findings): the mentioned
viewer's OWN handle doesn't chip in their transcript; DM display-name in
mention rows shows the stored lane name; mentioning a non-participant
should OFFER "add them?" (never auto-invite — ADR-495 D2 disclosure).

**G5 — verification debt**: suppression live-proof (declared NOT RUN in the
click-pass; gate-covered) — rides whichever pass next touches the seam.

## Explicitly OUT of Layer 1 (parked or refused)

Email default expansion, digest batching, push transport (Layer 2 — its
own deliberate arc, from a proven-quiet chokepoint) · `runs` email ·
`@everyone` · tags-as-routing (ADR-405 D5, never) · per-path subscriptions
(never) · stored read receipts (never).
