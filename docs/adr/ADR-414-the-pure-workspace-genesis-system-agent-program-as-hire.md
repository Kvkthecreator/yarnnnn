# ADR-414: The Pure Workspace — Genesis, the True System Agent, and Program-as-Hire

**Status**: Accepted (2026-07-07, operator-ratified — "fully aligned with stated points from canon moat statement, to the re-allocation map details"). Doc-first umbrella; implementation lands in the phased plan of §9, each phase its own commits + regression gate. The moat re-cut (D1) and canon cascade (§10) ride the Phase-0 commit with this ADR.
**Date**: 2026-07-07
**Dimension**: Substrate (Axiom 1 — what genesis seeds, where governance lives) + Identity (Axiom 2 — the system agent purified; the two-order agent model made structural) + Purpose (Axiom 3 — MANDATE re-homed per-agent) + Channel (the FE recomposition it forces)
**Relates to**: ADR-408 (the three AI altitudes — this ADR is their substrate/genesis completion), ADR-383 (the consistent agent framework — D2 amends it), ADR-216 (orchestration vs judgment — D3 collapses the seam it drew), ADR-207/206 (mandate gate + operation-first scaffolding — D4 retires their genesis-time force), ADR-222 (workspaces run programs — D5 finally honors it in code), ADR-373/404/407 (the multi-principal commons this ADR assumes), ADR-380/381/382 (the activation ladder / Freddie / persona-agent seats — D5/D6 build their substrate layer without building Rung-2 runtime), ADR-391 (per-principal allocations — D6 lands its deferred implementation line), the re-founding keystone (ADR-384 / FOUNDATIONS v9.13 — D4 implements it at genesis, where it is cheapest: nothing to migrate)
**Supersedes/Amends**: amends ADR-383 (steward files → kernel constants), ADR-216 + LAYER-MAPPING (the two-class taxonomy re-cut as three altitudes), ADR-207 (MANDATE gate becomes per-agent, never genesis), ADR-206/244 (init re-derived), ADR-226/230 (activation record moves from prose marker to grant row), ADR-320 D4 (required-region gate re-pointed per-agent). ESSENCE v15 (the moat re-cut) and FOUNDATIONS v9.16 (DP24/DP30 two-order annotation) are companion amendments in the same commit.

---

## 1. Context — the un-run cascade

The 2026-07-05→07 band (ADR-407→413) completed the pivot to a multi-human,
multi-model coworking commons: three scopes, three AI altitudes, three
chromes, protocol drivers, the workspace runtime. What that band did NOT
touch — verified by a full-repo audit (2026-07-07) — is the layer beneath
it: **workspace genesis, the program/bundle mechanics, and the wake-envelope
contract are still hardened on the single-Reviewer-judgment-seat
philosophy** the altitudes model dissolved. Concretely:

- `initialize_workspace` seeds a steward persona *as files* (ADR-383
  defaults), scaffolds a second entity labeled "System Agent"
  (`thinking_partner`), seeds `OCCUPANT.md` as `human:{user_id}` (drifted
  from the runtime truth on every bare workspace), and takes a
  `program_slug` parameter — a genesis-time program fork that violates
  ADR-222's own "workspaces don't have types" claim.
- Program activation *turns the steward into the operation*: the fork
  overwrites `persona/IDENTITY.md`/`principles.md` and stamps the seat's
  OCCUPANT — exactly the Altitude-1/Altitude-3 conflation ADR-408 D2
  dissolved ("Freddie carries the universal files but operationally
  exercises only the steward subset").
- The activation record is a prose regex (`# Mandate — {slug} (template)`),
  the envelope loads the full judgment load-out for steward wakes, and the
  canon layer (THESIS, LAYER-MAPPING, FOUNDATIONS Reviewer rows,
  agent-composition §3.2.1) still teaches the one-judgment-seat world.

The operator's ruling (2026-07-07) resolves the fork this exposes — seeded
program-steered genesis vs the pure OS — **toward the pure OS**, with the
recognition that the seeded path's virtues re-home rather than die:
structure-emergence moves into Freddie's stewardship (its ADR-381 job
description), and program steering moves into Altitude-3 hiring.

## 2. D1 — The moat re-cut: the system of record where human and AI work settles

