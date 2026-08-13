# ADR-280: Substrate ABI — Bundles Are Libraries; the Reviewer Is the Librarian

**Status**: **Superseded by [ADR-281](ADR-281-substrate-canonical-substrate-only-prompts.md) (2026-05-15)**

> **Dissolution rationale (2026-05-15)**: ADR-280 reached its Phase 1 +
> dissolution + Stream A milestones (commits `7d3013b` + `43374cf` +
> `c7e1c84` + `3ebfb8e`). Two architectural revisions surfaced empirical
> falsifications during its lifetime: (1) genesis-by-Reviewer was
> empirically falsified by the Phase 1 migration on kvk's workspace
> (16 successive empty-content WriteFile calls); (2) the
> `ENVELOPE_SUMMARIZERS` registry shipped in Stream A was empirically
> derived as an Axiom 1 violation (kernel-side prompt-time computation
> producing state without substrate writes — same pattern Axiom 1
> fourth sub-clause names as a violation).
>
> Per Singular Implementation discipline ("delete boldly that which
> isn't true"), ADR-280 is superseded in full rather than revised in
> place. The body below is preserved as historical artifact for the
> discourse arc; the architecture is canonized in ADR-281, which derives
> the wake-envelope shape cleanly from the substrate-canonical-world
> axiom + the new Derived Principle 19 ("The kernel does not compute
> for the prompt"). ADR-281 preserves the correctly-derived parts of
> ADR-280 (library/librarian partition, six-role taxonomy, bundle
> MANIFEST as authority, lock policy 4-layer composition, workspace
> guide as bundle-shipped operator-canon) and revises only the
> summarizer machinery.
>
> All shipped commits (Phase 1, dissolution, Stream A preserved
> portions) remain canonical under ADR-281 — only the
> `ENVELOPE_SUMMARIZERS` + `_summarize_signal_files` portion of Stream A
> is revised. See ADR-281 §11 for the full discourse trail.

**Original Status**: Phase 1 Implemented (2026-05-15) — Stream A + Stream B in flight
**Date**: 2026-05-15
**Dimensional classification**: **Substrate** (Axiom 1) primary — kernel/program/operator authority over substrate topology. **Identity** (Axiom 2) secondary — library vs librarian partition. **Trigger** (Axiom 4) tertiary — librarian operates at every wake from the library it inherits at activation.

**Implements (extends)**: [ADR-222](ADR-222-agent-native-operating-system-framing.md) (OS framing — finishes Principle 16's "no kernel touch when adding a program" commitment at the substrate-paths layer), [ADR-224](ADR-224-kernel-program-boundary-refactor.md) (extends the boundary refactor from registries to substrate paths + persona pedagogy), [ADR-188](ADR-188-domain-agnostic-framework.md) (registries as template libraries — same principle at the substrate layer), [ADR-209](ADR-209-authored-substrate.md) (every write attributed and retained — load-bearing for bundle-fork attribution + operator/Reviewer revision), [ADR-275](ADR-275-introspection-cadence-reviewer-authored.md) (Reviewer authors its own Trigger dimension — extends to substrate-organization dimension via Clarify/ProposeAction), [ADR-277](ADR-277-feed-emission-policy.md) ("each event has one canonical home" — same rule at the substrate-pedagogy layer: each substrate concept has one canonical teaching surface).

**Amends**: [ADR-258 revised](ADR-258-reviewer-as-personified-chat-mode-operator.md) D9 (`DEFAULT_REVIEWER_WRITE_LOCKS` is kernel-universal-only; program-specific locks compose in from bundle MANIFEST `substrate_abi`), [ADR-276](ADR-276-reactive-trigger-envelope-governance-preload.md) (`reviewer_envelope.load_reviewer_governance_envelope` reads bundle MANIFEST via `bundle_reader` instead of hardcoding `context/{program}/*` paths), [ADR-205](ADR-205-primitive-collapse.md) signup workspace-init (kernel-default workspace guide is one more universal skeleton), [ADR-194 v2](ADR-194-reviewer-layer-and-impersonation.md) (Reviewer's `decisions.md` semantics tighten to single-writer judgment lineage; renamed `judgment_log.md` per §5).

**Supersedes**: the post-FOUNDATIONS-v8.4 `append_recurrence_fire` infrastructure-side blanket-write path in `services/reviewer_audit.py` + `services/invocation_dispatcher.py` (replaced by deterministic material-outcome gate per §5).

**Preserves**: FOUNDATIONS Axioms 1–9, Derived Principles 1–18, ADR-194 v2 Reviewer substrate (six canonical seat files unchanged), ADR-258 revised primitive surface (`REVIEWER_PRIMITIVES`), ADR-260 real-time Reviewer loop, ADR-261 recurrence model, ADR-265 `execution_events` as canonical forensic substrate.

---

## Revision: 2026-05-15 — Genesis-by-Reviewer dissolved; bundle ships the library

The first version of this ADR specified Reviewer-authored genesis at first wake — the Reviewer would author `_workspace_guide.md` from a kernel template + bundle's `substrate_abi` declaration in a Sonnet tool-loop. The Phase 1 migration against kvk's live workspace empirically falsified this design: 16 successive `WriteFile` calls landed with empty content; the model failed to thread a multi-KB structured prompt through its tool schema; attribution fell through to `yarnnn:chat` because no dispatch-layer injection was wired.

The architectural simplification, surfaced through the operator's library/librarian metaphor: **the bundle is the library; the Reviewer is the librarian.** The library — its structure, its shelves, its operating manual — exists *before* any librarian shows up. Bundles ship every authored canonical file (MANDATE, IDENTITY, principles, `_operator_profile.md`, `_risk.md`, `_recurrences.yaml`, and **the workspace guide itself**) at `reference-workspace/`. `services.programs.fork_reference_workspace` deterministically copies the library into the operator's workspace at activation. The Reviewer's role is to **read** the operating manual and **operate** within the library — not to author the library's substrate-pedagogy doc.

The "engine-jump-start" property survives via the deterministic fork: the Reviewer's first wake is structurally identical to its second wake — it reads `MANDATE.md`, `principles.md`, `IDENTITY.md`, `AUTONOMY.md`, `_workspace_guide.md`, perceives the substrate topology immediately, operates from substrate awareness. No special-case bootstrap, no LLM round to author the guide. Operational substrate (`research/` directories, `notes.md` patterns, `judgment_log.md` accumulation) emerges through Reviewer judgment + work over tenure — the librarian fills the library as the operation actually runs.

The rest of this ADR is written as if this had always been the architecture. The dissolution discourse trail lives in this Revision section + commit `43374cf` for anyone tracing the architectural learning; the body of the ADR canonizes only the current shape.

---

## 1. Context

### 1.1 The library / librarian partition

The OS framing (FOUNDATIONS Derived Principle 16, ADR-222) committed: kernel changes are sacred; programs do not modify the kernel; adding a program is purely additive. ADR-224 enforced this for three registries (`task_types.py`, `directory_registry.py`, `orchestration.CAPABILITIES`). This ADR extends the same discipline to the substrate-paths layer + persona pedagogy.

Under the OS framing, the substrate layer has two distinct roles, with distinct authorities:

| Role | Authority | Examples |
|---|---|---|
| **The library** | Kernel + program designer + operator | Bundle MANIFEST `substrate_abi`; kernel `workspace_paths.py` constants; bundle-shipped canonical files (MANDATE, IDENTITY, principles, the workspace guide); `workspace_init.py`; lock policy structure |
| **The librarian** | Reviewer (persona-bearing Agent per Axiom 2) | Reads the library's operating manual; operates within it; surfaces drift via Clarify; writes notes/reflections; renders judgment that accumulates in `judgment_log.md` |

**The library is built before the librarian shows up.** Activation deterministically forks the bundle's `reference-workspace/` (including the workspace guide) into the operator's workspace. The librarian's first wake reads the inherited library; subsequent wakes read the same inherited library plus whatever the librarian + operator have accumulated.

### 1.2 The drift this ADR closes

Audit of `api/` (excluding `__pycache__`, tests, `docs/programs/`) for program-domain path strings (`context/trading`, `context/commerce`, `context/defi`): **52 sites** in production code. Categorized by class:

| Class | Count | Closure path |
|---|---|---|
| 1 — Load-bearing kernel reads (substrate behavior) | 24 | Phase 1 + Stream A |
| 2 — Persona prose (pedagogical) | 9 | Stream A + Stream B |
| 3 — Cockpit FE routes | 9 | Out of scope (ADR-225 compositor) |
| 4 — Oneshot scripts (bundle-coupled) | 3 | None — bundle-coupled by intent |
| 5 — `workspace_paths.py::DEFAULT_REVIEWER_WRITE_LOCKS` | 4 | Phase 1 ✓ Closed |
| 6 — `reviewer_envelope.py` hardcoded reads | 3 | Stream A |

**Phase 1 closes 4 sites. Stream A closes ~22 more. Stream B is largely librarian-pedagogy work that doesn't itself close drift sites but unlocks Reviewer correctness against the kernel-cleaned library.**

The full enumerated catalog with file paths + line numbers + closing-stream assignment lives at §10 below.

### 1.3 What ADR-277 just canonized (load-bearing for this ADR)

Yesterday's ADR-277 ratified the rule of thumb at the feed-emission layer: *"Each event has one canonical home. The feed is for events whose canonical home is conversation."*

This ADR applies the same rule at the substrate-pedagogy layer: **each substrate concept has one canonical teaching surface. The bundle MANIFEST is the authority for substrate-ABI declarations. The workspace guide is the operator-and-Reviewer-readable narration of what the bundle declares + the universal kernel "how" prose. Persona prose, kernel constants, scattered docstrings — none of these are second canonical teaching surfaces; they are pointers at most.**

---

## 2. Decision

### D1 — The Substrate ABI: bundles declare their topology in MANIFEST.yaml

Bundle MANIFESTs declare a top-level `substrate_abi` block — the program's substrate-topology contract with the kernel. This is the **machine-readable authority** for everything program-shaped at the substrate layer. Schema:

```yaml
# MANIFEST.yaml — alpha-trader bundle (illustrative)
substrate_abi:
  schema_version: 1

  # Path zones the program contributes beyond the kernel-universal set.
  path_zones:
    - path: context/trading
      role: operator-canon
      purpose: per-instrument entities + signals + watched universe
      authored_files: [_operator_profile.md, _risk.md, _universe.yaml]
      accumulating_files: [_performance.md, _money_truth.md, _tracker.md]
      glob_zones: ["signals/*.yaml", "{TICKER}.yaml"]
    - path: context/portfolio
      role: operator-canon
      purpose: account-level state, performance, risk
      accumulating_files: [_money_truth.md, _tracker.md]

  # Substrate the Reviewer needs pre-loaded at every wake.
  reviewer_wake_envelope:
    - key: operator_profile_md
      path: context/trading/_operator_profile.md
      optional: false
    - key: risk_md
      path: context/trading/_risk.md
      optional: false
    - key: performance_md
      path: context/trading/_performance.md
      optional: true
    - key: signal_files
      path_glob: context/trading/signals/*.yaml
      summarizer: signal_files
      optional: true
```

The **bundle MANIFEST is the single source of truth** for program-shaped substrate-ABI declarations. The kernel reads this declaration via `services/bundle_reader.py` helpers at the three classes of moments ADR-224 already enforces (composition / scaffolding / display). At runtime: lock policy + wake envelope read directly from `bundle_reader`; the workspace guide narrates what the bundle declares for the operator + Reviewer's reading.

### D2 — The role taxonomy (operator-legible vocabulary, six roles)

Six roles classify every path zone. Each role declares writer + reader + lock + retention deterministically — lock policy is **derived from role**, not declared separately. The role enum is the contract:

| Role | Writer | Reader | Lock from Reviewer | Retention |
|---|---|---|---|---|
| **`operator-canon`** | operator (via YARNNN-routed primitives) | all | locked | retained forever |
| **`reviewer-workbench`** | Reviewer | Reviewer + operator | unlocked | retained forever |
| **`system-ledger`** | infrastructure (single render site) | Reviewer + operator | locked from all LLM writers | retained forever, append-only |
| **`world-mirror`** | mechanical primitives (`SyncPlatformState` per ADR-264) | Reviewer | locked from LLM writers | overwritten each fire (revision chain preserves history) |
| **`running-narrative`** | mechanical or judgment, append shape | Reviewer + operator | unlocked for declared writer only | retained forever, append-only |
| **`kernel-index`** | kernel | kernel + Reviewer (read-only) | not writable outside kernel | regenerated idempotently |

`running-narrative` is the **default classification for unclassified paths** under the descriptive-not-prescriptive principle (D7 below). When a reader encounters substrate the workspace guide doesn't classify, it treats it as `running-narrative` for its own reading purposes only and surfaces drift through normal authoring channels.

### D3 — The workspace guide: the library's operating manual

Every workspace has exactly one canonical workspace guide:

**`/workspace/_workspace_guide.md`**

The file has YAML frontmatter (machine-readable mirror of the bundle's `substrate_abi`) + prose body (the operator-and-Reviewer-readable operating manual). Same `_money_truth.md`-grandfathered pattern (one file, two consumers, no sync problem). Per ADR-254 file-format discipline this is acceptable: primary-LLM-readable prose with structured machine-readable frontmatter.

**The guide is bundle-shipped, not Reviewer-authored.** Bundles ship their guide at `docs/programs/{slug}/reference-workspace/_workspace_guide.md` alongside every other canonical file. `services.programs.fork_reference_workspace` deterministically copies it into the operator's workspace at activation, attribution `system:bundle-fork`. No-program workspaces get `DEFAULT_WORKSPACE_GUIDE_MD` from `services/orchestration.py`, written by `workspace_init.py` Phase 2 alongside MANDATE/IDENTITY/BRAND/AUTONOMY/PRECEDENT skeletons (attribution `system:workspace-init`).

The frontmatter mirrors the bundle's `substrate_abi.path_zones` + `reviewer_wake_envelope` (so operators reading the guide see the same declarations the kernel reads). Subsequent operator/Reviewer revisions land via the normal `WriteFile` path with proper attribution (`operator` / `reviewer:{occupant}`); ADR-209 retains all prior revisions.

The prose body has three required sections plus one program-specific section:

- `## How this workspace works` — Authored Substrate semantics, primitive surface, substrate-as-bus invariant, the six-role taxonomy
- `## What this workspace contains` — narration of the path zones (universal + program-specific)
- `## When things diverge` — descriptive-not-prescriptive principle, drift-handling posture
- `## What NOT to write to operator-canon` — explicit carve-outs preventing librarian drift into operator-canon territory

### D4 — Genesis is the deterministic fork at activation

Workspace activation runs the existing deterministic scaffold:
1. `workspace_init.py` writes universal skeletons (MANDATE/IDENTITY/BRAND/AUTONOMY/PRECEDENT + kernel-default workspace guide)
2. `fork_reference_workspace` forks the bundle's `reference-workspace/` directory (which includes `_workspace_guide.md` for program workspaces, overriding the kernel default)

The Reviewer's first wake is structurally identical to its second wake — reads MANDATE, principles, IDENTITY, AUTONOMY, the workspace guide, and operates. No special-case bootstrap. No LLM round to author the library. The deterministic fork IS the engine-jump-start.

**Failure mode: the same as any fork failure today** — `fork_reference_workspace` is deterministic Python; if it succeeds, the guide exists; if it fails, workspace creation fails (same shape as MANDATE.md fork failure today). No LLM-loop failure mode.

**Activations of the same bundle produce identical guides.** Per-workspace divergence happens through normal operator/Reviewer revision after activation.

**Operational substrate emerges from work** — `research/` directories appear when investigation work surfaces a need; `review/notes.md` accumulates patterns; `review/judgment_log.md` accumulates judgment lineage (rendered by infrastructure from the Reviewer's structured outputs per §5). The librarian fills the library as the operation actually runs.

### D5 — Composition: the kernel reads the bundle MANIFEST as authority

Three concrete refactors apply the bundle MANIFEST as the kernel's source of truth. The workspace guide remains the **operator-and-Reviewer-readable surface** but the kernel reads `bundle_reader` directly for routing decisions. This avoids parsing a derivative artifact when the source is already exposed.

#### D5.a — Lock policy reads bundle MANIFEST + operator overrides

```python
# services/primitives/workspace.py — _is_path_locked_for_reviewer
def _is_path_locked_for_reviewer(client, user_id, path):
    # 1. Kernel-universal locks (from constant — present in every workspace).
    locked = set(DEFAULT_REVIEWER_WRITE_LOCKS)

    # 2. Bundle-declared per-program locks via bundle_reader (the authority).
    locked |= bundle_reader.get_path_zone_locks_for_workspace(user_id, client)

    # 3. Operator overrides (workspace guide frontmatter `locks: {add, remove}`
    #    + legacy /workspace/_shared/_locks.yaml during transition).
    overrides = _read_operator_overrides(client, user_id)
    locked.update(overrides.get("add", []))
    locked.difference_update(overrides.get("remove", []))

    return path in locked
```

Three layers, in order of precedence: kernel-universal → bundle MANIFEST (the program-shaped authority) → operator overrides. **No kernel branch on program; no flat constant containing program paths.**

#### D5.b — Wake envelope reads bundle MANIFEST

```python
# services/reviewer_envelope.py
async def load_reviewer_governance_envelope(client, user_id):
    # 1. Universal envelope reads (kernel-hardcoded — program-agnostic).
    universal_reads = await _read_universal_envelope(client, user_id)

    # 2. Bundle-declared envelope inputs via bundle_reader (the authority).
    abi = bundle_reader.get_substrate_abi_for_workspace(user_id, client)
    program_reads = {}
    for decl in abi.get("reviewer_wake_envelope", []):
        if "path" in decl:
            program_reads[decl["key"]] = await _read(decl["path"])
        elif "path_glob" in decl:
            summarizer = ENVELOPE_SUMMARIZERS[decl["summarizer"]]
            program_reads[decl["key"]] = await summarizer(client, user_id, decl["path_glob"])

    return {**universal_reads, **program_reads}
```

`ENVELOPE_SUMMARIZERS` is a kernel-side registry of named summarizer functions (today: `signal_files`). Programs reference summarizers by name in MANIFEST; the kernel hosts the implementations. Adding a new summarizer kind requires its own ADR (rare event; security-relevant — bundles reference, kernel implements).

**Adding a new program requires zero edits to `reviewer_envelope.py`.** The new bundle declares its envelope; bundle_reader exposes it; the envelope assembler reads it; the Reviewer perceives the new program's substrate at wake time.

#### D5.c — Persona prose teaches the librarian where to look

The Reviewer's persona prose (across `tools_core.py`, `cockpit_awareness.py`, `reviewer_agent.py`, `prompts/chat/*.py`, `prompts/headless/*.py`) collapses into a single canonical pointer:

```
**Substrate semantics live in `/workspace/_workspace_guide.md`** — the library's
operating manual declaring path zones, their roles, lock policies, and
Authored Substrate semantics. Read it at every wake to understand what
substrate exists and how to navigate it. The path zones declared in the
guide are guaranteed to be the substrate topology — you do not need to
`ListFiles` defensively before writing within them. Updates land via
normal authoring (operator edits, you propose changes via Clarify). Treat
unclassified substrate as `running-narrative` (most permissive role) and
surface drift to the operator — never silently mutate substrate to match
the guide.
```

That single paragraph replaces ~150 lines of scattered teaching across 9 persona-prose files (catalogued in §10 Class 2). Per ADR-277's rule of thumb at the substrate-pedagogy layer: one canonical home for substrate teaching; everything else is a pointer.

### D6 — Operator overrides: same `_locks.yaml` pattern, evolving

Operator-authored overrides on top of bundle-derived locks live in two surfaces:

- **`/workspace/_workspace_guide.md` frontmatter `locks: {add, remove}`** — the modern surface; revisable like any other file via `WriteFile` with `authored_by="operator"`. Recommended for new operator override declarations.
- **`/workspace/_shared/_locks.yaml`** — the legacy surface from ADR-258 D9; preserved for backward compatibility with operator-authored lock declarations that pre-date the workspace guide. New overrides should land in the workspace guide; legacy `_locks.yaml` continues to function during the transition.

Both surfaces feed the same `_is_path_locked_for_reviewer` composition; per Singular Implementation, future cleanup will collapse the legacy surface once no operator workspaces still use it.

### D7 — D-Drift: the workspace guide describes; the librarian doesn't enforce

The workspace guide is **descriptive cartilage, not prescriptive bone.** Any reader (Reviewer, future Auditor Agent, future co-operator) sniffs out divergences and surfaces them through normal authoring channels; no reader ever silently mutates substrate to enforce the guide.

Three properties:

- **Author-agnostic.** Drift is drift whether the divergent author was operator, Reviewer, future Auditor Agent, or external system. The drift-surface mechanism doesn't track *who* drifted; it tracks *what's diverged from declaration*.
- **Force-free.** Like Claude Code refusing to silently restructure a codebase, the librarian refuses to silently classify or relocate substrate. It can surface divergence ("I see files at `/workspace/research/findings/` the workspace guide doesn't classify — want to formalize?") but the operator chooses.
- **Substrate-honest.** The guide is canon (operator-readable, attributed via Authored Substrate, revision-tracked); the substrate is canon (Authored Substrate per ADR-209). Divergence between them is honest and visible.

Two concrete behaviors:

- **Operator drops files in unclassified zone:** Reviewer treats the path as `running-narrative` for reading (so it doesn't break) AND surfaces drift via the daily-update pointer (low-noise; operator can ignore or formalize).
- **Bundle ships `substrate_abi` v2 after operator activated v1:** Reviewer at next wake detects bundle MANIFEST is newer than workspace guide; surfaces drift via Clarify with the structured diff. Operator chooses. Same mechanism as operator drift, scoped to bundle update.

### D8 — Attribution: standard ADR-209 attribution, no special variants

The workspace guide is a normal authored-substrate file. Attribution per ADR-209:

- `system:bundle-fork` — guide forked from bundle's `reference-workspace/` at activation
- `system:workspace-init` — kernel-default guide written for no-program workspaces
- `operator` — operator revisions
- `reviewer:{occupant}` — Reviewer revisions (e.g., when Reviewer surfaces drift via ProposeAction and operator approves the resulting guide update)

No special attribution variant is needed. The revision chain naturally records the provenance — operators can `ListRevisions` to see "the bundle forked the guide at activation; operator revised it twice since."

---

## 3. The librarian / library partition (canon)

This ADR canonizes the operator's library/librarian metaphor as the right organizing frame for the substrate-pedagogy layer:

**The library** (kernel + program designer + operator authority — the static reality of the building):
- Bundle MANIFEST `substrate_abi` declarations
- Bundle `reference-workspace/` files (canonical authored substrate including the workspace guide)
- Kernel `workspace_paths.py` constants (universal substrate path conventions)
- Kernel `services/orchestration.py` `DEFAULT_*_MD` constants (universal skeletons including `DEFAULT_WORKSPACE_GUIDE_MD`)
- `services/workspace_init.py` (the construction process)
- `services/programs.py::fork_reference_workspace` (the deterministic fork mechanism)
- Lock policy structure (4-layer composition; the access rules)
- ENVELOPE_SUMMARIZERS registry (kernel-implemented, bundle-referenced)

**The librarian** (Reviewer authority — reads the library at every wake, operates within it):
- Reads MANDATE, IDENTITY, principles, AUTONOMY, the workspace guide at every wake (the operating manual)
- Surfaces drift via Clarify (not silent mutation)
- Authors notes/reflections in `reviewer-workbench` substrate (`review/notes.md`)
- Renders judgment that infrastructure compiles into `system-ledger` substrate (`review/judgment_log.md`)
- Proposes operator-canon changes via ProposeAction (operator approves; operator authors)
- Develops operational substrate as work demands (e.g., `research/` directories appear when investigation work surfaces a need)

**The two are orthogonal authorities.** Library work is structural — kernel hygiene + bundle authoring + activation mechanics. Librarian work is operational — pedagogy that teaches the librarian to operate well + substrate where its operation accumulates. Phasing the rest of this ADR's implementation reflects this distinction.

---

## 4. Roadmap: Stream A + Stream B

Phase 1 is shipped (commits `7d3013b` + `43374cf`). The remaining work splits into two named streams:

### Stream A — Library hygiene (kernel-side cleanup)

Closes ~22 of the remaining drift catalog sites by routing kernel reads through the bundle MANIFEST authority instead of hardcoded program paths.

**Scope:**
- `services/reviewer_envelope.py::load_reviewer_governance_envelope` reads bundle MANIFEST via `bundle_reader.get_substrate_abi_for_workspace` (authoritative source); zero hardcoded `context/{program}/*` paths
- `agents/reviewer_agent.py::read_signal_files` accepts `path_glob` parameter; default removed; relocated to `services/reviewer_envelope.py` as `_summarize_signal_files` module-private function
- `ENVELOPE_SUMMARIZERS` registry lands in `services/reviewer_envelope.py`
- Persona prose **path-string cleanup** (the program-specific path references in `tools_core.py`, `platforms.py`, etc. — replace with role-naming where the prose is structurally fine, mark for Stream B if the prose itself needs librarian-pedagogy rewriting)
- Orphan duplicate-function cleanup in `reviewer_agent.py` (lines 1300-1325 — leftover from earlier refactor)
- Grep gate `api/test_adr280_no_program_paths_in_kernel.py` enumerating banned patterns under enumerated scope; returns zero matches
- ADR-276 regression gate continues to pass against bundle-MANIFEST-driven envelope

**Risk profile:** medium. Touches the wake envelope ADR-276 just hardened. Bundle MANIFEST declarations + bundle_reader from Phase 1 are the source of truth — Stream A just rewires consumers. ADR-276 regression gate must pass.

**Net scope:** ~250 LOC + extended test gate. Single atomic commit.

### Stream B — Librarian activation (substantive product work)

Teaches the librarian its responsibilities post-genesis + ships the substrate where its judgment accumulates. This is what makes the platform actually work.

**Scope:**
- Persona prose **librarian-pedagogy rewrite**: across the 9 persona-prose files, replace scattered substrate-teaching with the canonical pointer to `/workspace/_workspace_guide.md` per D5.c. Persona frame teaches: *read the guide at every wake, operate within it, surface drift via Clarify, never silently mutate operator-canon, write your patterns to `notes.md`, your judgment lands in `judgment_log.md` via infrastructure rendering*.
- Judgment lineage substrate (the worked example from §5):
  - Rename `decisions.md` → `judgment_log.md` (constant rename + SQL migration of existing rows)
  - Single-writer infrastructure-rendered contract (Reviewer never `WriteFile`s directly; infrastructure renders from `ReturnVerdict` per material-outcome gate)
  - Deterministic 5-condition material-outcome gate (per §5.D3)
  - Delete `append_recurrence_fire` blanket write (Singular Implementation)
  - Bundle workspace guides declare `judgment_log.md → system-ledger` (already shipped in both bundle guides)
- First-wake validation against kvk's live workspace post-migration: the Reviewer's next reactive wake should read its bundle-shipped workspace guide, perceive the topology, and operate from substrate awareness (the engine-jump-start property finally tested empirically)
- Documentation cascade per §6 (FOUNDATIONS Axiom 1 fifth sub-clause + Derived Principle 19; GLOSSARY entries; Tier 2/3 doc references)

**Risk profile:** medium-high. Persona prose changes are the highest-risk-to-behavior part of the ADR. The judgment_log substrate refactor touches the Reviewer's audit trail. SQL migration on the 5 live workspaces. Worth its own discourse round to nail before code.

**Net scope:** ~400 LOC code + extensive doc updates + SQL migration + extended test gate. Likely two commits (persona prose + librarian-readiness validation; then judgment_log substrate + documentation cascade).

### Sequencing

Stream A first. Stream B's correctness depends on the wake envelope reading the workspace guide via bundle MANIFEST (Stream A) — without that, the librarian doesn't perceive program-shaped substrate at every wake, and the Stream B persona-prose rewrite has no clean library to teach the librarian to operate over.

---

## 5. The judgment_log worked example (Stream B substrate)

The discourse that produced this ADR began with `/workspace/review/decisions.md` becoming a wake-audit log instead of a judgment-lineage record. Three reactive Reviewer wakes on 2026-05-15 each produced an identical-shape entry — *"Workspace is fully operational. Portfolio is empty, no signals fired. Standing down."* — duplicating information already in `execution_events`.

Structurally identical to ADR-277's feed-emission pathology: events whose canonical home is a substrate row were also emitted to a parallel narrative surface, without the parallel emission carrying any operator-relevant judgment the substrate row didn't already carry.

The judgment_log file is the worked example for ADR-280's role taxonomy + writer-discipline contract. **Not a separate ADR scope** — the smallest concrete demonstration that the role taxonomy + bundle-driven lock policy + writer-discipline contract land cleanly on a real file.

### 5.D1 — `decisions.md` is renamed to `judgment_log.md`

The current filename overloads two concepts (file is both *decisions about specific proposals* and *every wake's reasoning*). The rename makes the file's role legible:

- **`/workspace/review/decisions.md` → `/workspace/review/judgment_log.md`**

"Judgment log" names the file's role precisely — the Reviewer's structured lineage of operation-shaping judgment moments.

Constant rename: `services/workspace_paths.py::REVIEW_DECISIONS_PATH = "review/decisions.md"` becomes `REVIEW_JUDGMENT_LOG_PATH = "review/judgment_log.md"`. Per Singular Implementation, no compat alias.

The bundle workspace guides already declare `review/judgment_log.md → system-ledger`. Lock policy derives the lock from the role. The Reviewer's tool-loop primitive set excludes direct `WriteFile` to the path. Reasoning content reaches the file only through the structured `ReturnVerdict` → infrastructure-render contract per D2 below.

### 5.D2 — Single-writer contract: infrastructure renders from `ReviewerOutput`

Infrastructure renders `judgment_log.md` from the Reviewer's structured `ReviewerOutput` (per ADR-256 D5) at exactly two trigger points:

1. **Proposal arrival** — Reviewer renders verdict on a proposal (`approve | reject | defer`); infrastructure renders a `--- decision ---` block. Existing `append_decision` path in `services/reviewer_audit.py` continues, just renamed to write to `judgment_log.md`.
2. **Recurrence-fire wake with material outcome** — `judgment`-mode recurrence fires the Reviewer; if the wake produces a material outcome (per D3 below), infrastructure renders a structured block whose shape names the outcome. **Replaces today's `append_recurrence_fire` blanket write.**

Authorship attribution: `authored_by="reviewer:{occupant}"` per ADR-209. Reasoning is the Reviewer's; rendering is infrastructure's. Attribution names the reasoner.

### 5.D3 — Material-outcome gate: deterministic, code-evaluated

Infrastructure inspects the wake's `ReviewerOutput.actions_taken` and renders a lineage entry iff at least one of:

1. **`ProposeAction` was called.** Wake produced a proposal awaiting review.
2. **`Schedule` was called with action ∈ `{create, update, archive}`.** Wake authored cadence (per ADR-274 + ADR-275 — operation-shaping).
3. **`WriteFile` was called against an `operator-canon` substrate path** (Reviewer wrote to operator-authored library via lock-bypass or with explicit operator permission). Operation-shaping by definition.
4. **`Clarify` was emitted carrying an operator-relevant alert** (per `clarify_alert: true` flag — explicit alert-shaped signal).
5. **`ReturnVerdict.verdict` is one of `{pause_autonomy, narrow, relax, character_note}`** — meta-level operation-shaping verdicts.

If none are true, the wake produced no material outcome — file gets no entry. Wake's existence is recorded in `execution_events` (per ADR-265); reasoning lands in the wake's narrative entry on the feed surface (per ADR-258 revised, weight=routine for routine stand-downs per ADR-277). **Both surfaces remain complete; duplication into `judgment_log.md` ceases.**

The list is canonical and grows by ADR.

### 5.D4 — `append_recurrence_fire` deletion (Singular Implementation)

`services/reviewer_audit.py::append_recurrence_fire` and its blanket-write call site in `services/invocation_dispatcher.py` are **deleted**. No compat shim. The new path replaces the old.

Substrate-as-bus invariant continues to be honored by:
- `execution_events` row (kernel-written; mode/status/duration/cost per ADR-265)
- Narrative entry on the feed surface (Reviewer's per-action narration per ADR-258 revised; weight tier per ADR-277)
- Any substrate writes the Reviewer's tool-loop performed (operator-canon paths, workbench paths — all attributed via ADR-209)

These three exhaust the substrate-as-bus invariant for routine wakes. The judgment-lineage file is load-bearing for *operator's retrospective audit of operation-shaping moments*, not for the substrate-as-bus invariant.

### 5.D5 — Reviewer's notebooks remain Reviewer-authored (`reviewer-workbench`)

- **`/workspace/review/notes.md`** — working scratch across wakes
- **`/workspace/review/reflections.md`** (future) — pattern-tracking journal

These files are `reviewer-workbench` role — Reviewer-authored, no lock against Reviewer writes. Persona prose (consolidated to a workspace-guide pointer per D5.c) distinguishes the workbench from the judgment log. The role taxonomy carries the distinction.

### 5.D6 — Migration: existing `decisions.md` content renamed in-place

```sql
UPDATE workspace_files
SET path = '/workspace/review/judgment_log.md'
WHERE path = '/workspace/review/decisions.md' AND user_id = $1;

UPDATE workspace_file_versions
SET path = '/workspace/review/judgment_log.md'
WHERE path = '/workspace/review/decisions.md' AND user_id = $1;
```

Revision chain preserved per ADR-209. Two-row update per workspace; no content transformation.

---

## 6. Documentation cascade (Stream B)

**Tier 1 — Canon docs:**
- **FOUNDATIONS.md** — Axiom 1 gains a fifth sub-clause: "Substrate organization is operator-readable canon" (the workspace guide as the operating manual). New Derived Principle 19: "The workspace guide describes; the librarian operates within it but does not silently enforce it."
- **GLOSSARY.md** — new entries: *Substrate ABI*, *Workspace guide*, *Library / librarian partition*, six role-name entries (`operator-canon` / `reviewer-workbench` / `system-ledger` / `world-mirror` / `running-narrative` / `kernel-index`).
- **THESIS.md** — Commitment 4 ("authored accumulation") gains a sentence on how operators perceive the accumulation contract via the workspace guide.

**Tier 2 — Architecture docs:**
- **`authored-substrate.md`** — new §"Operator-and-Reviewer-readable surface" pointing at `_workspace_guide.md`.
- **`primitives-matrix.md`** — header note: path-zone semantics live in the workspace guide + bundle MANIFEST, not in primitive docs.
- **`reviewer-substrate.md`** — new §"How the Reviewer learns its workspace" pointing at the workspace guide.
- **`SERVICE-MODEL.md`** Frame 5 — application bundle row gains `substrate_abi` field reference.
- **`compositor.md`** — one-line note that compositor-level substrate semantics also live in the guide.
- **`docs/programs/README.md`** — bundle convention requires `substrate_abi` MANIFEST block + `reference-workspace/_workspace_guide.md`.

**Tier 3 — Design docs:**
- **`design/WORKSPACE.md`** — Files surface gains a row for `_workspace_guide.md` (operator-readable; bundle-shipped or kernel-default; operator-and-Reviewer-revisable thereafter).

**Tier 4 — Persona prose code (Stream A path-string cleanup + Stream B librarian pedagogy):**
- 9 persona-prose files (per §10 Class 2): scattered teaching deleted, replaced by single canonical pointer per D5.c.
- `api/prompts/CHANGELOG.md` — entry per protocol.
- `CLAUDE.md` — ADR-280 entry in the ADR list.

---

## 7. What this ADR does NOT do (deferred / out of scope)

- **Per-file frontmatter for substrate-role classification.** Bundle MANIFEST + workspace guide carry the taxonomy without per-file metadata.
- **Multi-program operator UX.** A workspace activating two programs simultaneously needs envelope merging and lock-set union. `bundle_reader.bundles_active_for_workspace` already returns a list; composition functions iterate. Multi-program is structurally supported. Operator UX deferred (per ADR-222 open questions).
- **Cockpit FE routes (Class 3 catalog, 9 sites).** Program-specific FE rendering is the compositor's job per ADR-225.
- **`risk_gate.py` migration.** `services/risk_gate.py` is alpha-trader-program-specific code that belongs in the bundle as program-shipped capability, not in kernel `services/`. Out of scope; flagged for a future bundle-relocation ADR.
- **Operator-authored override of `reviewer_wake_envelope`.** Today the bundle declaration is authoritative; operator-overridable envelope declarations could land later via the same `locks: {add, remove}` pattern in workspace guide frontmatter. Deferred until concrete operator demand.
- **Legacy `_locks.yaml` collapse.** Both surfaces (workspace guide `locks: {add, remove}` + legacy `_locks.yaml`) feed the same composition during transition; future cleanup collapses the legacy surface.

---

## 8. Acceptance criteria

### Phase 1 (Implemented 2026-05-15 — commits `7d3013b` + `43374cf`)

- [x] `MANIFEST.yaml` schema documented to include `substrate_abi` block (ADR-223 §3.bis updated).
- [x] alpha-trader bundle MANIFEST contains a non-empty `substrate_abi` block per D1.
- [x] alpha-commerce bundle MANIFEST contains a non-empty `substrate_abi` block (validates additive pattern for deferred bundle).
- [x] `services/workspace_guide.py` exports `read_frontmatter` + `read_frontmatter_async` + helpers (the operator-and-Reviewer-readable surface reader).
- [x] `services/bundle_reader.py` extends with `get_substrate_abi_for_workspace` + `get_path_zone_locks_for_workspace` (the kernel's authoritative bundle-MANIFEST reader).
- [x] `docs/programs/alpha-trader/reference-workspace/_workspace_guide.md` exists (bundle-shipped operator-canon).
- [x] `docs/programs/alpha-commerce/reference-workspace/_workspace_guide.md` exists (validates additive pattern).
- [x] `services/orchestration.py::DEFAULT_WORKSPACE_GUIDE_MD` (kernel default for no-program workspaces).
- [x] `services/workspace_init.py` Phase 2 writes the kernel-default guide alongside MANDATE/IDENTITY/BRAND/AUTONOMY/PRECEDENT skeletons. Bundle-shipped guide overrides via Phase 5 fork.
- [x] `services/workspace_paths.py::DEFAULT_REVIEWER_WRITE_LOCKS` contains zero program-specific paths (closes 4 sites).
- [x] `services/primitives/workspace.py::_is_path_locked_for_reviewer` composes kernel + bundle MANIFEST + operator overrides.
- [x] One-shot migration script `adr280_seed_workspace_guides.py` writes the alpha-trader bundle guide into existing operator workspaces (5/5 succeeded).
- [x] Workspace guide budget gate: `services/workspace_guide.py::_check_guide_size` warns at 25KB / 600 lines (defends ADR-159 compact-index token budget).
- [x] Regression gate `api/test_adr280_phase1.py` passes (30/30); sibling regression ADR-274 + ADR-275 + ADR-276 (27/27).

### Stream A (kernel hygiene)

- [ ] `services/reviewer_envelope.py::load_reviewer_governance_envelope` reads bundle MANIFEST via `bundle_reader.get_substrate_abi_for_workspace`; zero hardcoded `context/{program}/*` paths (closes 7 sites).
- [ ] `agents/reviewer_agent.py::read_signal_files` accepts `path_glob` parameter; default removed; orphan duplicate at lines 1300-1325 deleted (closes 2 sites).
- [ ] `_summarize_signal_files` relocated to `services/reviewer_envelope.py` as module-private function.
- [ ] `ENVELOPE_SUMMARIZERS` registry lands in `services/reviewer_envelope.py` (`{"signal_files": _summarize_signal_files}`).
- [ ] Persona prose path-string cleanup across `tools_core.py`, `platforms.py`, etc. — replace with role-naming where prose is structurally fine; mark for Stream B if the prose itself needs librarian-pedagogy rewriting.
- [ ] Grep gate `api/test_adr280_no_program_paths_in_kernel.py` returns zero matches for banned patterns under enumerated scope.
- [ ] ADR-276 regression gate passes against bundle-MANIFEST-driven envelope.
- [ ] Regression gate `api/test_adr280_stream_a.py` passes.

### Stream B (librarian activation)

- [ ] Persona prose librarian-pedagogy rewrite across 9 files — scattered substrate-teaching deleted; replaced by canonical pointer to `_workspace_guide.md` per D5.c. Persona frame teaches the librarian: read the guide at every wake; operate within it; surface drift via Clarify; never silently mutate operator-canon; write patterns to `notes.md`; judgment lands in `judgment_log.md` via infrastructure rendering.
- [ ] `api/prompts/CHANGELOG.md` carries the persona-prose change entry.
- [ ] judgment_log substrate per §5: `decisions.md → judgment_log.md` rename via SQL migration; `REVIEW_DECISIONS_PATH` deleted, replaced by `REVIEW_JUDGMENT_LOG_PATH`; `append_recurrence_fire` deleted; `render_lineage_entry_if_material(reviewer_output) → bool` evaluating §5.D3 gate.
- [ ] First-wake validation: kvk's next reactive Reviewer wake reads its bundle-shipped `_workspace_guide.md`, perceives the substrate topology, operates from substrate awareness. Empirical check on the engine-jump-start property.
- [ ] Tier 1 + 2 + 3 documentation cascade per §6.
- [ ] FOUNDATIONS Axiom 1 fifth sub-clause + Derived Principle 19 added.
- [ ] GLOSSARY entries added (Substrate ABI, Workspace guide, Library/librarian partition, six role names).
- [ ] Regression test `api/test_adr280_stream_b.py` covers: proposal-arrival path renders entry; material-outcome recurrence-fire renders entry; routine-stand-down recurrence-fire renders no entry; Reviewer attempting direct `WriteFile` to `judgment_log.md` is rejected by lock policy.
- [ ] `CLAUDE.md` ADR list updated with ADR-280 entry.

---

## 9. Rejected alternatives

**A. Per-file frontmatter declaring substrate role.** Considered; rejected. Scatters the same declaration across hundreds of files; bundle MANIFEST + workspace guide consolidates without losing expressiveness.

**B. Fully agnostic kernel — Reviewer figures out organization from filesystem alone.** Considered; rejected. (a) Cold-start cost — every wake spends tokens reasoning about structure before doing work. (b) Operator predictability — debugging "why didn't the Reviewer perceive X" requires knowing what the Reviewer expects to find; the workspace guide makes this inspectable; pure-figure-it-out makes it opaque.

**C. Two files (`_substrate_abi.yaml` machine-parsed + `_substrate_semantics.md` LLM-readable).** Considered; rejected. One file with frontmatter + prose (the `_money_truth.md` pattern, ADR-254-grandfathered) eliminates sync drift while honoring format-by-axiomatic-fit.

**D. Kernel reads workspace guide frontmatter as authority instead of bundle MANIFEST.** Considered; rejected. Bundle MANIFEST is already the machine-readable authority for substrate-ABI declarations and is already exposed via `bundle_reader` (Phase 1). Making the kernel parse the workspace guide as a separate authority would create a derivative source competing with the original — Singular Implementation violation. The workspace guide narrates what the bundle declares; the kernel reads the bundle.

**E. Reviewer-authored genesis (the original §D4 design).** Considered; ratified; empirically falsified in Phase 1 migration; dissolved per Revision section above. The library/librarian partition makes clear why: bundles ARE libraries; librarians don't author the library they inherit. The dissolution is the architectural learning.

**F. New kernel registry for substrate roles parallel to `task_types.py`.** Considered; rejected. Re-creates the exact pattern ADR-224 tore down: a kernel registry containing program-specific paths that the kernel reads for runtime dispatch. Same problem one layer up; same architectural fix (move to bundles, read at point-of-use).

---

## 10. Drift catalog (empirical, full enumeration)

Grep audit of `api/` (excluding `__pycache__`, tests, `docs/programs/`) for program-domain path strings (`context/trading`, `context/commerce`, `context/defi`). 52 total sites:

### Class 1 — Load-bearing kernel reads (24 sites)

| File | Lines | Closes |
|---|---|---|
| `services/workspace_paths.py` | 147, 148, 149, 150 | Phase 1 ✓ |
| `services/reviewer_envelope.py` | 53, 54, 55, 56, 95, 96, 97 | Stream A |
| `agents/reviewer_agent.py` | 1309, 1400 | Stream A (read_signal_files glob) |
| `services/risk_gate.py` | 7, 34, 48, 84, 95, 429 | Out of scope (program-specific code; future bundle-relocation ADR) |
| `services/review_proposal_dispatch.py` | 355 | Stream A |
| `services/execution_router.py` | 223 | Stream A |
| `services/primitives/track_regime.py` | 5, 61, 394 | Out of scope (alpha-trader-specific primitive) |
| `services/primitives/track_universe.py` | 6, 16, 66, 145, 158, 250, 264 | Out of scope (alpha-trader-specific primitive) |
| `services/primitives/schedule.py` | 71 | Out of scope (alpha-trader-specific bundle prompt example) |

### Class 2 — Persona prose (9 sites)

| File | Lines | Closes |
|---|---|---|
| `agents/prompts/tools_core.py` | 36, 87, 88, 150 | Stream A path-string cleanup; Stream B librarian-pedagogy rewrite |
| `agents/prompts/platforms.py` | 91, 95 | Stream A (relocate program-specific guidance to bundle-shipped persona overlay) |
| `agents/prompts/chat/workspace.py` | 239 | Stream A |
| `agents/cockpit_awareness.py` | 74 | Stream A (auto-generated section gains workspace-guide reference) |
| `agents/prompts/headless/base.py` | 27 | Stream A (signal log glob; workspace-guide pointer) |

### Class 3 — Cockpit FE routes (9 sites)

| File | Lines | Closes |
|---|---|---|
| `routes/cockpit.py` | 314, 315, 316, 327, 329, 330, 358, 407, 458 | Out of scope (ADR-225 compositor; program-shaped cockpit faces are program-shaped by design per ADR-273) |

### Class 4 — Oneshot scripts (3 sites)

| File | Lines | Closes |
|---|---|---|
| `scripts/oneshot/phaseB_unify_recurrences.py` | 132, 146, 149 | Out of scope (one-time alpha-trader bootstrap; intended program-coupling) |

### Closure summary

- **Phase 1 closes:** 4 sites (workspace_paths.py) ✓
- **Stream A closes:** 13 sites (reviewer_envelope.py + reviewer_agent.py glob + adjacent program-path readers + persona prose path-string cleanup)
- **Stream B closes:** ~9 sites (persona prose librarian-pedagogy rewrite — overlaps with Stream A's path-string scope)
- **Phase 1 + Stream A + Stream B total:** **26 of 52 sites closed** at the substrate-pedagogy + kernel-perception layers
- **Out of scope:** Class 3 (9 sites — ADR-225 compositor scope) + Class 4 (3 sites — intended) + program-specific primitives (10 sites — bundle-shipped code, future bundle-relocation ADR)

The remaining out-of-scope sites are honest program-shaped code that belongs in alpha-trader-bundle territory rather than kernel `api/services/` territory.

**Final grep gate** (Stream A acceptance): `grep -rn -E "context/(trading|commerce|defi)" api/agents/ api/services/workspace_paths.py api/services/reviewer_envelope.py api/services/primitives/workspace.py api/services/review_proposal_dispatch.py api/services/execution_router.py` returns zero matches. Narrower scope reflects the ADR's intent — substrate-pedagogy + kernel-perception is closed; program-specific primitives (bundle-shipped code) remain bundle-coupled by design.

---

## 11. Discourse trail

This ADR consolidates the 2026-05-15 substrate-topology discourse:

1. Operator observed three identical "I read 4 files and stood down" entries in `decisions.md` over 24h on kvk's workspace (post-ADR-276 deploy).
2. First proposal: single-writer contract for `decisions.md`. Drafted as parked sibling ADR; dissolved into §5 of this ADR per Singular Implementation.
3. Operator pushed: *"are we creating file naming to folder structure taxonomies that are not agnostic in nature?"* — opened the substrate-topology question.
4. Naming converged on **Substrate ABI** (parallel to Syscall ABI from Principle 16).
5. Phase 1 scope: lock-policy-only as the smallest meaningful slice.
6. Discovered Authored Substrate teaching scattered across 8+ persona-prose files; consolidate Substrate ABI + Authored Substrate pedagogy into one operator-readable workspace guide.
7. Original mechanism: Reviewer authors the workspace guide at first wake from kernel template + bundle declaration ("genesis-by-Reviewer").
8. Phase 1 shipped (commit `7d3013b`); migration script run against kvk's workspace.
9. **Empirical falsification of genesis-by-Reviewer:** 16 successive empty-content WriteFile calls; Reviewer model failed to thread multi-KB structured prompt through tool schema; attribution fell through to `yarnnn:chat`.
10. **Architectural simplification surfaced via the operator's library/librarian metaphor:** the bundle is the library; the Reviewer is the librarian; libraries exist before librarians; bundles ship the workspace guide as one more canonical operator-canon file.
11. Dissolution shipped (commit `43374cf`): genesis machinery deleted; bundle-shipped guide added; simplified migration succeeded against 5/5 workspaces.
12. **This ADR rewritten end-to-end** under the librarian/library partition — no superseded sub-sections preserved (per Singular Implementation discipline; preserving prior framing alongside current canon creates two-source-of-truth drift). Discourse arc preserved in this section + Revision section + commits `7d3013b`, `43374cf`.
13. Stream A + Stream B roadmap derived from the partition: Stream A is library hygiene (kernel-side cleanup); Stream B is librarian activation (substantive product work).

**This is the singular ADR for the substrate-pedagogy work.** No parked sibling, no parallel spec. The judgment_log file (§5) is the worked example demonstrating the role taxonomy + bundle-driven lock policy + writer-discipline contract land cleanly on a real file — included as Stream B work, not as a follow-on.
