# ADR-292: Operator-Initiated Versioned Substrate Update — Kernel + Bundle Updates Reach Live Workspaces

**Status**: Implemented (Phase 1 — backend, 2026-05-18); Phase 2 (FE surface) Proposed; **v3 amendment (2026-05-20) — Implemented**: content-vs-prose taxonomy + version-bump CI gate close the silent-drift class surfaced by Checkpoint 2 of ADR-296 v2; **ADR-320 relocation (2026-06-10) — Implemented**: audit log + conflict-backups moved off the dissolved `_shared/` root to `system/` (see "ADR-320 path relocation" below)
**Authors**: KVK, Claude

> **ADR-320 path relocation (2026-06-10).** ADR-292 was authored before [ADR-320](ADR-320-constitution-region-topological-cut.md) dissolved the `_shared/` root into the five-root topology. Two substrate-update bookkeeping paths were stranded on the dead root and are relocated to `system/` (the orchestration-runtime root — same semantic class as `system/_playbook.md` / `_schedule_index.md`; both are `system:substrate-update`-authored runtime state). Every occurrence of `_shared/substrate-update-log.md` and `_shared/conflict-backups/{ran_at}/{path}` in the body below now reads `system/substrate-update-log.md` and `system/conflict-backups/{ran_at}/{path}`. Code: `UPDATE_AUDIT_LOG_PATH` + `CONFLICT_BACKUP_PREFIX` in [substrate_reapply.py](../../api/services/substrate_reapply.py). **No data migration for existing `_shared/` audit-logs + backups — they are the SOLE copy of an append-only historical record (ADR-209-retained, ADR-292 line 296 "immutable historical record"), with no `system/` twin.** Archiving them would erase the only copy, so they are left in place: inert (the Files tree no longer fetches `_shared/`, so they're invisible to the operator; nothing reads them as live substrate) but retained. New update events write under `system/`. (Distinct from the ADR-320 *domain* stragglers under `context/`, which DO have current `operation/` twins and are archived as duplicates — see the ADR-320 Files-surface commit.)

**Dimensional classification** (FOUNDATIONS v8.5):
- **Substrate** (Axiom 1) — primary. Defines how platform-managed substrate evolves in live workspaces.
- **Trigger** (Axiom 4) — secondary. Operator-initiated, not scheduled. Versioned platform-update model (Claude Code's `claude --update`, not a daily cron).
- **Identity** (Axiom 2) — tertiary. `authored_by` attribution is the load-bearing gate between platform-managed and operator-authored revisions.

**Companion canon**:
- FOUNDATIONS Axiom 1 (Substrate) — workspace_files + revision chain
- FOUNDATIONS Axiom 2 (Identity) + Derived Principle 13 — every revision is authored, attribution distinguishes actors
- FOUNDATIONS Derived Principle 14 (Singular Implementation) — one update path, not per-layer ceremony
- ADR-209 — Authored Substrate; `authored_by` taxonomy is the boundary
- ADR-222 — agent-native OS framing; kernel/program boundary
- ADR-223 — Program Bundle Specification (MANIFEST.yaml shape)
- ADR-226 — Reference-Workspace Activation Flow (one-shot fork at signup)
- ADR-244 — Workspace Settings Surface (the FE home for the update affordance)
- ADR-286 — Kernel/Program substrate single-writer discipline
- `docs/architecture/propagation-discipline.md` — the planning doc this ADR ratifies

**Supersedes**: None — net new mechanism.

**Amends**:
- ADR-226 — adds an operator-initiated versioned-update companion to one-shot activation fork. ADR-226's fork primitive is unchanged; this ADR adds detection + version stamping + a second trigger site that re-uses the same primitive.

**Preserves**: All upstream canon. No primitive renames, no schema changes.

---

## Drafting history

- **2026-05-18 (drafted, reverted same day)**: v1 daily mechanical recurrence + new `ReapplyPlatformSubstrate` primitive. Reverted after operator feedback: the right model is Claude Code's `claude --update` — versioned platform releases, operator-initiated adoption — not a polling cron.
- **2026-05-18 (v2, Implemented)**: corrected shape per D1–D8 below. `bundle_update_available` + `kernel_update_available` detection helpers + `apply_substrate_update(scope, source)` worker + MANDATE.md frontmatter version-stamp substrate + audit log.
- **2026-05-20 (v3 amendment, Implemented)**: closes a structural drift class surfaced by ADR-296 v2 Checkpoint 2 — bundle reference-workspace content can change without bumping `MANIFEST.yaml::version`, AND operator-edited bundle-config files (e.g., `_recurrences.yaml`) skip silently during re-fork even when the bundle's content is functionally newer. v3 introduces (a) a content-vs-prose taxonomy on bundle files with auto-overwrite-with-backup for config files when versions mismatch, and (b) a CI lint enforcing version bump on any reference-workspace content change. See decisions D9–D11 below.

---

## Problem

YARNNN has multiple live operator workspaces — three alpha-author dogfood personas (`yarnnn-author`, `netflix-script-author`, `korea-thriller-shorts`) plus kvk's alpha-trader-2. These workspaces accumulate real operator content while kernel skeleton text and program bundle templates continue to evolve in `main`.

When kernel constants like `DEFAULT_REVIEW_PRINCIPLES_MD` tighten on 2026-05-25, or when a program bundle's `context/_shared/IDENTITY.md` improves upstream, there is currently **no mechanism that propagates the improvement to already-forked workspaces.** Only new workspaces see the change.

The existing fork primitive ([api/services/programs.py::fork_reference_workspace](/Users/macbook/yarnnn/api/services/programs.py)) and `initialize_workspace()` Phase 2 ([api/services/workspace_init.py](/Users/macbook/yarnnn/api/services/workspace_init.py)) run once per workspace, at signup or persona-harness invocation. There is no second trigger that re-applies upstream changes.

The result: live workspaces drift further from canon every time the platform improves.

## Decision

Adopt the **Claude Code update model** for substrate: platform versions its substrate, operator opts in on demand.

### D1. Two version stamps

Single string per layer:

- **`KERNEL_VERSION`** constant in [api/services/orchestration.py](/Users/macbook/yarnnn/api/services/orchestration.py). Bumped manually when any kernel-universal seed constant changes meaningfully. Format: date-stamped `YYYY-MM-DD[.N]` aligning with [api/prompts/CHANGELOG.md](/Users/macbook/yarnnn/api/prompts/CHANGELOG.md).
- **`version:`** field in each bundle's [MANIFEST.yaml](/Users/macbook/yarnnn/docs/programs/alpha-trader/MANIFEST.yaml). Bumped manually by the bundle author on any `reference-workspace/` or `specs/` change. Same date-stamp format.

Discipline cost: one line per substrate change, identical to the CHANGELOG entry the change already needs.

### D2. Workspace-side version record is substrate-native (MANDATE.md frontmatter)

The workspace records which versions it has adopted via frontmatter at the top of MANDATE.md:

```yaml
---
activated_bundle_version: 2026-05-18.1
activated_kernel_version: 2026-05-18.1
---
# Mandate — alpha-trader (template)
...
```

Rationale:
- FOUNDATIONS Axiom 1 (Substrate) consistency — workspace state lives in workspace_files, not in schema columns.
- ADR-209 attribution captures the version-advance event in the revision chain.
- No schema bifurcation (ADR-244 D4 already established this principle when L2/L4 resets preserve `active_program_slug` by reading MANDATE.md, not a column).
- `parse_active_program_slug` is unchanged — the heading regex iterates past frontmatter without modification.

Absence of frontmatter is the legitimate "no version recorded yet" state — workspaces activated before ADR-292 shipped fall in this bucket and the detection helpers handle it naturally.

### D3. The boundary is `is_skeleton_content`, not `authored_by`

The existing [api/services/programs.py::fork_reference_workspace](/Users/macbook/yarnnn/api/services/programs.py) already uses [api/services/workspace_utils.py::is_skeleton_content](/Users/macbook/yarnnn/api/services/workspace_utils.py) as the gate that decides "operator has customized this file → never touch." That gate is battle-tested across every persona activation since ADR-226 shipped.

ADR-292 reuses that gate, NOT a parallel `authored_by`-based gate. Singular Implementation: one decision authority. Adding a second gate would create the possibility of two answers disagreeing.

### D4. Update is operator-initiated, NOT scheduled

The mechanism is `claude --update`-shaped:

1. Platform releases new substrate (bumps `KERNEL_VERSION` or `MANIFEST.yaml::version`).
2. Operator opens Settings → Workspace (ADR-244 surface).
3. Backend detection helpers return `BundleUpdateInfo` and/or `KernelUpdateInfo` if the workspace's recorded version is behind canon.
4. Operator sees "Update available" with a diff summary.
5. Operator clicks "Update." This invokes `apply_substrate_update(client, user_id, scope=..., source="operator")`.
6. Update worker walks the relevant layers, re-applies platform-managed files (skipping operator-authored), advances MANDATE.md frontmatter version stamps, appends UpdateReport to `/workspace/_shared/substrate-update-log.md`.

**Explicit non-goals** (the wrong shape that was reverted):
- ❌ Daily back-office cron walking every workspace every 24h
- ❌ A `ReapplyPlatformSubstrate` mechanical primitive in HANDLERS
- ❌ Bundle recurrences shipping a `back-office-substrate-reapply` entry

Updates only happen when the operator chooses. The platform's job is to make the choice visible and trivial; the operator's job is to decide when to take it.

### D5. Single public function, scope-parameterized

[api/services/substrate_reapply.py::apply_substrate_update](/Users/macbook/yarnnn/api/services/substrate_reapply.py) takes a `scope` parameter: `"kernel"` | `"bundle"` | `"both"`. Both layers share the same gate (`is_skeleton_content`), the same attribution actor (`system:substrate-update`), and the same audit log. The operator UI surfaces the two layers as separate notifications, but the worker treats them as one mechanism with two scopes.

### D6. Audit log substrate

`/workspace/_shared/substrate-update-log.md` — system-authored, append-only markdown. Each entry records one update event: source, scope, from/to versions, files touched, skip counters.

Operator-readable; not operator-actionable. The operator has already made the decision by clicking Update; the log records what happened, not what to decide.

### D7. What this ADR does NOT do

Explicit non-goals to prevent scope creep:

- ❌ Bundle version auto-bump from git (manual discipline mirrors prompt CHANGELOG)
- ❌ Diff-findings table — diff is computed on read, not persisted
- ❌ Per-file accept/reject affordance — version-level only
- ❌ Per-workspace prompt version pinning
- ❌ Canary rollout / staged release infrastructure
- ❌ Operator-customized files diverging from upstream are NOT surfaced as "potential updates" — once the operator takes authorship, they own it
- ❌ Schema migration for version columns (substrate-native record per D2)

Each of these becomes its own ADR if and when a concrete production failure makes it acute.

### D8. Prompts and DB schema remain on their current models

- Prompts ship at HEAD; all workspaces get them on next invocation. [api/prompts/CHANGELOG.md](/Users/macbook/yarnnn/api/prompts/CHANGELOG.md) is the audit trail.
- DB schema migrations apply atomically at deploy time.

Recovery from a regression in either path is `git revert + redeploy`, affecting all workspaces uniformly. At current operator scale (handful of dogfood personas, one human directing), this is correct. The first concrete production regression that this fails to recover from triggers a future ADR — not this one.

---

## v3 amendment (2026-05-20) — content-vs-prose taxonomy + CI version-bump gate

The 2026-05-20 audit of kvk's alpha-trader and yarnnn-author workspaces ([docs/evaluations/2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2](/Users/macbook/yarnnn/docs/evaluations/2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2/findings.md)) surfaced two structural gaps in the v2 mechanism:

**Gap A — version-bump dependency on author discipline.** ADR-296 v2 Checkpoint 2 (commit `37426c5`, 2026-05-20T07:45Z) modified bundle reference-workspace files (`_recurrences.yaml`, `_hooks.yaml`, `review/principles.md`) for both alpha-trader and alpha-author **without bumping `version:` in either `MANIFEST.yaml`**. Both bundles still declared `version: 2026-05-18.1`. Live workspaces had no path to detect the update because `bundle_update_available()` compares version strings and both matched. Result: code shipped at deploy; bundles did not propagate.

**Gap B — silent skip of operator-edited bundle config files.** The `fork_reference_workspace` worker uses `is_skeleton_content()` as the only gate. Once an operator (or the Reviewer per ADR-275) edits `_recurrences.yaml` to add deliverable Schedule entries, the file ceases to be skeleton — and every subsequent re-fork attempt skips it silently. yarnnn-author's substrate-update-log shows this: the 2026-05-20T03:08Z re-fork counted 5 files as "Skipped (operator-authored)" including `_recurrences.yaml`. When Checkpoint 2 later changed the bundle's `_recurrences.yaml` (deleted `pre-ship-audit` recurrence, added `_hooks.yaml`), the live workspace had no way to receive the change because its `_recurrences.yaml` was no longer skeleton.

Both gaps preserve the v2 model's core (operator-initiated, Claude-Code-shaped) but make the propagation contract honest about: *which files can be auto-overwritten when the bundle moves, vs. which files require manual operator decision*.

### D9. Bundle file taxonomy — config vs prose

Files shipped in `docs/programs/{slug}/reference-workspace/` divide into two classes by **architectural role**, not by file extension or path heuristic:

**Config files (operationally load-bearing).** Their content is consumed by the kernel scheduler / wake architecture / runtime dispatch as the source of truth for *what the workspace does*. Operator-edits express *operator intent*, but the bundle's shape constraints (which slugs exist; which sub-shapes are valid; what prompts are runtime-coupled) come from upstream. When the bundle changes shape (e.g., deletes a slug, migrates a recurrence to a hook, introduces a new wake-source-coupled prompt), operator-edits on the old shape may be **functionally inert or broken** under the new code. The right discipline is auto-overwrite-with-backup: the bundle's new shape lands; the operator's prior edits are preserved at a backup path for manual re-application.

Canonical config files (CONFIG_PATHS):
- `_recurrences.yaml` — cron-tick wake source's configuration (ADR-296 v2 D2)
- `_hooks.yaml` — substrate-event wake source's configuration (ADR-296 v2 D2)

This list is closed-set today. Adding a third config file in a future ADR requires updating CONFIG_PATHS in code + this section.

**Prose files (operator-authored substrate).** Their content is consumed by the LLM at reasoning time as operator-authored declaration — IDENTITY, MANDATE, BRAND, principles, voice, editorial, risk envelope, operator profile. Operator-edits are the substantive content of the file; the bundle ships a template that the operator overwrites and never expects the system to touch again. The right discipline is preserve-and-surface: the bundle's new template content is recorded in the update audit log + UpdateReport, but the operator's content is not overwritten. (Same behavior as v2 — explicitly preserved here as half of the taxonomy.)

The taxonomy is a code-level declaration in `services/substrate_reapply.py`:

```python
# Bundle files that are operationally load-bearing config — the kernel's
# wake architecture reads them as source of truth. Auto-overwrite with
# backup when bundle version moves; operator's prior edits go to
# /workspace/_shared/conflict-backups/{ran_at}/{relative_path}.
CONFIG_PATHS: frozenset[str] = frozenset({
    "_recurrences.yaml",
    "_hooks.yaml",
})
```

### D10. Re-fork worker gains content-aware conflict handling

`fork_reference_workspace` (and by extension `_update_bundle_layer` per D5) extends the per-file decision tree:

```
existing = read(target_path)
bundle_body = read(bundle_path)

if existing is None:
    → write bundle_body, attributed system:bundle-fork
elif existing == bundle_body:
    → skip (already aligned)
elif is_skeleton_content(existing, bundle_body=bundle_body):
    → write bundle_body, attributed system:bundle-fork (still skeleton — refresh)
elif relative_path in CONFIG_PATHS:
    → AUTO-OVERWRITE WITH BACKUP:
        1. write existing to /workspace/_shared/conflict-backups/{ran_at}/{relative_path}
           attributed system:substrate-update with message "backed up operator-edited config"
        2. write bundle_body to target_path
           attributed system:substrate-update with message "config re-applied from {slug} bundle vN.M (operator edits backed up)"
        3. append ConflictedFile entry to UpdateReport.config_conflicts
else:
    → skip (operator-authored prose, preserve)
        and count to skipped_operator_authored as today
```

The backup path convention `/workspace/_shared/conflict-backups/{ran_at}/{relative_path}` is operator-readable; revisions are attributed per ADR-209 so the chain shows the backup write + the overwrite as one atomic update event in the audit log.

`UpdateReport` gains a new field:

```python
@dataclass
class ConflictedFile:
    path: str
    backup_path: str
    bundle_version: str

@dataclass
class UpdateReport:
    # ... existing fields ...
    config_conflicts: list[ConflictedFile] = field(default_factory=list)
```

Audit log rendering names the conflicts explicitly:

```markdown
## Substrate update — 2026-05-20T11:00:00+00:00
- **Source**: `operator`
- **Scope**: `bundle`
- **Bundle version**: `2026-05-18.1` → `2026-05-20.1`
- **Actions taken**: 3
- **Skipped (operator-authored prose)**: 5
- **Config conflicts auto-resolved**: 1

### Config conflicts (operator-edits backed up, bundle re-applied)
- `_recurrences.yaml` → backup at `_shared/conflict-backups/2026-05-20T11:00:00/_recurrences.yaml`
  Operator may inspect the backup to re-apply edits selectively. Bundle's new content
  is now live.
```

### D11. CI version-bump enforcement

A CI lint script enforces: any change under `docs/programs/{slug}/reference-workspace/` or `docs/programs/{slug}/specs/` requires a bump in the corresponding `docs/programs/{slug}/MANIFEST.yaml::version` in the same commit (or in a commit ahead of the change in the same PR).

Implementation: `scripts/lint_bundle_version_bump.py` runs in CI on every PR. Compares files-changed-by-PR against `git diff --name-only HEAD~1..HEAD` (PR head vs main); if a reference-workspace or specs file changed AND MANIFEST.yaml did NOT change (or its `version:` line is identical), CI fails with a descriptive error pointing the author at the bump.

This is discipline-as-code: the rule "every bundle content change bumps version" was previously a `propagation-discipline.md` convention; v3 makes it CI-enforced. Mirrors the ADR's own observation that this discipline costs "one line per substrate change, identical to the CHANGELOG entry the change already needs" (D1 rationale).

### D12. What v3 does NOT change

Explicit non-goals to preserve v2's core:

- ❌ Daily cron — still NOT a daily back-office recurrence. Operator-initiated only.
- ❌ Per-file accept/reject UI for the operator. The config-vs-prose taxonomy is the policy; operator doesn't choose per-file at update time.
- ❌ Three-way merge of operator-edits into the new bundle's `_recurrences.yaml`. Auto-overwrite-with-backup; operator re-applies manually if needed.
- ❌ Backwards-compat shim for the old "silent skip" behavior. Singular Implementation — there's one decision tree, codified in D10.
- ❌ A new primitive. The mechanism is still `apply_substrate_update(scope, source)`.
- ❌ Conflict notification via chat (Clarify proposal from substrate-update). Audit log + UpdateReport are sufficient at current scale; the FE surface (Phase 2) renders them.

## Implementation Status

### Phase 1 — Backend (Implemented 2026-05-18, this ADR's commit)

| Component | Status | Notes |
|---|---|---|
| `KERNEL_VERSION` constant | ✅ | [api/services/orchestration.py](/Users/macbook/yarnnn/api/services/orchestration.py) — set to `"2026-05-18.1"` |
| `version:` field on alpha-trader MANIFEST | ✅ | Set to `2026-05-18.1` |
| `version:` field on alpha-author MANIFEST | ✅ | Set to `2026-05-18.1` |
| `bundle_reader.get_bundle_version(slug)` helper | ✅ | Reads MANIFEST.yaml's `version:` field |
| MANDATE.md frontmatter read/write helpers | ✅ | Tolerant parser; absence = "no version recorded yet" |
| `bundle_update_available(client, user_id)` detection | ✅ | Returns `BundleUpdateInfo` or `None` |
| `kernel_update_available(client, user_id)` detection | ✅ | Returns `KernelUpdateInfo` or `None` |
| `apply_substrate_update(client, user_id, *, scope, source)` worker | ✅ | Single public entry point, scope-parameterized |
| MANDATE.md version-stamp advance | ✅ | Idempotent write to frontmatter on success |
| `/workspace/_shared/substrate-update-log.md` audit log | ✅ | Append-only, system-authored |
| `system:substrate-update` attribution actor | ✅ | Distinct from `system:bundle-fork` |
| Regression test gate | ✅ | [api/test_adr292_continuous_reapply.py](/Users/macbook/yarnnn/api/test_adr292_continuous_reapply.py) |

### Phase 2 — Frontend (Proposed)

| Component | Status | Notes |
|---|---|---|
| `GET /api/workspace/state` returns `bundle_update`/`kernel_update` info | Pending | Calls the detection helpers |
| Settings → Workspace surface renders update affordances | Pending | When detection returns non-None |
| "Update bundle" button calls `POST /api/programs/update` (or similar) | Pending | Invokes `apply_substrate_update` with scope/source |
| Audit-log viewer in Settings → Workspace | Pending | Reads `substrate-update-log.md` |
| Config-conflict surfacing in audit-log viewer | Pending (v3) | Renders `UpdateReport.config_conflicts` block with backup paths |

Backend can stand alone; FE is independent and lands in a follow-up commit.

### Phase 3 — v3 amendment (Implemented 2026-05-20)

| Component | Status | Notes |
|---|---|---|
| `CONFIG_PATHS` constant in substrate_reapply | ✅ | Closed-set: `{_recurrences.yaml, _hooks.yaml}` |
| `ConflictedFile` dataclass | ✅ | Carries path + backup_path + bundle_version |
| `UpdateReport.config_conflicts` field | ✅ | List of ConflictedFile; rendered in audit log |
| Conflict-aware fork worker (config files auto-overwrite-with-backup) | ✅ | `fork_reference_workspace` extends the decision tree per D10 |
| Backup path `/workspace/_shared/conflict-backups/{ran_at}/{path}` | ✅ | ADR-209-attributed via `system:substrate-update` |
| `scripts/lint_bundle_version_bump.py` CI lint | ✅ | Fails on bundle content change without MANIFEST version bump |
| Regression test gate (v3 additions) | ✅ | Extends `api/test_adr292_continuous_reapply.py` with config-conflict + CI-lint tests |

## Test Gate

Invariants enforced by [api/test_adr292_continuous_reapply.py](/Users/macbook/yarnnn/api/test_adr292_continuous_reapply.py):

1. `substrate_reapply` module exports the seven public symbols (`apply_substrate_update`, two detection helpers, two info dataclasses, audit log path, attribution actor).
2. Audit log path constant matches `_shared/substrate-update-log.md`.
3. Attribution actor matches `system:substrate-update` and passes ADR-209 `is_valid_author` taxonomy.
4. No mechanical primitive registered — `ReapplyPlatformSubstrate` is NOT in HANDLERS.
5. No daily recurrence — `back-office-substrate-reapply` is NOT in any bundle's `_recurrences.yaml`.
6. `KERNEL_VERSION` constant exists in orchestration.py and is a non-empty string.
7. Both active bundles declare `version:` in MANIFEST.yaml.
8. MANDATE.md frontmatter parse/render round-trip is idempotent for the empty case.
9. MANDATE.md frontmatter version-stamp write preserves heading + body.
10. ADR-292 doc + propagation-discipline.md exist and reference each other.

## Out of Scope / Future ADRs

The following remain explicitly out of scope and become future ADRs only if a concrete failure case emerges:

- Bundle-template-vs-workspace per-file diff viewer (operator-facing surface)
- Prompt version pinning + canary rollout
- Per-migration schema feature flags
- Cross-workspace propagation observability dashboard
- Operator-authored file divergence notification ("upstream improved this file you've customized")
- Reflexive loop (lived → bundle graduation) — already deferred as ADR 6 in [docs/architecture/os-framing-implementation-roadmap.md](/Users/macbook/yarnnn/docs/architecture/os-framing-implementation-roadmap.md)
