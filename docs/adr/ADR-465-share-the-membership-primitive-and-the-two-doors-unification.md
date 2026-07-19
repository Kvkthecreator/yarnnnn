# ADR-465 — Share: the membership primitive, and the two-doors unification

> **Status**: **Proposed** (2026-07-18, doc-first per CLAUDE.md — drafted for operator
> ratification BEFORE code). Derived from the 2026-07-18 first-principles reassessment of Share:
> the operator's thesis that Share is not an artifact convenience but a **first-class primitive**,
> tested against the axioms (not the ADRs) and against the live genesis/auth seam with receipts.
> **Ruling requested**: proceed to phase the code, or amend the decisions below.
**Date**: 2026-07-18
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Identity (Axiom 2 — how a stranger becomes a principal in a commons) + Purpose
(Axiom 3 — the constitutive act that switches the moat on) + Channel (Axiom 6 — the entry doors
a person arrives through).

**Amends**:
- **ADR-437 D4** — Share is **re-cut from "Phase D of an activation ADR" to a system primitive.**
  Everything ADR-437 built (the `workspace_shares` transport, the `/s/{token}` accept surface,
  broad-by-default member grant, one accept surface for two origins) is **preserved**; what changes
  is its *altitude* — Share owns the entry flow end-to-end rather than being an activation tactic.
  ADR-437 open q#2 (`share-as-view`) and q#3 (the MCP `share` verb contract) are **resolved here**.
- **ADR-414 D4** (pure genesis) — the "genesis mints exactly one owner-workspace per user" invariant
  gains a **branch**: a *share-first arrival* mints **no** owner-workspace (join-only). Owner-genesis
  defers to the first owner-act. The trigger that enforced 1:1 (migration 106) is reconsidered (D2).
- **ADR-368** — the MCP interop face gains a **fourth verb, `share`** — the *membership* verb
  completing the *content* trio (`remember`/`recall`/`trace`).

**Preserves**: ADR-373 (workspace = the multi-principal binding unit; the grant is the authorization
fact) · ADR-378 (the workspace is the outermost unit — **no org-above-workspace layer; a person
reaching N workspaces is the ADR-373 world, not a new tenant entity**) · ADR-408 D1 (free-for-all
within granted regions; trust by attribution + revertibility + witness) · ADR-434 (the powerbox
narrows a grant; it is not the default posture) · ADR-437 §8 guardrails (no substrate fork; solo↔team
is presentation; N=1 byte-identical).

---

## 1. Context — the thesis, and why it is stronger than ADR-437 framed it

ADR-437 filed Share under **activation** ("how does a stranger become an activated principal") and
shipped it as Phase D — a growth wedge. The operator's 2026-07-18 thesis is that this *undersells*
what Share is. Tested from the axioms rather than the ADRs, the thesis holds and goes further:

**The moat only turns on with a second principal.** Per ADR-373 the binding unit is the
workspace-as-multi-principal-commons; per FOUNDATIONS the atom of everything is the attributed
revision — *who did this, under what grant, and why.* Attribution across a **single** principal is
trivial: a one-member commons is a diary. `trace`, correction-compounding, "diverge privately,
settle publicly" (ESSENCE v16) are all **latent until someone else is in the room.** Therefore:

> **The act that creates the second principal is the act that switches the moat on. It is not a
> peripheral convenience; it is a constitutive act of the product.**

This makes Share **first-class by construction.** And it exposes a structural symmetry the interop
face already half-shows. The MCP surface is three verbs — `remember` (write), `recall` (read),
`trace` (provenance) — the **content** half of the commons ABI. What is missing is the
**membership** half: the verb that governs *who is in the commons at all*. ADR-437 reserved `share`
as a fourth MCP verb but hid its nature under "activation." First-principles, `share` is the
**access primitive**, peer to the content verbs — it **completes the primitive set** (content
verbs + the membership verb = the full commons ABI).

**Ruling adopted**: Share is a first-class access primitive. This ADR raises it to that altitude.

## 2. The measured seam (Hat-A receipts — the audit that reframed the workflow)