The prior statement ("the authored, attributed, portable substrate —
defended by `trace`") named the artifact, not the position. Ratified
re-cut (lands in ESSENCE v15 verbatim):

> **YARNNN is the system of record where human and AI work settles.**
> Engines commoditize on a quarterly cycle; the accumulated, attributed
> history of a working commons does not — it compounds with tenure and
> cannot be re-inferred by a bigger model or reconstructed by a competitor.
> Every actor — every human, every model, every protocol — enters through
> one invocation contract: projection in, attributed revision out, one
> ledger (ADR-413). That contract is the moat's mechanism: it makes **the
> engines fungible precisely because the memory is not.** Portability is
> the trust wedge (you can leave, which is why you stay). Attribution is
> the accountability wedge (you can answer *who did this, under what
> grant, and why* — which no model vendor can offer neutrally, because a
> vendor auditing its own model's work is a self-audit). Accumulation is
> the compounding wedge (quality is monotonic in tenure). `trace` is the
> proof surface — the demo of the moat, not the moat.

Three properties the re-cut adds: (a) **position over feature** — "system
of record / settlement layer for multi-actor work" is a category claim
(git made distributed collaboration trustable because *history* was the
trust substrate; double-entry made the firm scalable because every entry
was attributable); (b) **anti-fragility to model churn** — every new
frontier model makes the vendor-neutral commons *more* necessary; the
wave that washes out every AI-app moat strengthens this one; (c) `trace`
correctly demoted from defense to **proof** — the defense is the toll gate
(nothing reaches durability except as an attributed revision) plus the
network effect (every principal and engine added deepens the commons).

This is a wording ratification, not a strategy change: ADR-380 §5's
conservative re-cut (substrate commons + Freddie lead; judgment defers)
stands; ADR-413's invocation contract already made the mechanism true
architecturally. The moat statement catches up to the architecture.

## 3. D2 — The steward's files become kernel constants (amends ADR-383)

The DP33 test ("collapse the category into data; layer what remains")
applied to Freddie's file set: **a file that is never legitimately
different across workspaces is a constant wearing a file costume.** No
workspace has a *different* steward mandate, steward identity, or steward
principles — ADR-383 seeded them as files only so the agent-universal
structure would hold; ADR-408 D2 then ruled Freddie "operationally
exercises only the steward subset." The completion:

1. **Steward identity, mandate, and principles move into the kernel** —
   carried by the persona-frame (`freddie_agent.py`) and kernel constants,
   never seeded into substrate. `DEFAULT_STEWARD_MANDATE_MD` /
   `DEFAULT_STEWARD_IDENTITY_MD` / `DEFAULT_STEWARD_PRINCIPLES_MD` and the
   `<!-- yarnnn:steward-default -->` marker machinery are **deleted**.
2. **What remains operator-tunable is exactly two dials**: the witness
   dial (`governance/_autonomy.yaml`, per-family delegation per ADR-405/
   408 D3) and the budget allocation (`governance/_budget.yaml`, ADR-391's
   per-principal envelope). These stay files — they ARE workspace-variable.
3. **The envelope re-carves per altitude** (the owed ADR-408 D2 work):
   steward wakes load the steward subset (dials + commons state + the
   ask); the judgment load-out (ground-truth, risk, operator-profile,
   expected-output, persona files) loads only for a hired agent's wakes
   (D5). `FreddieContext`'s carried-not-exercised annotation resolves by
   removal, not annotation — the ADR-390 dilution lesson applied
   structurally.
4. **`persona/` ceases to be Freddie's home.** The seat path stops being
   the steward's persona store; per-agent homes (D6) are where persona
   files live. Freddie's inspection surface is Workspace Settings → System
   Agent (ADR-412 D5), shrunk to the two dials + read-only legibility
   (activity, capabilities); the identity/principles panes become
   kernel-described "about" content, not substrate mirrors.

The ADR-383 one-file-structure thesis survives *for agents that carry
operation content* (Altitude 3); the steward exits it. "Every agent has a
purpose" also survives: Freddie's purpose is stated by the kernel, which
is the strongest form of "never empty."

## 4. D3 — The ADR-216 collapse: one system agent, the rail is its voice

ADR-216 split "YARNNN the orchestration chat surface" from the
persona-bearing judgment entity. That seam separated orchestration from
*judgment* — and judgment has since moved to Altitude 3 (ADR-408 D2,
ADR-382 §3). With the steward being non-judgment infrastructure and the
rail already the steward's thread (ADR-412 D2), the seam no longer
separates anything: **there is one system agent — Freddie — and the rail
is its voice.**

1. The `thinking_partner` agents-table row is **retired** (migration).
   Chat-session continuity re-keys to the workspace narrative session
   directly; `session_type='thinking_partner'` survives as a data-compat
   slug (GLOSSARY exception, relabel-keep-slug precedent).
2. `SYSTEMIC_AGENTS` reworks: the registry's `thinking_partner` entry and
   the "System Agent" display name **delete** — the naming collision (two
   entities answering to "System Agent", ADR-381 vs ADR-216) resolves
   structurally. The addressed-wake path (`stream_addressed_wake`) is
   already Freddie; the chat surface stops pretending to be a second mind.
3. The Freddie roster-synthesis in `routes/agents.py` **deletes**
   (backend catches up to ADR-412 D5's "Freddie left the roster"); the
   live-bug `reviewer:%` proposal-feed filter fixes to `freddie:` in the
   same motion; dead `FREDDIE_ROUTE` deletes FE-side.
4. YARNNN remains the **brand**; "Freddie" (or the operator-relabeled
   name) remains the system agent the rail addresses. LAYER-MAPPING's
   two-class taxonomy re-cuts as the three altitudes (§10).

## 5. D4 — Pure genesis: the workspace is born empty, constituted, and shared

`initialize_workspace` collapses to what a multi-principal OS actually
requires at birth:

| Genesis step | Survives? | Notes |
|---|---|---|
| Workspace row + owner grant | ✅ | The constitutional facts (ADR-373/386 D4) |
| Steward boot | ✅ | Kernel constants (D2) + the two dial files with kernel defaults |
| Narrative session | ✅ | The rail's thread (member-experience scope per ADR-407 D6) |
| Balance audit trail | ✅ | Unchanged |
| Steward-default persona/mandate/principles files | ❌ deleted | D2 — kernel constants |
| `system/_playbook.md`, `system/style.md`, `system/notes.md`, `persona/_principles.yaml`, `constitution/PRECEDENT.md` seeding | ❌ deleted | Materialize on first write (Axiom 1 corollary: substrate grows from work, not signup scaffolding — finally honored without exception) |
| `OCCUPANT.md` signup seeding (`rotate_occupant`) | ❌ deleted | The occupant fact becomes kernel data (D2); the signup-time `human:{user_id}` drift bug dies with it |
| `program_slug` parameter + Phase-5 fork | ❌ deleted | Programs are post-genesis hires (D5); genesis never forks |
| MANDATE hard gate (ADR-207 / ADR-320 D4) | ❌ retired at workspace level | Re-pointed per-agent: a *hired agent* must have a MANDATE to dispatch; the workspace needs none |

**Member genesis is the invite path** (ADR-404), which never runs
`initialize_workspace` — a member lands on a genuinely empty workspace and
everything renders. The acceptance test for this phase is exactly that
walk.

**The cold-start virtue re-homes, deliberately.** The blank-page risk is
real: an empty workspace with a chat rail is superficially every AI chat
product. The answer is not pre-scaffolded directories — it is that
**structure-emergence is Freddie's ADR-381 job description**
(derive-and-cite, placement, arbitration): the steward's first visible
acts — deriving structure from the first uploads and messages, with
attribution the member watches accumulate — ARE the onboarding demo.
Making that first-contact arc deliberate is named here as a
**product-design task** (the Setup surface re-derives around
invite + chat + files), so it cannot silently reduce to an empty-state
copy pass. This is also the re-founding keystone (meaning-organized
filesystem, FOUNDATIONS v9.13) implemented where it is cheapest: at
genesis, where there is nothing to migrate — directories are born from
what arrives, named by meaning, never by template.

## 6. D5 — Program activation is an Altitude-3 hire; the record is a grant row

"Hire a trader," not "become a trading workspace." A program installs a
**persona agent** (Altitude 3) that brings its own file set to its own
home; the workspace is never typed by it (ADR-222, finally honored).

1. **The activation record is a `principal_grants` row** (role from the
   existing enum's agent seam), created at hire, revoked at fire — DP33:
   "the agent count is data." The MANDATE-heading regex
   (`_TEMPLATE_HEADING_RE`), `parse_active_program_slug`,
   `resolve_active_program_slug`, and `strip_program_marker_from_mandate`
   are **deleted**; every consumer re-points to the grant lookup.
2. **`fork_reference_workspace` re-derives as `hire_program_agent`**: the
   bundle's persona/mandate/principles/governance content installs into
   the agent's home (D6), never into the steward seat.
   `_populate_occupant_for_runtime` (the fork stamping Freddie's OCCUPANT
   with the operation) **deletes** — the conflation it papered over no
   longer exists.
3. **Envelope assembly reads the active agent's home**: a hired agent's
   wakes load its full judgment load-out from `agents/{slug}/…`; steward
   wakes load the steward subset (D2). The single wake funnel, queue, and
   drain (ADR-296/298) are unchanged — what changes is whose files the
   envelope loads. This ships the *substrate layer* of ADR-382 with N≤1;
   the full Altitude-3 lifecycle (creation surface, trust clock,
   multi-agent arbitration) stays ADR-382-deferred, build-when-demanded.
4. **Alpha-trader migrates as the first Altitude-3 agent** — a one-shot
   with receipts moves the live workspace's operation persona from
   `persona/` to the agent home and mints its grant row. The Rung-2
   dogfood clock (ADR-380) continues uninterrupted; nothing is orphaned.
5. `bundles_active_for_workspace` and its consumers (substrate ABI,
   watches, ground-truth, market context) re-key to the grant row and go
   agent-scoped; the residual raw `user_id` reads in `bundle_reader.py`
   sweep to `_scoped()` in Phase A as the precondition.

## 7. D6 — The governance re-allocation map (the core table)

| Concept | Was (one-seat world) | Becomes |
|---|---|---|
| Mandate, persona (IDENTITY/principles), expected-output | Workspace `constitution/` + `persona/` + `contract/` roots | **Per-agent** — `agents/{slug}/` homes for Altitude 3; the steward's versions → kernel constants (D2) |
| Autonomy | One workspace `governance/_autonomy.yaml` | **Per-agent witness dial** — Freddie's = the System Agent pane; each hired agent's = its own home's grant sidecar (the grant a grantee can't rewrite stays locked — ADR-366's logic, per-agent) |
| Budget | One workspace `_budget.yaml` | **Workspace balance + per-principal allocations** (ADR-391's ratified architecture, implemented here) |
| Workspace constitutional layer | MANDATE hard gate + seeded constitution | **Grants + owner-as-constitutional-author** (ADR-386 D4) + an optional operator-authored charter — no gate, no seed |
| Ground-truth (Axiom 8), DP24 stewardship, DP30 standing obligation | Workspace judgment substrate, the Reviewer's | **Park with Altitude 3** (ADR-382 §3's decided relocation, FOUNDATIONS-annotated in v9.16) — relocated, not deleted |
| Chats/lanes/shell state | (already done) | Member-experience scope — ADR-407 ✓ unchanged |
| Connectors | (already right) | Workspace peripherals, personal credentials — ADR-407 D5 ✓ unchanged |
| Filesystem roots | Six seat-shaped semantic roots | The re-founding endpoint: **meaning folders + attribution metadata + grants**; the topological residue = the grant/floor reads + `system/` + the per-agent principal-homes (exactly FOUNDATIONS v9.13's minimized DP25) |

The six roots were seat-shaped (`constitution/`, `persona/`,
`governance/` all describe ONE judgment entity's anatomy); per-agent
homes + pure genesis dissolve the reason most of them existed at the
workspace root. Live-workspace migration is a one-shot with receipts
(small N); new workspaces are born pure.

## 8. Deletion ledger

Everything named here dies in its phase; a survivor found later is a bug,
not a judgment call. Code: `DEFAULT_STEWARD_MANDATE_MD` /
`DEFAULT_STEWARD_IDENTITY_MD` / `DEFAULT_STEWARD_PRINCIPLES_MD` + the
steward-marker recognition in `workspace_utils.is_skeleton_content` (D2);
`initialize_workspace` Phase-2 skeleton seeding, `program_slug` param,
Phase-5 fork call, signup `rotate_occupant` (D4); ADR-207/320-D4
workspace-level mandate gate (D4); `_TEMPLATE_HEADING_RE`,
`parse_active_program_slug`, `resolve_active_program_slug`,
`strip_program_marker_from_mandate`, `_populate_occupant_for_runtime`
(D5); `SYSTEMIC_AGENTS["thinking_partner"]` + the init Phase-1 agents-row
scaffold + the "System Agent" display collision (D3);
`routes/agents.py` Freddie roster synthesis + the `reviewer:%` feed
filter (D3); judgment fields from steward envelope assembly (D2). FE:
`FREDDIE_ROUTE`; "Reviewer" operator-facing copy (QueueBody, StandingBand,
AutonomyCard); the `reviewer-bubble` shape name; `reviewer_identity` /
`reviewer_reasoning` API field names (renamed with their backend in one
commit); stale `routes.ts` header comments. Docs: the pre-Freddie
THESIS §Vocabulary + Runtime Model, LAYER-MAPPING's superseded rows,
FOUNDATIONS Reviewer-row paths, agent-composition §3.2.1's
`reviewer_agent.py` pointers, occupant-contract doc's dead symbols.

## 9. Implementation phases

- **Phase A — finish the re-key spine** (precondition): scheduler
  wake-iteration unit off owner `user_id`; `bundle_reader.py` reads
  through `_scoped()`; `routes/integrations.py` sweep. Gate extends the
  ADR-373 family.
- **Phase B — system-agent purification** (D2 + D3): steward constants,
  envelope re-carve, `thinking_partner` retirement (migration 205+), the
  live bugs, FE System-Agent panes shrink. Persona-frame changes carry
  `api/prompts/CHANGELOG.md` entries; the phase closes with a Hat-B eval
  re-run (`probe_freddie_addressed_baseline` vs `CURRENT_BASELINE` —
  the envelope shrink must hold or improve the sentinels).
- **Phase C — pure genesis** (D4): init collapse, gate retirement, Setup
  re-derivation; acceptance = the member-on-empty-workspace walk.
- **Phase D+E — per-agent homes + program-as-hire** (D5 + D6, one coupled
  arc): agent-home layout, grant-row activation, envelope re-pointing,
  ADR-391 allocations, alpha-trader migration one-shot, FE dispatch
  re-keying.
- **Phase F — FE recomposition + vocabulary sweep**: the ADR-410 D4 debt
  paid; Home front page re-derives around members + activity + files
  (the constitution band's referent is gone — this satisfies ADR-412
  D7's evidence gate); StandingBand/JudgmentTrail become per-agent,
  dormant until a hire exists.

**CI ratchets shipped with their phases** (the ADR-209 pattern): (1) no
steward-file seeding; (2) no prose activation markers; (3) no
`user_id`-keyed substrate reads outside the grant/account layer; (4) no
"Reviewer" (or internal enums) in operator-facing FE strings; (5) every
new persistent store declares its DP35 scope in a manifest the gate
parses.

## 10. Canon cascade (Phase 0, this commit)

ESSENCE → v15 (D1 verbatim); FOUNDATIONS → v9.16 (DP24/DP30 two-order
annotation per ADR-382 §3 — production accountability relocates to the
persona agent, stewardship accountability to the system agent; Axiom 8
relocation note; Axiom 2 member-table correction — management seat +
judgment seats, live paths); THESIS rewrite (the four commitments
re-derived in the altitudes world — the thesis survives, its runtime
model catches up); LAYER-MAPPING rewrite (three altitudes replace the
two-class table as the authoritative taxonomy); GLOSSARY (program =
hire, activation record = grant row, steward-files-as-kernel-constants);
agent-composition §3.2.1 re-pointed (`freddie_agent.py`, per-agent
partition); reviewer-occupant docs' dead symbols corrected; CLAUDE.md
corrections (`freddie:` attribution, `minimum_pace` gone, this ADR's
top-note).

## 11. What this ADR does NOT do

- **No Altitude-3 runtime build**: creation surface, trust clock,
  multi-agent arbitration, per-seat wake routing beyond N=1 stay
  ADR-382-deferred. This ADR ships the substrate + records layer only.
- **No pricing change**: ADR-396/409 stand; the connector gate suspension
  (ADR-404) stands.
- **No kernel-boundary breach**: programs still never modify the kernel
  (ADR-222); hire is additive.
- **No witness-model change**: ADR-405/407/410 attention + witness
  derivations are consumed as-is; per-agent dials route through the same
  ADR-307 gate.
- **No federation**: the workspace stays the outermost unit (ADR-378).
- **No re-founding flag-day beyond genesis**: existing workspaces migrate
  per-phase with one-shot receipts; the full meaning-folder migration for
  legacy content remains sequenced under the keystone's own plan.
