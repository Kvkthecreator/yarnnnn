# ADR-285: Holistic Wake Envelope — Kernel-Universal Classes + Bundle-Declared World-Mirror Pattern

**Status**: D3 Implemented via [ADR-301](ADR-301-reviewer-pulse-envelope.md) (2026-05-24). D5+ bundle world-mirror entries remain Proposed for separate bundle work (alpha-trader `MirrorTickerSnapshot` + `MirrorPositionState`).

> **Update 2026-05-24** — ADR-301 ratifies D3 (Recent Execution Lineage) and adds a sibling `_schedule_index.md` (the second envelope entry the 2026-05-22 schedule-self-misdiagnosis surfaced as load-bearing). ADR-301 refined D4 by piggybacking on the scheduler-tick maintenance phase (`services.kernel_mirrors`) rather than scaffolding a kernel-universal `_recurrences.yaml` entry at workspace-init. Both mirrors are kernel maintenance, not workspace work — same precedent as `reclaim_stale_locks`. The synthesis canon at [`docs/architecture/cadence-and-wakes.md`](../architecture/cadence-and-wakes.md) §8 is the canonical reference for the resulting envelope shape; this ADR is preserved as historical context for the structural taxonomy + class-discipline rule.

**Original status (preserved for trace)**: Proposed
**Date**: 2026-05-17
**Companion docs**: `docs/architecture/FOUNDATIONS.md` (Axiom 1 + Axiom 2 envelope-as-Identity-perception clarification), `docs/adr/ADR-284-standing-intent-substrate-and-occupant-envelope.md` (sibling — substrate scope this ADR consumes), `docs/adr/ADR-281-substrate-canonical-substrate-only-prompts.md` (Derived Principle 19 "kernel does not compute for the prompt" — preserved discipline this ADR honors), `api/services/reviewer_envelope.py` (the mechanism this ADR reshapes)
**Amends**: `reviewer_envelope.py` (envelope-class accounting becomes explicit, not implicit-in-list-order); bundle MANIFEST `substrate_abi.reviewer_wake_envelope` schema (gains semantic role-tag per entry); alpha-trader MANIFEST + workspace_guide (world-mirror declarations grow to lift per-ticker, per-position state); new mechanical primitive `MirrorRecentExecution`; new mechanical primitive `MirrorTickerSnapshot` (alpha-trader-specific, bundle-shipped)
**Preserves**: ADR-281 §1 derivation chain ("substrate is canonical, prompt sees only substrate, kernel does not compute for the prompt"); ADR-281 §3 six-role taxonomy + write-policy semantics; ADR-209 Authored Substrate attribution for every write; bundle envelope-declaration mechanism (kernel reads MANIFEST; bundle declares additions); Singular Implementation for envelope helper (one helper, two callers — feed.py + invocation_dispatcher)

## Context

ADR-284 (sibling) introduced two kernel-universal envelope additions (OCCUPANT + standing_intent). The 2026-05-17 Reviewer-posture audit surfaced a third missing envelope class — **recent execution lineage** — and a structural pattern question that ADR-284 deliberately deferred to this ADR: **what classes of substrate should every Reviewer wake envelope carry, regardless of program?**

Today's envelope (post-ADR-281, post-ADR-275 refinement) carries:

- 6 governance entries hardcoded as kernel-universal in `reviewer_envelope.py:_UNIVERSAL_ENVELOPE_DECLS` (IDENTITY, principles, PRECEDENT, MANDATE, AUTONOMY, _preferences)
- N program entries read from active bundle's MANIFEST `substrate_abi.reviewer_wake_envelope` (alpha-trader declares 4: operator_profile, risk, performance, signal_files)
- 1 operating-context block assembled at wake time (time + timezone + market state + tenure)

