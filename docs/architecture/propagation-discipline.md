---
title: Substrate Propagation Discipline — Canonical Reference
date: 2026-05-18
status: planning doc — ratified into ADR-292 (Proposed) on 2026-05-18
related:
  - docs/adr/ADR-209-authored-substrate.md (authored_by attribution — the load-bearing primitive)
  - docs/adr/ADR-222-agent-native-operating-system-framing.md (kernel/program boundary)
  - docs/adr/ADR-223-program-bundle-specification.md (bundle shape)
  - docs/adr/ADR-226-reference-workspace-activation-flow.md (one-shot fork)
  - api/prompts/CHANGELOG.md (prompt audit trail)
---

# Substrate Propagation Discipline — Canonical Reference

> **What this is:** the canonical reference for how kernel + program-bundle substrate updates reach live operator workspaces. Names the one mechanism needed.
>
> **What this is not:** an ADR. The ADR drafts when this is ratified.

---

## Motivation

YARNNN now has three live dogfood persona workspaces (`yarnnn-author`, `netflix-script-author`, `korea-thriller-shorts`) forked from the alpha-author bundle on 2026-05-18. When kernel skeleton text improves on 2026-05-25 (e.g., tightened safety language in `DEFAULT_REVIEW_PRINCIPLES_MD`), or when the alpha-author bundle's `context/_shared/IDENTITY.md` improves upstream, **there is no current mechanism to propagate those improvements to the three live workspaces.** The improvements reach new workspaces only.

This doc names the discipline that closes that gap. The OS metaphor is the right one: when Claude Code updates, the platform code replaces; the operator's content is untouched. YARNNN should work the same way.

---

## The boundary that makes update-in-place safe

ADR-209 already gave us the load-bearing primitive: every revision of every workspace file carries an `authored_by` attribution. The taxonomy (`operator` | `yarnnn:<model>` | `agent:<slug>` | `specialist:<role>` | `reviewer:<identity>` | `system:<actor>`) cleanly distinguishes **platform-written** revisions (anything `system:*`) from **operator-authored** revisions (anything else).

That is the boundary. Files where HEAD revision is `system:*` are platform-managed — safe to update. Files where HEAD revision is anything else are operator-authored — never touched by the update mechanism.

No version columns. No accept/reject UI. No canary infrastructure. The attribution chain already encodes the decision.

---

## The mechanism

A single continuous re-apply path. Triggered on deploy and as a cheap daily back-office task.

For each workspace:

1. Walk the **kernel-managed paths** — `SHARED_CONTEXT_FILES` + the seeded review-substrate paths (defined in `workspace_paths.py` and `workspace_init.py` Phase 2).
2. Walk the **bundle-managed paths** — every file in `docs/programs/{activated_slug}/reference-workspace/` (when a program is activated).
3. For each path: read HEAD revision's `authored_by`. If it starts with `system:`, compare current content against the canonical source (kernel constant or bundle template). If they differ, write a new revision via `authored_substrate.write_revision()` with `authored_by="system:reapply"` and a message naming the change source.
4. If `authored_by` is anything else, skip. The operator (or any non-system actor) has taken authorship.

That's the whole mechanism. One service. One cron entry. No schema changes. No UI.

---

## What this does and does not cover

**Covers:**
- Kernel skeleton improvements reach all workspaces where the skeleton is still platform-written.
- Bundle template improvements reach all forked workspaces where the file is still bundle-written.
- The three dogfood personas accumulate updates continuously, the same way Claude Code accumulates updates between releases.

**Does not cover:**
- **Operator-authored files diverging from upstream improvements.** Once the operator writes their own IDENTITY.md, they own it. If we improve the bundle's IDENTITY.md, the operator does not get the improvement. This is correct — overriding operator content is a worse failure than letting them miss an upstream improvement.
- **Prompts.** Already work this way (HEAD ships, all workspaces get it). CHANGELOG.md is the audit trail.
- **Schema.** Already works this way (atomic migrations).

For prompts and schema, the implicit choice is: **no per-workspace version pinning, no canary rollout.** When a regression ships, recovery is `git revert + redeploy` and affects all workspaces uniformly. This is the right tradeoff at current operator scale (one human, a handful of workspaces). The first concrete production regression that this tradeoff fails to recover from is the trigger for a future ADR — not this one.

---

## Implementation shape (for the ADR draft)

When this gets ratified into an ADR:

- New service: `api/services/substrate_reapply.py` with one entry point `reapply_platform_substrate(client, user_id) -> ReapplyReport`.
- New back-office recurrence: `back-office-substrate-reapply` in workspace_init's signup-time scaffolds, daily cadence.
- Optional: invoke once on app deploy from a one-shot script the deploy hook runs, so kernel improvements propagate immediately rather than waiting up to 24h.
- ReapplyReport written to `/workspace/_shared/substrate-reapply-log.md` (append-only, system-authored). Operator-visible audit trail; no affordance needed because no decision is required of them.

No schema migration. No new tables. No new columns. No FE surface.

---

## What this does not become

Explicitly out of scope so the ADR draft does not drift back into the original over-engineered shape:

- ❌ Bundle versioning (MANIFEST.yaml gaining `version:`)
- ❌ Workspace columns tracking `activated_bundle_version`
- ❌ Drift detection findings table
- ❌ Operator-facing accept/reject affordance
- ❌ Prompt version pinning
- ❌ Canary rollout infrastructure

If any of those become acute later (concrete failure case observed in production), they get their own ADR at that time. We do not pre-build them.

---

## Relationship to ADR 6 (Reference-Reflexive Loop)

The deferred ADR 6 in `os-framing-implementation-roadmap.md` graduates lived substrate patterns *back into bundles*. This doc handles the reverse — updated bundles reaching lived workspaces. Same `authored_by` attribution layer is load-bearing for both, but the two mechanisms are independent and can ship in either order.
