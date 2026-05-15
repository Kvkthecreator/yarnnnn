# ADR-281: Substrate-Canonical, Substrate-Only Prompts — The Kernel Does Not Compute for the Prompt

**Status**: Proposed (2026-05-15) — Implementation in flight as one atomic revision
**Date**: 2026-05-15
**Dimensional classification**: **Substrate** (Axiom 1) primary — derives the wake-envelope shape from substrate-canonical-world; **Mechanism** (Axiom 5) secondary — names the kernel/program partition for prompt-time computation; **Identity** (Axiom 2) tertiary — preserves the library/librarian partition from ADR-280.

**Supersedes**: [ADR-280](ADR-280-substrate-abi-workspace-guide.md). ADR-280 reached its Phase 1 + dissolution + Stream A milestones (commits `7d3013b` + `43374cf` + `c7e1c84` + `3ebfb8e`) but went through two wrong-shape architectural revisions before its derivation settled (genesis-by-Reviewer empirically falsified; `ENVELOPE_SUMMARIZERS` registry empirically derived as an Axiom 1 violation). Each revision left the ADR thicker without sharpening canon. Per Singular Implementation discipline ("delete boldly that which isn't true"), ADR-280 is superseded in full; ADR-281 starts from the substrate-canonical-world axiom and derives the architecture cleanly.