The shape works mechanically but has implicit semantic structure that's invisible to bundle authors and future maintainers. Six universal entries are governance-shaped; four bundle entries are a mix of operator-canon (operator_profile, risk) + world-mirror (performance, signal_files). When alpha-author ships, it will need different world-mirror entries (corpus-coherence) and possibly its own operator-canon additions. There's no discipline rule that says "this class belongs to the kernel; this class belongs to the bundle" — every bundle author would have to re-derive the separation.

**The 2026-05-17 audit also surfaced one structural gap independent of ADR-284's standing-intent gap**: the Reviewer perceives at every wake what it should reason against (governance, framework, ground-truth substrate) but does not perceive **what the system has been doing** (recent execution lineage — what recurrences fired, what they wrote, what outcomes landed since last wake). This is the substrate counterpart to the question every operator asks first when they check in: *"what happened while I was away?"*

Without recent execution lineage in the envelope, the Reviewer must call `GetSystemState` or `ListRevisions` mid-loop to perceive system-side activity. This works but burns tool-rounds for state that's load-bearing on every wake — same shape as governance state, which is correctly pre-loaded for the same reason.

A holistic envelope reshape is overdue. The question is: **what classes are kernel-universal and what classes are bundle-declared, and what discipline rule separates them future-proofly?**

## Decision

### D1 — Envelope-class taxonomy (kernel-universal vs bundle-declared)

Every Reviewer wake envelope is composed of entries classified into one of six structural classes. The class determines who declares the entry (kernel or bundle) and which substrate role the entry's content belongs to.

| Class | Author of declaration | Substrate role | Examples | Cardinality |
|---|---|---|---|---|
| **Persona + Framework** | Bundle (extends kernel-universal IDENTITY) | `operator-canon` | IDENTITY, principles, MANDATE, AUTONOMY, PRECEDENT, _preferences (kernel-universal); _operator_profile, _risk (bundle-specific) | One file per slot, governance-shaped |
| **Seat Occupant** | Kernel-universal | `system-ledger` | OCCUPANT.md | Single file, one per Reviewer seat |
| **Standing Intent** | Kernel-universal | `reviewer-workbench` | standing_intent.md | Single file, one per Reviewer seat (ADR-284) |
| **Current World State** | Bundle-declared | `world-mirror` | alpha-trader: _signals_summary.md, future _positions_summary.md, _account_summary.md; alpha-author: corpus-coherence equivalent; alpha-commerce: customer + revenue summaries | One or more compact summary files written by mechanical primitives |
| **Recent Execution Lineage** | Kernel-universal | `running-narrative` | _recent_execution.md | Single file, kernel-universal, written by new mechanical primitive |
| **Ground-Truth Substrate** | Bundle-declared | `world-mirror` (when reconciler-written) | alpha-trader: _money_truth.md (per ADR-282 instance vocabulary); alpha-author: corpus-coherence equivalent | One or more reconciler-written files |
| **Operating Context** | Kernel-assembled at wake time | (not substrate — wake-envelope ephemeral per FOUNDATIONS Axiom 4 v8.5) | time, timezone, market state, workspace tenure | Computed at wake, not persisted |

The discipline rule that separates kernel vs bundle:

> **Kernel-universal classes are entries that apply to every persona-bearing Agent regardless of program. Bundle-declared classes are entries whose shape varies by what external state the program operates against.**

Persona + Framework, Seat Occupant, Standing Intent, Recent Execution Lineage, and Operating Context all apply to every Reviewer in every program. They are kernel-universal. Current World State and Ground-Truth Substrate vary in shape per program (a trading workspace's world state is per-ticker indicators; a screenplay workspace's world state is corpus pieces) — they are bundle-declared.

This rule is stable: adding a new program never requires modifying the kernel-universal class list. Adding new world-mirror entries within a program is a bundle MANIFEST edit. Promoting a class from bundle-declared to kernel-universal would require an ADR (because it commits the kernel to a shape every future bundle must accommodate).

### D2 — Bundle MANIFEST envelope declaration gains explicit role tag

