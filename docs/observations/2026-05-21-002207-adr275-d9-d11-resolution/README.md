# ADR-275 D9–D11 resolution — contract-shape gap closed

**Hat**: External Developer (Hat B) — empirical capture of the resolution outcomes.
**Time**: 2026-05-21T00:22Z.
**Hat-A commit**: `8652d09` — ADR-275 D9–D11 amendment + bundle-fork-from-preferences seeding + persona-frame contract simplification.

## One-line verdict

Contract-shape gap closed. All three live workspaces re-forked successfully; deliverable cadences are now scheduled at the activation layer regardless of which Reviewer wakes first. kvk-vs-alpha-trader-2 cycle-1 asymmetry resolves structurally.

| Workspace | Tasks index post-D9 |
|---|---|
| kvk (alpha-trader) | 11 active (8 bundle + 3 D9-seeded deliverables) |
| alpha-trader-2 (alpha-trader) | 11 active (8 bundle + 3 D9-seeded; prior Reviewer-authored entries preserved in conflict backup) |
| yarnnn-author (alpha-author) | 5 active (3 bundle + 2 D9-seeded deliverables) |

## Three side-findings recorded for future Hat-A work

1. **feed.py ADR-276 envelope-helper drift** (pre-existing, out of scope for O4) — `feed.py` doesn't yet import `load_reviewer_governance_envelope`. Needs separate commit.
2. **ADR-292 v3 D10 + ADR-275 D9 interaction** — operator-authored `_recurrences.yaml` config-conflict auto-resolves to backup, then D9 seeds preferences against the bundle-clean state. Architecturally correct; minor cosmetic question deferred.
3. **Pre-existing test gate drift closed** — `trade-proposal` removed from PRESERVED_SLUGS, `mirror-signal-state` added; `_preferences.yaml` lock policy applied per original ADR-275 D6.

See `findings.md` for the full empirical capture + cross-references.
