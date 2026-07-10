# ADR-437 — The Activation Model: Discovery, Cold Landing, and the Shared-Artifact Wedge

**Status**: Proposed (2026-07-10, doc-first). Supersedes the `/setup` onboarding
sequence entirely (delete, not repair). Reframes the question from "what does
onboarding look like" to "**how does a stranger become an activated principal in a
commons**." No code in this commit; the phases in §9 are each their own follow-on.
**Date**: 2026-07-10
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Channel (Axiom 6 — the surfaces a new user enters through) + Identity
(Axiom 2 — how a stranger becomes a principal with a grant) + Purpose (Axiom 3 —
what the first contact is *for*)
**Relates to**: ADR-414 (the pure workspace — genesis is empty; this ADR removes the
last surface that assumed otherwise), ADR-421 (no workspace constitution — the setup
step that authored one dies here), ADR-373/386/404 (multi-principal grants + member
invites — the plumbing the share wedge extends), ADR-407/408 (the coworking commons —
the model a new user is entering), ADR-434 (the powerbox — the scoping the shared
grant narrows through), ADR-429 §12 (Free = owner + 1 guest — the viral funnel this
gives an on-ramp), ADR-331 (Setup as Rendering — the ADR this supersedes), ADR-297
(HOME_ROUTE = /desktop — the default landing this inherits), ADR-435 (delete Home — the
subtraction-ADR precedent), ADR-368 (the MCP memory verbs — the surface a `share` verb
joins), ADR-372 (ChatGPT widget rendering — the interop face a share can originate from)
**Supersedes/Amends**: **supersedes ADR-331** (Setup as Rendering — the `/setup`
Sequence surface is deleted; setup-as-a-guided-wizard is retired, not re-rendered);
**amends ADR-404** (the member-invite path gains a sibling: the shared-artifact
wedge, one accept surface, both origins); **amends ADR-414 §9b** (the deferred Home
cold-start CTA reframe is subsumed — cold-start points at the commons, not at program
activation, and there is no `/setup` to point to)

---

## 1. Context — the setup wizard is the last surface built on the pre-pure-workspace model

The onboarding audit (`docs/analysis/onboarding-legacy-framing-audit-2026-07-10.md`)
established, with receipts, that `/setup` is frozen in a world three ratified ADR
bands deleted:

- Step 1 "Pick a program" frames activation as **"a program forks a domain-shaped
  workspace — the floor of becoming operational"** — but ADR-414 D4/D5 made genesis
  empty and programs **anytime hires** into `agents/{slug}/`, never a workspace type
  or a setup gate.
- Step 2 "Author your constitution" asks for a **workspace-level** mandate + identity —
  but ADR-421 ruled **a workspace has no constitution of its own.**
- The whole flow is **single-player** — but ADR-373/407/408 made the workspace a
  multi-principal commons a team joins.

The backend already moved on (genesis is pure; `active_program_slug` resolves through
a hire grant row). The wizard is a surface **lying about its own data source**. The
operator's ruling: **`/setup` should be deleted and cleaned up in full — it is simply
not in line with the evolved service model.**

But the deeper move the operator named is upstream: **do not ask "what kind of
onboarding," ask "how do new users get activated."** Activation has channels
(discovery routes, invite routes), and the product should be designed from those
channels inward — not from a wizard outward. This ADR does both: it deletes the
wizard **and** names the activation model that replaces it, so the subtraction is
justified by a replacement, not done in a vacuum.

## 2. The activation model — two channels, derived from how a stranger arrives

A new user becomes an activated principal through exactly two channels. Everything
else is a variant of one of them.