Today's bundle declaration shape: `{key, path, optional}`. Post-ADR-285: `{key, path, role, optional}` where `role` is one of the six substrate roles per ADR-281 §3.

```yaml
reviewer_wake_envelope:
  - key: operator_profile_md
    path: context/trading/_operator_profile.md
    role: operator-canon
    optional: false
  - key: signal_files
    path: context/trading/_signals_summary.md
    role: world-mirror
    optional: true
```

The role tag is **descriptive** (it names the kind of substrate this entry points at, mirroring the file's actual role per the six-role taxonomy) and **prescriptive** (it makes envelope-class accounting explicit so bundle authors choose the correct class when adding entries).

Backward compatibility: entries without an explicit role default to `operator-canon` (the conservative default — locked from Reviewer writes per ADR-281 §3). Bundle authors should add explicit roles in the same revision they author the entry; the kernel reads role-tagged entries and consults `bundle_reader` for the per-bundle role list.

### D3 — Kernel-universal envelope additions

`api/services/reviewer_envelope.py:_UNIVERSAL_ENVELOPE_DECLS` extends from 6 entries to 9:

```python
_UNIVERSAL_ENVELOPE_DECLS: list[tuple[str, str, str]] = [
    # (key, path, role)
    # — Governance (Persona + Framework class) —
    ("identity_md",      REVIEW_IDENTITY_PATH,      "operator-canon"),
    ("principles_md",    REVIEW_PRINCIPLES_PATH,    "operator-canon"),
    ("precedent_md",     SHARED_PRECEDENT_PATH,     "operator-canon"),
    ("mandate_md",       SHARED_MANDATE_PATH,       "operator-canon"),
    ("autonomy_md",      SHARED_AUTONOMY_PATH,      "operator-canon"),
    ("preferences_yaml", SHARED_PREFERENCES_PATH,   "operator-canon"),
    # — Seat Occupant (ADR-284) —
    ("occupant_md",      REVIEW_OCCUPANT_PATH,      "system-ledger"),
    # — Standing Intent (ADR-284) —
    ("standing_intent_md", REVIEW_STANDING_INTENT_PATH, "reviewer-workbench"),
    # — Recent Execution Lineage (ADR-285) —
    ("recent_execution_md", MEMORY_RECENT_EXECUTION_PATH, "running-narrative"),
]
```

The tuple shape grows from `(key, path)` to `(key, path, role)`. The role is currently unused at envelope-load time (the envelope helper just reads paths) but becomes a contract assertion for future tooling — e.g., a regression test that asserts kernel-universal entries respect the per-class kernel-vs-bundle discipline rule from D1.

### D4 — New mechanical primitive: MirrorRecentExecution

Per Derived Principle 19 ("kernel does not compute for the prompt"), recent execution lineage must be written to substrate by a mechanical primitive at known cadence, not summarized at envelope-load time.

New primitive: `MirrorRecentExecution` in `api/services/primitives/mirror_recent_execution.py`. Reads the last N `execution_events` rows for the workspace; writes a compact markdown summary to `/workspace/memory/_recent_execution.md`. Diff-aware (no-op when summary hasn't changed). Attribution `system:mirror-recent-execution` per ADR-209.

Schema of `_recent_execution.md`:

```markdown
---
as_of: <iso8601>
window: 24h
fire_count: <int>
---

# Recent execution lineage

## Last 24h
- 2026-05-15T20:30:35Z · track-regime · mechanical · success · 1620ms
- 2026-05-15T20:02:05Z · track-account · mechanical · success · 793ms
- 2026-05-15T13:46:10Z · signal-evaluation · judgment · success · 35405ms · 32.3k input / 2.7k output tokens
- 2026-05-15T08:33:00Z · addressed turn · judgment · success · 30.2k input / 2.3k output tokens

## Notable patterns (last 7d)
- signal-evaluation: 1 fire, 0 entries, 0 trade-proposals — bootstrap state
- track-universe: 4 fires, indicators refreshed for 5 tickers
- (etc., kernel-deterministic pattern detection — counts + simple comparisons, no LLM summarization)
```

**Kernel-universal** mechanical primitive — every workspace gets this recurrence regardless of program. Cadence: `@every 30min` (deterministic; bundle doesn't author).

Scaffolded at workspace-init in `workspace_init.py` Phase 5 alongside other kernel-universal recurrences (when those exist). Today's workspace_init.py doesn't scaffold any kernel-universal recurrences (bundle-fork is the only path); the `MirrorRecentExecution` recurrence becomes the first kernel-universal recurrence. The mechanism: a small kernel-universal `_recurrences.yaml` template (just this one entry) that workspace_init writes alongside the bundle fork's recurrence content.

If the operator removes the recurrence from `_recurrences.yaml`, the envelope simply has empty `recent_execution_md` content — fail-soft per `reviewer_envelope.py:138`. The operator can re-add or schedule manually.

### D5 — Bundle world-mirror declarations grow (alpha-trader)

The 2026-05-17 audit observed that the Reviewer perceives `_signals_summary.md` (the compact summary of what fired) but does not perceive **per-ticker current state** at envelope time. The Reviewer must call `ReadFile` per ticker mid-loop to evaluate "is anything close to firing?" — which the persona prompt encourages in principle but the envelope shape teaches against (default reasoning context says nothing's actionable, so the Reviewer concludes nothing's actionable).

Per Option β from the stress-test discourse (mechanical primitive writes envelope-friendly summary file, preserves Derived Principle 19), alpha-trader gets one or two new mechanical primitives:

- `MirrorTickerSnapshot` — reads all `/workspace/context/trading/{TICKER}.yaml` files, writes a compact `/workspace/context/trading/_tickers_snapshot.md` with per-ticker current indicators + close-to-firing flags (deterministic computation: distance from each indicator threshold per declared signal — no LLM).
- `MirrorPositionState` (when positions exist) — reads `/workspace/context/portfolio/positions/{TICKER}.yaml` files, writes `/workspace/context/portfolio/_positions_snapshot.md` with per-position current state + exit-trigger flags.

Both are alpha-trader-bundle-shipped mechanical recurrences. The bundle MANIFEST `reviewer_wake_envelope` adds two entries pointing at the snapshot files:

```yaml
reviewer_wake_envelope:
  # ... existing entries ...
  - key: tickers_snapshot
    path: context/trading/_tickers_snapshot.md
    role: world-mirror
    optional: true
  - key: positions_snapshot
    path: context/portfolio/_positions_snapshot.md
    role: world-mirror
    optional: true
```

The recurrence schedule for `MirrorTickerSnapshot` mirrors `track-universe` (post-fire, deterministic compaction). `MirrorPositionState` mirrors `track-positions`. Both `fire_on_activation: true`.

These are **bundle-side additions**, not kernel-side. Alpha-author's MANIFEST will declare different world-mirror entries for its own shape (corpus-coherence per piece, etc.). Alpha-commerce's MANIFEST will declare customer + product snapshots.

### D6 — `_build_user_message` rendering

`api/agents/reviewer_agent.py::_build_user_message` adds rendering for the new envelope keys with appropriate section headings:

- `occupant_md` → `## OCCUPANT.md — Your current seat`
- `standing_intent_md` → `## standing_intent.md — What you were watching for last cycle`
- `recent_execution_md` → `## _recent_execution.md — Recent system activity (last 24h)`
- `tickers_snapshot` (bundle-declared) → `## _tickers_snapshot.md — Current universe state` (rendered when present)
- `positions_snapshot` (bundle-declared) → `## _positions_snapshot.md — Current position state` (rendered when present)

Section headings mirror the file paths so the Reviewer's persona prompt instructions ("don't cite filenames; cite the substrate concept") remain coherent — the heading itself names the file, the prompt asks the Reviewer to speak about the *concept* the file represents.

### D7 — Persona prompt amendment

`_PERSONA_FRAME` gains a new section: **"Your wake envelope teaches you what's load-bearing."** Names the envelope classes (governance, occupant, standing intent, world state, recent execution, operating context) and what to do with each. Replaces the implicit-via-section-headings teaching with explicit class-by-class guidance.

Key clauses:

- **Recent execution lineage**: "Read this first. What has the system been doing? Anything new since standing_intent.md was last updated? Anything material the operator should know?"
- **World state**: "Check current world state against what you were watching for in standing_intent.md. Did anything cross a threshold? Did anything change shape?"
- **Standing intent**: "Update before standing down. Always. The substrate counterpart to a no-fire judgment is an updated standing_intent.md — that *is* the action."

### D8 — Singular Implementation: one envelope helper, two callers, six classes

`reviewer_envelope.py::load_reviewer_governance_envelope` remains the single canonical assembly point. Both callers (feed.py addressed turns + invocation_dispatcher reactive turns) consume the same envelope shape. The function's responsibility grows minimally — same parallel-`asyncio.gather` mechanism, more entries in the gather.

The bundle-declared entries continue to flow through `bundle_reader.get_substrate_abi_for_workspace` per ADR-281 §3. No new mechanism, no parallel envelope helper, no bundle-specific envelope path.

### D9 — Implementation surface

| Layer | Change |
|---|---|
| Kernel — `api/services/workspace_paths.py` | Add `MEMORY_RECENT_EXECUTION_PATH = "memory/_recent_execution.md"` |
| Kernel — `api/services/reviewer_envelope.py` | `_UNIVERSAL_ENVELOPE_DECLS` grows from 6 to 9 entries (with role tag); class-accounting comment block added |
| Kernel — `api/services/primitives/mirror_recent_execution.py` | New mechanical primitive |
| Kernel — `api/services/primitives/registry.py` | Add MirrorRecentExecution to HANDLERS |
| Kernel — `api/services/workspace_init.py` | Phase 5 scaffolds `MirrorRecentExecution` recurrence as kernel-universal alongside any bundle fork |
| Kernel — `api/agents/reviewer_agent.py` | `_build_user_message` renders new envelope keys; `_PERSONA_FRAME` envelope-class section |
| Kernel — `services/bundle_reader.py` | (No change — already preserves arbitrary keys per entry; role tag passes through opaquely) |
| Bundle — `docs/programs/alpha-trader/MANIFEST.yaml` | Existing 4 envelope entries gain `role:` tag; 2 new world-mirror entries added (tickers_snapshot, positions_snapshot) |
| Bundle — `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` | Add `mirror-ticker-snapshot` + `mirror-position-state` mechanical recurrences (paired with track-universe + track-positions) |
| Bundle — `api/services/primitives/mirror_ticker_snapshot.py` | New mechanical primitive (alpha-trader-shipped, registered in kernel registry per ADR-281 §3 mechanism) |
| Bundle — `api/services/primitives/mirror_position_state.py` | Same |
| Canon — FOUNDATIONS Axiom 1 (sub-clause 5 envelope-as-Identity-perception clarification) | New paragraph naming the six envelope classes |
| Canon — GLOSSARY | New `Wake envelope classes` entry; sharpened `Wake envelope` entry |
| Canon — `docs/architecture/reviewer-substrate.md` | Envelope-class table added |
| Test gate — `api/test_adr285_holistic_wake_envelope.py` | Contract assertions: 9 kernel-universal entries with correct roles; mechanism handles `(key, path, role)` tuple shape; bundle MANIFEST entries accept role tag; MirrorRecentExecution + MirrorTickerSnapshot + MirrorPositionState primitives exist and write correct paths |

### D10 — Phasing relative to ADR-284

ADR-284 lands first. Phase 1 (canon + kernel substrate) + Phase 2 (bundle amendments) ship as two commits. Then ADR-285 lands:

| Order | Commit | Scope |
|---|---|---|
| 1 | ADR-284 Phase 1 | Canon + kernel substrate for OCCUPANT + standing_intent |
| 2 | ADR-284 Phase 2 | Alpha-trader bundle amendments for standing_intent posture |
| 3 | **ADR-285 Phase 1** | Kernel-universal envelope class accounting + MirrorRecentExecution primitive + persona prompt envelope-class section + canon updates |
| 4 | **ADR-285 Phase 2** | Alpha-trader bundle world-mirror additions (MirrorTickerSnapshot + MirrorPositionState + MANIFEST envelope additions) |

Each commit is independently green (test gate + regression sweep across sibling ADRs).

### D11 — Out of scope (deferred)

- **Bundle envelope-class enforcement** (regression test that rejects bundle entries with `role: kernel-universal-class`). Useful future tooling; not required for landing.
- **Operator-level envelope overrides** (`/workspace/_envelope_overrides.yaml` operator-canon file extending bundle envelope). Same as ADR-284 D10 — not needed for current alpha.
- **Alpha-author + alpha-commerce world-mirror entries**. Those bundles will declare their own per-program world-mirror entries when shipped. ADR-285 establishes the pattern; alpha-trader is the first instance.
- **MirrorRecentExecution pattern detection**. Phase 1 ships only the counts + simple comparisons. Smarter pattern detection (drift, anomalies, expectancy shifts) can extend the primitive in future ADRs without changing the envelope mechanism.
- **Per-class envelope size budgeting**. Token-budget governance per envelope class. Not needed at current volumes; flagged for future pressure (if envelope crosses ~50k tokens cumulatively, this becomes worth addressing).

## Why this is structurally right

The envelope mechanism today works mechanically but its semantic structure is invisible — bundle authors must re-derive what belongs in kernel-universal vs bundle-declared per their bundle. ADR-285 makes the structure explicit, future-proof, and self-documenting.

The discipline rule (kernel-universal = applies to every Agent; bundle-declared = varies by external state shape) is stable under the stress tests run during the discourse:

- alpha-author ships → declares its own bundle world-mirror entries; doesn't need kernel changes ✓
- operator wants to add envelope entries → flagged for future operator-overrides ADR; doesn't break the rule ✓
- kernel-universal class changes (e.g., standing_intent.md schema evolves) → audit bundles that reference the file; same discipline as today's kernel-constant changes ✓

The kernel/program separation respects Derived Principle 19 (kernel doesn't compute for the prompt) at every envelope class — every entry is a path the helper reads; no entry is a kernel-side summarization. Compaction substrate (signals_summary, tickers_snapshot, positions_snapshot, recent_execution) is written by mechanical primitives at known cadence, not summarized at envelope-load time.

The architectural payoff:

1. **Standing intent + occupant** (ADR-284) become first-class envelope perceptions.
2. **Recent execution lineage** becomes substrate the Reviewer reads first on every wake — "what has the system been doing?" gets answered before "what should I do?"
3. **Current world state** becomes envelope-visible at bundle-declared paths, so the Reviewer can perceive "is anything close to firing?" without burning tool-rounds on per-file reads.
4. **Bundle authoring discipline** becomes explicit — the role tag + class taxonomy give bundle authors a clear shape to follow when declaring world-mirror entries.
5. **Future-proofness** — adding a new bundle requires zero kernel changes; the envelope mechanism handles any bundle declaring substrate-only entries with role tags.

No new substrate roles. No new envelope mechanism. One new kernel-universal mechanical primitive (MirrorRecentExecution). Two new alpha-trader-bundle mechanical primitives. Targeted amendments to existing canon + persona prompt. The cumulative kernel surface change is small; the structural payoff is large.
