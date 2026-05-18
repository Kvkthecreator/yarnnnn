# ADR-292: Operator-Initiated Versioned Substrate Update — Kernel + Bundle Updates Reach Live Workspaces

**Status**: Implemented (Phase 1 — backend, 2026-05-18); Phase 2 (FE surface) Proposed
**Authors**: KVK, Claude

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

Drafted 2026-05-18 in the wrong shape (daily mechanical recurrence + new `ReapplyPlatformSubstrate` primitive). Reverted same day after operator feedback: the right model is Claude Code's `claude --update` — **versioned platform releases, operator-initiated adoption** — not a polling cron. This ADR documents the corrected shape directly; the wrong-shape commit `837356b` is amended in place by the corrective commit on top.

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

Backend can stand alone; FE is independent and lands in a follow-up commit.

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
