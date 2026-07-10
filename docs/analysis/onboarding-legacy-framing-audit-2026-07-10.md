# Onboarding Legacy-Framing Audit — genesis, first-run, and the coworking commons

**Date**: 2026-07-10
**Hat**: A (system canon — real-operator-facing) for the audit; the proposed direction is a pre-ratification draft (Hat B until it becomes an ADR).
**Author**: Claude (collaborator) + KVK (operator)
**Status**: Audit + proposed direction. **Not an implementation session** — no code changed. **The proposed direction (§6) became [ADR-437](../adr/ADR-437-the-activation-model-discovery-cold-landing-and-the-shared-artifact-wedge.md)** (2026-07-10) — reframed per the operator ruling from "what onboarding looks like" to "how users get activated": `/setup` is **deleted in full** (not repaired), and the replacement is the two-channel activation model (cold discovery → default landing with a deliberate empty state; invited/shared → one accept surface, the shared-artifact wedge with broad-by-default grants). This doc is retained as ADR-437's derivation record.

---

## 0. Thesis under test

> The current onboarding is built on a legacy mental model that three ratified
> ADR bands have since superseded. The setup sequence still asks the operator to
> "pick a program that forks a domain-shaped workspace" and "author a
> workspace-level constitution," and the whole flow is single-player — none of
> which survives ADR-414 (pure workspace), ADR-421 (per-agent constitution), or
> ADR-373/407/408 (the multi-principal coworking commons).

**Verdict: CONFIRMED, with one important nuance.** The *backend* genesis and
activation machinery already migrated to the post-414 world (pure-empty genesis;
activation resolves through a hire grant row). The drift is almost entirely at
the **surface / framing layer** — the FE copy, the step ordering, and the
single-player mental model are frozen pre-414 even though the mechanism beneath
them changed. This makes the fix cheaper than the thesis implies (it is largely a
surface re-derivation, not a machinery rebuild) and sharper (the surfaces are now
*lying about* a backend that has already moved on).

---

## 1. The three ratified ADRs (what the current world actually is)

### ADR-414 — The Pure Workspace (Accepted, Implemented 2026-07-07→08)

- **D4 — pure genesis**: the workspace is born empty. `initialize_workspace`
  seeds only two governance dial files + one narrative session + a balance-audit
  row. The `program_slug` parameter and the Phase-5 genesis-time fork are
  **deleted**. The MANDATE hard gate (ADR-207/320 D4) is **retired at the
  workspace level** and re-pointed per-agent.
  ([ADR-414 §5, deletion ledger §8](../adr/ADR-414-the-pure-workspace-genesis-system-agent-program-as-hire.md))
- **D5 — program activation is an Altitude-3 hire; the record is a grant row.**
  "Hire a trader," not "become a trading workspace." `fork_reference_workspace`
  installs the bundle's files into `agents/{slug}/` — the hired agent's home —
  never into the workspace root. `parse_active_program_slug` /
  `resolve_active_program_slug` / `strip_program_marker_from_mandate` /
  `_TEMPLATE_HEADING_RE` are **deleted**; the activation record is a
  `principal_grants` row. **Hiring is anytime, not a setup gate.**
- **D6 — governance re-allocation**: mandate / persona (IDENTITY/principles) /
  expected-output move **per-agent** (`agents/{slug}/`); the workspace holds
  "grants + owner-as-constitutional-author + an optional operator-authored
  charter — no gate, no seed."

### ADR-421 — The Workspace Has No Constitution Surface (Accepted 2026-07-08)

- **Ruling: a workspace has no constitution of its own.** "It holds files,
  members, connections, and a balance." Mandate/Identity/Principles are **removed
  from every workspace-level surface** — the panes go dormant, the Constitution
  group is deleted from Workspace Settings.
  ([ADR-421 §1–2](../adr/ADR-421-the-workspace-has-no-constitution-surface.md))
