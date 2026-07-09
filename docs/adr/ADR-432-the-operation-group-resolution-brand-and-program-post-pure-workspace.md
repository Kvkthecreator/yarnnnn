# ADR-432 — The OPERATION Group Resolution: Brand and Program Post-Pure-Workspace

> **Status**: **Accepted** (2026-07-09, operator-ruled from a Workspace-Settings audit). This is the long-owed **ADR-387 D4 follow-on** ("Program/Operation surface scope post-Freddie") — it decides Brand's placement (D3) + Program's home (D4) + the residual-container question (D5), which ADR-387 named and deferred. **Partly doc-decision, partly a small correctness fix.**
> **Date**: 2026-07-09
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimension**: Channel (Axiom 6 — what the Workspace-Settings OPERATION group surfaces) + Substrate (Axiom 1 — whether `operation/BRAND.md` is a consumed input)
> **Relates to**: ADR-387 D3/D4/D5 (the deferral this resolves — Brand's home, Program's scope, the residual container), ADR-414 D5/D6 (the pure workspace — program-as-hire; a program is a hired Altitude-3 agent recorded as a `principal_grants` row installed into `agents/{slug}/`, NOT a constitution fork), ADR-419 (constitution is per-agent — moved mandate/identity/principles to `agents/{slug}/`), ADR-421 (the workspace has no constitution surface — deleted the workspace-level Constitution group), ADR-424 (the pure-OS filesystem — `operation/` is demoted from "the operation's canon root" to "Documents, a default work-home"), ADR-382 (persona-agent seats — the hired-agent roster this defers the Program fold to), ADR-380 §5 (build-when-demanded), ADR-320 (the topology lock — the region a gate must key on)
> **Amends**: ADR-387 D3/D4/D5 (resolves the three deferred questions), the Program pane's stale FE framing + gate (ADR-412 D3 comment), the Brand pane's interim status
> **Preserves**: the program-as-hire backend (ADR-414 D5 — fully migrated, untouched here), the `/agents` roster (ADR-297/412 — untouched; the fold is deferred), ADR-320 topology semantics (the gate fix aligns the FE to the region the hire actually writes)

---

## 1. Context — the audit finding

A Workspace-Settings audit (2026-07-09) examined the OPERATION group (Brand ·
Program), which the operator flagged as ambiguous "now that the codebase has
evolved to a pure-OS, agnostic, per-agent-constitution model." The audit
confirmed both panes are pre-ADR-414 artifacts the surrounding band stepped
around. Receipts:

**Brand** — `operation/BRAND.md` is **written but read by no live generation
path**. It is absent from `freddie_envelope.py` (the single canonical wake
assembly point), `lane_runner.py`, `dispatch_specialist.py`, `conventions.py`.
Its only readers (`working_memory.py::build_working_memory`,
`workspace.py::read_all`) have **zero production callers** (the former is
annotated "Zero production callers (only tests)"). The pane's tagline promises
"the brand voice writing-agents apply" — no agent applies it. ADR-387 D3
deferred Brand's home to "a D4 follow-on ADR"; **that follow-on was never
written** (this is it). Meanwhile ADR-419 relocated Brand's whole conceptual
family (mandate/identity/principles) to `agents/{slug}/` and ADR-421 deleted the
workspace constitution surface — **Brand is the un-swept sibling**, still at
workspace scope while its family emigrated per-agent.

**Program** — the backend is **fully migrated** to ADR-414's program-as-hire
model (`resolve_hired_program_slug` reads the hire grant; `activate` →
`mint_hire_grant` installs into `agents/{slug}/`; `deactivate` → `revoke`;
`parse_active_program_slug` deleted). But the **FE was left behind**: its
routing comment + drawer copy say activation "forks the constitution / writes
MANDATE/persona/governance seeds" (the deleted occupant-fork model), and it is
gated on `GrantGate region="constitution/"` — the **wrong region**, because the
hire writes into `agents/{slug}/` and ADR-421 removed the workspace
`constitution/` root entirely. And the singular workspace-level "Program"
concept is **redundant with `/agents`** (the plural roster of the same hire
rows).

## 2. Decisions

### D1 — Brand: the placement is per-agent, but consumption is decided FIRST

Of ADR-387 D3's three candidate homes (agent output-styling / operator brand /
per-persona-agent), the **per-agent output-styling** placement is the one
consistent with what ADR-419/421 did to Brand's siblings. But relocating a file
**no producing path reads** would just move a dead file. So the decision is
ordered:

- **D1a — Consumption is the prior question, and today the honest answer is
  "not load-bearing."** `operation/BRAND.md` reaches no generation prompt.
  Until a producing agent actually applies brand voice, Brand is a write-only
  promise the UI should not make.
- **D1b — Direction (ratified): brand voice is a HIRED AGENT's output-styling
  concern.** When it becomes load-bearing, it lives at `agents/{slug}/` (a
  per-agent output-styling file, e.g. `agents/{slug}/_voice.md` or a `BRAND.md`
  under the agent home), wired into that agent's producing envelope, and
  surfaced on the agent detail — following ADR-419, NOT on a workspace-level
  Operation pane. The workspace has no brand of its own for the same reason it
  has no constitution of its own (ADR-421).
