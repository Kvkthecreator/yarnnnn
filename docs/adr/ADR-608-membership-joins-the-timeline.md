# ADR-608: Membership Joins the Timeline — a fourth source for "what happened"

**Status**: Accepted (2026-08-25) — implemented same session (Layer-1 G2, ADR-593 §6)
**Dimension**: Channel (Axiom 6) + Identity (whose acts a principal is shown)
**Amends**: ADR-410 §2 (the closed two-source rule for the timeline derivation widens by one source: `principal_grants` membership events; the closure discipline itself is unchanged — this ADR is the required ceremony)
**Preserves**: DP29 (derived, never stored — no membership-event table), ADR-405 D4 (self-suppression: the joiner is not told they joined), ADR-489 (weight: a new colleague is material)
**Gate**: `api/test_adr608_membership_on_the_timeline.py`

## 1. The gap (audit receipt)

The Layer-1 comprehensiveness audit
(`docs/evaluations/2026-08-25-notifications-layer1-comprehensiveness-audit.md`,
G2): `accept_invite` writes the grant and the invite status and touches none
of the three ledgers the timeline derives from — so **"X joined the
workspace" reaches no attention surface**. In a multi-principal commons,
a new colleague arriving is among the most basic facts a member should be
told; today it is invisible everywhere except the Workspace Settings roster,
which nobody is routed to.

## 2. Decision — derive membership events from the grant ledger itself

The timeline derivation (`GET /api/workspace/timeline`) gains a fourth
source: `principal_grants` rows with `role IN ('member','viewer')` in the
acting workspace, each rendered as `kind="membership"`:

- **joined** — an `active` grant, at its `created_at`.
- **left** — a `revoked` grant, at its `created_at`... **NO** — a revoked
  row's `created_at` is the *grant's* birth, not the revocation moment, and
  the table carries no revocation timestamp. A "left" event with a wrong
  time is worse than none: **v1 derives JOINS only**, and "left" waits for a
  revocation timestamp if it ever earns one. Recorded so the asymmetry reads
  as a decision, not an oversight.
- The **owner's founding grant is not a join** — genesis is the workspace's
  birth, already legible elsewhere; announcing it as an arrival would be
  noise on every timeline's floor.
- **AI-principal grants are NOT membership entries** — a connection is a
  rail (ADR-594) with its own surface (Workspace Settings → AI connections);
  putting `foreign-llm` grants here would double-count the connection story.
  Species-blindness is not violated: the *event class* differs (joining the
  human roster vs. wiring a consented rail), not the treatment of a
  participant.

Mechanics: no new storage (DP29 — the grant ledger IS the record); the
block reads via the service client (`principal_grants` is not RLS-readable
to member JWTs; the workspace filter is the already-resolved acting
workspace — the `activity_log` precedent). `actor = "member:{principal_id}"`
+ `actor_id = principal_id`, so the FE viewer layer resolves names and
self-suppression exactly as for revisions. Weight: **material**, explicit in
`classify_weight` (a colleague arriving is precisely what the bell exists
for). The bell's Activity section accepts the new kind; the workbench
renders it through the shared row grammar ("‹actor› joined the workspace").

## 3. What this does not do

No membership-event table; no To-do entry (nothing to resolve); no email
kind (Layer 2, and it would need its own ADR-593 D1 row); no rendering of
`own-agent`/`foreign-llm`/`platform`/`a2a` grants; no "left" events until a
revocation timestamp exists; no invite-*sent* events (an unaccepted invite
is not an act on the commons).