- **D3 — the per-agent constitution is the only home.** `AgentConstitutionBlock`
  reads `agents/{slug}/`; the workspace has none.

### ADR-373 / ADR-407 / ADR-408 — the multi-principal coworking commons

- ADR-373 re-keyed the substrate binding unit from `user_id` to `workspace_id`;
  **the workspace is a multi-principal attributed commons** (humans, their
  agents, other humans, platforms, foreign/local LLMs). **N=1 is the degenerate
  case, byte-identical.**
- ADR-407 declared the three scopes (workspace content / member experience /
  account) and named the interaction model **"macOS, not Figma": N first-person
  shells over one shared filesystem.**
- ADR-408 D1 — **the coworking contract**: "the workspace is a coworking commons,
  not an approval hierarchy." A principal acting within their grant binds
  immediately (after-witness); the grant is the only boundary between humans.
  ([ADR-408 §2](../adr/ADR-408-the-coworking-contract-and-the-three-ai-altitudes.md))
- ADR-429 §12 — pricing collapsed to **Free + one paid plan** ($20/$15); Free =
  **owner + 1 guest** (`included_seats: 2`); a **team may try the commons before
  paying** (the viral-team funnel). The Starter/Pro split returns only when the
  dormant capture lane ships.
  ([ADR-429 §12.3c](../adr/ADR-429-the-three-axis-pricing-model-workspace-base-human-seats-pooled-meter.md))

---

## 2. Legacy-framing findings, with file:line receipts

### Finding 1 — Setup step 1 "Pick a program" carries the pre-414 fork framing

