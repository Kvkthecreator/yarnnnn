# ADR-645 — Reach is the connection surface, and reach follows the member

**Status**: Proposed (doc-first — no implementation until ratified)
**Date**: 2026-09-08
**Amends**: ADR-642 ("consent, selection and aperture stay Settings acts; Reach
lists and doors") · ADR-425 D1 / ADR-577 D1 (re-affirmed, not changed)
**Successor question, explicitly OUT of scope**: workspace identity for
unattended reach (§7)

---

## Context

ADR-642 gave the Channel dimension a front door. The first click-pass of that
door (2026-09-07) raised a question the canon had answered three times without
ever answering it in ONE place, so it kept being re-asked:

> *Reach — what is its scope? User level or workspace level? And thus, how
> should managing connections occur?*

The observed inconsistency is real. Reach's three panes are scoped two
different ways:

| Pane | Scope today | Reader |
|---|---|---|
| Connected | the **member's account** | `connection_rows(client, user_id)` |
| Leaving | **this workspace** | `QueueBody families=[external-write, capital]` |
| Crossed | **this workspace** | `GET /workspace/timeline?lens=boundary` |

That is not drift, and this ADR does not repair it. It is the correct shape,
and §1 states why. What IS wrong is that the surface never says the rule, and
that the acts belonging to the boundary live behind a door out to Settings.

Two candidate models were put:

- **(A) The workspace ADOPTS the owner's credentials** and passes them to
  system-level agents and chats across the workspace — possibly mirrored or
  replicated for due diligence.
- **(B) Pure per-member**: all grants and permissions adopt the currently
  acting member.

---

## D1 — Model (A) is CLOSED. Reach follows the acting member.

**(A) is not an open design option. It was built, it shipped, and it was
withdrawn** — and it is re-proposed roughly once a quarter because the
withdrawal is recorded in three ADRs and no surface.

The record:

- **ADR-425 D3** retired the owner-reuse branch.
- **ADR-566 D2** forbade it — but keyed the guard on a `principal_grants` role
  (`own-agent`) that **zero rows hold**, behind a `workspace_id` that
  `HeadlessAuth` never carries. *A principled guard that cannot run protects
  nothing.* **So until ADR-577, production actually did it**: agents reached
  through the owner's personal OAuth tokens.
- **ADR-566 D5** built the workspace credential store to hold (A) properly. It
  was **unfillable** (GET-only; no allocation door was ever built),
  **mis-filled** (migration 201's owner-fill trigger stamped every human
  connect into it) and **unreadable** (RLS is `user_id = auth.uid()`). The pane
  it fed rendered *the owner's personal tokens* labelled as workspace agent
  credentials. **ADR-577 D1/D3** withdrew the store and deleted the route.

**Mirroring or replicating the credential does not rescue (A).** That is the
same withdrawal with a copy step: a mirrored token is still the owner's token,
still revocable only by them, still carrying their identity to the far side,
and now in two places with two expiries.

**The reason is not fussiness — a credential carries IDENTITY.** If a workspace
adopts a member's Slack token, every agent post is *that human* posting, to
everyone reading Slack, forever. Attribution is the moat (ESSENCE), and (A)
breaks it at the boundary — **invisibly, on the far side, where no yarnnn
surface can show it**. A system whose whole claim is "every act is signed"
cannot have its outbound acts signed by the wrong person.

**(B) is therefore ratified as the standing rule**, and it is what the code
already enforces at the one chokepoint:

```
resolve_platform_credential(auth, platform):
    agent-shaped caller   → None   (REFUSED + logged at WARNING)
    any human principal   → that human's account credential
    unrecognized          → None   (FAIL CLOSED)
```

A member's chat **lane** stamps `member:{id} via {model}` and IS the member's
hands — so an AI driving a member's lane correctly reaches through *that
member's* connection. This is not an exception to (B); it is (B).

> **The layman sentence** (the criterion this ruling was asked to meet):
> *You connected your Slack. Things you do here reach through it. When you
> leave, your reach leaves with you.*
>
> (A) requires instead: *"the owner's Slack silently backs everyone else's
> actions"* — which is both hard to say and alarming once said.

### D1.a — Owner vs. guest is not a view mode

It falls out of (B) and needs no mechanism of its own. **Every member sees
their own connections** in Connected — a guest sees theirs, never the owner's.
What differs by role is only the *workspace* half (who may change what this
workspace reads through a connection), and that is an **ADR-643 access check**,
not a view mode. Do not build a role-branched Connected pane.

---

## D2 — There is no workspace credential store. Do not build one.

Re-stated here because this is the file a future proposal will read first.
`platform_connections.workspace_id` means **ROUTING** — which workspace a
credential feeds (ADR-425 AD1) — **never ownership**.

**Re-entry test (inherited from ADR-577 §7, and it applies to this ADR too):**
before any change may claim an agent acts through a workspace credential, it
must exhibit a **DRIVEN TRACE** — a real auth object, through
`resolve_platform_credential`, returning the workspace row. Not a passing gate.
Not a docstring. Not an ADR.

---

## D3 — Reach is the connection surface. Settings → Connectors is DELETED.

ADR-642 ruled that Reach "lists and doors, never acts", and sent consent,
selection and aperture out to Settings. **That clause is amended.**

It was written when Reach did not exist, and it was protecting against the
right thing (a read-only surface silently acquiring Settings' acts) by the
wrong means. The census that motivates the amendment:

| Decision | True scope | Lives today |
|---|---|---|
| Connect / disconnect an account | **account** | Settings |
| Which sources *this workspace* reads (`landscape.selected_sources`) | **workspace** | Settings |
| Per-tool aperture (`direct`/`propose`/deny) | **workspace** | Settings |
| Whether an agent may reach through it | **workspace** | agent page (ADR-612/615) — **stays there** |

**Three of the four are workspace decisions wearing a Settings costume.** A
member must currently leave the workspace surface to make a workspace decision,
on a page that cannot easily say *which* workspace it is deciding for. That is
the defect, and a redirect from the boundary's own front door institutionalises
it.

**Ruling**: Reach → Connected becomes the ONE door for every connection act.
`/connectors` becomes an ADR-308 redirect stub into
`/reach?reach.pane=connected`; the `connectors` pane leaves the Settings roster.

This is **Singular Implementation** (CLAUDE.md §2), not redundancy: one way to
do things, the legacy home deleted rather than left as a parallel path.

### D3.a — This is a MOVE, not a rewrite

The acting machinery already exists and is not in question (~2,300 lines):
`ConnectedIntegrationsSection` (688) · `ManageConnectionSubsurface` (707) ·
`FindConnectorModal` (464) · `AttachedConnectorSubsurface` (328) ·
`ConnectorCard` (121). `ReachConnected` (249) is a read-only *view* of the same
rows.

The components move to the Reach pane; the Settings mount is deleted. **Do not
fork them** — a mirrored design is a second write path (recorded lesson). The
`describe()` face from ADR-644 stays the reading half: **acts may join Connected,
but no new reach SENTENCE may be written there.** Anything telling a member what
a connection lets a turn do still renders `reach_status` — a sentence anywhere
else is the fifth face (ADR-644).

### D3.b — The ADR-592 obligation rides along

A slug leaving the served roster leaves the auth gate with it. Deleting the
`connectors` pane REQUIRES, in the same change: the redirect stub at
`/connectors`, the hand-listed entry in `middleware.ts`
(`LEGACY_AND_STUB_PREFIXES`), and every in-app caller re-pointed —
`UserMenu` (`foregroundSurface('connectors')`), `SendToSlack` and
`StudioPublish` (`navigateToSurface('connectors')`, both of which name the
member's door per ADR-644). Miss one and `/connectors` serves 200 to a
logged-out visitor — the exact defect repaired 2026-08-20.

---

## D4 — Connected states its two scopes on the surface

The pane already carries the right subtitle for its own half. The rule the
whole surface embodies is never said, so it has to be re-derived by whoever
asks next (which is how this ADR came to be written).

Connected shows **account-scoped rows** and **workspace-scoped decisions about
them**, and must say so. The existing "Read by" row — *"Standing declarations in
this workspace that read through your connection"* — is the honest shape of the
whole design in one line, and is promoted from an incidental detail to the
pane's organising idea:

> **The credential is yours. The reach is this workspace's.**

---

## §7 — Successor question (OUT of scope): workspace identity for unattended reach

Under D1, **unattended work has no outbound reach.** A standing declaration
runs with no member present, so `is_agent_caller` refuses it a credential —
**correctly**. That is why Slack's row reads *"never scheduled"* and WordPress's
*"carries only your own clicks"*.

That is a genuine product limit, not a bug, and it is NOT solved by (A).

The successor is a **workspace-owned identity**: yarnnn's own Slack bot token,
its own WordPress application password — an identity agents reach through **as
yarnnn**, never as a member. This is how Slack itself models the distinction
(bot token vs. user token). It is **additive**, touches no personal credential,
and keeps attribution honest because the far side sees a distinct actor.

Constraints recorded now so the next session does not re-derive them:

1. It is a **new identity**, never an adopted or mirrored member credential —
   D2's re-entry test still binds.
2. It needs its own row in Connected, visibly NOT a member's ("this workspace's
   Slack", no member avatar).
3. Every act through it still passes the ADR-307 gate and the witness dial —
   reach is not authority (ADR-566 D1).
4. **Drive the N>1 member case first.** Today every Connected row is the
   owner's because there is one member. The moment a second member connects,
   "Read by" becomes load-bearing and this design either holds or obviously
   does not. That case is asserted in gates and **has never been looked at** —
   the same gap that hid the ADR-297 deep-link defect through three green
   sessions.

---

## Consequences

- The three ADRs that withdrew model (A) now have **one surface-level home**, so
  the next proposal reads a ruling instead of re-deriving a withdrawal.
- Reach becomes a genuine kernel surface — the boundary's door owns the
  boundary's acts, consistent with its promotion in ADR-642.
- Settings shrinks to what is actually account-shaped, which is the direction
  ADR-491 already moved billing.
- Unattended outbound stays impossible until §7 is decided. **Do not close that
  gap by relaxing D1.**

## Gates (on ratification)

- `test_adr645_reach_owns_connections.py` — the `connectors` slug is off the
  served roster; `/connectors` is a redirect stub; `middleware.ts` hand-lists
  it; **no caller navigates to the retired slug** (assert the relation both
  directions — a negative check catches a forgotten deletion and never a
  forgotten addition, ADR-636's lesson).
- `test_adr577_credential_claim.py` — unchanged and re-run: the agent refusal
  is D1's enforcement point. Note it carries **TWO** allowlists
  (`PRINCIPAL_LESS_CREDENTIAL_READS` and `ENUMERATION_ONLY`); a new enumeration
  reader goes in both.
- `test_adr644_one_reach_status.py` — re-run: acts joining Connected must not
  grow a fifth reach face.
- A **browser click-pass**, not a build: the acts on their new home, both
  themes. Yesterday's defect was invisible to tsc and to three green sessions.