The operator's intuition was "checking if a user has a grant, then showing files; and if not in a
workspace, whether that check is a sub-step on sign-up." The 2026-07-18 code audit found the
intuition points at a **real** gap but **mislocates** it. Two receipts:

- **The grant check already exists and runs on every request.** `principal_reaches_workspace(user_id,
  ws)` is the authority gate (`routes/shares.py:77`); `_substrate_scope` keys every read/write on
  `workspace_id` via the active grant; accept is idempotent for owner and re-accepting member
  (`workspace_shares.py:170`). **There is no "add a grant check" work** — the check is the spine.
- **The gap is two disjoint entry doors.** (1) Cold sign-up → the migration-106 DB trigger
  `on_auth_user_created` unconditionally `INSERT INTO workspaces (name, owner_id)` → the user lands
  on `/desktop` of *their own* workspace. (2) Accept `/s/{token}` → mints a member grant into
  *someone else's* commons, auth-gated (an anonymous visitor bounces through login with `?next`
  preserved). **The two doors do not know about each other.**

The precise consequence, confirmed in code: a brand-new person who clicks a shared deck has **no
account**. They bounce to login (`?next=/s/{token}`), sign up — and the **DB trigger mints them an
owner-workspace before the share is ever considered** (`workspace_init.py` genesis + the trigger
below the app layer). The `?next` round-trip *does* then land them on the shared artifact (so the
share is not "lost") — but they now **silently own an empty phantom workspace they never asked for**,
and the entry flow's terminal state was decided by two independent doors rather than one.

> **The finding that reframes the workflow**: the work is not "add a grant check" (it exists). It is
> **unify the two doors** — sign-up becomes share-aware, so arriving-through-a-share and
> arriving-cold are two branches of *one* activation flow whose terminal state is "you are a
> principal in the right commons, looking at the right thing." **Join-only is impossible today** not
> for lack of app logic but because a DB trigger mints an owner-workspace *below* the app, before the
> share is seen. That trigger is the thing this ADR must clear.

## 3. Decisions

### D1 — Share is the membership primitive; it owns the entry flow end-to-end

Share is re-cut to a first-class access primitive, peer to `remember`/`recall`/`trace`. Concretely
this changes *ownership*, not (mostly) *mechanism*: the `workspace_shares` transport, the accept
surface, and the broad-by-default grant all stand. What Share now **owns** is the **unified entry
flow** (D2) and the **membership verb on the interop face** (D5). It stops being "an affordance on an
artifact" and becomes "the act by which the commons gains a principal, wherever that act originates
(cockpit, invite, MCP)."

### D2 — The two-doors unification: share-aware sign-up, and **join-only genesis** (the crux)

**Operator ruling (2026-07-18): a share-first arrival mints NO owner-workspace — join-only.** The
recipient exists purely as a **member** of the commons they were shared into; owner-genesis of their
*own* workspace **defers to the first owner-act** (they create/own something, or explicitly start
their own workspace). This is the cleaner primitive: the share *is* their entry; there is no phantom
empty workspace.

This collides with the **"every user owns exactly one workspace" invariant** — real and load-bearing:
`resolve_owner_workspace_id` documents it "confirmed 1:1 with users" (`supabase.py:100`), and the
**migration-106 trigger** enforces it at the DB layer, below the app. Join-only therefore **cannot be
an app flag** — it requires clearing the trigger's unconditional mint. Two ways to clear it, decided
here:

- **(chosen) Make owner-genesis lazy, not automatic.** Retire the migration-106 auto-mint trigger;
  owner-workspace creation moves to an **explicit, app-controlled** act (`initialize_workspace` on
  first owner-need, or an explicit "start your own workspace"). A share-first arrival simply **never
  calls it** — they hold a member grant and no owner row. A cold (non-share) arrival calls it on
  first `/desktop` load (the lazy-scaffold path already exists — `GET /api/workspace/state` triggers
  backend scaffolding on first load, `auth/callback` comment). **Net: the trigger's job moves up into
  the app, where it can be conditional.**
- *(rejected) Keep the trigger, delete the phantom on accept.* Mint-then-reap is a race and a lie
  (the owner row exists for a window; billing/state endpoints may observe it). It also keeps the
  invariant nominally true while making it operationally false. Clean removal beats compensating.

