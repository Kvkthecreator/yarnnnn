# ADR-320 — Workspace Permission Topology: Five Roots, One Gate, `access(2)` for the Agent OS

> **Status**: ACCEPTED (2026-06-05). Decisions D1–D9 RESOLVED. Ratified by KVK. Canon-first phase (P1: FOUNDATIONS DP25 + Axiom 1 subsection + v9.0 + THESIS two-poles sharpening + GLOSSARY five-region vocabulary) landing alongside this status flip. P2–P5 (code + bundles + eval suite + live migration) in progress.
> **Date**: 2026-06-05
> **Authors**: KVK, Claude
> **Upstream discourse**: [personified-judgment-seat-vs-task-harness-2026-06-05.md](../analysis/personified-judgment-seat-vs-task-harness-2026-06-05.md) (the commissioned-tool vs delegated-agent axis) + [personified-seat-canon-sketches-2026-06-05.md](../analysis/personified-seat-canon-sketches-2026-06-05.md) (the canon amendments this enables).
> **Dimensional classification**: **Substrate** (Axiom 1 — filesystem topology) + **Identity** (Axiom 2 — person/operation/system orthogonality) + **Channel** (Axiom 6 — the lock IS the legible permission surface) primary.
> **Canon backing**: ADR-222 + Derived Principle 16 (literal OS framing) — this ADR *implements the agent OS's permission model*, correcting the filesystem toward the OS analogy it already committed to.
> **Amended by [ADR-366](ADR-366-autonomy-mode-as-execution-breadth.md) (2026-06-25)** — the five-root cut becomes six: `governance/` splits into the **GRANT** (`governance/`, `_autonomy` + `_budget`, locked-always) + the operating **CONTRACT** (`contract/`, `_preferences` + `_expected_output`, mode-governed). Execution breadth = the AUTONOMY mode, not a capability lock. The pure-prefix `_is_path_locked` property is preserved (a new root, not a per-file exception).

---

## The one-sentence thesis

**The directory a file lives in determines who may write it — for every caller class, derivable from the path prefix alone, with zero file enumeration.** Topology *is* the access-control policy. This is `chmod` / `access(2)` for the agent OS (Derived Principle 16): a 2D permission matrix of *caller-class × root*, expressed as the filesystem itself.

---

## Context — the gap

The workspace root mixes three orthogonal semantic classes inside one directory, so write-permission cannot be derived from the path. Receipts:

