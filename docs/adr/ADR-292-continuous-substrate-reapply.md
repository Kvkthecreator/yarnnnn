# ADR-292: Continuous Substrate Re-Apply — Kernel + Bundle Updates Reach Live Workspaces

**Status**: Proposed (2026-05-18)
**Authors**: KVK, Claude

**Dimensional classification** (FOUNDATIONS v8.5):
- **Substrate** (Axiom 1) — primary. Defines how platform-managed substrate evolves in live workspaces.
- **Mechanism** (Axiom 5) — secondary. Fully-deterministic re-apply loop, no judgment.
- **Identity** (Axiom 2) — tertiary. `authored_by` attribution is the load-bearing gate between platform-managed and operator-authored revisions.

**Companion canon**:
- FOUNDATIONS Axiom 1 (Substrate) — workspace_files + revision chain
- FOUNDATIONS Axiom 2 (Identity) + Derived Principle 13 — every revision is authored, attribution distinguishes actors
- FOUNDATIONS Derived Principle 14 (Singular Implementation) — one re-apply path, not per-layer ceremony
- ADR-209 — Authored Substrate; `authored_by` taxonomy is the boundary
- ADR-222 — agent-native OS framing; kernel/program boundary
- ADR-223 — Program Bundle Specification
- ADR-226 — Reference-Workspace Activation Flow (one-shot fork at signup)
- ADR-286 — Kernel/Program substrate single-writer discipline
- `docs/architecture/propagation-discipline.md` — the planning doc this ADR ratifies

**Supersedes**: None — net new mechanism.

**Amends**:
- ADR-226 — adds a continuous companion to one-shot activation fork. ADR-226's idempotency-on-re-fork semantics survive; this ADR generalizes them into a continuous daily cycle.

**Preserves**: All upstream canon. No primitive renames, no schema changes.

---

## Problem

YARNNN now has multiple live operator workspaces — three alpha-author dogfood personas (`yarnnn-author`, `netflix-script-author`, `korea-thriller-shorts`) plus kvk's alpha-trader-2. These workspaces accumulate real operator content while kernel skeleton text and program bundle templates continue to evolve in `main`.

When kernel constants like `DEFAULT_REVIEW_PRINCIPLES_MD` tighten on 2026-05-25, or when a program bundle's `context/_shared/IDENTITY.md` improves upstream, there is currently **no mechanism that propagates the improvement to already-forked workspaces.** Only new workspaces see the change.

The existing fork primitive ([api/services/programs.py::fork_reference_workspace](/Users/macbook/yarnnn/api/services/programs.py)) and `initialize_workspace()` Phase 2 ([api/services/workspace_init.py](/Users/macbook/yarnnn/api/services/workspace_init.py)) run once per workspace, at signup or persona-harness invocation. There is no scheduled re-apply.

The result: live workspaces drift further from canon every time the platform improves. With one operator (kvk) at one workspace, this was tolerable. With three dogfood personas now triangulating bundle evolution across distinct format/cadence/audience combinations, drift accumulates faster than manual re-application can address.

## Decision

Add a single continuous re-apply mechanism that runs on app deploy and as a daily back-office task. The mechanism walks platform-managed paths and re-writes them where the operator has not taken authorship.

### D1. The boundary is `authored_by` attribution, not version metadata

ADR-209's revision chain already records `authored_by` on every revision. The taxonomy distinguishes platform-written (`system:*`) from operator-authored (`operator`, `yarnnn:*`, `agent:*`, `specialist:*`, `reviewer:*`).

A file's HEAD revision's `authored_by` is the single signal that determines whether re-apply touches it:

- HEAD `authored_by` starts with `system:` → platform-managed, candidate for re-apply
- HEAD `authored_by` is anything else → operator has taken authorship, never touch

No bundle version field. No `activated_bundle_version` workspace column. No diff-detection findings table. The attribution chain is already the answer.

### D2. The mechanism — one service, one entry point

