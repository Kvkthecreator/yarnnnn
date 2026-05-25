# ADR-275 D9–D11 resolution — contract-shape gap closed

**Hat**: External Developer (Hat B) capturing the empirical resolution of the contract-shape gap.
**Time captured**: 2026-05-21T00:22Z.
**Author**: Claude (Opus 4.7).

**Hat-A artifact**: commit `8652d09` — ADR-275 D9–D11 amendment + `_seed_recurrences_from_preferences` extension + persona-frame contract simplification.

**Hat-B context**: companion to [substrate contract audit](../2026-05-20-235100-substrate-contract-audit/findings.md) (the Hat-B finding that motivated the Hat-A amendment).

---

## What this captures

The 2026-05-20T13:46-13:47Z kvk-vs-alpha-trader-2 cycle-1 asymmetry surfaced a contract-shape mismatch on `_preferences.yaml`. The substrate contract audit walked seven options across the spectrum (promote / hard-gate / strengthen text / reframe-bundle-fork-honors / dissolve into MANDATE / dissolve into `_recurrences` / delete entirely). Operator agreed to move on **Option 4 (reframe: bundle-fork honors first-time `_preferences.yaml` at activation; Reviewer reconciles subsequent operator preference CHANGES)** as the structurally correct fix.

This observation records the empirical re-fork outcomes against the three live workspaces post-amendment.

---

## Re-fork outcomes (2026-05-21T00:21Z)

Re-forked all three live workspaces against the new `fork_reference_workspace` with the D9 `_seed_recurrences_from_preferences` step.

### kvk (alpha-trader)