- **D1c — Interim (this pass): the Brand pane's copy stops over-promising.**
  The tagline "the brand voice writing-agents apply" is corrected to reflect the
  honest state (operator-authored styling not yet wired to a producer), OR — the
  operator's call at implementation time — the pane + `DEFAULT_BRAND_MD` seed are
  retired outright (the cleaner honest endpoint, reintroducible per-agent when a
  hire needs it). **This ADR ratifies the direction; the retire-vs-reword choice
  is a bounded implementation decision recorded when the code lands.**

### D2 — Program: land the correctness fixes now; the fold is ADR-382's

The Program pane's backend is correct; only the FE framing + gate are stale, and
the structural fold is a deferred build.

- **D2a — Fix the gate (correctness).** `GrantGate region="constitution/"` →
  `region="agents/"` (`workspace-settings/page.tsx`). The hire writes into
  `agents/{slug}/`; ADR-421 removed the workspace `constitution/` root; the
  `agents/` GrantGate label already ships (ADR-419, `GrantGate.tsx:34`). Gating
  on a root the door's own comments say no longer exists is incoherent.
- **D2b — Reword the stale framing (accuracy).** The routing comment
  (`workspace-settings/page.tsx`) and the `ProgramLifecycleDrawer` copy that say
  activation "forks the constitution / writes MANDATE/persona/governance seeds"
  describe the DELETED occupant-fork model. Reword to the hire-grant model:
  activation **hires an agent** whose load-out installs into its own home
  (`agents/{slug}/`); deactivation **fires** it (revokes the grant).
- **D2c — The fold into `/agents` is the ratified DIRECTION, deferred to
  ADR-382.** Post-ADR-414 "hire a program" == "hire an Altitude-3 agent," and
  `/agents` is already the plural home for that. The singular workspace-level
  "Program" pane should ultimately fold into the roster (one data source, one
  model). BUT: the two surfaces draw from **disjoint sources** today — `/agents`
  reads the `agents` table (user-authored); a hired program is a
  `principal_grants` row + `agents/{slug}/` files with **no `agents` table row**.
  Folding therefore requires `list_agents` to synthesize hired-program cards from
  grants + a hire affordance on the roster — which **is the ADR-382
  persona-agent roster**, a name-only deferred build. And ADR-414's backfill
  found **zero live program workspaces** — there is no live data to fold today.
  Building it now would invert the build-when-demanded discipline (ADR-380 §5).
  **So: the fold is ratified as the endpoint and assigned to ADR-382; the
  workspace Program pane stays this pass (with corrected gate + framing) until
  the roster reconciliation ships.**

### D3 — The residual container (ADR-387 D5) — resolved: keep Workspace Settings

After this pass the OPERATION group holds Brand (interim) + Program (interim,
corrected). With Access (Members) + Billing, "Workspace Settings" remains a
coherent container: the workspace's operation-level configuration + who may
write it + what it costs. The ADR-387 D5 "is this the right container?" question
resolves to **yes for now** — the residue is coherent, and the two panes that
made it feel ambiguous (Brand, Program) are each on a named trajectory
(per-agent / ADR-382). No container rename.

## 3. What this is NOT

- **NOT a backend change to program activation.** ADR-414's hire-grant machinery
  is correct and untouched. Only the FE gate region + copy change.
- **NOT the Program→/agents fold.** That is ratified as direction, assigned to
  ADR-382, and explicitly NOT built here (zero live data; it is the deferred
  persona-agent roster).
- **NOT a Brand substrate move.** `operation/BRAND.md` does not relocate in this
  pass; D1 ratifies the per-agent DIRECTION for when it becomes load-bearing.
  The only Brand change this pass is honest copy (or retirement — impl choice).
- **NOT a new gate/schema/primitive.** D2a re-points an existing FE gate to an
  existing region label; no backend, no migration.

## 4. Implementation scope

FE-only, small:
- `web/app/(authenticated)/workspace-settings/page.tsx` — Program `GrantGate`
  `constitution/` → `agents/` (D2a); reword the `case "program"` routing comment
  to the hire model (D2b); correct the Brand pane tagline to stop over-promising
  (D1c) OR retire the Brand pane (operator's impl call).
- `web/components/library/ProgramLifecycleDrawer.tsx` — reword the fork-vocabulary
  copy ("forks", "post-fork content") to the hire/fire model (D2b).
- If Brand is retired (D1c option): remove the `brand` pane + case, and stop
  seeding `DEFAULT_BRAND_MD` in `orchestration.py` (a follow-on cleanup, not
  required for the copy-only path).
- No backend change; `tsc --noEmit` clean; Render parity trivially satisfied
  (FE-only).

## 5. Open follow-ons (named, not dropped)

1. **Program → /agents fold** (D2c) — assigned to **ADR-382** (the persona-agent
   roster: `list_agents` synthesizes hired-program grant cards + a hire
   affordance). Build-when-demanded; there is no live hired program today.
2. **Brand becomes load-bearing** (D1) — when a hired agent needs output styling,
   wire a per-agent `agents/{slug}/` voice file into that agent's producing
   envelope + surface it on the agent detail. Until then Brand is honestly
   inert (reworded) or retired.
3. **`DEFAULT_BRAND_MD` seed cleanup** — if Brand is retired (D1c), stop seeding
   the skeleton at genesis (`orchestration.py`).
