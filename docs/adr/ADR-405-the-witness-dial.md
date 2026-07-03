# ADR-405: The Witness Dial — permission, autonomy, and notification as one contract

**Status**: Accepted (2026-07-03) — doc-first; the emission wiring lands with member invites (ADR-404 sequence step 4)
**Date**: 2026-07-03
**Dimension**: Purpose (Axiom 3, what binds when) + Identity (Axiom 2, who acts) + Channel (Axiom 6, where the witness happens)
**Relates to**: ADR-307 (unified permission taxonomy — the before-witness gate), ADR-345 (autonomy-as-witness reframe — this ADR's direct ancestor), ADR-373 (per-principal grants), ADR-400 (two-principal Files surface — the collision that surfaced this), ADR-380 (harness honesty), ADR-406 (stale-parent rejection — the mechanical sibling)
**Amends**: ADR-345 (extends the witness reframe from the autonomy dial to the notification system), ADR-307 (the gate is re-described as one end of a two-ended contract)

---

## 1. Context — the collision ADR-400 surfaced

ADR-400 gave the operator direct file manipulation (move/rename/trash/restore)
across the whole workspace. The operator immediately observed a mismatch:

- The **operator** moves a file → it just happens. No gate, no notification.
- **Freddie** (the Rung-1 steward) wants to change the same file → it becomes a
  proposal in the queue, waiting for approval.
- A **foreign LLM** writes via MCP → it lands silently under a grant, judged
  async.
- **Notifications** meanwhile run as their own system (`notifications` table +
  email/in-app sends), wired to specific events, with no principled relation
  to any of the above.

The operator's read: this smells like an axiomatic break in multi-principal
handling, and the blunt fix is a level playing field — humans and AI get the
same permission scopes, or the complexity compounds unboundedly.

The finding of this ADR: **the level playing field is already ratified canon**
(ADR-373: every actor is a principal with a grant; class defaults, not species
law). What is genuinely missing is not a permission model — it is the *name*
for why the remaining asymmetry is legitimate, and the recognition that
notifications and the proposal queue are the same thing at two settings.

## 2. Decision — one contract, three named parts

**D1 — Permission is the grant.** *Who may act on which region.* This is
ADR-373's `principal_grants` scopes over ADR-320's topology (and, post
re-founding, permission-as-metadata). It is identical in kind for every
principal — operator, member, Freddie, own-agent, foreign LLM. No rule in the
permission layer may key on species (human vs AI); it keys on the grant.

**D2 — Autonomy is the witness dial.** *When an act binds.* Every
consequential act (ADR-307's class) is witnessed by the workspace's
accountable principal(s). The dial has exactly two settings per (principal ×
act-class):

- **Before-witness**: the act becomes a proposal; it binds when a witness
  approves. This is the ADR-307 gate + `action_proposals` queue. QUEUE =
  decided-and-waiting-for-witness (ADR-345), never blocked.
- **After-witness**: the act binds immediately; the witness is *told*. This is
  a notification.

**D3 — Notification is the after-witness channel.** A notification is not a
feature with its own event vocabulary; it is what the witness dial emits at
the "after" setting. The canonical after-witness feed is **derived from the
attributed ledgers** (`workspace_file_versions` for substrate acts,
`execution_events` for invocations, the emissions ledger for outbound) —
derived-never-stored per DP29. The existing `notifications` table remains the
*transport* record for pushed channels (email, in-app ping); it does not
become a second source of truth about what happened. What happened lives in
the ledgers; a notification is a pointer to it (ADR-202 discipline preserved).

**D4 — The asymmetries that remain are dial settings, not species rules.**

- The operator's own acts bind immediately with no notification: self-witness
  is trivially satisfied. Not a privilege — a degenerate case of D2.
- Freddie's substrate proposals sit at before-witness today because the
  steward's track-record clock (ADR-380 Rung-1→2) hasn't run, not because
  Freddie is AI. As the clock accrues, the dial moves per act-class — this is
  precisely the existing AUTONOMY dial, now understood as one instance of D2.
- A future human **member**'s file move binds immediately (their grant allows
  it) *and notifies the other principals* — after-witness. Same rule as
  Freddie at full autonomy. The level playing field is the model.
- A foreign LLM's MCP write is after-witness with an additional standing
  witness: the steward's async judgment on substrate events (ADR-310). Two
  witnesses, same contract.

**D5 — Witness routing is derived, not configured.** Who gets the
after-witness signal for a given act = the workspace's principals with
standing on that region (owner always; later, grant-holders whose scopes
cover the path). No per-notification subscription matrix. Mute/digest
preferences are presentation-layer (attention routing, DP29), never
authorization-layer.

## 3. What this changes now vs. later

**Now (this ADR, doc-only):** the vocabulary. Surfaces, ADRs, and prompts
describing "approval" vs "notification" describe them as the two settings of
one dial. No schema change, no new table, no gate-code change — `permission.py`
already behaves as D2 describes (ADR-345 established this for the gate half).

**With member invites (ADR-404 step 4):** the first real after-witness
emission — peer-principal substrate acts surface to the other principals'
attention feed, derived from `workspace_file_versions` (the query is the
feature; the ledger already carries actor + path + message + time).

**Not now:** per-act-class dial UI for arbitrary principals (the AUTONOMY
surface already covers Freddie; members get the class-default dial at
invite); outbound-push fan-out per member (transport scaling is a follow-on).

## 4. Dimensional classification

Purpose (primary): what binds and what merely informs is a Purpose-dimension
distinction. Identity: the witness contract is per-principal. Channel: the
after-witness feed is a Channel instance, not a new system.

## 5. The test

Any future feature that wants to special-case "AI edits" vs "human edits"
must instead answer: *which grant, which act-class, which dial setting?* If
the feature can't be expressed in those three terms, it is reintroducing
species law and violates this ADR.
