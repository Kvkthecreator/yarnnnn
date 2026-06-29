# ADR-387 — Agent governance lives on the agent's pane (Freddie absorbs the seat's settings out of Workspace Settings)

> **Status**: **Proposed** (2026-06-29). Doc-first. Channel-dimension (Axiom 6) — pure surface/IA reshape: it **moves** where existing panes render (from the `workspace-settings` surface onto the `?agent=freddie` agent-detail surface); it does NOT change substrate, paths, primitives, schema, routes, or the read/write gate. No new component logic — the existing `SettingsPaneShell` + the `workspace-concepts/*Card` components re-mount on the agent surface. The move is a **relocation, not a copy** (Singular Implementation — Workspace Settings *loses* each pane the agent pane gains).
> **Date**: 2026-06-29
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: live screenshot-walk of `/setup?...&workspace-settings.pane=expected-output` (2026-06-29). Operator read: *"the recent refactor related to system agent Freddie's evolution from the reviewer agent requires the workspace-settings panes and information closely integrated to the workspace itself be rooted out of here and into the agent-specific pane. The existing reviewer/agent surface needs to house the scope — identity, autonomy, principles, expected output. The current workspace identity then needs to be revisited from its fundamental concept, and that side-discussion dictates where it is housed. The same goes for Program, but Program will probably need its own scoped ADR — for now leave it in Workspace Settings but document the separate scope."*
> **Builds on**: [ADR-381](ADR-381-freddie-the-rung-1-substrate-steward.md) (Freddie = the named Rung-1 system agent / substrate steward — the *concrete, first-class entity* this ADR's surface move requires) + [ADR-383](ADR-383-the-consistent-agent-framework-and-mandate-as-purpose.md) (the consistent agent framework — every agent is constituted by persona + principles + MANDATE + governance/contract; the agent IS the workspace's installed agent) + [ADR-320 D2b](ADR-320-constitution-region-topological-cut.md) (operator-identity already collapsed into `persona/IDENTITY.md` — there is no separate workspace-identity file to move) + [ADR-366](ADR-366-autonomy-mode-as-execution-breadth.md) (the `governance/` GRANT vs `contract/` CONTRACT root split this ADR's grouping mirrors).
> **Re-affirms**: [ADR-251](ADR-251-system-agent-reviewer-first-class-surfaces.md) §"Why Autonomy + Principles belong under the Reviewer" — *"Autonomy is the operator's delegation to the [agent]. Principles is the [agent]'s judgment framework. Both belong to the [agent] entity, not to the system surface."* ADR-251's thesis was correct; it was reversed by ADR-297 partly because its host entity ("System Agent") had **no real identity backing** (ADR-272's audit). ADR-381/383 supplies the missing foundation: Freddie is a concrete, identity-backed, first-class agent. This ADR restores ADR-251's thesis on that foundation.
> **Supersedes (surface only)**: [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) D-Reviewer-shrink (which dissolved the Reviewer's Autonomy/Principles tabs into atomic per-substrate surfaces and shrank the agent page to "Identity, Capabilities, Activity") + the [ADR-340](ADR-340-operator-experience-model.md)/[ADR-341](ADR-341-two-settings-doors.md) consolidation that re-homed those atomic surfaces into the **Workspace Settings** `SettingsPaneShell`. The grouped-pane *shell* (ADR-341) is preserved and reused; what moves is **which surface hosts the agent-scoped groups.**
> **Preserves**: the Singular-Implementation invariant ADR-297 fought for (no two-surfaces-one-substrate) — by making this a **move, not a copy**; the seat≠occupant boundary (ADR-315 — this moves *occupant settings* presentation, touches no seat machinery); the read/write gate (ADR-307/320/366 — `governance/` stays operator-only-authored, `persona/` stays the agent's, `contract/` stays mode-governed; **the surface move changes nothing about who may author what**).
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6) — presentation/IA only.

---

## 1. The problem (grounded in the walk)

Workspace Settings today presents **eight panes in four groups**:

| Group | Pane | Substrate root | Whose thing is it? |
|---|---|---|---|
| CONSTITUTION | Mandate | `constitution/MANDATE.md` | the operator's intent (why the agent exists) |
| CONSTITUTION | Identity | `persona/IDENTITY.md` (+ `operation/BRAND.md`, merged) | **the agent's** reasoning-character |
| CONSTITUTION | Principles | `persona/principles.md` | **the agent's** judgment framework |
| CONTRACT | Budget | `governance/_budget.yaml` | the operator's GRANT (spend ceiling the agent runs under) |
| CONTRACT | Autonomy | `governance/_autonomy.yaml` | the operator's GRANT (delegation ceiling the agent runs under) |
| CONTRACT | Expected Output | `contract/_expected_output.yaml` | the operator's CONTRACT (what the agent owes) |
| OPERATION | Program | `operation/` (activation state) | the program/bundle |
| ACCESS | Workspace Members | `principal_grants` | workspace access |

The framing is **"Workspace Settings"** — as if all eight are configuration of *the workspace*. But six of the eight are **about the agent**: who it is (Identity), how it judges (Principles), what it's permitted (Budget, Autonomy), and what it owes (Expected Output). Post-ADR-381/383 this is a category error: the workspace's installed agent is a concrete named entity (Freddie), and "how the agent reasons / what it's permitted / what it owes" is **the agent's settings**, not the workspace's.

The mismatch was *invisible* before ADR-381 because the agent was un-named — there was no "agent pane" for these to obviously belong to, so they piled onto a generic "Workspace Settings." ADR-381 named the agent and gave it a first-class detail surface (`?agent=freddie`). That makes the right home obvious: **the agent's settings go on the agent's pane.**

This is not a new claim. **ADR-251 made it in 2026-05** — Autonomy and Principles belong under the agent, not the system surface — and was reversed (ADR-297) because the host entity had no identity backing. ADR-381/383 removes that objection.

## 2. The boundary — what is "agent-scoped" vs "workspace-scoped"

The ADR-320 five-root + ADR-366 grant/contract split already draws the line in the *substrate*; this ADR follows it to the *surface*. Three roots describe the agent; two describe the workspace around it:

| Root | What it is | Agent-scoped? |
|---|---|---|
| `persona/` | the agent's reasoning-character + judgment rules (`IDENTITY.md`, `principles.md`) | **yes — it IS the agent** |
| `governance/` | the GRANT — authority + spend the agent runs *under* but cannot set (`_autonomy.yaml`, `_budget.yaml`, `AUTONOMY.md`) | **yes — it is *the agent's* operating permission** (operator-authored, agent-honored) |
| `contract/` | the CONTRACT — what the operator declares the agent *owes* + prefers (`_expected_output.yaml`, `_preferences.yaml`); agent-honored, mode-governed | **yes — it is *the agent's* output contract** |
| `constitution/` | pure intent — *why* the agent exists (`MANDATE.md`, `PRECEDENT.md`) | **no — the operator's purpose declaration, the workspace's reason for being** |
| `operation/` | program activation + output (`Program`, `BRAND.md`, specs) | **no — the program's** |

**Operator authorship is unchanged.** "Agent-scoped" is a statement about *what the pane is about*, not about *who may write it*. The operator still authors `governance/` (the agent cannot set its own ceiling — ADR-320/366) and `constitution/MANDATE.md`. Putting Autonomy on Freddie's pane does not let Freddie raise its own ceiling; it says "this is the delegation *to Freddie*, displayed where you think about Freddie." The gate (`_is_path_locked`) is untouched.

## 3. Decisions

### D1 — Six panes move to Freddie's agent surface; three stay in Workspace Settings

**Move to `?agent=freddie` (the agent-detail surface):**
- **Identity** (`persona/IDENTITY.md`) — *unmerge from BRAND first; see D3.*
- **Principles** (`persona/principles.md`)
- **Autonomy** (`governance/_autonomy.yaml`)
- **Budget** (`governance/_budget.yaml`)
- **Expected Output** (`contract/_expected_output.yaml`)
- *(already there)* **Capabilities** (`operation/specs/*`) + **Activity** (supervision) — the agent surface's existing tabs, folded into the new grouped nav.

**Stay in Workspace Settings:**
- **Mandate** (`constitution/MANDATE.md`) — the operator's intent / the workspace's reason for being. (Open question D5: is "Workspace Settings" with one constitution pane + Program + Members still the right *container name*? Deferred — Mandate is genuinely not the agent's, so it has a home regardless.)
- **Program** (`operation/`) — **its own scoped ADR needed (D4)**; left in place this pass.
- **Workspace Members** (`principal_grants`) — workspace access; genuinely workspace-level.

**This is a move, not a copy (Singular Implementation, the ADR-297 invariant).** Each moved pane is *deleted* from the `workspace-settings` `PANE_GROUPS` registry the moment it appears on the agent surface. No pane renders on both surfaces. Deep-links to the old `workspace-settings.pane=identity|principles|autonomy|budget|expected-output` redirect (ADR-308 pure-transport stub) to the agent-surface equivalent (`?agent=freddie&agents.tab=...`).

### D2 — Freddie's pane adopts the grouped-nav `SettingsPaneShell`, grouped by root-ownership

Freddie's detail surface grows from 3 flat tabs (Identity · Capabilities · Activity) to a grouped sidebar mirroring the substrate root structure — the same `SettingsPaneShell` (ADR-341) the surface is absorbing the panes *from*, so it is reuse, not a new shell:

```
Freddie — the system agent
── PERSONA          (persona/ — the agent itself)
   ◉ Identity         persona/IDENTITY.md
   ⚖ Principles       persona/principles.md
── GRANT             (governance/ — what it's permitted; operator-authored)
   ⛡ Autonomy         governance/_autonomy.yaml
   💳 Budget          governance/_budget.yaml
── CONTRACT          (contract/ — what it owes)
   ◎ Expected Output  contract/_expected_output.yaml
── OPERATION
   📐 Capabilities    operation/specs/*
── SUPERVISION
   📈 Activity        recent runs / wakes
```

The group labels (PERSONA / GRANT / CONTRACT) name the **root-ownership semantics** the operator should understand: PERSONA is the agent's own; GRANT is the ceiling you set that it runs under; CONTRACT is what you declared it owes. This makes the operator-authorship boundary legible *on the surface itself* (you can see that GRANT is yours-to-set, PERSONA is the agent's-to-evolve).

The components do not change — `IdentityBrandCard` (→ `IdentityCard`, D3), `PrinciplesCard`, `AutonomyCard`, `BudgetCard`, `ExpectedOutputCard`, `FreddieCapabilitiesPanel`, `FreddieActivityPanel` re-mount under the new groups. Tab param stays window-namespaced (`agents.tab=...`, ADR-358 D6).

### D3 — Unmerge Identity from Brand (forced by the move; Brand's home deferred)

The current Identity pane is `IdentityBrandCard` — a **merged** card reading BOTH `persona/IDENTITY.md` (the agent's) AND `operation/BRAND.md` (operator brand voice / output styling, consumed by *agents writing to the workspace*, **not** by Freddie). When Identity moves to Freddie's pane, the merge is a category smudge: BRAND is `operation/`-rooted output styling, not the agent's reasoning-character, and Freddie does not read it.

- **Unmerge.** `persona/IDENTITY.md` becomes a clean **Identity** pane on Freddie's PERSONA group (`IdentityCard`).
- **BRAND's home is deferred — its own rethink (operator decision).** `operation/BRAND.md`'s correct placement post-Freddie is genuinely open: is it agent output-styling, operator brand, or per-persona-agent (ADR-382)? This ADR does **not** decide it. Interim: the BRAND half stays in Workspace Settings (a thin `BrandCard` under a residual group, OR folded into the Program/Operation scope of D4). The unmerge is the only forced change; Brand's destination is a follow-on.

### D4 — Program stays in Workspace Settings this pass; its re-scoping needs its own ADR

Program (`operation/` activation) is **not** agent-scoped in the same clean way — it's the *program/bundle* layer (ADR-222: programs are applications running in userspace; the agent is the installed steward the program reconfigures). Where Program management belongs post-Freddie (Workspace Settings? a dedicated Program/App surface? the compositor's App-Store framing per ADR-338?) is a **separate scoped question** entangled with the bundle/activation model and BRAND (D3). 

**Decision: leave the Program pane where it is (Workspace Settings → Operation) this pass, and open a follow-on ADR** — *"Program/Operation surface scope post-Freddie"* — to decide its home together with BRAND and the residual-Workspace-Settings container question (D5). Documented here so the scope is named, not silently dropped.

### D5 — The residual "Workspace Settings" container — named, deferred

After D1, Workspace Settings holds Mandate + Program + Members — a constitution pane, an operation pane, an access pane. Whether "Workspace Settings" is still the right *container name/shape* for that residue (vs. e.g. folding Mandate near the agent as its purpose-declaration, Program into an App surface, Members into Channels-Access) is a presentation question best decided **after** the agent-pane move lands and the residue is concrete. Deferred to the D4 follow-on ADR. The move (D1–D3) does not depend on resolving it.

### D6 — Workspace identity is NOT re-founded — it was already collapsed (ADR-320 D2b)

The operator raised "revisit the workspace identity from its fundamental concept." The investigation found **there is no separate workspace-identity file to revisit**: ADR-320 D2b (2026-06-05) already DELETED the standalone `context/_shared/IDENTITY.md` and collapsed it into `persona/IDENTITY.md`, on exactly this reasoning — *"the operator's operating posture and the embodied judge persona are the same reasoning-character described twice"* (Axiom 2: one principal, two runtime embodiments). So "workspace identity" already lives in the agent's `persona/IDENTITY.md`; the only thing left to do is **the surface move** (D1), which this ADR makes. **No substrate re-founding; the concept was settled in ADR-320 D2b.** This decision records that finding so a future session does not re-open a closed question.

## 4. What this is NOT

- **NOT a substrate change.** No path moves, no file is created/deleted, no schema/migration, no primitive, no gate change. The same files render under a different surface header.
- **NOT a copy / dual surface.** Each moved pane is removed from `workspace-settings`; Singular Implementation (the exact invariant ADR-297 enforced) is preserved by relocation.
- **NOT a permission change.** Operator still authors `governance/` + `constitution/`; the agent still owns `persona/`; `contract/` stays mode-governed. Putting Autonomy on Freddie's pane does not let Freddie set its own ceiling.
- **NOT the Program decision.** Program + BRAND + the residual-container name are explicitly deferred to a follow-on (D4/D5).
- **NOT seat machinery.** This touches *occupant-settings presentation*; `review_proposal_dispatch` / `review_rotation` / `review_policy` / the `persona/` seat path are untouched (ADR-315 seat≠occupant).

## 5. Implementation scope (when ratified)

FE-only (+ optional thin redirect stubs):
- `web/app/(authenticated)/agents/.../AgentContentView.tsx` (`ReviewerDetail`/`FreddieDetail` branch) — adopt `SettingsPaneShell` with the D2 grouped nav; mount the moved cards.
- `web/app/(authenticated)/workspace-settings/page.tsx` — `PANE_GROUPS`: remove Identity, Principles, Autonomy, Budget, Expected Output; keep Mandate, Program, Members. Unmerge `IdentityBrandCard` → `IdentityCard` (Freddie) + interim `BrandCard` (Workspace Settings, D3).
- Redirect stubs (ADR-308) for the five moved `workspace-settings.pane=*` deep-links → `?agent=freddie&agents.tab=*`.
- No backend change (the API routes — `GET /api/workspace/file`, `/api/budget`, `/api/proposals`, `/api/agents/freddie/*` — are surface-agnostic and unchanged).
- Render parity (CLAUDE.md §5): FE-only; `tsc --noEmit` clean; no env/schema/service change.
- Doc cascade: `agent-composition.md` §3 (the agent surface now hosts the governance panes), `docs/design/WORKSPACE.md` (per-tab surface contracts), this ADR's status → Implemented.

## 6. Open follow-ons (named, not dropped)

1. **Program/Operation surface scope post-Freddie** (D4) — its own ADR; decides Program's home + the App-Store/compositor framing.
2. **BRAND.md placement** (D3) — folded into the D4 follow-on (agent output-styling vs operator brand vs per-persona-agent).
3. **Residual "Workspace Settings" container name/shape** (D5) — decided after the move lands.