New service: `api/services/substrate_reapply.py` with one entry point:

```python
async def reapply_platform_substrate(
    client,
    user_id: str,
    *,
    source: Literal["deploy", "scheduled", "manual"],
) -> ReapplyReport
```

Logic:

1. Walk **kernel-managed paths**: `SHARED_CONTEXT_FILES` + seeded review-substrate paths from `workspace_paths.py`. For each path, resolve canonical content from the corresponding `DEFAULT_*_MD` constant in `orchestration.py`.
2. Walk **bundle-managed paths**: if `parse_active_program_slug(user_id)` returns a slug, walk every file in `docs/programs/{slug}/reference-workspace/`. Resolve canonical content from the bundle template (with tier frontmatter stripped per ADR-226).
3. For each canonical path:
   - Read HEAD revision via `list_revisions(client, user_id, path, limit=1)`.
   - If HEAD's `authored_by` does NOT start with `system:`, skip (operator owns it).
   - If HEAD's content equals canonical content byte-for-byte, skip (no drift).
   - Otherwise, write a new revision via `write_revision()` with `authored_by="system:reapply"` and a message naming the source (`kernel: DEFAULT_REVIEW_PRINCIPLES_MD updated` or `bundle: alpha-author/context/_shared/IDENTITY.md updated`).
4. Append a structured summary row to `/workspace/_shared/substrate-reapply-log.md` (system-authored, append-only).

### D3. Triggers — two only

- **On deploy**: a deploy-hook script invokes `reapply_platform_substrate(source="deploy")` for every active workspace. Kernel improvements land within minutes of deploy.
- **Daily scheduled**: a new back-office recurrence `back-office-substrate-reapply` scaffolded at signup, runs daily. Backstop for bundle improvements that ship without a code deploy (e.g., bundle-template-only PRs).

No manual operator trigger from the UI. If a workspace needs a fresh apply, the daily cycle will catch it. Manual one-off invocation via script is available for kvk during alpha.

### D4. What does NOT change

Explicit non-goals to prevent the implementation from drifting back into the over-engineered shape that the planning doc (`propagation-discipline.md`) initially proposed and rejected:

- ❌ Bundle versioning (MANIFEST.yaml gaining `version:`)
- ❌ Workspace schema columns (`activated_bundle_version`, `prompt_version_pin`, etc.)
- ❌ Drift-findings table
- ❌ Operator-facing accept/reject UI affordance
- ❌ Prompt version pinning at the workspace level
- ❌ Canary rollout infrastructure
- ❌ Per-file force-re-apply override

Each of those becomes its own ADR if and when a concrete production failure makes it acute. We do not pre-build.

### D5. Operator-authored files diverging from upstream are correct, not a bug

When the operator customizes `context/_shared/IDENTITY.md`, they take authorship. If the bundle's IDENTITY.md template improves later, the operator does NOT receive the improvement. This is the right tradeoff:

- Overwriting operator content is a worse failure than the operator missing an upstream improvement.
- The operator can manually pull upstream content by reading the bundle template (via filesystem or `docs/programs/{slug}/reference-workspace/` in the repo) and choosing what to merge.
- A future ADR can add a soft operator notification ("upstream improved this file you've customized") if the gap becomes concrete. Not now.

### D6. Prompts and schema remain on their current model

- Prompts ship at HEAD; all workspaces get them on next invocation. CHANGELOG.md is the audit trail.
- Schema migrations apply atomically at deploy time. No per-workspace gating.

Recovery from a regression in either path: `git revert + redeploy`. This affects all workspaces uniformly. At current operator scale (handful of dogfood personas, one human directing), this is correct. The first concrete production regression that this fails to recover from triggers a future ADR — not this one.

### D7. ReapplyReport — append-only audit substrate