[`web/components/library/SetupSequence.tsx:148-152`](../../web/components/library/SetupSequence.tsx#L148-L152):

```
key: 'pick-program',
title: 'Pick a program',
detail:
  'A program forks a domain-shaped workspace — mandate, agents, recurrences,
   context structure. The floor of becoming operational.',
```

This is verbatim the world ADR-414 D5 deleted:

- **"forks a domain-shaped workspace"** — false. Per ADR-414 D5 a program
  installs a *persona agent* into `agents/{slug}/`; **the workspace is never
  typed by it** (ADR-222, finally honored). The fork no longer touches the
  workspace root.
- **The step gates on `state.active_program_slug`**
  ([`SetupSequence.tsx:154`](../../web/components/library/SetupSequence.tsx#L154),
  `done: !!state.active_program_slug`) — treating "have you picked a program yet"
  as the **floor of becoming operational**, i.e. a setup precondition. ADR-414 D4
  retired that gate: hiring is a **post-genesis, anytime** act. The whole step
  presents an anytime hire as a first-run wizard step.
- The class heading, "The floor of becoming operational," directly contradicts
  ADR-414 §5's "the workspace is born empty, constituted, and shared" and its
  cold-start-virtue re-homing ("structure-emergence is Freddie's job, not
  pre-scaffolded directories").

**The backend has already moved on** — which sharpens the finding.
`api.workspace.getState()`'s `active_program_slug` is now derived via
`resolve_hired_program_slug(auth.user_id)`
([`api/routes/workspace.py:2328`](../../api/routes/workspace.py#L2328)) — the
**grant row**, ADR-414 D5. And `activation_state` is classified against the
mandate read from `resolve_judgment_home` — the *hired agent's home* when a hire
exists ([`workspace.py:2331-2342`](../../api/routes/workspace.py#L2331-L2342)).
So the field the FE gates on already means "is an agent hired," not "is the
workspace typed" — but the FE copy still describes the deleted behavior. **The
surface is stale relative to its own data source.**

(The `POST /api/programs/activate` docstring at
[`api/routes/programs.py:134-141`](../../api/routes/programs.py#L134-L141) also
still says "forking the bundle's `reference-workspace/` files into `/workspace/`"
— pre-414 prose over post-414 mechanics. A doc/comment drift, lower-severity than
the operator-facing FE copy, but worth sweeping in the same pass.)

### Finding 2 — Setup step 2 "Author your constitution" asks for an altitude that no longer holds one

[`SetupSequence.tsx:176-182`](../../web/components/library/SetupSequence.tsx#L176-L182):

```
key: 'author-constitution',
title: 'Author your constitution',
detail:
  'Your mandate and identity — what this workspace is for, and the voice it
   reasons in. Authored in chat; the agent walks you through it.',
done: constitutionAuthored,
```

where `constitutionAuthored`
([`SetupSequence.tsx:142-144`](../../web/components/library/SetupSequence.tsx#L142-L144))
is:

```
state.substrate_status.mandate.state === 'authored' &&
state.substrate_status.identity.state === 'authored'
```

This asks the operator to author a **workspace-level** mandate + identity — "what
this **workspace** is for, and the voice it reasons in." ADR-421 removed exactly
this: **"a workspace has no constitution of its own."** Mandate/Identity/Principles
belong to the steward (kernel constants, ADR-414 D2) or a hired agent
(`agents/{slug}/`, ADR-421 D3). A first-run operator on a bare (unhired)
workspace has no altitude that holds a constitution to author.

Note the compounding effect: on a bare workspace `resolve_judgment_home` is null,
so `substrate_status.mandate`/`identity` read the **steward-era workspace-root
paths** which pure genesis no longer seeds — so this step can only ever complete
by the operator authoring workspace-root files that ADR-421 says should not exist
as a workspace-level surface. The step is not just mis-framed; its completion
condition writes to a retired location.

### Finding 3 — Onboarding is single-player throughout; the commons a team joins is never introduced

The workspace is a multi-principal commons (ADR-373/407/408), N=1 degenerate.
But every onboarding surface addresses one solo operator:

- The setup welcome ([`SetupSequence.tsx:263-268`](../../web/components/library/SetupSequence.tsx#L263-L268))
  is "Welcome to YARNNN / Four moves to an operating workspace" — no mention that
  a workspace is something a team shares, that you can invite collaborators, or
  that AI principals attribute into the same commons.
- The five steps (pick-program → author-constitution → connect-platforms →
  bring-in-reality → first-artifact) are a **solo operationalization checklist**.
  There is no "invite your team" affordance, no seat awareness, no framing of the
  commons as shared.
- The genesis path itself is solo: the auto-create trigger names the workspace
  the hardcoded `'My Workspace'`
  ([`supabase/migrations/106_auto_create_workspace_on_signup.sql`](../../supabase/migrations/106_auto_create_workspace_on_signup.sql))
  — a possessive-singular label, not a shared-commons name.

This is a *missed-opportunity* finding more than a *broken* one: the invite path
works (ADR-404), N>1 is functionally real (ADR-407/408), and Free intentionally
includes a guest seat so a team can try the commons before paying (ADR-429
§12.3c). But onboarding never surfaces any of it — the viral-team funnel ADR-429
explicitly designed for has **no on-ramp in the first-run experience**.

---

## 3. Structural gaps (the surrounding first-run plumbing)

### Gap A — Two overlapping first-run surfaces, one of them dead code

Two components consume `?first_run=1` and both carry the pre-414 program-fork
framing:

1. **`SetupSequence.tsx`** — the live redirect target. `auth/callback/page.tsx`
   sends first-run operators to `/setup?first_run=1`
   ([`web/app/auth/callback/page.tsx:59-61`](../../web/app/auth/callback/page.tsx#L59-L61)).
2. **`web/components/settings/WorkspaceSection.tsx`** — reads
   `searchParams.get('first_run') === '1'`
   ([`WorkspaceSection.tsx:74`](../../web/components/settings/WorkspaceSection.tsx#L74)),
   still frames "Pick a program to fork its starting substrate"
   ([`WorkspaceSection.tsx:176`](../../web/components/settings/WorkspaceSection.tsx#L176)),
   still says "No program activated yet. Activate a program below to begin — it
   sets up…" ([`WorkspaceSection.tsx:233`](../../web/components/settings/WorkspaceSection.tsx#L233)).

**`WorkspaceSection` is not mounted anywhere** — a repo-wide grep for
`WorkspaceSection` returns only its own file. It is an orphaned second first-run
surface: dead code carrying stale framing, primed to mislead the next person who
wires it back in. The "two overlapping first-run surfaces" gap is real, and one
side is a landmine (dead but plausible-looking).

### Gap B — The invite accept is a fragile standalone page

`web/app/invite/[token]/page.tsx` documents its own prod incident
([`invite/[token]/page.tsx:8-16`](../../web/app/invite/[token]/page.tsx#L8-L16)):
inside the `(authenticated)` shell, `SurfaceViewport` renders page children for
non-surface routes **only when no windows are mounted** — so any operator with
persisted dock state got their Desktop instead of the invite page and the accept
**silently never ran** (operator-observed 2026-07-04: invited member landed on
Mandate, invite stayed pending). The fix pulled `/invite` *out* of the shell into
a standalone threshold page. This works but is fragile-by-construction: it is a
hand-rolled page outside the surface system, and the invite email is best-effort
(the copy-paste raw link is the de-facto reliable path). The single most
important growth act — a human joining the commons — runs on the least robust
surface in the app.

### Gap C — Seat awareness lives on the billing card, not where invites happen; the gate fails open

Free = owner + 1 guest (`included_seats: 2`,
[`billing_tiers.py:96`](../../api/services/billing_tiers.py#L96)); the 3rd human
invite requires paid (ADR-429 §12.3c). The gate is **enforced** — but in the
service, not the route: `create_invite`
([`api/services/workspace_invites.py:113-120`](../../api/services/workspace_invites.py#L113-L120))
computes `projected = human_members + len(pending) + 1` and raises
`InviteError("seat_limit", …)` when `projected > included`. Two caveats worth
noting: **(a) it fails OPEN** — the count block is wrapped in
`try/except Exception: pass`, so any DB read error silently skips the gate; and
**(b)** the route flattens `seat_limit` into a generic **HTTP 400** detail string
([`workspace.py:1436-1437`](../../api/routes/workspace.py#L1436-L1437)), not a
402/upgrade-required status the FE can branch on cleanly.

A proactive "X of Y seats used" indicator **does exist** — but only on the
**billing surface** (`SubscriptionCard.tsx:174`: `"{humanSeats} of
{includedSeats} seat(s) used"`, currently dormant/count-only since the seat fee
is $0). It is **absent from the members / invite surfaces** where a team actually
invites people: `GET /workspace/members`
([`workspace.py:127-131`](../../api/routes/workspace.py#L127-L131)) and
`preview_invite` return no seat count, cap, or remaining. So a team inviting
collaborators from the members roster hits the paid boundary as a surprise 400 —
the seat awareness that exists is one surface away from where the decision is
made.

---

## 4. What is NOT drift (verified — do not "fix" these)

- **Genesis is already pure.** `initialize_workspace`
  ([`api/services/workspace_init.py`](../../api/services/workspace_init.py))
  is v3.0 "PURE GENESIS (ADR-414 D4)": seeds only `_budget.yaml` + `_autonomy.yaml`
  + the narrative session + the balance-audit row; no `program_slug` param, no
  skeleton seeding, no OCCUPANT scaffold. This is correct and current.
- **Activation is already a hire.** `active_program_slug` resolves through
  `resolve_hired_program_slug` (the grant row); `fork_reference_workspace`
  installs into `agents/{slug}/`. The backend honors ADR-414 D5.
- **No workspace-type fork exists.** (See §5 — no `workspace_type` / `workspace_kind`
  column, enum, or type-branching service logic; personal-vs-team is label-only,
  derived from ownership + role.) The substrate is one unified commons; N=1 is
  byte-identical. **Do not propose a data/RLS/metering fork.**
- **BYOK is ~80% built and ratified as the enterprise lever.** The LiteLLM router
  (`api/services/model_router.py`) is flag-gated OFF (`MODEL_ROUTER_ENABLED`);
  `lane_runner.py` short-circuits when disabled
  ([`lane_runner.py:295-296`](../../api/services/lane_runner.py#L295-L296)); the
  per-call `api_key` kwarg is the named-unbuilt piece
  ([`model_router.py:49`](../../api/services/model_router.py#L49)). ADR-409
  ratifies "BYOK as the tier lever" — a tier privilege, zero-draw on the
  customer's key, no usage tax. This is the honest enterprise axis (ADR-429 §12
  notes it would re-justify a third rung).

---

## 5. Verification receipts (schema-fork + seat-gate)

> This section carries the two load-bearing verifications: (a) that no
> workspace-type fork exists in schema or services, and (b) exactly where/whether
> the Free-tier seat gate is enforced.

### 5a — No workspace-type fork exists (personal-vs-team is label-only)

- **No `workspace_type` / `workspace_kind` / `personal` / `team` / `is_team` /
  `org_id` column or enum.** The `workspaces` table
  ([`supabase/migrations/001_initial_schema.sql:10-16`](../../supabase/migrations/001_initial_schema.sql#L10-L16))
  is `id, name, owner_id, created_at, updated_at`. Every subsequent `ALTER TABLE
  workspaces ADD COLUMN` adds only billing/subscription/digest/impersonation
  columns — never a type. The **only** CHECK constraint on `workspaces` is
  `workspaces_subscription_tier_check`
  ([`194_adr396_type_b_subscription.sql:39-41`](../../supabase/migrations/194_adr396_type_b_subscription.sql#L39-L41))
  — a **billing tier** (free/starter/pro), not a personal/team type. No
  `CREATE TYPE` enum for workspace/team/personal exists.
- **No service/route branches on workspace type.** The seat-role set is flat:
  `HUMAN_SEAT_ROLES = ("owner", "member")`
  ([`billing_tiers.py:218`](../../api/services/billing_tiers.py#L218)). Behavioral
  gates key on `subscription_tier` / `billing_exempt` (a billing plan) and
  principal `role` (owner/member/AI-class) — never a workspace category.
- **Personal-vs-team presentation is derived at request time** from ownership +
  grant role. In `get_workspace_memberships`
  ([`api/routes/workspace.py:1044-1083`](../../api/routes/workspace.py#L1044-L1083)):
  the caller's own workspace is labeled `"My workspace"` (`role="owner"`); a
  workspace where the caller holds an active `member` grant is labeled
  `"{email}'s workspace"` (falling back to `"Shared workspace"`). No stored type;
  the label is a pure function of `workspaces.owner_id` + `principal_grants.role`.
  **This confirms solo↔team is safely a presentation concern** — the substrate
  does not fork.

### 5b — The Free-tier seat gate: enforced, service-side, fails open

- **Enforced** in `create_invite`
  ([`api/services/workspace_invites.py:113-120`](../../api/services/workspace_invites.py#L113-L120)):
  `projected = human_members + len(pending) + 1; if projected > included: raise
  InviteError("seat_limit", …)`, where `included = tier_included_seats(tier)`
  (Free = 2). Pending invites hold seats, so a team can't over-invite past the
  cap. `accept_invite` does **not** re-check (the gate is at invite-create, not
  accept).
- **Fails OPEN**: the count block is wrapped in `try/except Exception: pass`
  ([`workspace_invites.py:83, 121-124`](../../api/services/workspace_invites.py#L83-L124))
  — a DB read error silently skips the gate. `billing_exempt` workspaces bypass
  entirely.
- **Not called through the canonical helpers**: the invite gate does its own
  inline `principal_grants` count; `count_human_seats` / `billable_seats` /
  `seat_fee_usd` ([`billing_tiers.py:231-270`](../../api/services/billing_tiers.py#L231-L270))
  are called only on the **subscription status** path
  ([`api/routes/subscription.py:281-295`](../../api/routes/subscription.py#L281-L295)),
  which feeds the (dormant) billing-card seat indicator. Minor Singular-
  Implementation smell (two seat-counting code paths), noted for the fix pass.

---

## 6. Proposed direction (candidate ADR-437) — onboarding re-derived from the current architecture

The onboarding should be **derived from what the architecture now is** — a
pure-empty, multi-principal commons where structure emerges through work and
programs are anytime hires — rather than reconstructed from the pre-414 wizard.
The direction, framed as decisions to ratify:

### DD1 — First-run is "enter your commons," not "configure your workspace"

The first-run surface stops being a **configuration wizard** (pick a type, author
a constitution, complete the checklist) and becomes an **orientation to a living
commons**: here is your workspace (empty, yours, shareable); here is Freddie (the
system agent, the rail is its voice); drop in a file or say what you're working
on and watch structure + attribution accumulate. This is ADR-414 §5's
"structure-emergence is the onboarding demo" made concrete — the first-contact
arc is *work happening with attribution*, not form-filling.

### DD2 — "Pick a program" is deleted as a setup step; hiring is an anytime affordance

Per ADR-414 D4/D5, a program is an Altitude-3 **hire**, done anytime, recorded as
a grant row. It has no place as a first-run gate or "the floor of becoming
operational." The program-picker relocates to an **anytime "Hire an agent"**
affordance (its natural home is the agents surface / a hire drawer), framed as
"bring in a specialist," not "type your workspace." The first-run experience
works fully with zero hires (the bare commons is a first-class resting state, not
a pre-operational one).

### DD3 — No workspace-level constitution authoring; constitution is per-agent

Per ADR-421, delete the "author your workspace constitution" step. If constitution
authoring appears in onboarding at all, it appears **scoped to a hired agent**
(author *this trader's* mandate/identity, on the agent detail via
`AgentConstitutionBlock`) — never as a workspace-level surface. The workspace's
own "identity" at first-run is just its name + members + balance.

### DD4 — Introduce the commons as something a team joins (solo↔team as framing, not fork)

Onboarding names the workspace as a **shared, attributed commons** from the first
screen, and surfaces an **invite affordance** as a first-class (if optional) move
— the viral-team funnel ADR-429 §12.3c designed for gets its on-ramp. Critically:
**this is presentation, not a data fork.** The substrate stays one unified commons
(ADR-373/378); "solo" and "team" are the same path with different copy and lead
CTA, **derived from seat count + tier**. The open sub-question (§7) is whether a
signup-time "just me / with my team" prompt is worth capturing.

### DD5 — Harden the two fragile first-run surfaces

- **Delete `WorkspaceSection.tsx`** (dead code, stale framing) or re-derive it as
  the anytime hire surface if that component is wanted — but there must be **one**
  first-run surface, not a live one plus a dead twin.
- **Make invite-accept robust.** The standalone-threshold-page fix (Gap B) works
  but the surface deserves first-class treatment: reliable email delivery is the
  real fix (best-effort + copy-paste-link is a launch stopgap), and the accept
  flow is the single highest-value growth path in the product.
- **Add proactive seat awareness** (Gap C): a "N of M seats" indicator on the
  members/invite surface, derived from `count_human_seats` + `tier_included_seats`,
  so a team sees the paid boundary before hitting it.

### DD6 — BYOK/empowerment surfaces as the enterprise ceiling, communicated at the tier boundary

BYOK ("your keys, your infra, our substrate") is the honest enterprise axis
(ADR-409). It does **not** belong in the solo first-run flow, but it is where the
onboarding narrative *points* for a team that outgrows the shared meter — the
empowerment ceiling. The MCP interop face is already de-facto BYOK (an external
ChatGPT/Claude runs on the customer's own subscription, off our books). Onboarding
should communicate the through-line: **the substrate is ours and portable; the
engines are yours.** Surfacing detail is a tier/pricing-page concern, not a
first-run step — noted here so the re-derivation keeps a hook for it.

---

## 7. Open questions for ratification

1. **The solo↔team capture question.** Framing-only (a "just me / with my team"
   signup prompt that only changes copy + lead CTA, everything else derived from
   seat count + tier) vs a cosmetic stored `workspace_kind` hint (UX-only, no data
   effect) to capture an intent a solo-on-paid founder can't derive from seat
   count. **Recommendation: start framing-only**; add the stored hint only if a
   real presentation decision genuinely can't be derived (avoid storing state the
   architecture can compute — ADR-407 D1's "a store that cannot name its scope is
   a design smell").
2. **Where the anytime "Hire an agent" affordance lives** (agents surface vs a
   dedicated hire drawer) and how much of the old program-picker UX survives the
   relocation.
3. **Whether onboarding introduces Freddie explicitly** (a "meet your system
   agent" beat) or lets the rail speak for itself.
4. **Sequencing vs the deferred Home recompose** (ADR-414 §9b, "Home last"). The
   first-run cold-start CTA currently still points at program activation
   ([ADR-414 §9b](../adr/ADR-414-the-pure-workspace-genesis-system-agent-program-as-hire.md)
   records `HomeFrontPage::UnactivatedHomeCTA` framing the empty Home as "activate
   a program → /setup"). The onboarding re-derivation and the Home recompose share
   the "reframe cold-start toward the commons" work — decide whether they ship
   together or the onboarding leads.

---

## 8. Explicit "do NOT touch" guardrails

- **No substrate fork.** Do not introduce a personal-vs-team data model, separate
  RLS regime, or per-type metering. The workspace is one unified multi-principal
  commons; N=1 is byte-identical (ADR-373/378). Solo↔team is *presentation*.
- **No org-above-workspace layer.** ADR-378 deliberately left federation /
  organization-above-workspace **unbuilt**. Do not add a tenant/org entity, a
  cross-workspace roll-up, or a "team account" that owns multiple workspaces. The
  workspace is the outermost unit.
- **No new workspace-level constitution surface.** ADR-421 removed it; do not
  reintroduce mandate/identity/principles at the workspace altitude under any
  onboarding banner.
- **No genesis-time program fork.** ADR-414 D4 deleted it; onboarding must not
  reinstate program selection as a signup precondition or re-add a `program_slug`
  genesis parameter.
- **No second first-run surface.** Consolidate to one; do not leave (or add) a
  parallel first-run flow.

---

## 9. Deliverable summary

- **Confirmed** the thesis: onboarding is built on the pre-414/421/373 mental
  model. The drift is concentrated at the **surface/framing layer** (SetupSequence
  copy + step gating; a dead second surface; single-player framing) over a backend
  that already migrated to pure-genesis + hire-grant activation.
- **Concrete drift**: [SetupSequence.tsx:148-152](../../web/components/library/SetupSequence.tsx#L148-L152)
  (program-fork framing), [:176-182](../../web/components/library/SetupSequence.tsx#L176-L182)
  (workspace constitution authoring), single-player throughout; the dead
  [WorkspaceSection.tsx](../../web/components/settings/WorkspaceSection.tsx)
  twin; the fragile [invite accept](../../web/app/invite/[token]/page.tsx); the
  reactive-only seat gate.
- **Proposed direction**: a candidate **ADR-437** re-deriving onboarding as
  "enter your commons" — no program-pick gate, no workspace constitution, commons
  introduced as team-joinable (framing not fork), BYOK as the communicated
  ceiling, the fragile surfaces hardened.
- **Guardrails**: no substrate fork, no org-above-workspace layer, one first-run
  surface, no genesis-time program fork, no workspace-level constitution.
