---
title: Substrate Propagation Discipline — Canonical Reference
date: 2026-05-18
status: planning doc — ratified into ADR-292 (Implemented Phase 1) on 2026-05-18
related:
  - docs/adr/ADR-292-continuous-substrate-reapply.md (operator-initiated versioned updates)
  - docs/adr/ADR-209-authored-substrate.md (authored_by attribution — the load-bearing primitive)
  - docs/adr/ADR-222-agent-native-operating-system-framing.md (kernel/program boundary)
  - docs/adr/ADR-223-program-bundle-specification.md (bundle shape)
  - docs/adr/ADR-226-reference-workspace-activation-flow.md (one-shot fork)
  - docs/adr/ADR-244-workspace-settings-surface.md (operator-facing update surface home)
  - api/prompts/CHANGELOG.md (prompt audit trail)
---

# Substrate Propagation Discipline — Canonical Reference

> **What this is:** the canonical reference for how kernel + program-bundle substrate updates reach live operator workspaces. Names the one mechanism, names the shape.
>
> **What this is not:** an ADR. The ADR is [ADR-292](../adr/ADR-292-continuous-substrate-reapply.md).

---

## Motivation

YARNNN now has three live dogfood persona workspaces (`yarnnn-author`, `netflix-script-author`, `korea-thriller-shorts`) forked from the alpha-author bundle on 2026-05-18, plus kvk's alpha-trader-2. When kernel skeleton text improves on 2026-05-25 (e.g., tightened safety language in `DEFAULT_REVIEW_PRINCIPLES_MD`), or when the alpha-author bundle's `persona/IDENTITY.md` improves upstream, the improvement does not reach the three live workspaces. Drift accumulates faster than manual re-application can address.

The right mental model: **Claude Code's `claude --update`.** Anthropic releases a new model; Claude Code presents the update as available; the operator decides when to take it. Versioned, operator-initiated, not a polling cron.

---

## The boundary that makes update safe

ADR-209's revision chain records `authored_by` on every revision. The taxonomy distinguishes platform-written (`system:*`) from operator-authored (`operator`, `yarnnn:*`, `agent:*`, `specialist:*`, `reviewer:*`).

But the operative gate is finer: [api/services/workspace_utils.py::is_skeleton_content](../api/services/workspace_utils.py) compares the *content* of a workspace file against canonical content. A file passes the "still platform-managed" check if and only if content matches the canonical template (verbatim, or against bundle-template markers). This is what `fork_reference_workspace` already uses — battle-tested across every persona activation since ADR-226.

ADR-292 reuses this gate; no parallel `authored_by`-only gate. Singular Implementation.

---

## The mechanism (Claude Code shape)

Three pieces:

1. **Platform version stamps.**
   - `KERNEL_VERSION` constant in [api/services/orchestration.py](../api/services/orchestration.py). One string per release. Date-stamped (`2026-05-18.1`).
   - `version:` field in each bundle's `MANIFEST.yaml`. Bumped by the bundle author per substrate change.

2. **Workspace version record (substrate-native).**
   - MANDATE.md frontmatter carries `activated_bundle_version` and `activated_kernel_version`.
   - Absence = "no version recorded yet" (workspaces activated before ADR-292).
   - ADR-209 attribution captures version-advance events in the revision chain.

3. **Operator-initiated update flow.**
   - Backend detection helpers (`bundle_update_available()`, `kernel_update_available()`) compare workspace version against platform version. Return non-None when behind.
   - Settings → Workspace surface (ADR-244 home) renders "Update available" when detection returns non-None.
   - Operator clicks Update → backend invokes `apply_substrate_update(client, user_id, scope=...)`.
   - Worker re-applies platform-managed files via existing `fork_reference_workspace` + a parallel kernel-layer walker. Operator-authored files skipped via `is_skeleton_content`.
   - MANDATE.md frontmatter version stamps advance on success.
   - Audit log appended to `/workspace/_shared/substrate-update-log.md`.

That's the whole mechanism. No cron, no schema columns, no diff-findings table.

---

## What this covers, and what it does NOT

**Covers:**
- Kernel skeleton improvements reach all workspaces where the operator hasn't customized AND the operator chooses to take the update.
- Bundle template improvements reach all forked workspaces under the same conditions.
- The three dogfood personas adopt updates on the operator's cadence, the same way Claude Code adopts updates on the user's cadence.

**Does not cover:**
- **Automatic propagation.** Operator decides. No background pull.
- **Operator-authored files diverging from upstream.** Once the operator writes their own IDENTITY.md, they own it. If the bundle improves IDENTITY.md, the operator does NOT get the improvement automatically. Correct: overwriting operator content is a worse failure than missing an upstream improvement.
- **Prompts.** Ship at HEAD; all workspaces get them on next invocation. CHANGELOG.md is the audit trail.
- **Schema.** Migrations apply atomically at deploy time.

For prompts and schema, the implicit choice is: **no per-workspace version pinning, no canary rollout.** Recovery from a regression is `git revert + redeploy` affecting all workspaces uniformly. Right tradeoff at current operator scale; first concrete production regression that this fails to recover from triggers a future ADR.

---

## Implementation shape (Phase 1 — Implemented)