- **The impurity**: `context/_shared/` holds governance (`AUTONOMY.md`, `_token_budget.yaml` — the seat's own ceilings), constitution (`MANDATE.md`, `PRECEDENT.md` — operator intent), and operation (`BRAND.md`, `CONVENTIONS.md` — output-shaping) in one bucket. *No real OS puts `/etc/security/limits.conf`, `~/.config/app/`, and `~/Documents/` in one directory.*
- **The impure gate**: `_is_path_locked_for_reviewer` (`primitives/workspace.py:1305`) is `candidate in {enumerated file set}` — set-membership against a flat list (`DEFAULT_REVIEWER_WRITE_LOCKS`, 5 paths). Its docstring records that it *once* was topological (path_zones) and was collapsed to a list.
- **The pure gate already exists for one caller**: `_is_path_locked_for_mcp` (`:1333`) is `candidate.startswith(prefix)` over `DEFAULT_MCP_WRITE_LOCK_PREFIXES = ("review/", "context/_shared/")` — synchronous, pure, "static subtree policy." The mechanism we want is shipped; it just isn't used for the seat, because the locked files aren't under one prefix.

This violates an orthogonality the axioms already declare (Axiom 1: identity manifests through filesystem; Axiom 2: identity orthogonal to mechanism) and the OS framing already commits to (Derived Principle 16: literal kernel/userspace/permissions).

---

## Decision — five roots, one gate

### The five roots (each is exactly one semantic class; the class is the directory name)

```
/workspace/
├── governance/     OPERATOR-ONLY ceilings the seat runs under but cannot set.
│                     AUTONOMY.md + _autonomy.yaml (delegation ceiling),
│                     _token_budget.yaml (compute ceiling),
│                     _pace.yaml (trigger budget), _preferences.yaml (cadence budget)
├── constitution/   OPERATOR-authored intent the seat AMENDS; read by ALL agents.
│                     MANDATE.md, PRECEDENT.md  (PURE INTENT — no IDENTITY; see
│                     operator-identity collapse note below)
├── persona/        THE SEAT — how it reasons + its own trail. Occupant-agnostic.
│                     IDENTITY.md (the operator's judgment embodied — absorbs the
│                       legacy operator operating-posture file), principles.md
│                       (+_principles.yaml),
│                     judgment_log.md, OCCUPANT.md, handoffs.md, calibration.md,
│                     standing_intent.md
├── operation/      THE WORK the agent operates on/produces. Many writers.
│                     BRAND.md, CONVENTIONS.md, _voice.md (D8), specs/, reports/,
│                     operations/, {domain}/ accumulated context (+ _money_truth.md etc.)
└── system/         ORCHESTRATION runtime accumulation. Not Identity-bearing (Axiom 2).
                      awareness.md, _playbook.md, notes.md, _schedule_index.md,
                      _recent_execution.md
```

### The one gate (`access(2)` for the agent OS)

`_is_path_locked_for_reviewer` + `_is_path_locked_for_mcp` **collapse into one** `_is_path_locked(caller_class, path)` — a per-caller prefix table, no filenames:

| Root | operator | reviewer (seat occupant) | domain agent / specialist | yarnnn:mcp (foreign) | system:* |
|---|---|---|---|---|---|
| `governance/` | **w** | r | r | — | — |
| `constitution/` | **w** | **w** (self-amends) | r | — | — |
| `persona/` | **w** | **w** (own seat) | r | — | seat-trail writes only¹ |
| `operation/` | **w** | **w** | **w** (domain-scoped²) | **w** (commons) | **w** |
| `system/` | — | — | — | — | **w** |

¹ `calibration.md` is written by the deterministic reconciler (`system:outcome-reconciliation`) — the one system-write into `persona/`; everything else in `persona/` is seat-written. This is the single cross-class write and it is *append-to-a-named-file*, not arbitrary; encoded as a path exception in the reconciler's caller, not a hole in the prefix rule (see D6).
² domain-scoping: an agent assigned `operation/{domain}/` writes only its own domain subtree — `chown` per directory (D9).

**Every cell is derivable from `(caller_class, top_level_root)`. No filename appears in the permission logic.** That is the axiomatic property: the lock IS the topology.

Derived per-caller **locked-from** prefix sets (what the gate actually stores):
- **reviewer**: `{governance/, system/}` (+ the `persona/calibration.md` reconciler-write handled at the reconciler's own caller)
- **yarnnn:mcp**: `{governance/, constitution/, persona/, system/}` (writes only `operation/`)
- **domain agent / specialist**: `{governance/, constitution/, persona/, system/}` + `operation/{not-my-domain}/`
- **system:***: `{constitution/, persona/* except calibration, operation/ is allowed}` — system writes `system/` + `operation/` (reconciler + cleanup) + the one `persona/calibration.md`
- **operator**: locked-from `{system/}` only (operator doesn't hand-edit orchestration runtime state)

---

## Resolved decisions

### D1 — Region topology: FIVE ROOTS (resolved)
Rejected: new single `constitution/` root (D1-A) — would fragment person-substrate into a third home. Rejected: split-inside-`context/_shared/` — leaves the cut nested under an ambiguous `context/` name (impure). **Resolved: five top-level roots**, each one semantic class, because (a) it makes the root itself the taxonomy, (b) it makes the lock pure-prefix for *every* caller (the table above), (c) it matches the OS analogy better than the status quo (see "OS mapping"). `context/` is dissolved as a root: `context/_shared/` splits across governance/constitution/operation; `context/{domain}/` moves under `operation/{domain}/`.

### D2 — PRECEDENT's side: CONSTITUTION (resolved)
PRECEDENT is operator-authored durable interpretation, read by all agents, that the seat amends over tenure. Same class as MANDATE → `constitution/`. (It is read-to-judge, but so is MANDATE; the distinguishing axis is reader-set + amend-rights, not "judge vs work," and on that axis it is constitution, not persona — persona is *occupant-rotating*, PRECEDENT *survives rotation*.)

### D2b — Operator-identity collapse: COLLAPSE INTO persona/IDENTITY.md (resolved, refinement 2026-06-05)
**Surfaced during P2 by the question "is IDENTITY constitution?"** — it is not. The legacy `context/_shared/IDENTITY.md` is the operator's *operating posture* ("process-first trader, I value discipline over outcomes, I use systems to constrain my bad habits") — reasoning-character, NOT intent (constitution) and NOT output-shaping (operation). It is the **same KIND** as the seat persona (`review/IDENTITY.md`, "Simons-style, numbers-first"). Per Axiom 2 (the operator is one principal with two runtime embodiments), the operator's posture and the embodied judge persona are *the same reasoning-character described twice*. Singular-implementation: keeping both is a dual representation. **Resolution: collapse.** `context/_shared/IDENTITY.md` is DELETED; `review/IDENTITY.md` becomes `persona/IDENTITY.md`, the singular home for "how this operator's judgment reasons." Consequences: `constitution/` is pure intent (MANDATE + PRECEDENT, no IDENTITY); the hard-gate required region (D4) is `constitution/MANDATE` + `persona/IDENTITY` + `persona/principles`; `InferContext` identity-inference targets `persona/IDENTITY.md` (persona root) while brand-inference targets `operation/BRAND.md` (operation root) — a clean two-root split. Migration: the two legacy IDENTITY files MERGE into one `persona/IDENTITY.md` (not two relocations).

### D3 — Lock topology: PURE PER-CALLER PREFIX, ONE FUNCTION (resolved)
`DEFAULT_REVIEWER_WRITE_LOCKS` (flat list) + `DEFAULT_MCP_WRITE_LOCK_PREFIXES` (prefix) → **deleted, replaced by** one `CALLER_WRITE_POLICY` prefix table + one `_is_path_locked(caller_class, path)`. Singular implementation: two divergent lock functions collapse to one. The governance ceiling that *was* the wrinkle (seat amends its constitution but not its ceiling) dissolves because the ceilings now live in their own root (`governance/`) — `startswith("governance/")` is the whole rule, no sub-prefix, no exception.

### D4 — Hard-gate: `constitution/` + `persona/` non-empty (resolved)
Generalizes ADR-207's MANDATE gate. The workspace cannot dispatch work (create recurrences / fire invocations) until `constitution/MANDATE.md` AND `persona/IDENTITY.md` + `persona/principles.md` are non-skeleton (reuse `workspace_utils.is_skeleton_content`). `governance/` defaults are bundle/kernel-seeded (not operator-gated — sensible ceilings ship). `operation/` empty is *legal and meaningful* — it signals "agent authored, no operation attached" (the bare-workspace two-halves state, ST-2). One aggregate gate function, not per-file.

### D5 — Fork compatibility: PRESERVED INVARIANT (resolved, regression-gated)
`fork_reference_workspace`'s three-way branch (`write_new` / `write_refresh_skeleton` / `skip_operator_authored_prose`) writes to new paths; behavior identical. P5 gate asserts the branch is intact across the move.

### D6 — Bare-workspace framing + the one cross-class write (resolved)
Bare workspace = populated `constitution/` + `persona/`, empty `operation/`, kernel-default `governance/`, minimal `system/`. "Onboarding" dissolves into "author the two required roots." The single cross-class write (`system:outcome-reconciliation` → `persona/calibration.md`) is encoded at the reconciler's caller as a *named-path* permission, NOT as a prefix hole — preserving "no filename in the prefix rule" by keeping the one exception in the *writer's* identity scope, where it is auditable. D8 guardrail: "front-load the persona" = write `persona/` + `constitution/` substrate, NEVER the system frame (Derived Principle 22).

### D7 — Naming (de-name "Reviewer"): SCOPED OUT (deferred to its own ADR)
This ADR uses "Reviewer"/"seat"/"persona" as-is. The de-naming (claim settled in discourse: name the detachment, not the review function) is a separate high-blast-radius ADR (DB enum slugs, routes). Named here so it's known-intentional. **`persona/` as a directory name is chosen to be de-name-compatible** — it denotes the detached judge regardless of what the entity is eventually called.

### D8 — Persona-AND-operation files (`_voice.md` class): OPERATION (resolved)
Files that shape both the judge's reasoning and the output (`_voice.md`, future style files) land in `operation/` — they shape the work-output. The *judgment about* them ("write in this voice; defer if voice drifts") is a rule in `persona/principles.md` (per agent-composition.md §3.2.1 four-field rule shape). **No dual mention**: the voice content lives once in `operation/_voice.md`; the rule-about-voice lives once in `persona/principles.md`; neither restates the other.

### D9 — One persona, N operations: CONFIRMED (resolved)
One `persona/` per workspace (one judgment seat), many `operation/{domain}/`. A single judge spans all operations — matches today's one-seat-per-workspace model + Axiom 2 (one systemic Reviewer). Multi-domain operators (trade + write) get one persona judging both, domain-scoped `operation/` subtrees `chown`'d to assigned agents. Per-domain sub-seats are explicitly rejected — they would fracture the judgment seat (anti-canon vs THESIS Commitment 2's *durable* seat).

---

## OS mapping (Derived Principle 16 — the framing is literal)

| Root | OS counterpart | Permission analog |
|---|---|---|
| `governance/` | `/etc/security/limits.conf` + cgroup/ulimits | root-owned; the process reads its limits, cannot raise them |
| `constitution/` | the app's own `~/.config/{app}/` it may rewrite | user+app writable (Claude-Code-edits-CLAUDE.md) |
| `persona/` | the process's own address space / working set | process owns it |
| `operation/` | `~/Documents/` + project working dirs | user + apps (the commons) |
| `system/` | `/var/lib/{service}` + `/tmp` | OS-managed runtime state |

The five-root split is **more OS-faithful than the status quo** (which co-locates `/etc`-class, `~/.config`-class, and `~/Documents`-class in `context/_shared/` — something no OS does). `_is_path_locked(caller, path)` is `access(2)`; the per-caller prefix table is the (owner, group, other) × (r,w) matrix. The OS analogy strongly *motivates* this topology (it makes the five-root shape the natural, low-surprise choice) — though it does not strictly *derive* it; D1 selected five over two live rivals (see the claim-tiering note below).

## Claim tiering (what is forced vs. chosen — added 2026-06-05 per parallel-review Finding 1)

"Axiomatic" was overclaimed in the framing. The honest decomposition, so future pushback on *cardinality* and *boundary placement* is not foreclosed by false necessity:

- **AXIOMATIC (forced by Axiom 1 + Axiom 2)**: that *a* filesystem boundary between identity-substrate and operation-substrate must exist. The 2-way person ⊥ operation cut is genuinely required — the filesystem cannot blur an orthogonality the axioms declare (discourse §2.3). This part is non-negotiable.
- **DERIVED-PRINCIPLE-GROUNDED (forced by DP16 OS-framing — a *chosen frame*, not an axiom)**: topological permission (`access(2)`); `system/` as a distinct non-identity root (Axiom 2 / ADR-257). Sound while we hold the OS framing; revisable if the framing is ever revised.
- **DESIGN CHOICE (selected, not forced — the ADR's own word is "Decisions")**: *exactly five* roots; the 3-way split of the person side (governance / constitution / persona — motivated by the write-permission gradient as an `access(2)` elegance goal); and the boundary placements D2 (PRECEDENT → constitution), D8 (`_voice.md` → operation), D6 (`calibration.md` cross-class write), D2b (operator-identity collapse → persona). These are defensible and stress-tested, but they are choices open to redesign without violating an axiom.

The cut is non-negotiable; the cardinality (2 / 3 / 5) and the boundary placements are design decisions. DP25's "topology IS the permission policy" claim is DP-grounded (the OS frame), not axiomatic — Axiom 1+2 force only the 2-way cut.

---

## Stress-test residue (carried from discourse, recorded so it isn't re-litigated)

- **Multi-domain (one persona / N operations)** — handled by topology (D9); surfaces the product fact that one judge spans operations. Accepted.
- **Human occupant** — `persona/` is occupant-agnostic (Derived Principle 14); human-filled seat writes the same files. ✅
- **Bare workspace** — empty `operation/` is the legible signal of the agent-authored-no-operation state. Strengthened, not strained. ✅
- **Cold-start residue** (first high-stakes verdict at operation-attach) — unchanged by this ADR; stays defer-to-human + cold-start `principles.md` (discourse §7).

---

## Scope / blast radius (this is a MAJOR ADR — ADR-217/ADR-231 class)

> **Scope amendment (2026-06-05, post-ratification impact scan).** An exhaustive codebase sweep (Explore agent, 400+ references mapped) surfaced two categories the original 9-point estimate underweighted, now folded in as points 10–11:
> - **Point 10 — Frontend is a first-class path consumer (~40 hardcoded refs).** `web/lib/content-shapes/{autonomy,pace}.ts` *write* to `_autonomy.yaml`/`_pace.yaml` via `writeShape`; `web/lib/reviewer-persona.ts` reads `review/IDENTITY.md`; `web/components/settings/WorkspaceSection.tsx` holds a hardcoded path-map; route pages (`mandate/`, `identity/`, `autonomy/`, `principles/`, `pace/`, `files/`, `settings/`) + components (`ContentViewer`, `HomeHeader`, `KernelJudgmentTrail`, `PrinciplesCard`, `AuthorHero`) reference old paths. The FE must migrate in lockstep (CLAUDE.md §5 render-parity discipline) or the cockpit reads moved files and silently renders empty.
> - **Point 11 — Duplicate-constant collapse (`conventions.py:222-224`).** `REVIEW_IDENTITY_PATH` / `REVIEW_PRINCIPLES_PROSE_PATH` / `REVIEW_PRINCIPLES_YAML_PATH` are *redefined* in `conventions.py` with `/workspace/`-absolute values — a second source of truth that violates singular-implementation. P2 collapses these into the single `workspace_paths.py` source (re-export, not redefine). Also: `alpha_trader.py`, `daily_pnl_email.py`, `risk_gate.py`, `workspace_guide.py` hold module-local hardcoded path constants (`_REGIME_PATH`, `MONEY_TRUTH_PATH`, `RISK_MD_PATH`, etc.) that must import from the source.
>
> **Immutable-history note**: applied SQL migrations (156, etc.) contain hardcoded old paths — these are NOT edited (migration history is immutable). Live data they wrote is moved by the P3 runtime migration script, not by editing migrations.


1. **`workspace_paths.py`** — all `SHARED_*` / `MEMORY_*` / `REVIEW_*` / `SPECS_*` constants re-rooted to the five roots. `DEFAULT_REVIEWER_WRITE_LOCKS` + `DEFAULT_MCP_WRITE_LOCK_PREFIXES` → one `CALLER_WRITE_POLICY` table.
2. **The gate** (`primitives/workspace.py`) — `_is_path_locked_for_reviewer` + `_is_path_locked_for_mcp` → one `_is_path_locked(caller_class, path)`. (Singular implementation: two functions deleted, one created.)
3. **Wake envelope** (`reviewer_envelope.py` + `reviewer_agent.py::_build_user_message`) — region-labeled headers read from new paths; headers can name the root (`## constitution/MANDATE.md`).
4. **Persona-frame minimal prompt** (`reviewer_agent.py::_compute_minimal_frame`) — lock language collapses to one sentence: *"you own everything except `governance/` and `system/`."* This SHRINKS the frame (composes with Derived Principle 22; no file enumeration in prose).
5. **The fork** (`programs.py`) — new paths; three-way branch preserved (D5).
6. **`_workspace_guide.md`** (ADR-281 substrate pedagogy) — teaches the five regions (single home for the pedagogy; the frame does not restate it — no dual mention).
7. **All readers** — `working_memory` (compact index + `_classify_activation_state` → hard-gate D4), `review_policy` (loads governance + persona), task pipeline (`gather_task_context`), revisions/read primitives, every bundle reference-workspace (alpha-trader + alpha-author + reference bundles).
8. **Docs** — FOUNDATIONS Derived Principle 25 + Axiom 1 subsection + version bump (v9.0); agent-composition.md §3.2 + §4.3 (placement invariant gains the region axis); reviewer-seat-substrate.md (seat = `persona/`); GLOSSARY (five-region vocabulary — the single vocabulary home); THESIS two-poles sharpening; `api/prompts/CHANGELOG.md`.
9. **Migration** — live workspaces (kvk + alpha-trader-2) path-migrated via revision-chain-preserving move (`write_revision` with `authored_by="system:adr320-migration"`). `research/mandate.md` (vestigial, no code reader) deleted.

**Singular-implementation / no-dual-mention discipline (this ADR's own constraint):** each file lives under exactly one root; each rule has exactly one home (voice-content in `operation/`, voice-rule in `persona/principles.md`, region-pedagogy in `_workspace_guide.md`, lock-logic in one `_is_path_locked`); the five-region vocabulary is defined once (GLOSSARY) and referenced, never restated. The migration *moves*, never *copies*. Two lock functions become one. Frame lock-prose becomes one sentence.

---

## Implementation phases

1. **P1 — Ratify + canon-first.** Operator sign-off. Then DP25 + THESIS sharpening + GLOSSARY five-region vocabulary land (citing this ADR). Axiom 1 subsection on permission-topology.
2. **P2 — Path constants + gate collapse.** `workspace_paths.py` re-root + `CALLER_WRITE_POLICY`; `_is_path_locked` unification (delete the two old functions). Unit-test the prefix table per caller.
3. **P3 — Writers + fork.** Fork to new paths (D5 branch preserved); reconciler `persona/calibration.md` named-path write (D6); migration script for live workspaces.
4. **P4 — Readers + envelope + frame.** Envelope headers, frame lock-sentence collapse, working_memory hard-gate (D4) + activation-state, review_policy, task pipeline, bundle reference-workspaces.
5. **P5 — Doc cascade + gate.** agent-composition.md, reviewer-seat-substrate.md, FOUNDATIONS version bump, CHANGELOG. Regression gate `api/test_adr320_permission_topology.py`: (a) every file resolves to exactly one root; (b) `_is_path_locked` derives every caller×root cell with no filename; (c) governance unwritable by reviewer/mcp/agent; (d) fork three-way branch intact; (e) hard-gate blocks dispatch on empty constitution/persona; (f) `operation/` empty is legal; (g) no live reader references old paths (grep gate).