**Implements (extends)**: [ADR-222](ADR-222-agent-native-operating-system-framing.md) (OS framing — finishes Principle 16's "no kernel touch" commitment at the substrate-paths layer), [ADR-224](ADR-224-kernel-program-boundary-refactor.md) (extends boundary refactor from registries to substrate paths + persona pedagogy), [ADR-188](ADR-188-domain-agnostic-framework.md) (registries as template libraries), [ADR-209](ADR-209-authored-substrate.md) (every write attributed and retained — load-bearing for bundle-fork attribution + Reviewer revision), [ADR-264](ADR-264-substrate-canonical-world-and-syncplatformstate.md) (substrate-canonical world — extends from external-system state to derivative-compaction state), [ADR-275](ADR-275-introspection-cadence-reviewer-authored.md), [ADR-276](ADR-276-reactive-trigger-envelope-governance-preload.md), [ADR-277](ADR-277-feed-emission-policy.md).

**Amends**: [ADR-258 revised](ADR-258-reviewer-as-personified-chat-mode-operator.md) D9 (lock policy composition unchanged from Phase 1; this ADR doesn't touch it), [ADR-194 v2](ADR-194-reviewer-layer-and-impersonation.md) (Reviewer's `decisions.md` semantics tighten to single-writer judgment lineage; renamed `judgment_log.md` per §6).

**Preserves from ADR-280** (the parts that were correctly derived):
- Library/librarian partition (Axiom 2 application — the bundle is the library; the Reviewer is the librarian)
- Bundle MANIFEST `substrate_abi` declarations as authority for program-shaped substrate topology
- Six-role taxonomy (`operator-canon` / `reviewer-workbench` / `system-ledger` / `world-mirror` / `running-narrative` / `kernel-index`)
- Workspace guide as bundle-shipped operator-canon at `reference-workspace/_workspace_guide.md` + kernel-default for no-program workspaces
- Lock policy 4-layer composition (kernel-defaults + bundle MANIFEST + workspace-guide overrides + legacy `_locks.yaml`)
- All Phase 1 + dissolution + Stream A code already shipped (commits `7d3013b` + `43374cf` + `c7e1c84` + `3ebfb8e`) — the bundle MANIFEST authority pattern, lock-policy composition, persona prose path-string cleanup, drift-catalog grep gate. ADR-281 revises one specific piece of Stream A (the `ENVELOPE_SUMMARIZERS` registry + summarizer pattern) and otherwise preserves the shipped work.

**Preserves**: FOUNDATIONS Axioms 1–9, Derived Principles 1–18.

**Adds**: New Derived Principle (numbered against current FOUNDATIONS) — **"The kernel does not compute for the prompt."** See §3 below.

---

## 1. Derivation chain (axiomatic)

ADR-281 derives the wake-envelope architecture from the FOUNDATIONS axioms, in four steps. Each step is a direct application of an existing axiom; nothing here is new commitment beyond the Derived Principle that names the result.

### Step 1 — Substrate is where state lives (Axiom 1)

> *"What persists lives in files. Nothing else persists."*
> *"Computation is stateless. Every component reads the filesystem, acts, writes the filesystem, and terminates. State persists only in files across invocations."*

Stateless computation is the load-bearing property. Components that produce state-shaped data without writing it to substrate violate the axiom — the data evaporates between invocations; the next invocation has no record it existed.

### Step 2 — Substrate is the bus, not the side-effect (Axiom 1 fourth sub-clause, hardening 2026-05-11)

> *"Substrate is not the place the runtime stores its outputs; substrate is the place the runtime exists. Implementation collisions with this sub-clause — e.g., Reviewer-to-System-Agent direct return values, in-memory caches that bypass substrate writes, parallel control planes — are Axiom 1 violations."*

The runtime Loop runs *over* substrate. Reviewer reads substrate; Reviewer directs the System Agent; System Agent writes substrate; the next Loop wake-up reads what the previous wake-up wrote. There is no parallel control-flow channel.

A kernel function that runs at prompt-assembly time, reads N substrate files, computes a compact representation, and embeds the result in the LLM's prompt — without writing the compact representation back to substrate — **is exactly the "in-memory cache that bypasses substrate writes" pattern this sub-clause names as a violation.**

### Step 3 — Every piece of state the Reviewer reasons about lives in substrate (Axiom 1 third sub-clause, ADR-264)

> *"The workspace's substrate is the workspace's complete model of the world, including state that originates in external systems. Judgment reads substrate. It does not call external APIs as primary perception."*

ADR-264 supplied this for *external* state: broker positions, account balances, signal evaluations, news, etc. — mediated into substrate by `mechanical`-mode recurrences invoking deterministic Python primitives. The principle is broader than the originating ADR's scope: **any state the Reviewer reasons about must live in substrate, regardless of whether the state's origin is external (broker API), internal (operator authoring), or *derivative* (compaction of other substrate).**

If the Reviewer reasons about "the compact summary of all signal files," then the compact summary IS state the Reviewer reasons about. Per Step 3, that state must live in substrate. The mechanism for getting derivative-compaction state into substrate is the same as for external state: a deterministic primitive writes it.

### Step 4 — Therefore: the wake envelope reads substrate; it does not compute substrate

The wake envelope is the kernel's prompt-assembly layer. Per Steps 1–3:
- It reads substrate files declared by the bundle's `substrate_abi.reviewer_wake_envelope` and the kernel-universal envelope set.
- It does not run summarization, aggregation, glob-scan-and-compose, or any other substrate-derivative computation at prompt-assembly time.
- For state that needs compaction (signal-state summary, customer aggregates, position summaries, any future case), the **bundle ships a mechanical-mode recurrence** that writes the compact form to a substrate file at known cadence. The Reviewer's wake envelope reads that file like every other substrate file.

This is the architecture. Bundle MANIFEST `reviewer_wake_envelope` declarations have **one shape**: `{key, path, optional}`. There is no `path_glob` shape. There is no `summarizer` field. There is no `ENVELOPE_SUMMARIZERS` registry.

---

## 2. Why this is closer to Claude Code's design — and why that's load-bearing

The derivation in §1 produces an architecture structurally identical to Claude Code's substrate-access model:

| Concern | Claude Code | YARNNN (ADR-281) |
|---|---|---|
| Filesystem access | `Read`, `Write`, `Edit`, `Glob`, `Grep` primitives — return raw substrate content | Same shape: envelope reads substrate files; primitives access substrate as substrate |
| Aggregation / summarization | Model does it in reasoning context after `Read`-ing the files | Done *before* the wake by mechanical primitives writing substrate; envelope reads the substrate |
| Memory / persistence | CLAUDE.md, MEMORY.md as filesystem state the model reads | Workspace guide + operator-canon files as substrate the Reviewer reads |
| Hooks / pre-session work | User configures hooks that run before model session, can write files | Mechanical-mode recurrences write substrate between Loop wake-ups |
| Kernel pre-computation for prompt | **None** — the kernel returns substrate content unchanged | **None** — substrate-time computation only |

What YARNNN adds beyond Claude Code is structural, not behavioral:
- **Authored Substrate (ADR-209)** — every write attributed and retained. Claude Code uses git on top; YARNNN canonizes attribution at the substrate layer.
- **Personification (Reviewer + Agents per Axiom 2)** — the librarian operates on standing intent (scheduled wakes, not just request-response).
- **Substrate-canonical world (ADR-264)** — external state is mirrored into substrate by mechanical primitives, never read live at LLM-prompt time.

These additions sharpen the substrate-access model; they don't change its shape. **Where YARNNN must NOT diverge from Claude Code is in how the kernel relates to the model's prompt** — substrate access only, no kernel-side prompt-time computation. ADR-280's `ENVELOPE_SUMMARIZERS` was YARNNN inventing kernel-side prompt-computation that Claude Code's design correctly rejects and that YARNNN's own Axiom 1 forbids.

---

## 3. New Derived Principle: "The kernel does not compute for the prompt"

This principle joins FOUNDATIONS Derived Principles in the same commit chain as this ADR.

> **The kernel does not compute for the prompt.** The wake envelope reads substrate; it does not derive new state at prompt-assembly time. Any computation that produces state-shaped data (summary, aggregation, compaction, projection) must write its result to substrate first; the envelope reads that substrate like every other substrate file. Per-wake LLM-prompt-time computation that produces state without writing it to substrate is an Axiom 1 violation (substrate-as-bus, fourth sub-clause).

**Diagnostic test**: if a kernel function takes substrate inputs and produces a string that goes directly into an LLM prompt without first being written to substrate, the function violates this principle. The fix is always the same shape: move the computation to a mechanical primitive; have it write the result to substrate; let the envelope read the substrate file.

**Mechanism**: the substrate-mirror pattern from ADR-264 (`SyncPlatformState` for external state) generalizes — a mechanical-mode recurrence invokes a deterministic primitive that writes derivative substrate at known cadence. Derivative-compaction substrate has the same canonical-home discipline as external-mirror substrate: written by a named primitive, attributed via ADR-209, retained in the revision chain, read by the envelope as a normal `path` entry.

**Future-proofing**: this principle prevents the same class of violation from re-emerging. Future cases (per-customer aggregation for alpha-commerce, per-position compaction for portfolio reconciliation, news-feed compaction, etc.) all map cleanly to substrate-mirror-via-mechanical-primitive. None need a summarizer registry.

---

## 4. Decision

### D1 — Bundle MANIFEST `reviewer_wake_envelope` has one declaration shape

```yaml
substrate_abi:
  reviewer_wake_envelope:
    - key: <field_name>          # field name in the envelope dict
      path: <relative_path>      # absolute workspace-relative path to a substrate file
      optional: true|false       # whether absence is tolerated (default false)
```

No `path_glob`. No `summarizer`. One shape, axiomatically derived. Per Singular Implementation, the alternative shape (`path_glob + summarizer`) is deleted from the schema and from any bundle MANIFEST that declares it.

For substrate that needs compaction, the bundle declares:
1. A mechanical-mode recurrence in `_recurrences.yaml` that writes the compact substrate file.
2. A `path` envelope entry pointing at the compact substrate file.

### D2 — Kernel envelope helper reads substrate; never computes

```python
# services/reviewer_envelope.py — post-ADR-281
async def load_reviewer_governance_envelope(client, user_id):
    # Universal envelope reads (kernel-shipped — present in every workspace).
    universal_results = await _read_universal_envelope(client, user_id)

    # Program-shaped reads — bundle-declared paths only.
    abi = bundle_reader.get_substrate_abi_for_workspace(user_id, client)
    program_reads = {}
    for decl in abi.get("reviewer_wake_envelope", []):
        # One declaration shape: {key, path, optional}.
        program_reads[decl["key"]] = await _read(decl["path"])

    return {**universal_results, **program_reads}
```

`ENVELOPE_SUMMARIZERS` registry is **deleted**. `_summarize_signal_files` function in the kernel is **deleted**. The `path_glob + summarizer` dispatch branch in the envelope-assembly loop is **deleted**.

### D3 — Derivative-compaction substrate is bundle-shipped, written by mechanical primitives

Bundles ship the mechanical-mode recurrence + the substrate-write primitive. The kernel hosts the *primitive surface* (the same way `SyncPlatformState` is kernel-shipped per ADR-264) but the bundle invokes it from a `_recurrences.yaml` entry with bundle-specific arguments.

For alpha-trader: a new mechanical primitive `MirrorSignalState` reads the raw signal yaml files and writes a compact `_signals_summary.md` substrate file. A new mechanical-mode recurrence in alpha-trader's bundle invokes this primitive at the same cadence the existing `track-positions` / `track-orders` mirrors fire (every minute during regular-hours, e.g.).

The compact substrate has:
- `authored_by="system:mirror-signal-state"` per ADR-209
- A revision chain (Reviewer can `ListRevisions` to see signal-state evolution)
- One canonical home (`_signals_summary.md` per the rule of thumb canonized in ADR-277)
- The `world-mirror` role per the six-role taxonomy (substrate written by mechanical primitives; locked from LLM writers; overwritten each fire with revision chain preserving history)

### D4 — Library/librarian partition preserved (from ADR-280)

The library/librarian partition canonized in ADR-280 §3 is structurally correct and remains canon under ADR-281. The bundle is the library; the Reviewer is the librarian; libraries exist before librarians; the Reviewer reads the inherited library and operates within it.

ADR-281 sharpens this: the library not only contains operator-canon files (MANDATE, IDENTITY, principles, the workspace guide), it also contains the **derivative-compaction substrate** that mechanical primitives write. The library has authored content (operator wrote it) AND mirrored content (mechanical primitives wrote it) AND accumulated content (Reviewer + work wrote it). The Reviewer reads all three classes uniformly — substrate is substrate.

### D5 — Lock policy composition preserved (from Phase 1)

The 4-layer lock policy composition (kernel-defaults + bundle MANIFEST + workspace-guide overrides + legacy `_locks.yaml`) shipped in commit `7d3013b` is correct under ADR-281 and remains canon. No changes.

### D6 — Workspace guide preserved (from ADR-280 dissolution)

The bundle-shipped workspace guide at `reference-workspace/_workspace_guide.md` + kernel-default `DEFAULT_WORKSPACE_GUIDE_MD` for no-program workspaces shipped in commit `43374cf` is correct under ADR-281 and remains canon. The workspace guide's frontmatter mirrors the bundle MANIFEST's `substrate_abi` declarations (operator-and-Reviewer-readable view of what the bundle declares).

The workspace guide frontmatter's `reviewer_wake_envelope` section updates in this revision to use the path-only declaration shape (matching the bundle MANIFEST schema change in D1). This is a small substrate revision; existing workspaces' guides are updated by the existing migration mechanism on next workspace-guide regeneration.

---

## 5. Implementation: what ships in this revision

### 5.1 Kernel changes (deletions)

- `api/services/reviewer_envelope.py`:
  - Delete `ENVELOPE_SUMMARIZERS` registry constant.
  - Delete `_summarize_signal_files` function.
  - Simplify the envelope-assembly loop: only handle `path` declarations; delete the `path_glob + summarizer` dispatch branch.
  - Delete the `summarizer` parameter type alias (`SummarizerFn`).

### 5.2 Kernel changes (additions)

- New primitive `MirrorSignalState` in `api/services/primitives/` (likely `mirror_signal_state.py` matching the `SyncPlatformState` location pattern). Inputs: source glob, output path. Reads the raw signal yaml files, regex-extracts `triggered_today` + `state` per file, composes the compact summary, writes via `write_revision` with `authored_by="system:mirror-signal-state"`.
- Primitive registered in `HEADLESS_PRIMITIVES` registry (per ADR-264 pattern for `SyncPlatformState`); not exposed to chat or Reviewer (operators don't invoke directly; mechanical-mode recurrences invoke).

### 5.3 Bundle changes (alpha-trader)

- `docs/programs/alpha-trader/MANIFEST.yaml`: `substrate_abi.reviewer_wake_envelope` `signal_files` entry shape changes:
  ```yaml
  # Before (ADR-280):
  - key: signal_files
    path_glob: context/trading/signals/*.yaml
    summarizer: signal_files
    optional: true
  # After (ADR-281):
  - key: signal_files
    path: context/trading/_signals_summary.md
    optional: true
  ```
- `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml`: new mechanical-mode recurrence `mirror-signal-state` invoking `@primitive: MirrorSignalState(source="context/trading/signals/*.yaml", output="context/trading/_signals_summary.md")` at minute cadence during regular-hours.
- `docs/programs/alpha-trader/reference-workspace/_workspace_guide.md`: frontmatter `reviewer_wake_envelope.signal_files` entry shape updated to match; prose body's "What this workspace contains" section updated to note `_signals_summary.md` as world-mirror substrate.

### 5.4 Bundle changes (alpha-commerce)

alpha-commerce's MANIFEST didn't use the `path_glob + summarizer` shape (no entries needed it); no changes required. Bundle workspace guide unchanged.

### 5.5 Documentation

- `docs/adr/ADR-280-substrate-abi-workspace-guide.md`: status flips to **Superseded by ADR-281 (2026-05-15)**. One-paragraph dissolution rationale at top: "Drafted 2026-05-15; reached Phase 1 + dissolution + Stream A milestones (commits 7d3013b + 43374cf + c7e1c84 + 3ebfb8e). Two architectural revisions surfaced empirical falsifications (genesis-by-Reviewer; ENVELOPE_SUMMARIZERS registry as Axiom 1 violation). ADR-281 supersedes by deriving the architecture cleanly from the substrate-canonical-world axiom + new Derived Principle 'the kernel does not compute for the prompt.' Preserves Phase 1 + dissolution + Stream A shipped work; revises only the summarizer machinery." Body of ADR-280 preserved as historical artifact; rest of canon is in ADR-281.
- `docs/adr/ADR-223-program-bundle-specification.md`: `substrate_abi` schema doc at §3.bis updated — drop the `path_glob + summarizer` declaration shape. One declaration shape: `{key, path, optional}`. Update validation rules to match.
- `docs/architecture/FOUNDATIONS.md`: add new Derived Principle (numbered against current FOUNDATIONS) — *"The kernel does not compute for the prompt"* — with the §3 derivation as the prose.
- `CLAUDE.md`: ADR list gains ADR-281 entry (and notes ADR-280 superseded).
- `api/prompts/CHANGELOG.md`: entry per protocol noting the kernel-side dissolution.

### 5.6 Tests

- `api/test_adr280_stream_a.py`: rename to `api/test_adr281_envelope_path_only.py`; update tests:
  - Delete `test_envelope_summarizers_registry_exists` (registry no longer exists).
  - Delete `test_summarize_signal_files_relocated_to_envelope_module` (function deleted entirely).
  - Add `test_envelope_summarizers_deleted` (assert the constant + function don't exist).
  - Add `test_envelope_assembly_path_only` (assert the loop only dispatches on `path`, not `path_glob`/`summarizer`).
  - Add `test_alpha_trader_envelope_uses_path_only_shape` (asserts MANIFEST decl is path-only).
  - Add `test_mirror_signal_state_primitive_exists` (asserts the new primitive is registered).
  - Preserve passing tests covering bundle MANIFEST authority, lock policy, persona prose path-string cleanup, grep gate.

### 5.7 Migration

The shipped Stream A code is correct in its preserved scope (bundle MANIFEST authority, lock policy composition, relocations, grep gate). Only the summarizer machinery dissolves. No DB migration needed — the workspace guides on kvk's live workspaces still have the path-only envelope decl shape (or the now-defunct `path_glob + summarizer` shape; the kernel will simply ignore unknown declaration keys per the simplified loop).

For the `_signals_summary.md` substrate to populate on kvk's workspace, the `mirror-signal-state` recurrence needs to fire at least once. The next reactive Reviewer wake will see an empty `signal_files` envelope entry until the mirror recurrence runs once; then subsequent wakes see the populated substrate. Acceptable transition.

---

## 6. The judgment_log worked example (preserved from ADR-280 §5)

The judgment_log substrate (Stream B work in ADR-280, preserved as Stream B work under ADR-281): rename `decisions.md` → `judgment_log.md`; single-writer infrastructure-rendered contract; deterministic 5-condition material-outcome gate; delete `append_recurrence_fire` blanket write; bundle workspace guides declare `judgment_log.md → system-ledger`. **Unchanged from ADR-280 §5.** This worked example demonstrates the role taxonomy + bundle-driven lock policy + writer-discipline contract land cleanly on a real file. Ships as Stream B (next commit window).

---

## 7. Stream B (librarian activation) preserved from ADR-280

Stream B scope unchanged from ADR-280 §4:
- Persona prose librarian-pedagogy rewrite across 9 persona-prose files
- Judgment lineage substrate (the §6 worked example)
- First-wake validation against kvk's live workspace
- Documentation cascade (FOUNDATIONS Axiom 1 fifth sub-clause + Derived Principles + GLOSSARY entries + Tier 2/3 doc references)

This ADR (ADR-281) ships the kernel-side substrate-canonical revision (this is what was Stream A's `ENVELOPE_SUMMARIZERS` portion); Stream B follows in a separate commit window.

---

## 8. Acceptance criteria

### Phase 1 (Implemented 2026-05-15 — commit `7d3013b`)
- [x] Bundle MANIFEST `substrate_abi` declarations + bundle_reader extensions
- [x] Workspace guide infrastructure (kernel default + bundle-shipped + reader)
- [x] Lock policy 4-layer composition
- [x] `DEFAULT_REVIEWER_WRITE_LOCKS` shrunk to kernel-universal only
- [x] Phase 1 regression gate

### Dissolution (Implemented 2026-05-15 — commit `43374cf`)
- [x] Genesis-by-Reviewer machinery deleted
- [x] Bundle-shipped workspace guides shipped
- [x] Live migration succeeded against 5/5 workspaces

### Stream A — preserved portion (Implemented 2026-05-15 — commit `3ebfb8e`)
- [x] Wake envelope reads bundle MANIFEST via `bundle_reader`
- [x] Hardcoded `context/trading/*` paths removed from kernel-perception files
- [x] Persona prose path-string cleanup
- [x] Drift-catalog grep gate

### Stream A — revised portion (this ADR, ADR-281)
- [ ] `ENVELOPE_SUMMARIZERS` registry deleted; `_summarize_signal_files` deleted; `path_glob + summarizer` dispatch deleted.
- [ ] `MirrorSignalState` mechanical primitive added; registered in `HEADLESS_PRIMITIVES`.
- [ ] alpha-trader bundle: `mirror-signal-state` recurrence added to `_recurrences.yaml`; MANIFEST envelope decl + workspace guide envelope decl updated to path-only shape.
- [ ] ADR-280 status flipped to Superseded with one-paragraph dissolution rationale at top.
- [ ] ADR-223 §3.bis schema updated to drop `path_glob + summarizer` shape.
- [ ] FOUNDATIONS gains new Derived Principle: *"The kernel does not compute for the prompt."*
- [ ] Tests renamed + updated: `test_adr281_envelope_path_only.py`. Assertions: registry deleted; function deleted; envelope path-only; alpha-trader MANIFEST path-only; primitive registered.
- [ ] CHANGELOG.md entry per protocol.
- [ ] Sibling regression: ADR-274, ADR-275, ADR-276 + Phase 1 tests continue to pass.

### Stream B (next commit window, scope preserved from ADR-280 §4)
- [ ] Persona prose librarian-pedagogy rewrite
- [ ] Judgment lineage substrate (rename + single-writer contract + material-outcome gate)
- [ ] First-wake validation
- [ ] Documentation cascade

---

## 9. Rejected alternatives

**A. Keep `ENVELOPE_SUMMARIZERS` registry as 1-entry-1-consumer infrastructure.** Considered; rejected per first-principles re-evaluation. The registry is an Axiom 1 violation (kernel-side prompt-time computation that produces state without substrate writes), not just speculative infrastructure. The discipline in ADR-281's Derived Principle prevents this class of pattern from re-emerging.

**B. Inline the summarizer at the call site (drop the registry, keep the function as an `elif` branch).** Considered; rejected. The inline-elif still violates the same Axiom 1 sub-clause — the kernel still computes substrate-derivative state at prompt time. Less abstracted; same architectural problem.

**C. Have the Reviewer model summarize the signal files itself (envelope returns raw file contents; model compacts during reasoning).** Considered; rejected. (a) Wake-envelope tokens grow N×~60 per signal vs. ~10 per signal compacted; not catastrophic but not free. (b) The Reviewer would re-do summarization at every wake — no substrate persistence; same Axiom 1 violation pattern, just shifted from kernel to Reviewer. (c) Substrate-mirror is the canonical pattern; uniformity beats per-case reasoning.

**D. Revise ADR-280 in place rather than supersede.** Considered; rejected. Per "delete boldly that which isn't true," ADR-280 went through three architectural revisions (genesis-by-Reviewer; ENVELOPE_SUMMARIZERS; this) — each leaving thicker scar tissue. ADR-281 starts from the axiom and derives cleanly. ADR-280 is preserved as historical artifact; ADR-281 is canon.

**E. Delete ADR-280 entirely.** Considered; rejected. The shipped commits (Phase 1 + dissolution + Stream A preserved portions) are correct and reference-able from the discourse trail. ADR-280 is the *narrative* of how the architecture was derived (with two empirical falsifications); the commits are *the fact*. Deleting the narrative makes the discourse arc less legible without changing the architecture.

---

## 10. Drift catalog (re-derived against post-ADR-281 state)

Same 52 sites as ADR-280 §10. Closure assignments updated:

- **Phase 1 closes:** 4 sites (workspace_paths.py program paths) — ✓
- **Stream A preserved portion closes:** 13 sites (reviewer_envelope.py + reviewer_agent.py glob + adjacent kernel readers) — ✓
- **ADR-281 dissolution closes:** 1 conceptual site (the `ENVELOPE_SUMMARIZERS` registry pattern as Axiom 1 violation; not a literal program-path drift but a structural drift)
- **Stream B closes:** ~9 sites (persona prose librarian-pedagogy)
- **Out of scope (per §7):** Class 3 (9 cockpit FE routes — ADR-225 compositor), Class 4 (3 oneshot scripts — bundle-coupled), program-specific primitives (10 sites — bundle-shipped code, future bundle-relocation ADR)

**Final grep gate** (Stream B acceptance, preserved from ADR-280): `grep -rn -E "context/(trading|commerce|defi)" api/agents/ api/services/workspace_paths.py api/services/reviewer_envelope.py api/services/primitives/workspace.py api/services/review_proposal_dispatch.py api/services/execution_router.py` returns zero matches.

---

## 11. Discourse trail

This ADR consolidates the 2026-05-15 substrate-pedagogy discourse arc, which produced ADR-280 (with two architectural revisions) and culminated in this clean derivation:

1. ADR-280 §1 originated with the `decisions.md` audit-log observation; opened the substrate-topology question.
2. ADR-280 §D4 first version proposed Reviewer-authored genesis at first wake. Phase 1 migration empirically falsified (16 successive empty-content WriteFile calls).
3. ADR-280 dissolution: workspace guide is bundle-shipped operator-canon, not Reviewer-authored. Library/librarian partition surfaced via the operator's metaphor. Migration succeeded against 5/5 workspaces.
4. ADR-280 streamline rewrote the ADR end-to-end under the librarian/library partition. Stream A + Stream B roadmap.
5. ADR-280 Stream A shipped (`3ebfb8e`) with `ENVELOPE_SUMMARIZERS` registry + `_summarize_signal_files` function for bundle-declared `path_glob + summarizer` envelope entries.
6. **Operator unease about the registry surfaced the second architectural falsification.** First-principles re-evaluation showed the registry pattern is an Axiom 1 violation (kernel-side prompt-time computation that produces state without substrate writes). The substrate-canonical-world axiom (ADR-264) extends from external state to derivative-compaction state: signals-summary is state the Reviewer reasons about, must live in substrate, must be written by a mechanical primitive, must be read by the envelope as a normal substrate file.
7. ADR-281 derives the architecture from the axioms in 4 steps (§1) and adds the new Derived Principle *"The kernel does not compute for the prompt"* (§3) so future ADRs cannot re-introduce the pattern.

The architectural property delivered: YARNNN's wake envelope is structurally identical to Claude Code's substrate-access model + Authored Substrate as first class + substrate-canonical-world for external + derivative state. The kernel reads substrate; substrate-time computation produces substrate writes; the LLM prompt sees substrate, never kernel-side prompt-time derivations.

**This is the singular ADR for the substrate-pedagogy work going forward.** ADR-280 is preserved as the discourse that produced this derivation.
