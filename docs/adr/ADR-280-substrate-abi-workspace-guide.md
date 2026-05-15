# ADR-280: Substrate ABI — Bundles Declare Their Topology, the Reviewer Authors Its Workspace Guide at Genesis

**Status**: Proposed (2026-05-15)
**Date**: 2026-05-15
**Dimensional classification**: **Substrate** (Axiom 1) primary — defines what the kernel encodes about substrate topology vs. what the program declares vs. what the workspace authors at genesis. **Identity** (Axiom 2) secondary — kernel/program/operator authority boundary expressed at the substrate-naming layer. **Trigger** (Axiom 4) tertiary — genesis-by-Reviewer is a one-shot reactive trigger on workspace activation.

**Implements (extends)**: [ADR-222](ADR-222-agent-native-operating-system-framing.md) (OS framing — finishes Principle 16's "no kernel touch" commitment at the substrate-paths layer), [ADR-224](ADR-224-kernel-program-boundary-refactor.md) (kernel/program boundary refactor — extends from registries to substrate paths + persona pedagogy), [ADR-188](ADR-188-domain-agnostic-framework.md) (registries as template libraries — same principle, substrate-naming layer), [ADR-209](ADR-209-authored-substrate.md) (every write attributed and retained — the substrate guarantee that makes genesis-by-Reviewer + operator divergence honest), [ADR-275](ADR-275-introspection-cadence-reviewer-authored.md) (Reviewer authors its own Trigger dimension — extends to substrate-organization dimension), [ADR-277](ADR-277-feed-emission-policy.md) ("each event has one canonical home" — same rule applied at the substrate-pedagogy layer: each substrate concept has one canonical teaching surface).

**Amends**: [ADR-258 revised](ADR-258-reviewer-as-personified-chat-mode-operator.md) D9 (`DEFAULT_REVIEWER_WRITE_LOCKS` becomes a kernel-defaults set composed with workspace-guide-declared locks, not a flat constant containing program-specific paths), [ADR-276](ADR-276-reactive-trigger-envelope-governance-preload.md) (`reviewer_envelope.load_reviewer_governance_envelope` becomes workspace-guide-driven via Reviewer-authored declarations, not via hardcoded `context/trading/*` paths), [ADR-205](ADR-205-primitive-collapse.md) signup workspace-init (genesis-by-Reviewer subsumes the deterministic substrate-fork step for ABI-shaped substrate; canonical files like MANDATE/IDENTITY skeletons remain init-fork), [ADR-194 v2](ADR-194-reviewer-layer-and-impersonation.md) (Reviewer's `decisions.md` semantics tighten — file becomes single-writer judgment lineage and is renamed `judgment_log.md` per §5 of this ADR).

**Supersedes**: the post-FOUNDATIONS-v8.4 `append_recurrence_fire` infrastructure-side blanket-write path in `services/reviewer_audit.py` + `services/invocation_dispatcher.py` (replaced by the deterministic material-outcome gate per §5.D7 of this ADR).

**Preserves**: FOUNDATIONS Axioms 1–9, Derived Principles 1–18, ADR-194 v2 Reviewer substrate (six canonical seat files unchanged), ADR-258 revised primitive surface (`REVIEWER_PRIMITIVES`), ADR-260 real-time Reviewer loop, ADR-261 recurrence model, ADR-209 Authored Substrate (load-bearing for this ADR — every workspace guide revision attributed), ADR-265 `execution_events` as canonical forensic substrate (the substrate-as-bus invariant for routine wakes is honored by `execution_events` + feed narrative — judgment_log carries operation-shaping outcomes only).

---

## 1. Context

### 1.1 The discourse arc that produced this ADR

The session that produced this ADR began with the operator's observation about `decisions.md` becoming a wake-audit log instead of a judgment-lineage record. An earlier draft proposed a parked sibling ADR ("Judgment Lineage Substrate") covering only that file's rename + single-writer contract; the operator collapsed it into this ADR per Singular Implementation discipline once it became clear every load-bearing decision was already absorbed by the Substrate ABI mechanism. The judgment_log file is now §5 of this ADR — a worked example demonstrating the role taxonomy + workspace-guide-driven lock policy + deterministic material-outcome gate end-to-end, not a separate spec. The operator pushed upstream:

> *"are we creating file naming to folder structure taxonomies that are not agnostic in nature? … some level of (back at the Agent OS metaphor) … almost agnostic and pure LLM, reviewer agent judgment … just be provided one group of files and directories can't touch, the rest is kind of figure it out … kernel project bundles to steer workspaces, but the essence of the framework, LLM prompting, and thus direction would be less of 'this folder is pre-made, pre-named, pre-folder directory, follow it' vs. 'here are the files, here are the rules, you navigate and figure it out'."*

That question is the load-bearing one. The discourse went through three architectural shapes (kernel-only / pure-figure-it-out / hybrid) and converged on: **the kernel encodes universals; the program bundle declares its specific topology as an ABI; the Reviewer authors a single canonical workspace guide at genesis from both inputs; operators and Reviewers refine it through normal authoring channels thereafter.**

Two secondary discourse moves shaped this ADR:

1. The **how/what split** — the kernel ships *how* to operate in any workspace (universal: Authored Substrate semantics, primitive surface, divergence-handling posture); the bundle declares *what* substrate this program uses (program-shaped: path zones with operator-legible role classifications, lock policies, envelope inputs).

2. The **descriptive-not-prescriptive principle** — much like Claude Code refuses to silently restructure a codebase, the workspace guide is **descriptive cartilage, not prescriptive bone.** Any reader (Reviewer, future Auditor Agent, future co-operator) sniffs out divergences and surfaces them through normal authoring channels (Clarify, ProposeAction, daily-update pointer); no reader ever silently mutates substrate to enforce the guide. This collapses the question of "what happens on operator drift?" and "what happens on bundle ABI updates?" into one author-agnostic principle.

### 1.2 What FOUNDATIONS already commits

ADR-222 + Derived Principle 16 are unambiguous about the discipline:

> *"Kernel changes are sacred. Programs do not modify the kernel. … Adding a program is purely additive — a new bundle, possibly new system component library entries, no kernel touch."*

ADR-224 enforced this for three registries (`task_types.py`, `directory_registry.py`, `orchestration.CAPABILITIES`). ADR-188 named the principle ("Registries are template libraries, not validation gates" — Derived Principle 10). The principle is canon. **The principle has not been extended to the substrate-paths layer or the persona-pedagogy layer.** This ADR closes that gap.

### 1.3 The drift catalog — empirical baseline

Grep audit of `api/` (excluding `__pycache__`, tests, `docs/programs/`) for program-domain path strings (`context/trading`, `context/commerce`, `context/defi`):

**52 total drift sites in production code.** Classified:

| Class | Count | Severity | Phase to close |
|---|---|---|---|
| **Class 1 — Load-bearing kernel reads** (substrate behavior changes) | 24 | High — every site is a Principle 16 violation | Phase 1–4 |
| **Class 2 — Persona prose** (pedagogical, dissolves into workspace guide) | 9 | Medium — operator-invisible drift, but creates new code-touch on every program addition | Phase 3 |
| **Class 3 — FE cockpit routes** (program-specific UI surface) | 9 | Low — kernel-shaped; cockpit is rendering surface, not perception | Out of scope for ABI ADR; addressed by ADR-225 compositor |
| **Class 4 — Oneshot scripts** (alpha-trader bundle bootstrap) | 3 | None — one-time scaffolding scripts, expected program-coupling | No migration needed |
| **Class 5 — `workspace_paths.py::DEFAULT_REVIEWER_WRITE_LOCKS`** | 4 | Highest — kernel constant tuple containing program-specific paths | Phase 1 |
| **Class 6 — `reviewer_envelope.py` hardcoded reads** | 3 | Highest — single canonical Reviewer perception assembler hardcodes one program | Phase 2 |

**Phases 1+2+3 close 40 of 52 sites.** Class 3 (cockpit FE routes) is a known follow-on under ADR-225 compositor scope and is excluded here. Class 4 (oneshot scripts) is bundle-coupled by intent. The remaining 40 are the closeable surface.

The full enumerated catalog with file paths + line numbers + closing-phase assignment lives at §10 below.

### 1.4 What ADR-277 just canonized (load-bearing for this ADR)

Yesterday's ADR-277 ratified the rule of thumb at the feed-emission layer:

> *"Each event has one canonical home. The feed is for events whose canonical home is conversation."*

This ADR applies the same rule at the substrate-pedagogy layer:

> **Each substrate concept has one canonical teaching surface. The workspace guide is the teaching surface for substrate semantics. Persona prose, kernel constants, scattered docstrings — none of these are second canonical teaching surfaces; they are pointers at most.**

Today substrate semantics are taught in 4+ persona-prose code sites (`tools_core.py`, `cockpit_awareness.py`, `reviewer_agent.py`, `chat_agent.py`), partially restated in 8+ design docs, and structurally encoded in path constants the Reviewer cannot read. The pathology is identical to ADR-277's pre-fix state: one concept, multiple uncoordinated teaching homes, drift between them.

---

## 2. Decision

### D1 — The Substrate ABI: bundles declare their topology in MANIFEST.yaml

Bundle MANIFESTs gain a top-level `substrate_abi` block declaring the program's substrate-topology contract with the kernel. Schema:

```yaml
# MANIFEST.yaml — alpha-trader bundle (illustrative)
schema_version: 1
slug: alpha-trader
# ... existing fields ...

substrate_abi:
  schema_version: 1

  # Path zones the program uses. Each declares its role + intended writers.
  # Roles use the operator-legible vocabulary defined at §2.D2 below.
  path_zones:
    - path: context/trading
      role: operator-canon
      purpose: per-instrument entities + signals + watched universe
      authored_files: [_operator_profile.md, _risk.md, _universe.yaml]
      accumulating_files: [_performance.md, _money_truth.md, _tracker.md, _regime.yaml]
      glob_zones: ["signals/*.yaml", "{TICKER}.yaml"]

    - path: context/portfolio
      role: operator-canon
      purpose: account-level state + performance + risk
      accumulating_files: [_money_truth.md, _tracker.md]

  # Substrate the Reviewer needs pre-loaded at every wake to perceive program state.
  # The kernel envelope-assembly function reads this declaration and gathers accordingly.
  reviewer_wake_envelope:
    - key: operator_profile_md
      path: context/trading/_operator_profile.md
      optional: false
    - key: risk_md
      path: context/trading/_risk.md
      optional: false
    - key: performance_md
      path: context/trading/_performance.md
      optional: true   # accumulated by reconciler — empty before first reconciliation
    - key: signal_files
      path_glob: context/trading/signals/*.yaml
      summarizer: signal_files   # names a kernel summarizer function
      optional: true
```

**The bundle declares the "what."** The kernel reads this declaration at three specific moments (the same three classes ADR-224 already enforces for other bundle reads — composition, scaffolding, display) via `bundle_reader.py`-extending helpers.

### D2 — The role taxonomy (operator-legible vocabulary, six roles)

The role taxonomy is canon — first-class architectural vocabulary the operator reads in `_workspace_guide.md` and reasons about. Six roles, each with deterministic writer + reader + lock + retention:

| Role | Writer | Reader | Lock policy | Retention |
|---|---|---|---|---|
| **`operator-canon`** | operator (via YARNNN-routed primitives) | all | locked from Reviewer by default | retained forever |
| **`reviewer-workbench`** | Reviewer | Reviewer + operator | unlocked for Reviewer | retained forever |
| **`system-ledger`** | infrastructure (single render site) | Reviewer + operator | locked from all LLM writers | retained forever, append-only |
| **`world-mirror`** | mechanical primitives (`SyncPlatformState` etc., per ADR-264) | Reviewer | locked from LLM writers | overwritten each fire (revision chain preserves history per ADR-209) |
| **`running-narrative`** | mechanical or judgment, append-shape | Reviewer + operator | unlocked for declared writer only | retained forever, append-only |
| **`kernel-index`** | kernel | kernel + Reviewer (read-only) | not writable by anything outside kernel | regenerated idempotently |

Lock policy is **derived from the role**, not declared separately. `operator-canon` is *always* locked from Reviewer; the role implies the lock; declaring lock separately is redundant and creates inconsistency risk. Retention is similarly derived. The role enum is the contract; lock + retention are computed properties.

`running-narrative` is the **default classification for unclassified paths** under D-Drift's descriptive-not-prescriptive principle (D7 below). When a reader encounters substrate the workspace guide doesn't classify, it treats it as `running-narrative` for its own reading purposes only and surfaces drift through normal authoring channels. The default is the most permissive role so unclassified substrate doesn't break Reviewer perception while drift is being surfaced.

### D3 — The workspace guide: single canonical file with frontmatter + prose

Every workspace has exactly one canonical workspace guide:

**`/workspace/_workspace_guide.md`**

The file has YAML frontmatter (machine-parsed by kernel) + prose body (read by operator and LLM). One file, two consumers, no sync problem (same pattern as `_money_truth.md`, grandfathered by ADR-254):

```markdown
---
# Machine-parsed by kernel via yaml.safe_load on frontmatter
schema_version: 1

# Path zones — universal kernel-shipped + program-shipped + operator-authored
path_zones:
  # Universal (kernel-shipped — present in every workspace):
  - path: context/_shared
    role: operator-canon
  - path: review
    role: reviewer-workbench   # the seat as a whole; specific files override below
  - path: review/IDENTITY.md
    role: operator-canon
  - path: review/principles.md
    role: operator-canon
  - path: review/judgment_log.md
    role: system-ledger
  # ... (full kernel template documented at §3 below)

  # Program-shipped (from bundle's substrate_abi):
  - path: context/trading
    role: operator-canon
    bundle: alpha-trader
  # ... etc

# Reviewer wake envelope inputs — universal + program
reviewer_wake_envelope:
  - key: identity_md
    path: review/IDENTITY.md
  # ... etc (see §3 for kernel template)

# Lock-policy adds beyond role-derived defaults (operator overrides)
locks:
  add: []
  remove: []
---

# How this workspace works

(prose narration of Authored Substrate semantics, primitive surface,
divergence-handling posture, role taxonomy with operator-legible names —
the universal "how" portion shipped from kernel template at genesis)

## What this workspace contains

(prose narration of the path zones above, why each exists, what to expect
in each, how to extend it — populated from bundle's substrate_abi at
genesis; operator/Reviewer revises as workspace evolves)

## When things diverge

(prose narration of the descriptive-not-prescriptive principle — what the
Reviewer does when it sees substrate the guide doesn't classify, how
operator drift surfaces, how bundle ABI updates surface)
```

The Reviewer reads `_workspace_guide.md` at every wake, the same way it reads `principles.md` and `MANDATE.md`. The kernel reads the frontmatter for lock-policy + envelope-assembly. The operator reads the prose to understand how their workspace works. **One file, three consumers, no scattered teaching.**

### D4 — Genesis-by-Reviewer: workspace activation produces the guide

The workspace guide is **authored by the Reviewer at first wake from kernel template + bundle MANIFEST `substrate_abi` declaration.** This eliminates the cold-start asymmetry where the substrate the Reviewer needs to operate doesn't exist when it first wakes.

The mechanism:

1. **Workspace activation** triggers a one-shot **genesis wake** — a Reviewer wake with a special `genesis_prompt` envelope.
2. The genesis envelope contains: kernel-shipped universal "how" template + active bundle's `substrate_abi` declaration (if any program is being activated) + a prompt directing the Reviewer to author `_workspace_guide.md` from these inputs.
3. The Reviewer reads both, composes the workspace guide (frontmatter + prose body), writes it via `WriteFile` with `authored_by="reviewer:{occupant}/genesis"` per ADR-209.
4. From this point forward, every Reviewer wake (including subsequent reactive + addressed wakes) reads the workspace guide as canon.

**The kernel template lives in one well-named module** (`api/agents/genesis_prompt.py` or similar) and is read at exactly one moment per workspace lifetime. The genesis-wake persona prose is structurally distinct from steady-state persona prose (which references the workspace guide rather than carrying its content). This is a one-shot bootstrap pattern, not a parallel persona system — Claude Code has the same property (very first session in a new repo has no CLAUDE.md to read; Claude operates from scratch and may help the user author one).

**Cost honest:** activation now costs ~one Sonnet wake of Reviewer reasoning + WriteFile (replacing today's deterministic substrate fork for ABI-shaped substrate). Canonical operator-authored library skeletons (MANDATE.md skeleton, IDENTITY.md skeleton, BRAND.md skeleton — content the bundle ships verbatim per ADR-226) **remain init-fork**, not genesis-by-Reviewer authored — those have a deterministic correct content the Reviewer should not paraphrase. Only the workspace guide itself is genesis-by-Reviewer authored.

**Failure mode:** if the genesis wake errors mid-way, the workspace guide may not exist or may be partially authored. Recovery: re-attempt the genesis wake idempotently. `is_skeleton_content` (per `services/workspace_utils.py`) extends to detect missing/partial workspace guide and triggers re-author on next workspace state read. No partial-state corruption — Authored Substrate's revision chain preserves any prior partial revision.

**Activations of the same bundle produce substantively-identical guides with textually-variable prose.** The role taxonomy + path-zone enumeration is structurally identical (driven by the same bundle declaration); the prose narration may differ in tone or phrasing across activations. This is acceptable — the structurally-identical content is the load-bearing part (kernel reads frontmatter; lock policy reads frontmatter); the prose is for human/LLM reading where minor textual variation is fine.

### D5 — Kernel template: the universal "how" portion

The kernel-shipped universal template (read by genesis + dissolved across persona prose today) declares everything that's true regardless of program:

**Path zones (universal):**
- `context/_shared/` — `operator-canon` (MANDATE, IDENTITY, BRAND, AUTONOMY, PRECEDENT)
- `context/_shared/_locks.yaml` — `operator-canon`
- `context/_shared/_preferences.yaml` — `operator-canon`
- `memory/` — `running-narrative` (orchestration accumulation: awareness, playbook, style, notes)
- `memory/recent.md` — `system-ledger` (back-office narrative digest)
- `review/IDENTITY.md` — `operator-canon`
- `review/principles.md` — `operator-canon`
- `review/_principles.yaml` — `operator-canon`
- `review/OCCUPANT.md` — `system-ledger`
- `review/handoffs.md` — `system-ledger`
- `review/calibration.md` — `system-ledger`
- `review/judgment_log.md` — `system-ledger` (renamed from `decisions.md` per §5 of this ADR)
- `review/notes.md` — `reviewer-workbench`
- `_recurrences.yaml` — `kernel-index`
- `agents/{slug}/` — `running-narrative` per agent
- `reports/{slug}/` — `running-narrative` (per-recurrence report substrate)
- `operations/{slug}/` — `running-narrative` (per-recurrence action state)
- `uploads/` — `operator-canon` (operator-contributed reference material)
- `working/` — `reviewer-workbench` (ephemeral scratch)

**Reviewer wake envelope (universal entries):**
- `identity_md` → `review/IDENTITY.md`
- `principles_md` → `review/principles.md`
- `precedent_md` → `context/_shared/PRECEDENT.md`
- `mandate_md` → `context/_shared/MANDATE.md`
- `autonomy_md` → `context/_shared/AUTONOMY.md`
- `preferences_yaml` → `context/_shared/_preferences.yaml`

**Prose body sections (universal):**
- `## How this workspace works` — Authored Substrate semantics, primitive surface (ReadFile / WriteFile / ListRevisions / ReadRevision / DiffRevisions / SearchFiles / ListFiles), substrate-as-bus invariant, the read-before-write discipline
- `## What NOT to write to operator-canon` — explicit carve-outs to prevent Reviewer drift in the operator-authored direction. Borrowed from Claude Code's `WHAT_NOT_TO_SAVE_SECTION` discipline (`docs/analysis/src_claudeCC/memdir/memdir.ts`): names categories of content the Reviewer must NOT write to `operator-canon` paths even when it could (e.g., derivable-from-other-substrate facts, ephemeral session state, things that belong in `reviewer-workbench` notebooks instead). Cheap insurance against Reviewer-drift-into-MANDATE class of bugs.
- `## When things diverge` — descriptive-not-prescriptive principle (D7 below), drift-handling posture, what to do when reader encounters unclassified substrate

**The kernel template plus the bundle's `substrate_abi` declaration plus the genesis prompt are the three inputs to the Reviewer's first wake.** Output: `_workspace_guide.md`.

### D6 — Composition: kernel reads workspace guide, not hardcoded paths

Three concrete refactors apply the workspace guide as the source of truth:

#### D6.a — Lock policy reads frontmatter

```python
# services/workspace_paths.py — post-ADR-280 (Phase 1)
DEFAULT_REVIEWER_WRITE_LOCKS = (
    # Kernel-universal locks only — present in every workspace regardless of program.
    # Program-specific locks DELETED — workspace guide carries them now.
    SHARED_MANDATE_PATH,
    SHARED_AUTONOMY_PATH,
    SHARED_AUTONOMY_YAML_PATH,
    SHARED_IDENTITY_PATH,
    SHARED_BRAND_PATH,
    SHARED_CONVENTIONS_PATH,
    SHARED_PRECEDENT_PATH,
    SHARED_PREFERENCES_PATH,
    "context/_shared/_locks.yaml",
)
```

```python
# services/primitives/workspace.py — _is_path_locked_for_reviewer (Phase 1)
def _is_path_locked_for_reviewer(client, user_id, path):
    # 1. Kernel-universal locks (from constant — present in every workspace).
    locked = set(DEFAULT_REVIEWER_WRITE_LOCKS)

    # 2. Workspace-guide-declared locks (frontmatter path_zones with operator-canon role).
    guide = workspace_guide.read_frontmatter(client, user_id)
    for zone in guide.get("path_zones", []):
        if zone.get("role") == "operator-canon":
            # Path zone may be a directory or specific file
            locked.add(zone["path"])

    # 3. Operator overrides (workspace guide frontmatter `locks: {add, remove}`).
    locked.update(guide.get("locks", {}).get("add", []))
    locked.difference_update(guide.get("locks", {}).get("remove", []))

    # 4. Legacy operator overrides via `_locks.yaml` (preserved for compat with existing operator data).
    overrides = _read_locks_yaml(client, user_id)
    locked.update(overrides.get("locked_paths", []))
    locked.difference_update(overrides.get("unlocked_paths", []))

    return path in locked
```

Three inputs, in order of precedence: kernel-universal → workspace-guide-declared (from bundle + operator revisions) → operator legacy overrides. **No kernel branch on program; no flat constant containing program paths.**

#### D6.b — Wake envelope reads frontmatter (Phase 2)

```python
# services/reviewer_envelope.py — post-ADR-280 (Phase 2)
async def load_reviewer_governance_envelope(client, user_id):
    # Read workspace guide frontmatter (single source of truth for envelope).
    guide = await workspace_guide.read_frontmatter_async(client, user_id)
    envelope_decls = guide.get("reviewer_wake_envelope", [])

    # Each declaration: {key, path | path_glob, summarizer?, optional}
    results = {}
    for decl in envelope_decls:
        if "path" in decl:
            results[decl["key"]] = await _read(decl["path"])
        elif "path_glob" in decl:
            summarizer = ENVELOPE_SUMMARIZERS[decl["summarizer"]]
            results[decl["key"]] = await summarizer(client, user_id, decl["path_glob"])

    return results
```

`ENVELOPE_SUMMARIZERS` is a small kernel-side registry of named summarizer functions (today: `signal_files`). Programs reference summarizers by name in MANIFEST; the kernel hosts the implementations. Adding a new summarizer kind requires its own ADR (rare event).

**Adding a new program requires zero edits to `reviewer_envelope.py`.** The new bundle declares its envelope; the Reviewer authors the workspace guide at genesis; the kernel reads the workspace guide; the Reviewer perceives the new program's substrate at wake time.

#### D6.c — Persona prose dissolves to one pointer (Phase 3)

The 9 persona-prose sites teaching path conventions + Authored Substrate semantics (enumerated in §10) collapse into one canonical pointer in the universal persona frame:

```
**Substrate semantics live in `/workspace/_workspace_guide.md`** — a canonical
file declaring the path zones in your workspace, their roles, lock policies,
and how Authored Substrate works. Read it at every wake to understand what
substrate exists and how to navigate it. The frontmatter is structured (read
by the kernel for lock policy + wake envelope assembly); the prose body
narrates the contract for you to read. **The path zones declared in the
workspace guide are guaranteed to be the substrate topology — you do not
need to `ListFiles` defensively before writing within them.** Updates to the
guide land via normal authoring (operator edits, you propose changes via
Clarify). Treat unclassified substrate as `running-narrative` (most
permissive role) and surface the drift to the operator — never silently
mutate substrate to match the guide.
```

That single paragraph replaces ~150 lines of scattered teaching across `tools_core.py`, `cockpit_awareness.py`, `reviewer_agent.py`, `prompts/chat/workspace.py`, `prompts/chat/behaviors.py`, `prompts/chat/entity.py`, `prompts/chat/onboarding.py`, `prompts/headless/deliverable.py`, `prompts/headless/base.py`. Per ADR-277's rule of thumb, applied at the substrate-pedagogy layer: one canonical home for substrate teaching; everything else is a pointer.

### D7 — D-Drift: descriptive cartilage, not prescriptive bone

The workspace guide describes; it does not enforce. Any reader sniffs out divergences and surfaces them through normal authoring channels; no reader silently mutates substrate to enforce the guide.

**Properties this commits:**

- **Author-agnostic.** Drift is drift whether the divergent author was operator, Reviewer, future Auditor Agent, future second human collaborator, or MCP-injected external system. The drift-surface mechanism doesn't track *who* drifted; it tracks *what's diverged from declaration*.
- **Force-free.** Like Claude Code refusing to silently restructure a codebase, the guide refuses to silently classify or relocate substrate. It can point out divergence ("I see files at `/workspace/research/findings/` that the workspace guide doesn't classify — want to formalize?") but the operator chooses.
- **Substrate-honest.** The guide is canon (operator-readable, attributed via Authored Substrate, revision-tracked); the substrate is canon (Authored Substrate per ADR-209). Divergence between them is honest and visible. Neither overrides the other.
- **Future-shape-proof.** Multi-agent: Reviewer A and Reviewer B (different occupants over time) both honor the discipline. Multi-user: collaborator's writes show up as drift to the original Reviewer; same surface mechanism. Multi-program: bundle v2 declarations are drift relative to the operator's authored guide; same surface mechanism. Three different concrete cases, one architectural mechanism.

**Two concrete behaviors this commits:**

- **Operator drops files in unclassified zone:** Reviewer treats the path as `running-narrative` for its own reading (so it doesn't break) AND surfaces drift via the daily-update pointer (low-noise, operator can ignore or formalize).
- **Bundle ships `substrate_abi` v2 after operator activated v1:** Reviewer at next wake detects bundle declaration is newer than workspace guide; surfaces drift via Clarify *with the structured diff* ("alpha-trader v2 declares a new role for `_money_truth.md` that's not in your workspace guide — want me to merge?"). Operator chooses. Same mechanism as operator drift, scoped to bundle update.

**Frontmatter-vs-prose drift** (operator updates prose body without updating frontmatter, or vice versa): the Reviewer reads the prose body; it notices "the prose says we have a `research/findings/` zone, but the frontmatter doesn't declare it"; surfaces drift via Clarify. Recursive D-Drift discipline. The Reviewer's persona frame includes a one-line discipline note for this case.

### D8 — Genesis-by-Reviewer attribution variant

Authored Substrate (ADR-209) `authored_by` taxonomy gains one new variant: **`reviewer:{occupant}/genesis`** for substrate the Reviewer authors at the genesis wake specifically. This makes the genesis act inspectable in the revision chain — operators can see "the Reviewer authored my workspace guide at activation; I revised it three times since" cleanly.

Genesis attribution applies to:
- `_workspace_guide.md` (always)
- Any other substrate the Reviewer authors during the genesis wake (rare; documented when added)

Subsequent Reviewer revisions to the workspace guide carry standard `reviewer:{occupant}` attribution — the `/genesis` qualifier is a one-shot signal of bootstrap origin.

---

## 3. The kernel template (universal "how" content)

Living in `api/agents/genesis_prompt.py` (new module). Three structured inputs the genesis wake assembles:

1. **Universal path-zone declarations** — the list at §2.D5 above. Lives in module-level constant; bundle-declared zones merge in at genesis.
2. **Universal envelope inputs** — `identity_md / principles_md / precedent_md / mandate_md / autonomy_md / preferences_yaml`. Lives in module-level constant; bundle-declared inputs merge in at genesis.
3. **Universal prose template sections** — `## How this workspace works`, `## When things diverge`. Lives in module-level template strings; the Reviewer is directed to populate `## What this workspace contains` from the bundle's `substrate_abi` declaration.

The genesis wake's special envelope contains:
- The full kernel template (constants + template strings)
- The active bundle's `substrate_abi` block (or empty dict if no program activated)
- A genesis prompt directing the Reviewer to compose `_workspace_guide.md` from these inputs

The genesis wake is bounded at 5 tool-use rounds (only needs ReadFile to inspect bundle declarations + WriteFile to author the guide). Sonnet by default; Haiku override available for cost discipline if measurement shows the genesis wake doesn't need Sonnet's reasoning.

---

## 4. Migration: from today's hardcoded paths to workspace-guide-declared

### 4.1 Phase 1 — Lock policy refactor + `substrate_abi` schema landing (smallest meaningful slice)

- **Bundle schema extension** (ADR-223 amend): `MANIFEST.yaml` gains optional `substrate_abi` block (this ADR's §2.D1 schema). alpha-trader bundle authors its `substrate_abi`. alpha-commerce bundle (deferred per ADR-224) also authors its `substrate_abi` to validate the additive pattern.
- **`bundle_reader.py` extensions:** `get_substrate_abi_for_workspace(user_id, client) → dict` and `get_path_zone_locks_for_workspace(user_id, client) → set[str]` helpers. Walk active bundles; expand `path_zones` with `role: operator-canon`; return as a set.
- **Workspace guide module:** new `api/services/workspace_guide.py` with `read_frontmatter(client, user_id)` (sync) + `read_frontmatter_async(client, user_id)` (async). Reads `/workspace/_workspace_guide.md`, parses YAML frontmatter via `yaml.safe_load`, returns dict. Returns empty dict if file absent (genesis hasn't run yet).
- **Lock policy refactor:** `_is_path_locked_for_reviewer` per §2.D6.a — kernel-universal locks + workspace-guide-declared locks + operator overrides. Phase 1 reads the workspace guide if present; falls back to bundle reader if guide absent (transitional support during migration window).
- **Genesis-by-Reviewer flow:** `api/agents/genesis_prompt.py` (new module) + integration into `services/workspace_init.py` (genesis wake invoked after deterministic substrate scaffold completes). For kvk's existing workspace, a one-time `services/back_office/migrate_to_workspace_guide.py` script triggers a genesis wake to author the workspace guide for the existing live workspace.
- **`workspace_paths.py` cleanup:** delete the 4 program-specific paths from `DEFAULT_REVIEWER_WRITE_LOCKS`. Constant becomes kernel-universal-only (closes 4 of the 52 drift sites — Class 5 in §1.3 catalog).
- **Regression gate:** `api/test_adr280_phase1.py` covers: workspace guide frontmatter parsing; lock policy composition (kernel + bundle + operator); alpha-trader operator's Reviewer cannot WriteFile to `context/trading/_operator_profile.md` (now via workspace-guide route, not kernel constant); workspace with no active program has no domain-specific locks; legacy `_locks.yaml` overrides continue to work.

**Phase 1 closes:** Class 5 (4 sites) + sets up the substrate for Phase 2-3.

### 4.2 Phase 2 — Wake envelope refactor + `read_signal_files` glob unhardcoding

- `services/reviewer_envelope.py` rewrites per §2.D6.b. Universal reads stay; program reads come from workspace guide.
- `agents/reviewer_agent.py::read_signal_files` accepts `path_glob` parameter; default removed. Caller (envelope helper) supplies the bundle-declared glob from workspace guide.
- `ENVELOPE_SUMMARIZERS` registry lands in `services/reviewer_envelope.py`.
- ADR-276 regression gate (`api/test_adr276_reactive_envelope.py`) continues to pass with workspace-guide-driven envelope.
- New regression gate: `api/test_adr280_phase2.py` covers wake envelope assembly from workspace guide; multi-bundle envelope merge; deferred-bundle exclusion.

**Phase 2 closes:** Class 6 (3 sites) + the 2 hardcoded glob sites in `reviewer_agent.py`.

### 4.3 Phase 3 — Persona prose dissolution + universal pointer

- Across 9 persona-prose files (enumerated in §10): delete scattered teaching of Authored Substrate semantics, path conventions, role implications. Replace with the single canonical pointer paragraph from §2.D6.c.
- `api/agents/cockpit_awareness.py` — auto-generated cockpit awareness section gains a one-line workspace-guide reference; substrate-naming hardcodes deleted.
- `api/prompts/CHANGELOG.md` — entry per protocol.
- Regression gate: `api/test_adr280_phase3.py` covers: persona prose contains exactly one workspace-guide pointer; persona prose contains zero alpha-trader-specific path references (grep gate); Reviewer wake successfully consults workspace guide as documented.

**Phase 3 closes:** Class 1 + Class 2 persona-prose sites (~24 + 9 = 33 sites). Combined with Phase 1+2 = **40 of 52 catalog sites closed.** Remaining 12 = Class 3 cockpit FE routes (out of scope under ADR-225 compositor) + Class 4 oneshot scripts (intended bundle-coupling).

### 4.4 Phase 4 — Documentation cascade + judgment_log worked example

- Tier 1 canon docs (FOUNDATIONS, GLOSSARY, THESIS) updated per §6 below.
- Tier 2 architecture docs (authored-substrate.md, primitives-matrix.md, reviewer-substrate.md, SERVICE-MODEL.md, compositor.md, docs/programs/README.md) updated per §6.
- Tier 3 design docs (design/WORKSPACE.md) updated per §6.
- The judgment_log worked example (per §5 below) lands as part of Phase 1 or as a small Phase 4 follow-on — the rename is a single workspace-guide entry change + a persona-prose pointer + a one-shot path migration. Validates ADR-280's workspace-guide mechanism end-to-end on the smallest concrete case (one file, one role, one writer-discipline contract).

---

## 5. The judgment_log worked example (the file that catalyzed this ADR)

The discourse that produced this ADR began with `/workspace/review/decisions.md` becoming a wake-audit log instead of a judgment-lineage record on kvk's alpha-trader workspace. Three reactive Reviewer wakes between 13:01–21:00 UTC on 2026-05-15 each produced an identical-shape `decisions.md` entry — *"Workspace is fully operational. Portfolio is empty, no signals fired. Standing down until [next scheduled fire]."* — duplicating information already present in `execution_events` (per ADR-265).

This is structurally identical to the pathology ADR-277 corrected at the feed-emission layer: events whose canonical home is the substrate-row were also being emitted to a parallel narrative surface, without the parallel emission carrying any operator-relevant judgment the substrate row didn't already carry.

The judgment_log file is the worked example for ADR-280's role taxonomy + workspace-guide-driven lock policy + writer-discipline contract. **The file is not a separate ADR scope — it is the smallest concrete demonstration that ADR-280's mechanism lands cleanly on a real file.**

### 5.D1 — `decisions.md` is renamed to `judgment_log.md`

The current filename overloads two concepts (the file is both *decisions about specific proposals* and, in today's drift state, *every wake's reasoning*). The rename makes the file's role legible to the Reviewer (in persona prose pointing at the workspace guide) and the operator (in `/agents?agent=reviewer` cockpit detail):

- **`/workspace/review/decisions.md` → `/workspace/review/judgment_log.md`**

"Judgment log" names the file's role precisely — the Reviewer's structured lineage of operation-shaping judgment moments. "Decisions" was historically accurate when proposal-verdicts were the only entries; under the expanded contract (proposal verdicts + material-outcome recurrence-fires + future operation-shaping events) the broader name is correct.

Constant rename: `services/workspace_paths.py::REVIEW_DECISIONS_PATH = "review/decisions.md"` becomes `REVIEW_JUDGMENT_LOG_PATH = "review/judgment_log.md"`. Per Singular Implementation, no compat alias.

The workspace guide declares `review/judgment_log.md → system-ledger`. Lock policy derives from the role (per §2.D2 — `system-ledger` is locked from all LLM writers). The Reviewer's tool-loop primitive set continues to exclude direct `WriteFile` to the path. The Reviewer's reasoning content reaches the file only through the structured `ReturnVerdict` → infrastructure-render contract per D2 below.

### 5.D2 — Single-writer contract: infrastructure renders from `ReviewerOutput`

Infrastructure renders `judgment_log.md` from the Reviewer's structured `ReviewerOutput` (per ADR-256 D5) at exactly two trigger points:

1. **Proposal arrival** — when the Reviewer renders a verdict on a proposal (`approve | reject | defer`), infrastructure renders a `--- decision ---` block. Existing path — `append_decision` in `services/reviewer_audit.py` continues to operate, just renamed to write to `judgment_log.md`.
2. **Recurrence-fire wake with material outcome** — when a `judgment`-mode recurrence fires the Reviewer and the wake produces a material outcome (per D3 below), infrastructure renders a structured block whose shape names the outcome. **New path — replaces today's `append_recurrence_fire` blanket write.**

Authorship attribution: every infrastructure-rendered entry carries `authored_by="reviewer:{occupant}"` in the Authored Substrate revision chain (ADR-209). The reasoning is the Reviewer's; the rendering is infrastructure's. Attribution names the reasoner, not the renderer — consistent with how `append_decision` already attributes proposal-verdict entries.

A future Auditor Agent or other systemic Agent that authors lineage-eligible outcomes via the same `ReviewerOutput` contract would carry `authored_by="auditor:{occupant}"` etc. — the contract is occupant-class-agnostic per Derived Principle 14.

### 5.D3 — Material-outcome gate is a deterministic, code-evaluated list

To prevent re-introducing the same noise pathology under a different name, the gate that decides whether a recurrence-fire wake earns a `judgment_log.md` entry is **deterministic code, not LLM judgment**. The wake's `ReviewerOutput.actions_taken` (per ADR-256 D5) carries the structured tool-call audit; infrastructure inspects it and renders a lineage entry iff at least one of the following is true:

1. **`ProposeAction` was called.** The wake produced a proposal awaiting review.
2. **`Schedule` was called with action ∈ `{create, update, archive}`.** The wake authored cadence (per ADR-274 + ADR-275, this is operation-shaping).
3. **`WriteFile` was called against an `operator-canon` substrate path** (per the role taxonomy — paths classified as operator-authored library that the Reviewer wrote to via lock-bypass or with explicit operator permission). Operation-shaping by definition.
4. **`Clarify` was emitted carrying an operator-relevant alert** (per the `clarify_alert: true` flag in the Clarify payload — explicit signal from the Reviewer that this Clarify is alert-shaped, not routine).
5. **`ReturnVerdict.verdict` is one of `{pause_autonomy, narrow, relax, character_note}`** — meta-level operation-shaping verdicts that are themselves the outcome.

If none of the above are true, the wake produced no material outcome — the file gets no entry. The wake's existence is recorded in `execution_events` (per ADR-265); the Reviewer's reasoning is recorded in the wake's narrative entry on the feed surface (per ADR-258 revised, with `weight=routine` for routine stand-downs per ADR-277). **Both surfaces remain complete; the duplication into `judgment_log.md` ceases.**

The list is canonical and grows by ADR — extending the gate is a load-bearing decision worth discoursing, not a one-off code change.

### 5.D4 — `append_recurrence_fire` deletion (Singular Implementation)

The current `append_recurrence_fire` function in `services/reviewer_audit.py` and its blanket-write call site in `services/invocation_dispatcher.py` are **deleted** in the same commit that ships the rename + material-outcome gate. No compat shim, no flag to disable, no deprecation period. Per Singular Implementation: the new path replaces the old; the old does not coexist.

The wake's substrate-as-bus invariant continues to be honored by:
- `execution_events` row (kernel-written, includes wake mode/status/duration/cost — per ADR-265)
- Narrative entry on the feed surface (Reviewer's per-action narration per ADR-258 revised; weight tier per ADR-277)
- *Any* substrate writes the Reviewer's tool-loop performed (operator-canon paths, workbench paths, etc. — all attributed via ADR-209)

These three together exhaust the substrate-as-bus invariant for wakes that produce no material outcome. The judgment-lineage file is not load-bearing for the invariant; it is load-bearing for the operator's retrospective audit of operation-shaping moments. Routine wakes produce no operation-shaping moments and therefore correctly produce no lineage entries.

### 5.D5 — Reviewer's notebooks remain Reviewer-authored (`reviewer-workbench` role)

The Reviewer's free-form journaling and working-scratch substrate stays Reviewer-authored via direct `WriteFile`:

- **`/workspace/review/notes.md`** — working scratch the Reviewer wants across wakes.
- **`/workspace/review/reflections.md`** (future) — patterns and self-observations the Reviewer wants to retain but that aren't yet decision-shaped.

These files are `reviewer-workbench` role — Reviewer-authored, no lock against Reviewer writes. Persona prose (now consolidated to a workspace-guide pointer per §2.D6.c) distinguishes the workbench (free-form, Reviewer-authored, for the Reviewer's continuity) from the judgment log (system-rendered, structured contract, for operation-shaping lineage). The role taxonomy carries the distinction; persona prose just points at the workspace guide.

### 5.D6 — Migration: existing `decisions.md` content renamed in-place

kvk's + seulkim88's live workspaces have authored `decisions.md` files with revision history. The migration is one SQL update per workspace:

```sql
UPDATE workspace_files
SET path = '/workspace/review/judgment_log.md'
WHERE path = '/workspace/review/decisions.md' AND user_id = $1;

UPDATE workspace_file_versions
SET path = '/workspace/review/judgment_log.md'
WHERE path = '/workspace/review/decisions.md' AND user_id = $1;
```

Revision chain preserved per ADR-209. Two-row update per workspace; no content transformation. Runs as part of Phase 1 or Phase 4 deployment.

### 5.D7 — Why this lives inside ADR-280, not as a separate ADR

The earlier draft proposed a parked sibling ADR for the judgment_log work. Reviewing both as a pair revealed that every load-bearing decision in the parked draft was already absorbed by ADR-280:

- The single-writer contract is the `system-ledger` writer-discipline rule (§2.D2 + §3.5 of this ADR, generalized from this one file).
- The lock policy is role-derived (§2.D2 — every `system-ledger` path is locked from LLM writers, no per-file declaration needed).
- The rename is a workspace-guide-entry edit + a constant rename + a persona-prose pointer (Phase 1 or Phase 4 task).
- The library/desk/log distinction is the role taxonomy applied at workspace scale.
- The material-outcome gate (D3 above) is the only judgment_log-specific decision; it lives here because it is the deterministic substrate-write contract that complements the role taxonomy.

Keeping a separate parked ADR would have created two-source-of-truth drift (Singular Implementation violation): reviewers reading the parked ADR in 6 months would not realize ADR-280 absorbed it. Folding it in is the correct discipline.

---

## 6. Documentation impact set (cascade in same commit chain)

**Tier 1 — Canon docs that gain a new sub-clause/principle:**

- **`FOUNDATIONS.md`** — Axiom 1 gains a fifth sub-clause: "Substrate organization is operator-readable canon" (the workspace guide as the substrate-pedagogy surface). Derived Principle 19 (new): "The workspace guide is descriptive cartilage, not prescriptive bone — readers sniff out drift and surface it; no reader silently mutates substrate to enforce the guide."
- **`GLOSSARY.md`** — new entries: *Substrate ABI*, *Workspace guide*, *Genesis wake*, *operator-canon* / *reviewer-workbench* / *system-ledger* / *world-mirror* / *running-narrative* / *kernel-index* (the role taxonomy).
- **`THESIS.md`** — Commitment 4 ("authored accumulation") gains a sentence on how operators perceive the accumulation contract via the workspace guide.

**Tier 2 — Architecture docs that gain references:**

- **`authored-substrate.md`** — gains §"Pedagogical surface" pointing at `_workspace_guide.md` as the canonical operator-and-Reviewer-readable teaching artifact.
- **`primitives-matrix.md`** — header note: path-zone semantics live in the workspace guide, not in primitive docs.
- **`reviewer-substrate.md`** — gains §"How the Reviewer learns its workspace" pointing at the workspace guide.
- **`SERVICE-MODEL.md`** Frame 5 — application bundle row gains `substrate_abi` field reference.
- **`compositor.md`** — one-line note that compositor-level substrate semantics also live in the guide.
- **`docs/programs/README.md`** — bundle convention gains the `substrate_abi` MANIFEST block as load-bearing.

**Tier 3 — Design docs:**

- **`design/WORKSPACE.md`** — Files surface gains a row for `_workspace_guide.md` (operator-readable, system-rendered-at-genesis-by-Reviewer, operator-and-Reviewer-revisable thereafter).

**Tier 4 — Persona prose code (the singular streamline):**

- 9 files in `api/agents/` (per §10 catalog) gut scattered teaching, replace with one-line pointer.
- `api/prompts/CHANGELOG.md` — entry per protocol.
- `CLAUDE.md` — ADR-280 entry in the ADR list.

---

## 7. What this ADR does NOT do (deferred / out of scope)

- **Per-file frontmatter for substrate-role classification.** Considered earlier in the discourse; rejected. Bundle MANIFEST + path zoning + workspace guide carries the taxonomy without per-file metadata.
- **Multi-program operator UX.** A workspace activating two programs simultaneously needs envelope merging and lock-set union semantics. `bundle_reader.bundles_active_for_workspace` already returns a list; the composition functions (D6.a, D6.b) iterate over all active bundles. Multi-program is structurally supported. Operator UX for multi-program activation is its own deferred design (per ADR-222 open questions).
- **Cockpit FE routes (Class 3 catalog, 9 sites).** Program-specific FE rendering is the compositor's job per ADR-225; this ADR's scope is Reviewer-perception substrate, not FE rendering substrate.
- **`risk_gate.py` migration.** `services/risk_gate.py` is alpha-trader-program-specific code (it gates trading orders against trading risk parameters). It belongs in the alpha-trader bundle as program-shipped capability, not in kernel `services/`. Out of scope for this ADR; flagged as Class 4-adjacent technical debt for a future bundle-relocation ADR.
- **Operator-authored override of `reviewer_wake_envelope`.** Today the bundle declaration plus workspace guide are the source of truth; operator-overridable envelope declarations could land later via the same `locks: {add, remove}` pattern in the workspace guide frontmatter. Deferred until concrete operator demand.

---

## 8. Acceptance criteria

### Phase 1
- [ ] `MANIFEST.yaml` schema documented to include `substrate_abi` block (ADR-223 doc updated).
- [ ] alpha-trader bundle MANIFEST contains a non-empty `substrate_abi` block per §2.D1 schema.
- [ ] alpha-commerce bundle MANIFEST contains a non-empty `substrate_abi` block (validates additive pattern for deferred bundle).
- [ ] `services/workspace_guide.py` exports `read_frontmatter` + `read_frontmatter_async`.
- [ ] `services/bundle_reader.py` extends with `get_substrate_abi_for_workspace` + `get_path_zone_locks_for_workspace`.
- [ ] `api/agents/genesis_prompt.py` (new module) contains the universal kernel template per §3.
- [ ] `services/workspace_init.py` invokes a genesis wake after deterministic substrate scaffold; wake authors `_workspace_guide.md` via `WriteFile` with `authored_by="reviewer:{occupant}/genesis"`.
- [ ] `services/workspace_paths.py::DEFAULT_REVIEWER_WRITE_LOCKS` contains zero program-specific paths (grep gate — closes 4 sites).
- [ ] `services/primitives/workspace.py::_is_path_locked_for_reviewer` reads workspace guide frontmatter for lock composition per §2.D6.a algorithm.
- [ ] One-shot migration script triggers genesis wake for kvk's existing workspace; workspace guide successfully authored; lock policy correctly enforces `context/trading/*` paths via workspace-guide route.
- [ ] Workspace guide budget gate: `services/workspace_guide.py` enforces a soft cap on guide size when reading (frontmatter parsing always succeeds; prose body has a soft truncation warning logged when content exceeds 25KB / 600 lines — same shape as CC's `truncateEntrypointContent` per `docs/analysis/src_claudeCC/memdir/memdir.ts:57`). Truncation warning is informational only — does not break Reviewer wake; the kernel logs that the operator may want to refactor an over-long guide. Defends ADR-159's compact-index token budget against silent guide-bloat as operators author richer substrate over time.
- [ ] Regression gate `api/test_adr280_phase1.py` passes.

### Phase 2
- [ ] `services/reviewer_envelope.py::load_reviewer_governance_envelope` reads workspace guide for envelope inputs; zero hardcoded `context/{program}/*` paths (closes 3 sites).
- [ ] `agents/reviewer_agent.py::read_signal_files` accepts `path_glob` parameter; default removed (closes 2 sites).
- [ ] `ENVELOPE_SUMMARIZERS` registry lands in `services/reviewer_envelope.py`.
- [ ] ADR-276 regression gate passes against workspace-guide-driven envelope.
- [ ] Regression gate `api/test_adr280_phase2.py` passes.

### Phase 3
- [ ] 9 persona prose files updated per §10 catalog; scattered Authored Substrate teaching deleted; replaced by single canonical pointer per §2.D6.c.
- [ ] Final grep gate `api/test_adr280_no_program_paths_in_kernel.py` enumerating banned patterns under enumerated scope returns zero matches.
- [ ] `api/prompts/CHANGELOG.md` carries the persona-prose change entry.

### Phase 4
- [ ] FOUNDATIONS Axiom 1 fifth sub-clause + Derived Principle 19 added.
- [ ] GLOSSARY entries added (Substrate ABI, Workspace guide, Genesis wake, six role-name entries).
- [ ] All Tier 2 + Tier 3 docs updated per §6.
- [ ] judgment_log worked example (per §5) lands cleanly: `decisions.md → judgment_log.md` rename via SQL migration; `services/workspace_paths.py::REVIEW_DECISIONS_PATH` deleted, replaced by `REVIEW_JUDGMENT_LOG_PATH = "review/judgment_log.md"`; all callers updated (grep `REVIEW_DECISIONS_PATH` returns zero matches in `api/`); `services/reviewer_audit.py::append_recurrence_fire` deleted; corresponding call site in `services/invocation_dispatcher.py` deleted; `services/reviewer_audit.py` gains `render_lineage_entry_if_material(reviewer_output: ReviewerOutput) → bool` evaluating §5.D3 gate; workspace guide for alpha-trader workspace declares `judgment_log.md → system-ledger` (validates role taxonomy end-to-end on a concrete file).
- [ ] Regression test `api/test_adr280_judgment_log.py` covers: proposal-arrival path renders entry; material-outcome recurrence-fire renders entry; routine-stand-down recurrence-fire renders no entry; Reviewer attempting direct `WriteFile` to `judgment_log.md` is rejected by lock policy (per `system-ledger` role-derived lock).
- [ ] `CLAUDE.md` ADR list updated with ADR-280 entry.

---

## 9. Rejected alternatives

**A. Per-file frontmatter declaring substrate role.** Considered in earlier discourse; rejected. Scatters the same declaration across hundreds of files; bundle MANIFEST + workspace guide consolidates without losing expressiveness.

**B. Fully agnostic kernel — Reviewer figures out organization from filesystem alone.** Considered; rejected for two reasons: (a) cold-start cost — every Reviewer wake spends tokens reasoning about structure before doing work; (b) operator predictability — debugging "why didn't the Reviewer perceive X" requires knowing what the Reviewer expects to find, which a workspace-guide makes inspectable, but pure-figure-it-out makes opaque. The workspace guide is the legible declaration of conventions; the Reviewer reasons over substrate, not over conventions-it-discovered.

**C. Two files (`_substrate_abi.yaml` machine-parsed + `_substrate_semantics.md` LLM-readable).** Considered; rejected per §2.D3 sync-problem analysis. One file with frontmatter+prose (the `_money_truth.md` pattern, ADR-254-grandfathered) eliminates sync drift while honoring format-by-axiomatic-fit.

**D. Bundle authors workspace guide directly via deterministic templating (no genesis-by-Reviewer).** Considered; rejected because it loses the "engine-jump-start" property — the Reviewer's continuous-operation discipline starts at moment-zero of workspace life when it authors its own workspace guide, exactly as it will author Schedule calls and judgment_log entries thereafter. Deterministic templating would keep substrate authoring as a one-time kernel-script concern divorced from Reviewer's standing-intent operation.

**E. New kernel registry for substrate roles parallel to `task_types.py`.** Considered; rejected. Re-creates the exact pattern ADR-224 tore down: a kernel registry containing program-specific paths the kernel reads for runtime dispatch. Same problem one layer up; same architectural fix (move to bundles, read at point-of-use).

**F. Ship `decisions.md` rename + single-writer contract as a separate parked ADR (the original "Judgment Lineage Substrate" draft).** Considered; rejected after drafting and reviewing both as a pair. Every load-bearing decision in the parked draft was already absorbed by this ADR's role taxonomy + workspace-guide-driven lock policy; keeping the separate ADR would have created two-source-of-truth drift (Singular Implementation violation). The judgment_log work is now §5 of this ADR — a worked example demonstrating the mechanism end-to-end on the smallest concrete case, not a parallel spec.

---

## 10. Drift catalog (empirical, full enumeration)

Grep audit of `api/` (excluding `__pycache__`, tests, `docs/programs/`) for program-domain path strings (`context/trading`, `context/commerce`, `context/defi`). 52 total sites:

### Class 1 — Load-bearing kernel reads (24 sites — closes Phase 1+2)

| File | Lines | Closes |
|---|---|---|
| `services/workspace_paths.py` | 147, 148, 149, 150 | Phase 1 (D6.a) |
| `services/reviewer_envelope.py` | 53, 54, 55, 56, 95, 96, 97 | Phase 2 (D6.b) |
| `agents/reviewer_agent.py` | 1309, 1400 | Phase 2 (D6.b — read_signal_files glob) |
| `services/risk_gate.py` | 7, 34, 48, 84, 95, 429 | Out of scope (program-specific code; future bundle-relocation ADR) |
| `services/review_proposal_dispatch.py` | 355 | Phase 2 (reads risk_gate path; updates with risk_gate relocation) |
| `services/execution_router.py` | 223 | Phase 2 (reads `_performance.md` via hardcoded path; refactor to workspace-guide envelope) |
| `services/primitives/track_regime.py` | 5, 61, 394 | Out of scope (program-specific primitive; alpha-trader bundle code) |
| `services/primitives/track_universe.py` | 6, 16, 66, 145, 158, 250, 264 | Out of scope (program-specific primitive) |
| `services/primitives/schedule.py` | 71 | Out of scope (alpha-trader-specific bundle prompt example in code) |

### Class 2 — Persona prose (9 sites — closes Phase 3)

| File | Lines | Closes |
|---|---|---|
| `agents/prompts/tools_core.py` | 36, 87, 88, 150 | Phase 3 (D6.c — replace with workspace-guide pointer) |
| `agents/prompts/platforms.py` | 91, 95 | Phase 3 (relocate program-specific guidance to bundle-shipped persona overlay) |
| `agents/prompts/chat/workspace.py` | 239 | Phase 3 |
| `agents/cockpit_awareness.py` | 74 | Phase 3 (auto-generated section gains workspace-guide reference) |
| `agents/prompts/headless/base.py` | 27 | Phase 3 (signal log glob; workspace-guide pointer) |

### Class 3 — Cockpit FE routes (9 sites — out of scope)

| File | Lines | Closes |
|---|---|---|
| `routes/cockpit.py` | 314, 315, 316, 327, 329, 330, 358, 407, 458 | Out of scope (ADR-225 compositor — program-shaped cockpit faces are program-shaped by design per ADR-273) |

### Class 4 — Oneshot scripts (3 sites — bundle-coupled by intent)

| File | Lines | Closes |
|---|---|---|
| `scripts/oneshot/phaseB_unify_recurrences.py` | 132, 146, 149 | Out of scope (one-time alpha-trader bootstrap; intended program-coupling) |

### Closure summary
- **Phase 1 closes:** 4 sites (workspace_paths.py)
- **Phase 2 closes:** 13 sites (reviewer_envelope.py, reviewer_agent.py glob, review_proposal_dispatch.py, execution_router.py)
- **Phase 3 closes:** 9 sites (persona prose)
- **Phase 1+2+3 total:** **26 of 52 sites closed**, plus risk_gate.py (6 sites) flagged for future bundle-relocation
- **Out of scope:** Class 3 (9 sites — ADR-225 compositor scope) + Class 4 (3 sites — intended) + program-specific primitives (10 sites — bundle-shipped code)

The remaining out-of-scope sites are honest program-shaped code that belongs in alpha-trader-bundle territory rather than kernel `api/services/` territory; relocating them is a future bundle-architecture ADR distinct from this ADR's substrate-pedagogy scope.

**Final grep gate** (Phase 3 acceptance): `grep -rn -E "context/(trading|commerce|defi)" api/agents/ api/services/workspace_paths.py api/services/reviewer_envelope.py api/services/primitives/workspace.py` returns zero matches. The narrower scope reflects the ADR's intent — substrate-pedagogy (kernel/agent perception) is closed; program-specific primitives (bundle-shipped code) remain bundle-coupled by design.

---

## 11. Discourse trail

This ADR consolidates the entire 2026-05-15 substrate-topology discourse:

1. Operator observed three identical "I read 4 files and stood down" entries in `decisions.md` over 24h on kvk's workspace (post-ADR-276 deploy).
2. First proposal: single-writer contract for `decisions.md` (drafted as a parked sibling ADR, dissolved into §5 of this ADR per Singular Implementation discipline).
3. Operator pushed: *"are we creating file naming to folder structure taxonomies that are not agnostic in nature?"* — opened the substrate-topology question.
4. First substrate-topology ADR drafted (deleted same day) — went straight to mechanism (lock policy refactor, envelope program-parameterization). Operator caught it: *"why do i feel like your focusing on the wrong information … the latter part was about the rather axiomatic change considerations, even focusing on the naming of the framing towards Agent OS more native ABI."*
5. Re-derivation: the question wasn't *should we be more agnostic* (Principle 16 already commits this) — it was *we drifted from Principle 16 and need to honor it at the substrate-paths + persona-pedagogy layers*.
6. Naming converged on **Substrate ABI** (parallel to Syscall ABI from Principle 16; symmetric ABI surfaces, opposite directions).
7. Phase 1 scope converged on lock-policy-only as the smallest meaningful slice; wake envelope reserved for Phase 2 to honor ADR-276's recency.
8. Stress test of how/what split against six concrete scenarios validated the architecture.
9. Discovered that Authored Substrate teaching is scattered across 8+ persona-prose files today — pedagogically second-class despite being architecturally first-class. Operator's instinct: consolidate Substrate ABI + Authored Substrate pedagogy into one operator-readable workspace guide.
10. Genesis-by-Reviewer mechanism: the Reviewer authors the workspace guide at first wake, eliminating cold-start ("jump-starting the engine through the same mechanism that runs continuously afterward").
11. D-Drift principle (descriptive cartilage, not prescriptive bone) collapsed two design questions (operator drift, bundle ABI updates) into one author-agnostic future-proof discipline.
12. Single-file frontmatter+prose pattern (`_money_truth.md`-grandfathered) chosen over two-file split to eliminate sync risk.
13. Empirical grep audit established the 52-site drift catalog; phase scoping closes 26 sites at the substrate-pedagogy layer with the remainder honestly flagged as bundle-shipped code or compositor scope.
14. Final consolidation pass: the parked sibling ADR (judgment_log) was dissolved into §5 of this ADR after both were drafted as a pair and review confirmed every load-bearing decision was already absorbed. Singular Implementation honored — one ADR, one source of truth, one concrete worked example demonstrating the mechanism end-to-end.

**This ADR is the singular ADR for the substrate-pedagogy work.** No parked sibling, no parallel spec. The judgment_log file (§5) is the smallest concrete demonstration that the role taxonomy + workspace-guide-driven lock policy + writer-discipline contract land cleanly on a real file — included as part of this ADR's implementation, not as a follow-on.
