# kvk probe-residue cleanup — Fix 1B hygiene pass

**Hat**: External Developer of the System (Hat B observation; cleanup writes attributed `system:probe-cleanup` per ADR-209).
**Time captured**: 2026-05-20T11:07Z.
**Author**: Claude (Opus 4.7).
**Reference**: companion to [pre-e2e-readiness-audit](../2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2/findings.md) §4 Fix 1B + [T0 PLAYBOOK](../2026-05-20-040500-kvk-autonomy-demonstration-T0/PLAYBOOK.md) §"Probe-residue named explicitly."

---

## What this captures

The kvk (alpha-trader) workspace accumulated probe-residue from the 2026-05-20 warm-start + post-refusal-self-amendment-probe scenarios (`docs/observations/2026-05-20-013220-warm-start-auto-execute/`, `2026-05-20-013632-warm-start-auto-execute/`, `2026-05-20-022520-post-refusal-self-amendment-probe/`). The T0 PLAYBOOK explicitly named the residue and warned that next-RTH Reviewer wakes would reason from polluted prior state.

Per operator-confirmed direction 2026-05-20T10:50Z, this is a separate hygiene pass independent of the e2e itself (which runs on alpha-trader-2). Five substrate writes + 5 action_proposal cancellations land here; all prior probe revisions are preserved in the workspace_file_versions revision chain as immutable historical record per ADR-209.

Execution: `api/scripts/oneshot/adr292_v3_kvk_probe_residue_cleanup.py`.

---

## Cleanup writes

| Path | Pre-cleanup head | Action | Post-cleanup head |
|---|---|---|---|
| `/workspace/context/trading/_operator_profile.md` | Reviewer-edit at 02:27:12Z (post-refusal-self-amendment-probe ADR-295 D3 anti-pattern capitulation) | Revert to pre-probe `system:bundle-fork` revision (00:11:38Z) | `system:probe-cleanup` at 11:07:30Z — content matches bundle |
| `/workspace/context/trading/_money_truth.md` | Probe-seeded at 02:25:36Z by `operator-proxy:scenario-runner:acting-as-kvk` (5 probe revisions total) | Reset to empty-state shape (`rolling_30d_expectancy_R: 0.0`, no outcomes, body explains reset) | `system:probe-cleanup` at 11:07:30Z |
| `/workspace/review/standing_intent.md` | Reviewer-authored at 02:27:24Z, content referencing fabricated `_risk.md` edits (8 probe revisions total) | Reset to bootstrap shape — empty sections with "pending first natural wake" markers | `system:probe-cleanup` at 11:07:31Z |
| `/workspace/review/judgment_log.md` | Reviewer-authored at 02:27:50Z, 4 decision blocks on probe-driven proposals (10 probe revisions total) | Reset to header-only bootstrap | `system:probe-cleanup` at 11:07:31Z |

All prior revisions preserved in `workspace_file_versions` per ADR-209. The cleanup writes appear as new entries at the head of each chain; the probe revisions stay walkable via `ListRevisions(path=...)`.

---

## Action proposals cancelled

5 `action_proposals` rows with `status='pending'` were probe-driven (4 from warm-start scenarios at 00:12-01:14Z, 1 from post-refusal probe at 02:25Z). All transitioned to `status='rejected'` with `execution_result.outcome='cancelled_during_cleanup'` and explanatory `execution_result.message`. None had been executed against the live broker (all were pending operator review when the cleanup ran).

| Proposal ID | Pre-cleanup status | Pre-cleanup action_type | Post-cleanup status |
|---|---|---|---|
| 4de33e11-a367-49e1-b1d3-5279997d5a15 | pending | trading.submit_order | rejected (cancelled_during_cleanup) |
| eeefca91-70fc-4873-8b39-f28a52dda79e | pending | trading.submit_order | rejected (cancelled_during_cleanup) |
| d8e7e7fd-0aa8-47df-ab7c-7c57a3f63b4a | pending | trading.submit_order | rejected (cancelled_during_cleanup) |
| 2a666593-c4e7-4343-8dfb-260cd39c801c | pending | trading.submit_order | rejected (cancelled_during_cleanup) |
| 3d3023bd-dc62-4f0b-9a26-79e8fd8d2952 | pending | trading.submit_order | rejected (cancelled_during_cleanup) |