```python
@dataclass
class ReapplyAction:
    path: str
    source: Literal["kernel", "bundle"]
    change_summary: str  # e.g., "DEFAULT_REVIEW_PRINCIPLES_MD updated"
    revision_id: str  # the new workspace_file_versions row

@dataclass
class ReapplyReport:
    user_id: str
    source: Literal["deploy", "scheduled", "manual"]
    ran_at: datetime
    actions: list[ReapplyAction]
    skipped_operator_authored: int
    skipped_aligned: int
```

Report is appended to `/workspace/_shared/substrate-reapply-log.md` via `write_revision(authored_by="system:reapply")`. Operator can read this file via the Files surface to audit what platform updates have landed in their workspace. No accept/reject; the report is informational.

## Implementation Plan

| Phase | Scope | Touches |
|---|---|---|
| 1 | `substrate_reapply.py` service + ReapplyReport schema + audit-log writer | New file only |
| 2 | Kernel path enumeration (read `SHARED_CONTEXT_FILES` + review skeleton paths from `workspace_paths.py`; resolve canonical content from `orchestration.py` constants) | Read-side only |
| 3 | Bundle path enumeration (walk `docs/programs/{slug}/reference-workspace/`, strip tier frontmatter, resolve canonical content via existing `_strip_tier_frontmatter` in `programs.py`) | Read-side only |
| 4 | Write path (`authored_by="system:reapply"` revisions) + audit-log append | Write-side via existing `write_revision()` |
| 5 | Back-office recurrence registration — `back-office-substrate-reapply` daily | `workspace_init.py` Phase 5 or back-office bundle |
| 6 | Deploy-hook script invocation across all active workspaces | New deploy-hook entry, Render service config |
| 7 | Regression test `api/test_adr292_continuous_reapply.py` covering: operator-authored skip, kernel re-apply, bundle re-apply, audit-log append, idempotency | New test |

No schema migration. No new tables. No frontend surface. No primitive renames. No prompt changes (audit-log writing is system-authored substrate, not prompt-shaped output).

## Test Gate

Invariants enforced by `api/test_adr292_continuous_reapply.py`:

1. Operator-authored file (HEAD `authored_by="operator"`) is never touched.
2. Skeleton-authored file (HEAD `authored_by="system:bundle-fork"`) with stale content gets re-applied; new revision has `authored_by="system:reapply"`.
3. Skeleton-authored file with content matching canonical is skipped (no spurious revisions).
4. Audit log at `/workspace/_shared/substrate-reapply-log.md` receives one append per re-apply run.
5. Idempotency: running re-apply twice in a row produces zero actions on the second run.
6. No bundle activated → only kernel paths walked; bundle walk skipped cleanly.

## Out of Scope / Future ADRs

The following remain explicitly out of scope and become future ADRs only if a concrete failure case emerges:

- Bundle-template-vs-workspace diff visibility (operator-facing surface)
- Prompt version pinning + canary rollout
- Per-migration schema feature flags
- Cross-workspace propagation observability dashboard
- Reflexive loop (lived → bundle graduation) — already deferred as ADR 6 in `os-framing-implementation-roadmap.md`

## Open Questions

- **Deploy-hook integration shape.** Render does not have a first-class post-deploy hook for arbitrary scripts. Options: (a) cron job that runs every 5 min and short-circuits if no deploy occurred since last run; (b) explicit one-shot job triggered manually via Render Job after each `main` deploy; (c) accept that "on deploy" really means "within 24h of deploy via the daily back-office task." Option (c) is the simplest and likely correct — kernel improvements are rarely time-critical to the minute.

- **Bundle freshness for the daily cycle.** The daily back-office task running on the API service reads bundles from the deployed code's `docs/programs/` directory. This means the daily cycle picks up bundle changes only after the code is deployed. Bundle-template-only PRs that need to reach workspaces require a deploy regardless. This is acceptable and matches Claude Code's "update the binary, propagate" shape.

- **Audit log retention.** `/workspace/_shared/substrate-reapply-log.md` grows monotonically. ADR-209 revision chain caps file size implicitly via revision count, not byte count. If audit log entries become dense, a future trim discipline may be needed — out of scope for now.
