# ADR-229: Persona-Program Registry Unification — One Activation Path, One Set of Templates

> **Status:** Proposed 2026-04-28
> **Authors:** KVK, Claude
> **Supersedes:** `api/scripts/alpha_ops/scaffold_trader.py` (the parallel scaffold path — *deleted in this ADR's implementation*).
> **Amends:** ADR-226 (Reference-Workspace Activation Flow — extends the activation surface to alpha personas), ADR-223 (Program Bundle Specification — bundles become the *only* source of program-shaped substrate templates).
> **Related:** ADR-222 (OS framing — "workspaces don't have types; they run programs"), ADR-228 (cockpit substrate audit, the surfacing event for this ADR), ADR-207 (MANDATE.md as gate), ADR-217 (AUTONOMY.md substrate), ADR-194 v2 (Reviewer substrate).

---

## Context

YARNNN currently has **three independent registries** that each carry partial information about how a workspace gets shaped:

| Registry | Lives at | What it declares | What it does NOT declare |
|---|---|---|---|
| Persona registry | `docs/alpha/personas.yaml` | Alpha operator → user_id, workspace_id, platform, expected substrate invariants | Which **program** the persona is dogfooding |
| Program registry | `docs/programs/{slug}/MANIFEST.yaml` | Program identity, oracle, dependencies, capabilities, context_domains, task_types, phases | Which operators are running it |
| Program reference-workspace | `docs/programs/{slug}/reference-workspace/*.md` | Bundled substrate templates (canon/authored/placeholder per ADR-223 §5) | Operational scaffolding (platform connect, JWT, task creation) |

There's **no link** between (1) and (2,3). And — the load-bearing problem that triggered this ADR — there are **two parallel scaffolding paths** that write to the same workspace file paths from different sources:

| Path | Source | Caller | Status |
|---|---|---|---|
| Canonical | `docs/programs/{slug}/reference-workspace/*.md` | `services/workspace_init.py::_fork_reference_workspace` (signup with `program_slug` OR `POST /api/programs/activate`) | Verified correct, idempotent, three-tier (ADR-223 §5) |
| Parallel | Inline Python constants in `api/scripts/alpha_ops/scaffold_trader.py` (~1,046 LOC: `IDENTITY_MD`, `BRAND_MD`, `OPERATOR_PROFILE_MD`, `RISK_MD`, `REVIEWER_IDENTITY_MD`, `PRINCIPLES_MD`, `REVIEWER_AUTONOMY_MD`) + `docs/alpha/personas/alpha-trader/MANDATE.md` | `python scaffold_trader.py` (alpha harness only) | Brittle: bypasses the canonical fork, doesn't honor three-tier rules, content can drift from bundle reference-workspace |

The 2026-04-28 cockpit substrate audit (ADR-228 follow-up) surfaced the consequence: **kvk's workspace (alpha-trader-2 persona) was scaffolded by kernel defaults at signup, never had alpha-trader activated, and never had the parallel scaffold run either.** The MANDATE/AUTONOMY 404s the audit chased were a symptom — the disease is that the canonical activation path and the alpha harness path both exist and neither was invoked.

### Terminology canonization

This is also a terminology fix. Conversation drift in the design discourse used "kernel project type," "alpha workspace type," "alpha user account," "scaffolded workspace," etc. interchangeably. ADR-222 already declared the canonical OS framing. This ADR locks the vocabulary into `personas.yaml` + reference docs:

| Use this term | When you mean… |
|---|---|
| **Program** | Platform-shipped opinion about how an operation should be run (`alpha-trader`, `alpha-commerce`). Canonical. |
| **Program bundle** | The on-disk artifact that ships a program — `docs/programs/{slug}/`. |
| **Reference workspace** | The bundle's substrate template at `docs/programs/{slug}/reference-workspace/`. Forked into operator workspaces at activation. |
| **Operator** | Real human running a workspace. Includes both alpha personas and post-launch users. |
| **Alpha operator** (or **alpha persona** when referring to the registry row) | Operator we're using to dogfood a program end-to-end. Dogfooding state lives in `docs/alpha/personas.yaml`. |
| **Program-activated workspace** | A workspace that has activated a program (the bundle has been forked into it). Per ADR-222: workspaces don't have *types*; they *run programs*. |

**Banned terms** (do not use in code, docs, or commit messages going forward): "workspace type" (workspaces don't have types — they run programs), "alpha workspace" used to mean a *kind* of workspace (alpha is an *operator-status* property, not a workspace property), "scaffold trader" / "scaffold commerce" used as if these were dedicated programs (the unit is the program; alpha personas activate one).

---

## Decision

### D1 — `personas.yaml` declares the program each alpha operator runs

Add a single field to every persona row:

```yaml
- slug: alpha-trader
  program: alpha-trader      # NEW — the bundle this persona activates
  email: seulkim88@gmail.com
  user_id: 2be30ac5-b3cf-46b1-aeb8-af39cd351af4
  workspace_id: b7e1b9bc-ffb3-478e-bd05-dcae01a8a6b1
  platform: { kind: trading, ... }
  ...

- slug: alpha-trader-2
  program: alpha-trader      # same program, different operator
  ...

- slug: alpha-commerce
  program: alpha-commerce    # different program
  ...
```

The persona slug and the program slug are independent. Two alpha-trader personas can run the same `alpha-trader` program. A future alpha-commerce-2 can run `alpha-commerce`. This decouples **who is dogfooding** from **what they're dogfooding**.

`load_registry()` in `api/scripts/alpha_ops/_shared.py` validates `program` against `docs/programs/{slug}/MANIFEST.yaml` existence at load time. Personas with no `program` field, or a `program` field pointing at a missing bundle, fail load with a clear error.

### D2 — Bundle reference-workspaces become the *only* source of program-shaped substrate templates

Every program-shaped substrate file currently sourced from inline Python constants or alpha-specific markdown moves into the program bundle's `reference-workspace/`. After this ADR:

| File path under operator's `/workspace/` | Source after unification |
|---|---|
| `/workspace/context/_shared/MANDATE.md` | `docs/programs/alpha-trader/reference-workspace/context/_shared/MANDATE.md` (already exists, `tier: authored`) |
| `/workspace/context/_shared/AUTONOMY.md` | `docs/programs/alpha-trader/reference-workspace/context/_shared/AUTONOMY.md` (already exists, `tier: canon`) |
| `/workspace/context/_shared/IDENTITY.md` | `docs/programs/alpha-trader/reference-workspace/context/_shared/IDENTITY.md` (already exists, `tier: authored`) |
| `/workspace/context/_shared/BRAND.md` | `docs/programs/alpha-trader/reference-workspace/context/_shared/BRAND.md` (already exists, `tier: authored`) |
| `/workspace/context/_shared/CONVENTIONS.md` | `docs/programs/alpha-trader/reference-workspace/context/_shared/CONVENTIONS.md` (already exists, `tier: authored`) |
| `/workspace/review/IDENTITY.md` | `docs/programs/alpha-trader/reference-workspace/review/IDENTITY.md` (already exists, `tier: authored`) |
| `/workspace/review/principles.md` | `docs/programs/alpha-trader/reference-workspace/review/principles.md` (already exists, `tier: authored`) |
| `/workspace/memory/awareness.md` | `docs/programs/alpha-trader/reference-workspace/memory/awareness.md` (already exists, `tier: placeholder`) |
| `/workspace/context/trading/_operator_profile.md` | **NEW** — `docs/programs/alpha-trader/reference-workspace/context/trading/_operator_profile.md`, `tier: authored` (currently inline `OPERATOR_PROFILE_MD` in scaffold_trader.py) |
| `/workspace/context/trading/_risk.md` | **NEW** — `docs/programs/alpha-trader/reference-workspace/context/trading/_risk.md`, `tier: authored` (currently inline `RISK_MD` in scaffold_trader.py) |

The bundle gains 2 files; ~700 LOC of inline Python content moves to markdown files. **One source of truth** per file. Alpha-specific operator content (kvk's voice for alpha-trader-2 stat-arb persona, seulkim88's voice for alpha-trader-1) is *not* baked into the bundle — it's authored on-behalf via the activation conversation (ADR-226 Phase 2) or the alpha harness's post-fork step (D5).

### D3 — `_fork_reference_workspace` is the single fork primitive

Already true in code. This ADR makes it the **only** fork primitive; no caller writes to `_shared/`, `review/`, `memory/`, or `context/{domain}/` template files outside this primitive. Audited write sites:

| Caller | Status after this ADR |
|---|---|
| `services/workspace_init.py::initialize_workspace(program_slug=...)` Phase 7 | KEPT — canonical signup-with-program path. |
| `routes/programs.py::activate_program` (`POST /api/programs/activate`) | KEPT — canonical post-signup activation path. |
| `scripts/alpha_ops/scaffold_trader.py` substrate writes | DELETED — file replaced by the thin wrapper in D5. |
| Anywhere else writing program-shaped templates | NONE FOUND in audit; if any exist post-rebase, they fail D3 and must be deleted. |

### D4 — `personas.yaml` activation is `_fork_reference_workspace(persona.user_id, persona.program)` — full stop

The alpha harness's "activate this persona's program" operation is exactly:

```python
from services.workspace_init import _fork_reference_workspace

persona = registry.persona(slug="alpha-trader-2")
summary = await _fork_reference_workspace(
    client=service_client,
    user_id=persona.user_id,
    program_slug=persona.program,
)
```

No alpha-specific content. No inline templates. No bypass. The same primitive that runs at operator signup runs for alpha personas. After execution, `personas.yaml.expected.core_files` invariants check is trivially satisfied because the bundle's reference-workspace IS the source of truth for those files.

### D5 — `scaffold_trader.py` is replaced by a thin program-agnostic harness

The current 1,046-line `scaffold_trader.py` has three concerns conflated:

1. **Substrate scaffolding** (writing IDENTITY/BRAND/MANDATE/AUTONOMY/etc.) — moves to D4 path.
2. **Operational scaffolding** (specialist agent pre-creation, platform connect, JWT minting) — keeps but generalizes.
3. **Persona-specific operator content** (kvk's voice, seulkim88's voice for the alpha-trader program — currently the same inline content for both, which is itself a bug) — moves to per-persona override files (D6).

Replaced by `scripts/alpha_ops/activate_persona.py` (~150 lines) that takes one `--persona` flag and runs:

```
1. Load persona from personas.yaml; resolve persona.program.
2. Validate bundle exists at docs/programs/{persona.program}/.
3. Run _fork_reference_workspace(persona.user_id, persona.program).
4. Apply persona-specific overrides per D6 (if any).
5. Pre-create specialist agent rows the bundle's task_types reference.
6. Run platform connect for persona.platform.kind via existing connect.py.
7. Run verify.py invariants check; report.
```

`scaffold_trader.py` and `scaffold_commerce.py` (if/when exists) collapse into this one harness. The harness is **program-agnostic** — it works for `alpha-trader` and `alpha-commerce` because both go through the same fork primitive with their own bundle.

### D6 — Persona-specific operator content lives in `docs/alpha/personas/{slug}/overrides/`

Some persona-shaped content legitimately differs across alpha operators of the same program — kvk's stat-arb operating profile differs from seulkim88's Simons-style profile, even though both run `alpha-trader`. This is **operator content**, not program template content. After this ADR:

```
docs/alpha/personas/alpha-trader-2/overrides/
  context/_shared/MANDATE.md            # kvk's stat-arb mandate, overrides bundle template
  context/trading/_operator_profile.md  # kvk's signal definitions, overrides bundle template
```

The activate harness (D5) applies overrides as a Step 4: after the bundle fork (D4), iterate `docs/alpha/personas/{slug}/overrides/` and overwrite matching paths with `authored_by="operator:alpha-{slug}"` revisions. This preserves the on-behalf authoring kvk did for alpha-trader-2 stat-arb (currently in commit `bcd864c` as direct substrate writes) without polluting the program bundle with one operator's voice.

Personas with no `overrides/` directory just get the bundle template. Authoring on-behalf is opt-in per persona.

### D7 — `docs/alpha/personas/alpha-trader/MANDATE.md` deletes

This file is the orphan that currently feeds `scaffold_trader.py`. Its content has drifted from the bundle's MANDATE.md template and from kvk's actual on-behalf authored MANDATE. After this ADR it's strictly deleted; the canonical MANDATE template is the bundle's, and any persona-specific overrides go in D6.

`docs/alpha/personas/alpha-trader/BOOTSTRAP.md` is preserved — that's the operator runbook (ADR-226 companion doc), not template substrate.

### D8 — Bundle file inventory becomes a contract enforced in tests

After D2, the bundle's `reference-workspace/` directory is the contract for what every program-activated workspace gets. Add a test gate `api/test_adr229_bundle_substrate.py` that:

- Walks every program with `status: active` in `docs/programs/`.
- Asserts the reference-workspace contains the canonical substrate set declared in MANIFEST.yaml's `context_domains[].authored_substrate` field.
- For alpha-trader specifically: asserts the reference-workspace contains `_operator_profile.md` and `_risk.md` (the two new files shipped by D2).
- Asserts every persona in `personas.yaml` has a `program` field whose target bundle exists.

This makes drift between persona registry and bundle registry impossible to ship without a CI-visible failure.

---

## What this ADR does NOT do

- Does not change `_fork_reference_workspace` logic. That primitive is correct; it just hasn't been the only path until now.
- Does not change the cockpit four-face render. ADR-228's Commits 1-2 + substrate-stub fix are independent and orthogonal.
- Does not introduce a new primitive, new schema, or new database table. Pure file consolidation + registry linking.
- Does not ship the activation FE (ADR-226 Phase 2). The alpha harness's `activate_persona.py` is the operational equivalent for alpha personas; the FE for real operators is still ADR-226's deferred Phase 2.
- Does not solve the operational problem of "kvk's workspace currently has kernel-default MANDATE." That's resolved by *running* the new `activate_persona.py --persona alpha-trader-2` once after this ADR ships. Operational, not architectural.

---

## Why this is the right shape

The OS framing in ADR-222 says: workspaces don't have types; they run programs. The bug pattern this ADR fixes is what happens when *the system pretends otherwise*. `scaffold_trader.py`'s existence is the codebase's confession that "alpha-trader workspace" was treated as a *type* with its own scaffolding logic, parallel to the OS's actual program-activation primitive. That confession needed to become an ADR-amend, not a permanent dual path.

The deletion is the load-bearing part. After this ADR:
- Alpha personas activate programs the *same way* real operators will (when ADR-226 Phase 2 ships).
- New programs (e.g., post-`alpha-prediction` activation) require zero alpha-harness changes — just `program: alpha-prediction` in `personas.yaml` and a bundle at `docs/programs/alpha-prediction/`.
- Bundle drift becomes impossible: the bundle's reference-workspace is the source of every program-shaped substrate template, full stop.
- Substrate audit (the kind that surfaced ADR-228's 404s) becomes mechanical: walk one path, not three.

The terminology canonization is the second load-bearing part. The drift between "alpha workspace," "kernel project type," "scaffolded workspace" reflected real conceptual confusion that produced real architectural drift. Locking the vocabulary into the registries means future PRs can be reviewed against ADR-222's framing — not against whatever shorthand showed up in conversation that day.

The substrate-class consequence (your follow-up question): with one canonical activation path, the three substrate classes (authored / accumulated / synthesis) get cleaner empty-state semantics:

| Substrate class | Pre-ADR-229 ambiguity | Post-ADR-229 |
|---|---|---|
| **Authored** (MANDATE, AUTONOMY, IDENTITY, BRAND, principles, _operator_profile, _risk) | "404 might mean: signup didn't fork, or fork hit different code path, or operator hasn't authored yet" | "Skeleton-state = bundle template was forked but operator hasn't customized. 404 = activation never invoked. Two distinct cases, both legible." |
| **Accumulated** (`_performance.md`, `decisions.md`) | Same as before | Same as before — fixed by ADR-228 substrate-stub follow-up. Empty stub on first run; absent file = upstream broken. |
| **Synthesis** (`_performance_summary.md`) | Same as before | Same as before — already correct. |

ADR-228's substrate audit identified the cockpit-side fixes; ADR-229 identifies the *systemic upstream* fix that makes those cockpit-side fixes work consistently for every operator regardless of how they joined.

---

## Implementation plan

Atomic commits. Each green-state.

### Commit 1 — Bundle gains 2 new authored-tier templates

- Create `docs/programs/alpha-trader/reference-workspace/context/trading/_operator_profile.md` with `tier: authored` frontmatter. Content: extract `OPERATOR_PROFILE_MD` constant from `scaffold_trader.py:218-300` verbatim into the bundle file (it's already program-shaped template content, not persona-specific).
- Create `docs/programs/alpha-trader/reference-workspace/context/trading/_risk.md` with `tier: authored` frontmatter. Extract `RISK_MD` constant from `scaffold_trader.py`.
- Update `docs/programs/alpha-trader/MANIFEST.yaml` `context_domains.trading.authored_substrate` to include both new files.
- Manual verify that the bundle templates match what the playbook §3A.2-3A.3 declared.
- No code changes in this commit. Pure bundle additions.

### Commit 2 — `personas.yaml` gains `program` field; loader validates

- Add `program: alpha-trader` to alpha-trader and alpha-trader-2 rows.
- Add `program: alpha-commerce` to alpha-commerce row.
- Update `_shared.py::load_registry()` to require `program` field on every persona, validate bundle existence at load time.
- Update `personas.yaml` header comment with the new field's contract.
- No bundle changes in this commit. Pure registry linking.

### Commit 3 — `activate_persona.py` ships, replaces `scaffold_trader.py`

- New file `api/scripts/alpha_ops/activate_persona.py` (~150 lines) implementing D5.
- Calls `_fork_reference_workspace` directly (Step 3 of D5 sequence).
- Calls existing `connect.py` for platform connect (Step 6).
- Calls existing `verify.py` for invariants check (Step 7).
- DELETE `scaffold_trader.py` (1,046 LOC).
- DELETE `docs/alpha/personas/alpha-trader/MANDATE.md` per D7.
- Update `docs/alpha/OPERATOR-HARNESS.md` to reference `activate_persona.py`.

### Commit 4 — Persona-specific overrides directory + apply step

- Create `docs/alpha/personas/alpha-trader-2/overrides/` with kvk's stat-arb-specific MANDATE + operator_profile (extracted from commit `bcd864c`'s direct substrate writes, currently lacking a canonical home).
- `activate_persona.py` Step 4 implementation: walk overrides directory, write each file via `write_revision` with `authored_by="operator:alpha-{slug}"`.
- alpha-trader-1 and alpha-commerce don't get overrides directories (their content is generic enough to use bundle templates as-is).

### Commit 5 — Bundle substrate test gate + doc sync

- New `api/test_adr229_bundle_substrate.py` per D8.
- Update CLAUDE.md ADR-229 entry.
- Update `docs/alpha/E2E-EXECUTION-CONTRACT.md` to reference the unified activation path.
- Update `docs/programs/README.md` registry table with the persona-program linking convention.
- Update `docs/alpha/INDEX.md` with the canonical terminology table from this ADR's Context section.

### Operational follow-up (out of scope for this ADR's commits)

After Commit 3 ships and is verified green, run `python api/scripts/alpha_ops/activate_persona.py --persona alpha-trader-2` once against kvk's workspace. This forks the bundle templates into kvk's `/workspace/`, resolving the cockpit's MANDATE/AUTONOMY 404s surfaced by the ADR-228 audit. Same for alpha-trader-1 and alpha-commerce if their substrate has drifted.

---

## Test coverage

| Test | What it locks |
|---|---|
| `test_adr229_bundle_substrate.py::test_personas_link_to_existing_bundles` | Every persona row's `program` field resolves to an existing bundle with `status: active`. |
| `test_adr229_bundle_substrate.py::test_bundle_carries_canonical_substrate` | For each active program, every authored-substrate path declared in MANIFEST.yaml exists as a file in `reference-workspace/` with valid tier frontmatter. |
| `test_adr229_bundle_substrate.py::test_no_orphan_alpha_mandate` | `docs/alpha/personas/alpha-trader/MANDATE.md` does NOT exist (D7 deletion regression guard). |
| `test_adr229_bundle_substrate.py::test_no_parallel_scaffold` | `api/scripts/alpha_ops/scaffold_trader.py` does NOT exist (D5 deletion regression guard). |
| Existing `test_adr226_activation.py` | All 15 assertions still pass — `_fork_reference_workspace` logic unchanged. |
| Existing `test_adr225_compositor.py` | All 10 assertions still pass — compositor reads unaffected. |

---

## Consequences

**Net code change.** ~1,046 LOC deleted from `scaffold_trader.py`; ~150 LOC added in `activate_persona.py`; 2 new bundle files (~150 LOC of markdown templates extracted from inline Python). Net: **roughly -750 LOC, with the saved lines moving from inline Python to markdown templates** (where they belong).

**Net surface change.** Alpha harness operators run one command per persona instead of two (no separate scaffold step before connect). Persona registry doubles as program-activation declaration. Future programs require zero harness changes.

**What we accept.** The bundle's reference-workspace becomes a hard interface — adding a program-shaped substrate file requires a bundle PR, not an inline Python patch. This is the right tradeoff: substrate drift in production was the disease, and a stricter authoring surface for templates is the cure.

**What we don't accept.** A "scaffold for alpha but not for real operators" pattern after this ADR. If a real-operator path needs a particular activation behavior, it goes in `_fork_reference_workspace` or in `routes/programs.py::activate_program` — not in a parallel script. Same primitive, all callers.

**Rollback discipline.** The bundle's two new templates (Commit 1) are pure additions — they don't break anything if Commits 2-5 are deferred. If Commits 2-5 ship and turn out wrong, the rollback is to revert those specific commits — Commit 1 stands.

---

## Open questions

1. **Should `personas.yaml` move to `api/config/personas.yaml`?** It's loaded by Python; `docs/` is a strange home. Out of scope for this ADR — defer to a future cleanup if the load-from-docs pattern proves friction. Today the file is small and the pattern works.

2. **How does ADR-226 Phase 2 (real operator activation FE) interact with persona-specific overrides (D6)?** Real operators don't have an "overrides" directory — they author through YARNNN chat. The override mechanism is alpha-only by design. When a real operator runs alpha-trader, they get bundle templates and YARNNN walks them through customization conversationally. This ADR keeps those paths clean: real operators activate via FE → fork → YARNNN conversation. Alpha personas activate via harness → fork → overrides apply. Same fork primitive; different downstream authoring surfaces.

3. **What about future `_strategy.md`, `_universe.md`, etc. that show up?** They follow the same pattern: bundle ships them as `tier: authored` templates; persona-specific operators override via D6. The bundle is the contract; overrides are operator voice.

---

## Related

- ADR-222 — OS framing (the framing this ADR enforces in code + registries)
- ADR-223 — Program Bundle Specification (the spec this ADR makes the *only* source of program-shaped substrate)
- ADR-226 — Reference-Workspace Activation Flow (the primitive this ADR declares the canonical path for alpha and real operators alike)
- ADR-228 — Cockpit as Operation (the surfacing event — substrate audit found the parallel-path symptom)
- ADR-207 — MANDATE.md as primary-action gate (consumer of forked substrate)
- ADR-217 — AUTONOMY.md substrate (consumer of forked substrate)
- ADR-194 v2 — Reviewer layer (consumer of forked substrate)
- FOUNDATIONS Axiom 1 (Substrate) — the kernel rule this ADR enforces: one source of truth per substrate file