The 3 already-terminal-status probe proposals (b06d53ed `rejected_at_execution`, 815ecc18 `rejected_at_execution`, ee7661ed `rejected`) were left untouched — they're historical artifacts, not live work.

---

## Post-cleanup state

| Property | Post-cleanup value |
|---|---|
| `_operator_profile.md` head | `system:probe-cleanup` reverting to pre-probe bundle-fork content |
| `_money_truth.md` head | `system:probe-cleanup` empty-state shape (no outcomes, no fabricated rolling expectancy) |
| `standing_intent.md` head | `system:probe-cleanup` bootstrap shape (next natural wake populates) |
| `judgment_log.md` head | `system:probe-cleanup` header-only bootstrap |
| `action_proposals` pending count | 0 (all 5 probe-pending rows cancelled) |
| Bundle version frontmatter | `2026-05-20.1` (from prior Fix 1A re-fork) |
| `_recurrences.yaml` | bundle-clean post-Fix-1A re-fork (no `trade-proposal`, signal-evaluation teaches inline ProposeAction) |
| `_hooks.yaml` | exists, `hooks: []` (alpha-trader bundle ships empty hook list) |

kvk's workspace is now equivalent to a freshly-activated alpha-trader workspace, except for:
- The full workspace_file_versions revision chain capturing the probe scenarios as historical record (ADR-209 attribution makes the audit story honest)
- Existing Alpaca paper-trading connection (preserved — not touched by cleanup)
- 3 terminal-status `action_proposals` rows from probe scenarios (rejected/rejected_at_execution — left for audit trail; do not surface as live work)

---

## Implications for the e2e

kvk is now available as a **secondary e2e validation persona** if needed alongside alpha-trader-2 (the primary). Both workspaces are post-Checkpoint-2 bundle-clean + autonomy-flipped (alpha-trader-2 to autonomous; kvk was already autonomous per its `_autonomy.yaml`). Running both in parallel would provide:

- alpha-trader-2 — stat-arb pairs persona (operator-authored body content, distinct signals from kvk's vanilla bundle defaults)
- kvk — vanilla bundle-default operator profile (no operator-authored stat-arb specifics; tests "fresh persona out of the box")

Or kvk can stay as a hygiene-validation baseline (no e2e load) while alpha-trader-2 carries the e2e. Operator's call.

---

## Architectural finding: probe-cleanup as a pattern

This cleanup is the second of its kind in the codebase (`adr281_e2e_purge_reinit_kvk.py` was the first, for a different purpose — full reinit rather than surgical revert). A pattern is emerging:

**When a scenario probe writes substrate that contaminates subsequent observation runs, the cleanup is a one-shot script that writes new revisions reverting state, attributed `system:probe-cleanup`, leaving the probe revisions in the chain as historical record.**

If this pattern recurs (e.g., future ADR-295 anti-pattern probes leave residue that needs cleanup before the next observation window), it might warrant a primitive — something like `RevertToRevision(path, target_revision_id, reason)` — or at minimum a doc convention naming `system:probe-cleanup` as the canonical actor + `/workspace/_shared/probe-cleanup-log.md` as a per-workspace cleanup audit trail.

Recording as a finding-level recommendation. Not pre-implementing — pattern needs a third occurrence to justify abstraction.

---

## Cross-references

- [Pre-e2e readiness audit findings](../2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2/findings.md) — surfaced the residue
- [T0 PLAYBOOK probe-residue section](../2026-05-20-040500-kvk-autonomy-demonstration-T0/PLAYBOOK.md) — explicitly named the contamination
- [Post-refusal-self-amendment-probe observation](../2026-05-20-022520-post-refusal-self-amendment-probe/) — the discipline-failure that produced the Reviewer-edited `_operator_profile.md`
- [alpha-trader-2 e2e persona flip](../2026-05-20-105038-alpha-trader-2-e2e-persona-flip/findings.md) — sibling Fix 1B work
- Commit `96acefe` — ADR-292 v3 system canon work
- Script: `api/scripts/oneshot/adr292_v3_kvk_probe_residue_cleanup.py`