**The invariant is amended, not abandoned**: a user owns **zero-or-one** owner-workspace (was
exactly-one). `resolve_owner_workspace_id` must tolerate `None` (a member-only principal) — every
caller that assumed 1:1 is audited in the phased work (§4). This is the ADR's largest blast radius
and the reason it is doc-first.

**Share-aware sign-up flow** (the unified door):

```
Stranger clicks /s/{token}  (no account)
  → middleware bounces to login/signup with ?next=/s/{token}  (exists today)
  → sign up  →  auth.users INSERT
       →  (NO owner-workspace auto-minted — trigger retired, D2)
  → auth/callback finalize() honors ?next → /s/{token}
  → accept_share() mints a broad member grant (or view, D3)
  → land on the shared artifact in the shared commons
  → the acceptor is a MEMBER-ONLY principal (no own workspace yet)
```

A cold (non-share) sign-up is the same flow with no `?next` share: `finalize()` lands on `/desktop`,
which lazily mints their owner-workspace on first state-fetch. **One flow, two branches, decided by
whether a share token is in hand** — the two doors are now one.

### D3 — The grant shape on accept: broad-member default, **`share-as-view` resolved as the second shape**

ADR-437 D4.2 shipped broad-member as the default (the Figma model) and **named-but-did-not-build**
`share-as-view` (its open q#2). A first-class, prominent Share **draws the "I just want them to see
this deck" case**, which under broad-member-only **silently over-grants full membership.** This ADR
**resolves q#2: build the second shape.** The sharer picks at share-creation time:

- **Full access (default)** — `role: member`, `scopes=None` → class-default write regions (unchanged;
  ADR-373 D3 / ADR-437 D4.2). The acceptor joins the commons able to work.
- **View only** — a read-scoped grant: the acceptor sees the artifact + its `trace` (the moat on
  contact) **without** broad write membership. Implemented as a **grant with a narrowed scope**
  (the powerbox vocabulary, ADR-434), **not** a new artifact-scoped access object — Singular
  Implementation (ADR-437 D4.3: one grant model, entry framings differ). The narrowing is *the
  powerbox applied at accept-time* rather than after.

The share row carries the chosen `role`/scope; the accept page shows the honest consequence
("Join {workspace} with full access" vs "View {artifact} — read-only"). This keeps the coworking
generous-default (ADR-408 D1) while making the honest read-only case first-class instead of a
silent over-grant.

### D4 — Post-entry legibility reuses existing surfaces (no new membership UI)

**Operator ruling (2026-07-18)**: once a person is in the system, we do **not** build new membership
chrome — we use existing surfaces + the owner/guest/member labeling that already exists. A person now
legitimately holds grants to **N** commons (their own, if any, + every share/invite accepted).
Concretely:

- **Solo↔team stays presentation** (ADR-437 §8): the label is derived from `owner_id` +
  `principal_grants.role` — never a data/RLS/metering fork. `WorkspaceMembersCard` already derives
  this; a member-only principal simply has no "your workspace" and one-or-more "guest in {X}" rows.
- **"Which workspace am I acting in?"** (`X-Workspace-Id`) becomes a real surfaced choice — a
  **workspace switcher** over the grants a user already holds, showing owner vs guest/member. This is
  the ADR-373 multi-principal world made visible; it is **not** an org-above-workspace layer
  (ADR-378 ceiling holds — no tenant entity, no cross-workspace roll-up).
- A **member-only** principal (no owner-workspace) sees only "guest in {X}" entries until they start
  their own — the empty-own-workspace state simply does not exist for them. This is the join-only
  payoff made legible with existing components.

### D5 — The MCP `share` verb completes the commons ABI (resolves ADR-437 q#3)

The interop face gains **`share`** — the membership verb beside the content verbs
(`remember`/`recall`/`trace`, ADR-368). An external LLM working in a member's session can `recall`
an artifact and then `share` it to a colleague, who lands on `/s/{token}` and becomes a principal —
**the viral loop running through the interop door**, and the same strategic move as the cockpit
affordance from the other end.

**Contract (resolving ADR-437 q#3)**: `share` **mints the share row and returns the shareable link**
for the assistant to relay (it does not itself deliver email — the model relays the link in its own
channel; ADR-404 honesty line: models come IN; no outbound a2a orchestration). It reuses
`create_share()` verbatim — **one transport, three origins** (cockpit, invite-sibling, MCP). The
verb is additive on the separate MCP deploy (Render service parity — the MCP server is its own
deploy, CLAUDE.md §5).

## 4. Phases (each its own commit; doc ratifies first)

- **Phase A — the ABI + doc canon (this ADR)**: ratify D1–D5. No code. This is the deliverable that
  needs operator eyes because D2 amends a load-bearing invariant.
- **Phase B — join-only genesis (D2, the crux + largest blast radius)**: retire the migration-106
  trigger (new migration); move owner-genesis to lazy/explicit; make `resolve_owner_workspace_id`
  `None`-tolerant; **audit every 1:1 caller** (billing, `X-Workspace-Id` fallback, state endpoints,
  `_acting_workspace`). Gate: a member-only principal has zero owner rows and full member function;
  a cold sign-up still gets exactly one owner-workspace lazily; N=1 owner byte-identical.
- **Phase C — share-aware sign-up (D2 flow)**: `?next` token survival is already there; the change is
  the branch — a share-first `finalize()` must NOT trigger owner-genesis. Rides Phase B's laziness.
- **Phase D — `share-as-view` (D3)**: the share-creation chooser + the read-scoped grant (powerbox
  narrowing at accept). Accept-page honest-consequence copy.
- **Phase E — the switcher + guest legibility (D4)**: reuse `WorkspaceMembersCard` + a switcher over
  held grants; owner/guest labels. No new data.
- **Phase F — the MCP `share` verb (D5)**: additive on the MCP deploy; reuses `create_share()`.

Phases B/C are the invariant-touching pair and ship together or not at all. D/E/F are independently
shippable.

## 5. What this ADR does NOT do (guardrails)

- **No org-above-workspace layer** (ADR-378) — a person reaching N workspaces is the ADR-373 world;
  no tenant, no cross-workspace roll-up, no "team account."
- **No substrate/RLS/metering fork** (ADR-437 §8) — solo↔team and owner↔guest are presentation; N=1
  byte-identical.
- **No second grant primitive / no artifact-scoped access object** (ADR-437 D4.3) — `share-as-view`
  is the powerbox narrowing the one grant model, not a parallel access entity.
- **No outbound a2a** (ADR-404) — the MCP `share` verb shares *into* a commons; yarnnn does not call
  out to other models.
- **No new membership UI beyond existing surfaces** (operator ruling, D4).
- **No re-introduction of a workspace-level constitution / setup wizard** (ADR-421/437) — entry is a
  flow, not a ceremony.

## 6. Open questions for ratification

1. **The join-only invariant amendment (D2)** is the one that needs an explicit yes: are we
   comfortable that a user may own **zero** workspaces (member-only)? This is the largest change and
   the reason for doc-first. If no, the fallback is ADR-437's status quo (own + shared, land on
   shared) — which preserves the 1:1 invariant at the cost of the phantom empty workspace.
2. **`share-as-view` scope shape (D3)** — the exact read-scope the powerbox writes (read-only across
   the artifact's path? the whole commons read-only?) is a Phase-D design detail; ratify the
   *direction* (build the second shape) here.
3. **The switcher's home (D4/E)** — top-bar vs a Files/Account surface. Presentation detail, deferred
   to Phase E; the *principle* (reuse existing labels, no new data) is ratified here.

## 7. The one-line statement

**Share is the membership primitive — the access verb that completes the commons ABI beside
`remember`/`recall`/`trace` — and its real work is not a grant-check (that exists) but the
unification of the two entry doors: sign-up becomes share-aware, a share-first arrival joins the
commons with no phantom owner-workspace (retiring the migration-106 auto-mint so join-only is real),
the honest read-only grant shape ships beside broad-member, membership stays legible through the
surfaces we already have, and one `share` verb carries the same act through the interop door — so
the act that switches the moat on is owned end-to-end instead of filed under activation.**
