# ADR-286: Kernel/Program Substrate Boundary — Single-Writer Per Path

**Status**: Fully Implemented (2026-05-17)

> **⚠ Amended by [ADR-384](ADR-384-the-re-founding-meaning-folders-permission-as-metadata.md) (the re-founding, FOUNDATIONS v9.13, 2026-06-29).** Single-writer-**per-path** relaxes to single-**head**, many-**authors** *for the work-commons* (the multi-principal commons many principals co-write): single-head-per-path is preserved (ADR-209 CAS), single-*author*-per-path is released, and a same-path semantic contradiction relocates the merge into the steward seat (a next-head judgment revision). **Conditioned on the single-substrate topology** (ADR-378; federation re-opens it). **Kernel-universal, bundle-owned, and `system/` paths are UNCHANGED — they stay strict single-writer.** The dual-write *elimination* this ADR achieved is preserved; what changes is that the *commons* now tolerates many attributed authors on one head-serialized path.

**Date**: 2026-05-17
**Companion docs**: `docs/architecture/FOUNDATIONS.md` (Axiom 1 + Derived Principle 16 — kernel-program boundary), `docs/architecture/GLOSSARY.md` (substrate-pedagogy clarification), `api/services/workspace_init.py` (Phase 2 kernel scaffold), `api/services/programs.py` (`fork_reference_workspace`), `api/services/workspace_utils.py` (`is_skeleton_content`)
**Amends**: ADR-269 iter-4 (`bundle_owned_paths` skip — dissolves into the single-writer rule); ADR-281 §3 substrate-pedagogy (operator-canon role inherits single-writer-per-path constraint); ADR-284 Phase 1 (OCCUPANT helper survives unchanged — already single-writer for its path)
**Preserves**: FOUNDATIONS Axiom 1 (substrate as canonical world), Derived Principle 16 (kernel-program boundary), ADR-209 Authored Substrate attribution + revision chain, ADR-281 §3 six-role taxonomy, Singular Implementation (CLAUDE.md rule #1) — this ADR is its enforcement at the substrate-write boundary

## Context

The 2026-05-17 Reviewer-posture audit surfaced a structural pattern: **the kernel writes default content for paths the bundle ALSO ships, then various rescue mechanisms try to reconcile the dual-write at fork time.** The pattern has been costing one patch per incident:

- **2026-05-13 (ADR-269 iter-4)**: AUTONOMY flip didn't propagate to kvk's workspace because kernel wrote `_autonomy.yaml` at signup; bundle-fork saw "non-skeleton content" and refused to overwrite. Fix: `bundle_owned_paths` skip in `workspace_init` Phase 2 (only when `program_slug` provided at signup).
- **2026-05-15 (ADR-281 Stream B)**: `_workspace_guide.md` kernel-default wasn't recognized as skeleton; bundle-fork didn't overwrite. Fix: signature detection in `is_skeleton_content` (line 64–75 of `workspace_utils.py`).
- **2026-05-17 (this ADR's trigger)**: `review/IDENTITY.md` + `review/principles.md` + `_shared/AUTONOMY.md` stuck on kernel defaults in kvk's workspace. The 2354-byte kernel-default `review/IDENTITY.md` is missing the entire "I am the operator's active principal / I own the full position lifecycle / passivity is not an option" posture content from the 5270-byte bundle version. Reviewer wakes against stale substrate; intended posture canon does not reach the LLM.

Each patch worked tactically but the underlying structural duality kept producing the same shape of bug. The audit traced the disease: **`workspace_init` Phase 2 writes 10 paths that the alpha-trader bundle ALSO ships. The two writers race on those 10 paths.**

The race resolution has been a per-path heuristic — `is_skeleton_content` tries to distinguish "kernel default that should be overwritten" from "operator-customized content that should be preserved." The heuristic is fundamentally unsound because kernel defaults can legitimately look like authored content (substantive prose, multiple section headings, no template markers). Every kernel-default content shape requires its own detection patch.

This is the **dual-approach pathology** that CLAUDE.md execution discipline #1 (Singular Implementation) names. The honest architectural correction is to eliminate the dual-write, not improve the heuristic that tries to reconcile it after the fact.

## Decision

### D1 — Single writer per program-shaped path

**For every path the active program bundle ships, the bundle-fork is the sole authoritative writer at workspace-activation time. The kernel scaffold writes nothing for those paths.**

The kernel scaffold continues to write **only kernel-universal paths** — paths that no bundle ever ships, present in every workspace regardless of program activation.

The discipline rule that separates them is verifiable mechanically: walk every bundle's `reference-workspace/` directory; any path that appears in any bundle is bundle-owned and the kernel does not scaffold it. The kernel-universal set is the complement.

Under this rule, the 10 dual-write paths cease to exist. They become:
- **Bundle-owned**: written by `fork_reference_workspace` at program activation. Absent on no-program workspaces.
- **Operator-customizable post-activation**: per existing `is_skeleton_content` post-fork preservation logic, operator edits survive subsequent re-forks. This semantic is preserved.

### D2 — Kernel-universal paths (the survivor set)

Paths the kernel continues to scaffold at workspace_init Phase 2, because no bundle ships them and they're load-bearing for the no-program workspace shape:

| Path | Why kernel-universal |
|---|---|
| `context/_shared/PRECEDENT.md` | Operator-authored durable interpretation log; never ships pre-authored content. Kernel scaffolds empty-skeleton; operator authors over time. |
| `memory/_playbook.md` | YARNNN orchestration playbook — kernel infrastructure, not program substrate. |
| `memory/style.md` | YARNNN-inferred style accumulator placeholder. |
| `memory/notes.md` | YARNNN-extracted facts placeholder. |
| `review/calibration.md` | Reviewer seat calibration trail — auto-generated by back-office cadence. Kernel ships empty stub. |
| `review/OCCUPANT.md` | Reviewer seat occupant declaration. Kernel scaffolds via `rotate_occupant` primitive (ADR-211 D4); ADR-284 Phase 1 helper overwrites at bundle-fork with runtime occupant identity. Path is kernel-owned; runtime-truth-alignment is bundle-fork-responsibility. |
| `review/handoffs.md` | Seat-rotation log — appended by rotation primitive. |
| `_workspace_guide.md` (no-program case only) | Kernel default writes ONLY when no program is activating at signup. Bundle-activation paths skip kernel default and write bundle-shipped guide directly. **Subtle**: this path is dual-classifiable — kernel-universal for no-program workspaces, bundle-owned for program-activated workspaces. The kernel scaffold writes the default **only when `program_slug is None`**; otherwise the bundle owns it. |

Everything else that the kernel currently scaffolds at Phase 2 — `MANDATE.md`, `IDENTITY.md`, `BRAND.md`, `AUTONOMY.md`, `_autonomy.yaml`, `awareness.md`, `review/IDENTITY.md`, `review/principles.md`, `review/_principles.yaml` — moves to bundle-owned.

### D3 — Bundle-owned paths (no kernel scaffold)

Paths the kernel STOPS scaffolding because every active bundle ships them. Empty (`None`) on no-program workspaces; bundle-fork populates on program activation.

Today's bundle-shipped set (consistent across alpha-trader + alpha-author):
- `context/_shared/MANDATE.md`
- `context/_shared/IDENTITY.md`
- `context/_shared/BRAND.md`
- `context/_shared/CONVENTIONS.md`
- `context/_shared/AUTONOMY.md`
- `context/_shared/_autonomy.yaml`
- `context/_shared/_preferences.yaml`
- `memory/awareness.md`
- `review/IDENTITY.md`
- `review/principles.md`
- `review/_principles.yaml`
- `_recurrences.yaml`
- `_workspace_guide.md` (when program is activating)

### D4 — No-program workspace shape

A workspace at signup with no program activation has:
- Kernel-universal paths populated per D2
- Bundle-owned paths **absent**
- Reviewer wake envelope renders empty-state hints for absent files (existing `_build_user_message` behavior — `or "_(empty — ...)_"` fallback per ADR-284 Phase 1 D6)
- YARNNN chat surface remains operative — operator can author content via `WriteFile(scope="workspace")` or activate a program

Honest semantic: a no-program workspace is *unconfigured*. The envelope reflects that honestly rather than pretending a generic Reviewer persona exists. Operator's first action is typically program activation; that populates the substrate via bundle-fork.

### D5 — Singular fork-write rule

`fork_reference_workspace` simplifies. Pre-ADR-286 behavior:
- Read existing file → call `is_skeleton_content(existing, bundle_body=body)` → write if skeleton, skip if non-skeleton

Post-ADR-286 behavior on first activation:
- Read existing file → existing is `None` (kernel didn't scaffold) → write unconditionally

Post-ADR-286 behavior on re-fork:
- Read existing file → existing carries operator content from prior cycles → preserve unless `is_skeleton_content` reports skeleton

The `is_skeleton_content` check survives **only for the operator-edited-then-stripped case** (operator deletes content; re-fork should re-populate). The check no longer has to differentiate kernel-defaults from authored content because kernel-defaults stop existing for bundle-owned paths.

### D6 — `is_skeleton_content` simplification

Patches in `workspace_utils.py::is_skeleton_content` that exist solely to rescue dual-write race-conditions are deleted:

| Patch | Reason it exists | Status under ADR-286 |
|---|---|---|
| `placeholder_phrases` check (line 49–58) | Detect kernel-default placeholder content (`"not yet declared"`, `"<!-- identity not yet"`, etc.) | **DELETED** — kernel no longer writes placeholders to bundle-owned paths |
| Reviewer-principles signature (line 61–62) | Detect kernel-default `principles.md` content | **DELETED** — kernel no longer writes principles.md |
| Workspace-guide kernel-default signature (line 64–75, added 2026-05-15) | Detect `"this workspace runs no program"` discriminator | **DELETED** — for program-activated workspaces, the guide is bundle-shipped from first write; for no-program workspaces the kernel default is correct and stays |
| Short-and-sparse rule (line 99–102) | Catch browser-tz-injected About Me kernel-default | **DELETED** — kernel no longer writes IDENTITY.md |

Patches that **survive** because they detect bundle-template intent (operator-hasn't-overwritten-yet — surface display semantic, not write decision):

| Patch | Reason it survives |
|---|---|
| Empty / whitespace check (line 39–40) | Universal — file missing or stripped means skeleton regardless of writer history |
| Bundle-body exact-match (line 44–45) | The file is still verbatim bundle content — operator hasn't customized. Used by surface display + working_memory's `_classify_activation_state` (post-fork-pre-author state detection) |
| `(template)` first-line marker (line 79–80) | Bundle ships some files with `(template)` in their `# Heading (template)` first line for prompt-shape clarity |
| `Author here:` / `**Operator**: author this` short-template rule (line 84–96) | Bundle files like `IDENTITY.md` ship with operator-prompt markers; the marker + short length = "operator hasn't written yet" |
| `_<not yet` placeholder (line 81–83) | Bundle template marker |

Net deletion: 4 patches (~30 LOC). Net retention: 4 patches (~20 LOC). The simplified function distinguishes only "bundle template" from "operator-authored content" — single-axis classification, no kernel-default-detection axis.

### D7 — `workspace_init` dual-write deletion

`workspace_init.py` Phase 2's `workspace_files` dict drops 10 entries. The `bundle_owned_paths` skip mechanism (ADR-269 iter-4) becomes unnecessary — there's no kernel write to skip. The skip block deletes.

What remains in Phase 2: the kernel-universal entries from D2. Phase 5 (bundle-fork) handles bundle-owned paths.

The `program_slug` parameter on `initialize_workspace` continues to gate Phase 5 (bundle-fork is conditional on program activation). Phase 2 no longer branches on `program_slug` because the kernel-universal set is identical regardless of program.

### D8 — Migration for existing alpha workspaces

Existing workspaces (kvk, alpha-trader, alpha-trader-2) have kernel-default content at bundle-owned paths from their pre-ADR-286 signup. They need re-fork to pick up bundle-shipped content.

The re-fork mechanism (`fork_reference_workspace`) under ADR-286 D5 will:
- Read existing `review/IDENTITY.md` (2354-byte kernel default) → existing is not empty, not bundle-body, not template-marker → `is_skeleton_content` returns False → fork **skips** to preserve operator-customized content

**This is wrong** for the migration window. The kernel-default content masquerades as operator-customized.

**Migration approach (pre-users, one-shot)**: a small migration script reads every workspace's bundle-owned paths, checks if content matches the kernel default that workspace_init pre-ADR-286 would have written (deterministic comparison — the defaults are constants in `services/orchestration.py`), and deletes those rows. Subsequent re-fork populates fresh from bundle.

Migration script ships once, runs once against the 3 alpha workspaces, then is archived per the oneshot-scripts convention (`api/scripts/oneshot/`).

Post-migration: any new workspace signup goes through the ADR-286-shaped flow (kernel scaffolds only universals; bundle-fork owns program-shaped). No race condition possible.

### D9 — Singular Implementation enforcement

The structural rule from D1 must be testable. Regression gate `test_adr286_single_writer_per_path.py` walks every active bundle and asserts:
- Every path in `bundle.reference-workspace/` is NOT in `workspace_init.workspace_files`
- Every entry in `workspace_init.workspace_files` is NOT in any active bundle's reference-workspace

Future bundle additions that violate the rule (a bundle that ships a path the kernel scaffolds) fail the gate. Bundle authors are forced to acknowledge: this path belongs to the bundle, kernel must drop its scaffold.

### D10 — Cascade across canon

- FOUNDATIONS Axiom 1 (substrate) gets a new sub-clause naming the single-writer-per-path rule
- Derived Principle 16 (kernel/program boundary) gets sharpened with the substrate-write boundary as a worked example
- GLOSSARY entry for "substrate writer" added — explicit "every path has one authoritative writer"
- `api/prompts/CHANGELOG.md` entry for behavioral artifact change (`workspace_init` content changed)

### D11 — Out of scope (deferred)

- **Operator-overlay file mechanism** (`/workspace/_overrides/` for operator customizations that survive bundle re-fork). Today's mechanism — operator edits the bundle-shipped file directly, fork preserves via `is_skeleton_content` non-skeleton check — survives. Overlay layer is a future ADR if pressure surfaces.
- **Multi-bundle workspaces** (workspace activates two programs simultaneously). Not supported today; not changed by ADR-286.
- **Bundle hot-reload** (operator activates bundle v2 over v1). Not a current scenario; future ADR if pressure surfaces.

## Cascade plan (atomic single commit)

This ADR ships as one atomic commit because the changes are tightly coupled:

1. **ADR doc**: this file (Proposed status, flipped to Implemented in same commit).
2. **`workspace_init.py` Phase 2 simplification**: drop 10 dual-write entries; delete `bundle_owned_paths` block.
3. **`workspace_utils.py::is_skeleton_content` simplification**: delete 4 rescue patches per D6.
4. **Migration script** at `api/scripts/oneshot/adr286_purge_dual_write_kernel_defaults.py`: walks 3 alpha workspaces, deletes kernel-default content at bundle-owned paths.
5. **Regression gate** `api/test_adr286_single_writer_per_path.py`: asserts D9 invariant.
6. **Re-fork validation**: run migration → re-fork kvk's workspace → verify drift sites resolved (`review/IDENTITY.md` bundle-sized, `AUTONOMY.md` bundle-sized, `review/principles.md` Phase-2-current).
7. **Canon cascade** per D10.
8. **CHANGELOG entry**.

## Why this is structurally right

The dual-write pattern has been the root cause of three substrate-drift incidents in five days. Each incident generated a tactical patch (skip rules, signature detection). The patches work but the pattern produces new drift surfaces faster than we patch.

The architectural truth: **substrate-write is a Singular Implementation question per CLAUDE.md rule #1.** Each path has one authoritative writer. The kernel writes universals; the bundle writes program-shaped substrate. The boundary is verifiable mechanically (walk the bundle directory). The rescue heuristics in `is_skeleton_content` exist *only* because the dual-write created reconciliation pressure.

Removing the dual-write removes the pressure removes the heuristics. The system gets smaller, more predictable, and easier to reason about. Future bundle additions (alpha-commerce, alpha-prediction, alpha-defi) inherit the rule automatically — no per-bundle kernel-default authoring, no per-path skeleton-detection patch.

The trade-off (no-program workspaces have empty bundle-owned paths) is honest. A no-program workspace IS unconfigured. The envelope reflects that truthfully instead of papering it with generic defaults that pretend a persona exists.

No new substrate roles. No new primitive. No new ADR pattern. Just the structural correction of the kernel/program boundary at the write surface. The architectural payoff is large because the drift it eliminates compounds: every future incident traceable to dual-write doesn't happen.