| | **Channel 1 — Cold discovery** | **Channel 2 — Invited / shared** |
|---|---|---|
| Origin | Ads (social, Reddit) → yarnnn.com → sign-up | An existing principal invites/shares |
| Arrives at | A **genuinely empty** commons (their own new workspace) | An **already-populated** commons (someone else's) |
| The onboarding IS | The empty state + the first substrate-creating act | The substrate they were invited into — no blank page |
| Blank-page risk | Real (ADR-414 §5) — the empty state must teach the moat | None — the commons is the demo |
| Sub-shapes | (one) | **2a** human-invites-human (ADR-404, exists); **2b** shared-artifact wedge (new) |

The design consequence: **Channel 1 needs a deliberate empty state; Channel 2 needs a
robust accept surface.** Neither needs a wizard. The wizard was a *third* thing — a
configuration ceremony between arrival and use — and it is exactly what the pure
workspace made unnecessary (structure emerges from work, ADR-414 §5).

## 3. D1 — Delete `/setup` in full (the subtraction)

The `/setup` Sequence surface (ADR-331) is deleted, not re-rendered. Every one of its
five steps is dead-on-arrival or redundant with a surface that already exists:

| Setup step | Fate | Why |
|---|---|---|
| 1. Pick a program | **deleted** | Hiring is an anytime act (ADR-414 D5), relocated to the agents surface (D2 below) |
| 2. Author constitution | **deleted** | The workspace has no constitution (ADR-421); per-agent constitution is authored on the agent detail |
| 3. Connect platforms | **deleted** | The capture lane is dormant (ADR-404); connectors have their own surface |
| 4. Bring in reality | **deleted** | This is "use Files" — the substrate surface already exists |
| 5. See first artifact | **deleted** | This is "the product working" — not a setup step |

**Deletion ledger** (the concrete surface, ignoring `.next/` build artifacts):
- `web/app/(authenticated)/setup/page.tsx` (the route) + its `SurfaceRegistry.tsx`
  entry.
- `web/components/library/SetupSequence.tsx` (the wizard).
- `web/components/library/HarvestPicker.tsx` (setup step 4's only consumer — dies
  with it, unless the anytime harvest affordance keeps it; §7 note).
- `web/components/settings/WorkspaceSection.tsx` (the **dead second first-run
  surface** — orphaned already, mounted nowhere, carries the same stale
  program-fork framing).
- The `first_run` redirect in `web/app/auth/callback/page.tsx:55-66` (the
  `activation_state === "none" && !active_program_slug → /setup?first_run=1` branch);
  the callback simply lands the user on `HOME_ROUTE`.
- `/setup` becomes a bookmark-safety redirect stub → `HOME_ROUTE` (the ADR-308 pure
  transport pattern), or is dropped entirely if no live link points at it.

**Boundary — what does NOT get deleted**: `activation_state` /
`available_programs` on `api.workspace.getState()` and their non-wizard consumers
(`workspace-settings/page.tsx`, `client.ts`) survive — they feed the **anytime-hire**
surface (D2), not the wizard. The deletion is the wizard surface + its redirect + the
dead twin, not the program-availability data model.

## 4. D2 — Program activation is an anytime hire; the operator surface defers to ADR-382

Per ADR-414 D5, a program is an Altitude-3 **hire**, recorded as a grant row, done
anytime — never a setup gate. A first-run user works fully with **zero hires**; the
bare commons is a first-class resting state, not a pre-operational one.

**The hire machinery already exists and is unchanged**: `POST /api/programs/activate`
mints the grant and installs the bundle into `agents/{slug}/` (its docstring's pre-414
"forks into `/workspace/`" prose is corrected here to reflect the hire model).

**The operator-facing hire SURFACE is deferred, not built here** — this aligns with
ADR-432 D2, which made the `program` slug dormant and ruled that the hired-agent
roster (where "hire an agent" lives) is **ADR-382's, build-when-demanded** (ADR-380
§5: zero hired-program grants exist; it is the deliberately-unvalidated Rung-2 path).
Building a hire UI now would re-open a ratified same-week deferral and duplicate
ADR-382. So D2's scope in this ADR is: **remove the wizard's program-pick step (done
in D1) and correct the drift prose; the anytime-hire affordance re-surfaces with the
ADR-382 roster.** The point that matters for onboarding — *activation is not a setup
step* — is fully delivered by D1's deletion.

## 5. D3 — Channel 1: cold landing is the current default surface, with a deliberate empty state

**The route is inherited, not invented.** A cold sign-up lands on **`HOME_ROUTE`
(`/desktop`, ADR-297 §D17)** — the current default main landing — with **no
activation-specific routing.** This is an operator ruling: the cold-landing decision
follows whatever the default landing is at the time, as one logic, not a special case.
If the default landing changes later, cold-start follows it for free.

**The empty state is where the design attention goes** — and it is a property of the
landing surface, not a separate route. ADR-414 §5 named this a **product-design task**
precisely so it "cannot silently reduce to an empty-state copy pass":

- The empty commons must **teach the one thing that makes yarnnn not-a-chat-app**:
  durable attributed memory. A cold user who does nothing has learned nothing; a cold
  user who drops a file or states a fact and **watches it placed, attributed, and
  recallable** has seen the moat on contact.