- **Bundle version**: 2026-05-20.1 → 2026-05-20.1 (no version change; D9 logic ships in fork helper, not bundle content)
- **D9 preferences seeded** (NEW): `pre-market-brief`, `weekly-performance-review`, `quarterly-signal-audit`
- **D9 preferences skipped (idempotency)**: none
- **Config conflicts**: 0 (kvk's `_recurrences.yaml` head was `system:bundle-fork` from the earlier post-Fix-1A re-fork; no operator-authored edits to back up)
- **Tasks index post-refork**: 11 active recurrences (8 bundle-shipped + 3 D9-seeded)
- **Outcome**: cycle-1 asymmetry resolved. kvk's deliverable cadences now match alpha-trader-2 structurally. The Reviewer at next natural wake (2026-05-21T13:45Z signal-evaluation) will see them already scheduled — its only contract is change-reconciliation (D10) if/when operator edits `_preferences.yaml`.

### alpha-trader-2 (alpha-trader)

- **D9 preferences seeded**: `pre-market-brief`, `weekly-performance-review`, `quarterly-signal-audit`
- **D9 preferences skipped (idempotency)**: none
- **Config conflicts**: 1 (`_recurrences.yaml` had Reviewer-authored entries from 2026-05-20T13:46Z; ADR-292 v3 D10 auto-resolved with operator backup at `_shared/conflict-backups/2026-05-21T00-21-20Z/_recurrences.yaml`)
- **Tasks index post-refork**: 11 active recurrences (8 bundle-shipped + 3 D9-seeded)
- **Outcome**: structurally identical to kvk post-refork. The Reviewer's earlier authorship is preserved in the conflict backup + the workspace_file_versions revision chain. Live state attribution is `system:bundle-fork-from-preferences` for the 3 deliverables — architecturally correct per D9.

### yarnnn-author (alpha-author)

- **D9 preferences seeded**: `weekly-corpus-review`, `quarterly-voice-audit`
- **D9 preferences skipped (idempotency)**: none
- **Config conflicts**: 0 (yarnnn-author's `_recurrences.yaml` head was bundle-clean from the post-Fix-1A re-fork)
- **Tasks index post-refork**: 5 active recurrences (3 bundle-shipped + 2 D9-seeded)
- **Outcome**: yarnnn-author's deliverable cadences (which were dropped from the tasks index during Fix 1A — the Reviewer had authored them on 2026-05-18 but those rows lived in the pre-Fix-1A `_recurrences.yaml` that got auto-replaced) are now structurally seeded at the activation layer. No future Reviewer cycle-1 judgment required for these.

---

## What changed structurally

| Property | Before D9 amendment | After D9 amendment |
|---|---|---|
| Initial honoring of `_preferences.yaml` | Reviewer judgment at first wake (variable across Reviewers) | bundle-fork-from-preferences (deterministic at activation) |
| Reviewer's runtime contract | "Read `_preferences.yaml` every wake, author Schedule(create) for unscheduled preferences" | "Read `_preferences.yaml` every wake, author Schedule(update/pause/archive) when operator-authored CHANGES detected" |
| Authorship attribution on deliverables | `reviewer:ai:reviewer-sonnet-v8` (when Reviewer judged the moment right) or absent (when Reviewer judged otherwise) | `system:bundle-fork-from-preferences` at activation; `reviewer:ai:reviewer-sonnet-v8` thereafter on operator-CHANGE reconciliation |
| Cycle-1 reproducibility | Variable (kvk vs alpha-trader-2 diverged on identical inputs) | Deterministic (bundle-fork runs same code per workspace) |
| Introspection cadence | Reviewer-authored per first-principled judgment | Reviewer-authored per first-principled judgment (unchanged — D11) |
| Operator authority over `_preferences.yaml` | Read-only by intent, write-unlocked by code (drift) | Read-only by intent AND by code (lock added to `DEFAULT_REVIEWER_WRITE_LOCKS`) |

---

## What the audit predicted vs what we observed

The audit's Observation 4 named the underlying class:

> **The asymmetry isn't a contract-strength problem. It's a contract-shape problem.** `_preferences.yaml` is declaration-shape (operator names what they want) but its honoring mechanism is Reviewer-judgment-shape (Reviewer decides each wake whether to act).

Prediction (post-O4): post-amendment, both workspaces would have the deliverable cadences scheduled at activation. ✓ Confirmed empirically.

Prediction (post-O4): the Reviewer's runtime authority survives at the layer where Reviewer judgment is genuinely appropriate — preference-CHANGE reconciliation. ✓ Confirmed by the persona-frame contract text + the test gate's D10 assertion.

Prediction (post-O4): introspection cadence (D11) is unchanged — Reviewer-authored from first principles. ✓ Confirmed; no D11 code or persona-frame edits touched introspection-cadence territory.

The structural reasoning held. No empirical surprises in the re-fork outcomes.

---

## Side-findings recorded (for future Hat-A work)

### Side-finding 1: feed.py ADR-276 envelope-helper drift

The test gate's `test_feed_addressed_site_loads_preferences_and_autonomy` + `test_d9_seed_helper_exists` runs revealed that `api/routes/feed.py` does NOT yet import `load_reviewer_governance_envelope` from `services.reviewer_envelope` as ADR-276 Singular Implementation prescribes. This drift is **pre-existing** (predates this commit) and **out of scope for the O4 amendment**.

Risk: addressed-trigger Reviewer wakes may not be loading the full governance envelope per ADR-276. The reactive-trigger path (`invocation_dispatcher.py`) was confirmed correct in ADR-276 §"RESOLVED by ADR-276"; the feed.py addressed-trigger path needs the same migration.

Recommendation: separate Hat-A commit to migrate `feed.py` to use `load_reviewer_governance_envelope`. Two test gate assertions will green automatically once it lands.

### Side-finding 2: ADR-292 v3 D10 + ADR-275 D9 interaction

When a workspace has operator-authored `_recurrences.yaml` AND new D9 preference-seeding runs in the same fork, the sequence is:

1. ADR-292 v3 D10: `_recurrences.yaml` config-conflict auto-resolves (operator content → backup, bundle template re-applied)
2. ADR-275 D9: `_seed_recurrences_from_preferences` reads post-D10 `_recurrences.yaml` (= bundle template, doesn't include operator's Reviewer-authored entries), seeds preferences

Net effect: Reviewer's prior cadence-authoring is preserved in the conflict backup + revision chain. Live attribution becomes `system:bundle-fork-from-preferences` per D9.

This is **architecturally correct** — D9 is the canonical authority for initial honoring; the Reviewer-authored entries from the pre-D9 era live in history. Operationally clean.

The minor cosmetic question: would it be desirable for D9 to inspect the conflict backup and "rescue" Reviewer-authored entries that match a `_preferences.yaml` slug? Probably no — over-engineered. The backup is operator-readable; the operator can manually re-apply Reviewer's prior cadence edits by editing `_preferences.yaml` if those edits represented genuine cadence preferences.

### Side-finding 3: pre-existing test gate drift (now closed)

The pre-existing ADR-275 test gate had `trade-proposal` in `PRESERVED_SLUGS` — outdated since ADR-296 v2 Checkpoint 2 deleted that recurrence (2026-05-20). This commit also added `mirror-signal-state` per ADR-281 §3 derived principle 19. Test gate now aligned with current bundle state.

Also closed: pre-existing drift between ADR-275 D6 (which specified `_preferences.yaml` should be locked) and `DEFAULT_REVIEWER_WRITE_LOCKS` (which had it unlocked). Lock now applied.

---

## Test gate state

| Gate | Before commit `8652d09` | After commit `8652d09` |
|---|---|---|
| `test_adr275_introspection_cadence.py` | 16/20 passing (4 failures: 1 stale PRESERVED_SLUGS, 1 lock policy drift, 2 ADR-276 feed.py drift) | 24/26 passing (2 remaining failures are pre-existing ADR-276 feed.py drift, out of scope) |
| `test_adr292_continuous_reapply.py` | 25/25 passing | 25/25 passing (no regression) |

---

## Cross-references

- Hat-A commit: `8652d09` (ADR-275 D9–D11 amendment + code)
- Hat-B finding: [substrate contract audit](../2026-05-20-235100-substrate-contract-audit/findings.md)
- ADR-275 doc: `docs/adr/ADR-275-introspection-cadence-reviewer-authored.md` (D9–D11 amendment section)
- Code: `api/services/programs.py::_seed_recurrences_from_preferences` + `_format_recurrence_entry_yaml`
- Persona frame: `api/agents/reviewer_agent.py::_PERSONA_FRAME` (D10 contract text)
- Test gate: `api/test_adr275_introspection_cadence.py` (6 new D9–D11 assertions)
- Prompt CHANGELOG: `api/prompts/CHANGELOG.md` `[2026.05.21.1]`