| Component | Location |
|---|---|
| Version constant | `KERNEL_VERSION` in `api/services/orchestration.py` |
| Bundle version | `version:` in `docs/programs/{slug}/MANIFEST.yaml` |
| Bundle version helper | `bundle_reader.get_bundle_version(slug)` |
| MANDATE.md frontmatter | `_parse_frontmatter` / `_render_frontmatter` in `substrate_reapply.py` |
| Detection (bundle) | `substrate_reapply.bundle_update_available(client, user_id)` |
| Detection (kernel) | `substrate_reapply.kernel_update_available(client, user_id)` |
| Worker | `substrate_reapply.apply_substrate_update(client, user_id, *, scope, source)` |
| Audit log | `/workspace/_shared/substrate-update-log.md` |
| Attribution actor | `system:substrate-update` |
| Test gate | `api/test_adr292_continuous_reapply.py` |

## Phase 2 — Frontend (Proposed)

| Component | Status |
|---|---|
| `GET /api/workspace/state` returns `bundle_update` + `kernel_update` info | Pending |
| Settings → Workspace surface renders update affordances | Pending |
| "Update" button calls update endpoint with scope | Pending |
| Audit-log viewer | Pending |

Backend stands alone; FE lands in a follow-up commit.

---

## What this is NOT (explicit non-goals)

To prevent future drift back into the over-engineered shapes:

- ❌ Daily back-office cron walking every workspace every 24h
- ❌ Mechanical primitive (`ReapplyPlatformSubstrate`) in HANDLERS
- ❌ Bundle recurrences shipping a `back-office-substrate-reapply` entry
- ❌ Schema columns for `activated_bundle_version` (substrate-native in MANDATE.md frontmatter)
- ❌ Per-file diff-findings table
- ❌ Per-file accept/reject affordance for operator at update-time (the config-vs-prose taxonomy per ADR-292 v3 D9 is the policy)
- ❌ Three-way merge of operator-edits into bundle config
- ❌ Prompt version pinning
- ❌ Canary rollout / staged release infrastructure

Each becomes its own ADR if a concrete production failure makes it acute.

---

## v3 amendment (2026-05-20) — config-vs-prose taxonomy + CI version-bump gate

Closes two structural drift classes surfaced by ADR-296 v2 Checkpoint 2 ([observation findings](../observations/2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2/findings.md)):

**Gap A — version-bump dependency on author discipline.** Checkpoint 2 modified bundle reference-workspace files for both alpha-trader and alpha-author without bumping `MANIFEST.yaml::version`. Both bundles still declared `version: 2026-05-18.1` post-Checkpoint-2. `bundle_update_available()` returned None because version strings matched; live workspaces had no path to detect the update.

**Fix (D11):** `scripts/lint_bundle_version_bump.py` — runnable lint that compares files-changed-in-range against `MANIFEST.yaml::version` line diff for every bundle under `docs/programs/`. Exit 1 when bundle content (`reference-workspace/` or `specs/`) changed but version didn't bump.

Run before commit:
```bash
python scripts/lint_bundle_version_bump.py --working-tree
```

Run against PR diff:
```bash
python scripts/lint_bundle_version_bump.py --base-ref origin/main
```

**Gap B — silent skip of operator-edited bundle config files.** The `fork_reference_workspace` worker uses `is_skeleton_content()` as the only gate. Once the operator (or the Reviewer per ADR-275) edits `_recurrences.yaml`, every subsequent re-fork attempt skips it silently. When the bundle later changes the file's shape (Checkpoint 2 deleted `pre-ship-audit` from `_recurrences.yaml` and added `_hooks.yaml`), the live workspace had no way to receive the change.

**Fix (D9 + D10):** introduce a config-vs-prose taxonomy on bundle files. **Config files** (operationally load-bearing: `_recurrences.yaml`, `_hooks.yaml`) auto-overwrite-with-backup when the bundle moves — operator edits go to `/workspace/_shared/conflict-backups/{ran_at}/{relative_path}`, bundle's new content lands at the live path, the audit log + UpdateReport surface the conflict explicitly. **Prose files** (IDENTITY, MANDATE body, BRAND, principles, voice, editorial, risk envelope, operator profile) stay operator-protected as before. Closed-set declared in code (`services.substrate_reapply.CONFIG_PATHS`); adding a third config file requires an ADR amendment.

The discipline change in plain words: when the platform ships a new bundle version, operationally-load-bearing config files reach the live workspace automatically (with the operator's prior edits backed up for inspection); operator-authored prose stays where the operator put it. The mismatch between "operator intent" (their edits) and "kernel runtime contract" (the bundle's shape) is resolved by giving each side its proper home — backup for the operator's intent record, live path for the kernel's runtime contract.

---

## Discipline lessons recorded

The doc was drafted three times in escalating-then-deescalating scope:

1. **v1** (initial) — 5 ADR slots (bundle versioning + drift detection + operator affordance + kernel re-apply + prompt pinning). 360 lines.
2. **v2** (corrected) — collapsed to "one continuous re-apply mechanism, gated by `authored_by`." 95 lines. Still wrong: framed as **daily cron**, not operator-initiated.
3. **v3** (current) — operator-initiated versioned-update shape (this version). Claude Code's `claude --update`, not a background pull.

The lesson: when the OS metaphor pulls toward "build deployment-platform infrastructure," check what real OSes actually do. macOS doesn't auto-merge changes to your `~/Library` daily. Anthropic doesn't push new Claude versions to your sessions. The user runs the update when ready. Same shape for YARNNN.

---

## Relationship to ADR 6 (Reference-Reflexive Loop)

The deferred ADR 6 in `os-framing-implementation-roadmap.md` graduates lived substrate patterns *back into bundles*. This doc handles the reverse — updated bundles reaching lived workspaces. Same `authored_by` attribution + `is_skeleton_content` gate are load-bearing for both, but the two mechanisms are independent.