- The empty state's first move is therefore the **substrate-creating act** (drop a
  file / capture a fact), not a form. Structure-emergence is the steward's job
  (ADR-381) — the first visible steward acts (derive, place, attribute) ARE the
  onboarding demo.
- Cold-start copy points at **the commons**, never at program activation (this
  subsumes the ADR-414 §9b deferred reframe — there is no `/setup` to point to, and
  the honest cold-start is "this is your commons; put something in it").

The empty-state design detail is scoped to the surface's own pass (§9); this ADR fixes
the *route* (inherited) and the *principle* (teach the moat, point at the commons).

## 6. D4 — Channel 2b: the shared-artifact wedge (both origins, one accept surface)

The sharpest activation wedge is **artifact-first**: an existing principal shares a
substrate artifact (a file, a recall, a trace); the recipient accesses it, and **the
act of accessing IS the activation.** The artifact is the landing page — the recipient
arrives with a reason and a piece of real, attributed substrate in hand, and sees
`trace`/attribution on contact (the moat, demonstrated, not described). This is
stronger than "sign up then figure out what to do."

**D4.1 — Two origins, one accept surface.** A share can originate from:
- **the cockpit** — a principal clicks "Share" on an artifact → a link (delivered by
  email and/or copy-paste); reuses the ADR-404 invite-token plumbing
  (`workspace_invites.py`: `create_invite` shape, `secrets.token_urlsafe`,
  `get_invite_by_token`).
- **an external LLM via MCP** — a new `share` verb joins the ADR-368 memory surface
  (`remember`/`recall`/`trace`), letting an assistant share an artifact with a named
  recipient on the user's behalf.

Both converge to **one accept/landing surface** (`/s/{token}`-shaped, standalone
threshold page — the ADR-407 D2 lesson: N origins, one filesystem; and the invite-page
incident lesson in D5 — threshold pages live OUTSIDE the shell). Origin is metadata on
the share record, not a separate flow.

**D4.2 — The grant on accept: broad by default (the Figma default).** Operator ruling:
**maximum access by default** — "think Figma invite: you can do everything, even as a
guest, by default." Accepting a shared artifact makes the recipient a **member of that
commons with broad access**, not a narrow read-only viewer. This aligns with the
coworking contract (ADR-408 D1: "free-for-all within granted regions; trust carried by
attribution + revertibility + witness, not by gates"). The powerbox (ADR-434) is the
mechanism to **narrow** a grant when the owner wants — it is not the default posture.
Two grant shapes were considered:

- **(chosen) Broad member grant** — accept mints a `principal_grants` row (`role:
  member`) with generous default scopes; the recipient is a real member of the commons,
  landing in it able to work. The shared artifact is the *entry point*; the access is
  the commons. Owner narrows via powerbox if desired.
- *(rejected as default) View-first, then optional join* — a read-only artifact view
  with no grant + a "join" CTA. Cleaner separation of "saw it" vs "joined," but it
  gates the generous-by-default coworking posture behind a second click. Kept as a
  *possible owner-chosen* share mode (share-as-view), not the default.

**D4.3 — The share is a member invite's generous sibling, not a fork of it.** Channel
2a (human-invites-human) and 2b (shared-artifact) both mint member grants and both land
on one accept surface; they differ only in **what the accept page shows** (2a: "join
{workspace}"; 2b: "here is {artifact} + its trace — join {workspace} to keep working
with it"). One grant model (ADR-373), two entry framings. This keeps Singular
Implementation: no second grant primitive, no artifact-scoped access object unless a
real narrower-than-member need appears.

## 7. D5 — Harden the Channel-2 accept surface (the growth path's robustness)

The single highest-value growth act — a person joining a commons — currently runs on
the least robust surface in the app. Three hardening moves ride with the wedge:

- **The accept page stays a standalone threshold page outside the shell.** The
  invite-accept incident (operator-observed 2026-07-04: inside `(authenticated)`,
  `SurfaceViewport` renders page children only when no windows are mounted, so an
  operator with persisted dock state got their Desktop instead of the accept page and
  the accept **silently never ran**) is a permanent constraint, not a one-off. `/s/{token}`
  and `/invite/{token}` are both threshold/transport pages, shell-free.
- **Reliable delivery is the real fix.** Email is best-effort today (the copy-paste
  raw link is the de-facto reliable path). The share/invite email deserves the same
  reliability discipline as any operator-addressing write (ADR-299/304 system wire).
- **Proactive seat awareness moves to where invites happen** (audit Gap C): the seat
  indicator exists but only on the billing card (`SubscriptionCard.tsx`); the members /
  invite surfaces return no seat count. Surface "N of M seats used" on the members
  roster (derived from `count_human_seats` + `tier_included_seats`) so a team sees the
  Free = owner + 1 guest boundary (ADR-429 §12.3c) before hitting it as a surprise 400.
  Also: the invite seat gate **fails open** on read error and flattens `seat_limit` into
  a generic 400 (audit §5b) — tighten to a clean upgrade-required signal.

## 8. What this ADR does NOT do (guardrails)

- **No substrate fork.** The workspace stays one unified multi-principal commons
  (ADR-373/378); N=1 is byte-identical. **Solo↔team is presentation** (label derived
  from `owner_id` + `principal_grants.role`, audit §5a), never a data/RLS/metering
  fork. No `workspace_type` / `workspace_kind` column — verified absent, stays absent.
- **No org-above-workspace layer.** ADR-378's ceiling stands — no tenant/org entity, no
  cross-workspace roll-up, no "team account" owning multiple workspaces. The workspace
  is the outermost unit.
- **No new workspace-level constitution surface.** ADR-421 removed it; onboarding must
  not reintroduce mandate/identity/principles at the workspace altitude under any
  activation banner.
- **No genesis-time program fork.** ADR-414 D4 deleted it; no `program_slug` genesis
  parameter, no program selection as a signup precondition.
- **No second first-run surface.** One accept surface, one cold landing; the dead
  `WorkspaceSection` twin dies, and no parallel first-run flow is added.
- **No cold-landing-specific routing.** Cold-start follows the default landing
  (`HOME_ROUTE`), not a special case (D3).
- **No outbound a2a orchestration.** A `share` MCP verb lets a model share *into* a
  commons (ADR-404's honesty line: models come IN); it does not make yarnnn call out to
  other models.

## 9. Phases (each its own commit)

- **Phase A — the subtraction (D1)**: delete `/setup` + `SetupSequence` +
  `HarvestPicker` (if unrelocated) + the dead `WorkspaceSection` + the `first_run`
  redirect branch; `/setup` → bookmark-safety stub or dropped. Cold landing = plain
  `HOME_ROUTE`. Gate: no `first_run` / `SetupSequence` references survive; the
  auth-callback lands on `HOME_ROUTE` for a fresh sign-up. **Ships first, low risk.**
- **Phase B — hire-model drift correction (D2)**: correct the `activate` route
  docstring (pre-414 "forks into `/workspace/`" → the hire model). The operator-facing
  "hire an agent" surface is **deferred to ADR-382** (ADR-432 D2 — build-when-demanded);
  Phase B does NOT build a hire UI. The onboarding-relevant point (activation is not a
  setup step) is delivered by Phase A's deletion.
- **Phase C — the cold empty state (D3)**: the `/desktop` empty-state design pass —
  teach the moat, point at the commons, invite the first substrate act. Design-led;
  coordinates with the ADR-414 §9b Home recompose if that lands adjacent.
- **Phase D — the shared-artifact wedge (D4)**: the `/s/{token}` accept surface + the
  broad-by-default member grant on accept + the cockpit "Share" affordance + the MCP
  `share` verb. Reuses the invite-token plumbing; one accept surface, two framings.
- **Phase E — accept-surface hardening (D5)**: reliable share/invite delivery; seat
  awareness on the members surface; the fail-open + generic-400 seat-gate fix.

## 10. Open questions for ratification

1. **Whether the cold empty state explicitly introduces Freddie** ("meet your system
   agent") or lets the rail/desktop speak for itself. (D3 leaves this to the empty-state
   pass.)
2. **Whether `share-as-view`** (the rejected-as-default read-only mode) is worth
   shipping as an owner-chosen share option, or dropped until demanded. (D4.2 keeps it
   named, not built.)
3. **The `share` MCP verb's exact contract** (does it mint the token, or return a
   shareable link for the assistant to relay?) — deferred to the Phase D design.
4. **The fate of the audit doc** (`onboarding-legacy-framing-audit-2026-07-10.md`) —
   whether it stays as the derivation record for this ADR or is folded in. (Operator's
   call; recommend keep as derivation, per the ADR-407 `Derivation:` precedent.)
