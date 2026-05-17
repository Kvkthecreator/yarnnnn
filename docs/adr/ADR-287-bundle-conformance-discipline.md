# ADR-287: Bundle Conformance Discipline — CI Gate for Kernel-Required Bundle Surface

**Status**: Implemented (2026-05-18) — single atomic commit `a8763b1` shipped ADR + new conformance test (8 ADR-keyed walks) + bit-rot fix in test_adr230 (3 stale tests corrected) + alpha-author backfill (review/IDENTITY.md + principles.md + 4 recurrence prompts + persona-row occupant_attribution). 16/16 conformance assertions PASS across alpha-trader (active) + alpha-author (deferred, 13/13 ready) + alpha-commerce (deferred, 1/13 placeholder per ADR-286 D3 scope).
**Date**: 2026-05-17 (status flipped 2026-05-18 post-test-validation)
**Companion docs**: `api/test_adr287_bundle_conformance.py` (new — ADR-keyed conformance walks across all bundles), the existing `api/test_adr230_bundle_substrate.py` (bit-rot fixed in same commit)
**Amends**: ADR-230 D8 (extends the bundle-substrate test gate to multi-ADR conformance walks)
**Preserves**: ADR-222 kernel/program boundary; ADR-223 bundle structure; ADR-224 kernel/program registry split; ADR-281 six-role taxonomy; every prior ADR's bundle-side requirements (this ADR catches drift, doesn't change any prior commitment)

## Context

The 2026-05-17 alpha-author bundle audit (post-ADR-283 step 6) surfaced a recurring process failure:

**Kernel ADRs that introduce new bundle-side requirements get hand-patched into alpha-trader (the canonical reference program) but get forgotten for every other bundle.**

Concrete instances observed:

| ADR | Required bundle surface | alpha-trader status | alpha-author status |
|---|---|---|---|
| ADR-284 (standing intent + OCCUPANT) | `review/IDENTITY.md` references `standing_intent.md` | ✓ amended | ✗ missing |
| ADR-284 | `review/principles.md` references `standing_intent.md` | ✓ amended | ✗ missing |
| ADR-284 | `_recurrences.yaml` judgment-mode prompts pair stand-down with standing-intent write | ✓ amended | ✗ missing |
| ADR-284 D3 | persona-row `expected.occupant_attribution` block | ✓ added (personas.yaml L124) | ✗ missing on yarnnn-author + netflix-script-author |
| ADR-284 D3 | persona-row `core_files` includes `review/OCCUPANT.md` | ✓ added (personas.yaml L118) | ✗ missing |
| ADR-285 D2 | bundle MANIFEST `reviewer_wake_envelope` entries have `role:` tag | (backward-compat default) | (backward-compat default) |
| ADR-286 D3 | bundle ships 13 program-owned substrate files | ✓ verified | ✗ partial (need check) |

The pattern: ADR author updates alpha-trader at ADR time, doesn't think to update every other bundle. Each future ADR re-opens the gap. The existing `api/test_adr230_bundle_substrate.py` was the natural conformance surface but **has itself bit-rotted** — `test_bundle_carries_canonical_substrate` asserts tier-frontmatter that ADR-261/262 D2 dissolved; `test_alpha_trader_tasks_yaml_carries_default_tasks` asserts a file (`tasks.yaml`) that ADR-231 deleted; `test_alpha_trader_no_overrides_directory` is false post-ADR-284 (kvk's commits added overrides).

A stale conformance gate is worse than no gate — it normalizes red CI and trains authors to ignore failures. The ADR-283 step 6 dogfood-readiness assessment surfaced this; the operator's framing ("future-proof approach, not a short-term patch") names the structural fix this ADR commits to.

## Decision

### D1 — Bundle conformance is a CI discipline, not an ADR-author memory test

Going forward: **every kernel ADR that introduces a bundle-side requirement (substrate file presence, persona-row invariant, MANIFEST field, recurrence prompt clause, etc.) must extend the conformance test in the same commit as the ADR ships.** Adding a requirement without extending the test is rejected at code review.

The conformance test is the *single source of truth* for "what every active and deferred bundle must provide." When the kernel changes its requirements, the test changes. The test's job is to fail loudly across every bundle in the registry — not just the bundle the ADR author was thinking about.

### D2 — One conformance test, walks every bundle

New file: `api/test_adr287_bundle_conformance.py`. Pure-fs assertion test (no DB, no network, no LLM). Each test function:

- Walks every bundle in `docs/programs/{slug}/` with `status: active | deferred` (per ADR-223 lifecycle states).
- Asserts conformance to one ADR's bundle-side requirement, keyed by docstring comment (`# ADR-284 D6: judgment-mode recurrences pair stand-down with standing-intent write`).
- Reports gaps as test failures with bundle slug + missing surface + ADR reference, so a failure points at exactly what to fix.

The conformance walk pattern (pseudocode):
```python
def test_adr284_d6_recurrences_pair_with_standing_intent():
    for bundle in _all_active_or_deferred_bundles():
        recurrences = _load_recurrences(bundle)
        for entry in recurrences:
            if entry["mode"] != "judgment":
                continue
            assert "standing_intent" in entry["prompt"], (
                f"bundle '{bundle.slug}' recurrence '{entry['slug']}' is "
                f"judgment-mode but the prompt does not reference "
                f"standing_intent.md (ADR-284 D6). Pair stand-down with "
                f"a standing-intent update."
            )
```

### D3 — Pre-existing test bit-rot gets fixed in the same commit

Three failures in `api/test_adr230_bundle_substrate.py` get corrected:

1. **`test_bundle_carries_canonical_substrate`** asserts tier frontmatter on every authored-substrate file. ADR-261/262 D2 dissolved the tier system operationally — the assertion is stale. Fix: drop the tier-frontmatter assertion. The file-presence assertion (the part that catches real regressions) stays.
2. **`test_alpha_trader_tasks_yaml_carries_default_tasks`** asserts existence of `tasks.yaml` with 6 specific task titles. ADR-231 Phase 3 cutover deleted `tasks.yaml`; recurrences live in `_recurrences.yaml`. Fix: rewrite to assert recurrence-set conformance against `_recurrences.yaml` instead.
3. **`test_alpha_trader_no_overrides_directory`** asserts no overrides directory for alpha-trader. ADR-284 Phase 3 (commit `d4c1cfe`) and related work added overrides. Fix: delete the test (the assertion was already weak — "should run bundle as-is" is operator preference, not architectural invariant).

These are not new tests; they're corrections of stale ones. They land in the ADR-287 commit because they're symptomatic of the same drift this ADR addresses structurally.

### D4 — Conformance test schema, keyed by ADR

The new test file organizes assertions by ADR. Each ADR section opens with a header comment naming the requirement + the ADR + the decision number:

```python
# =============================================================================
# ADR-284 — Standing Intent + OCCUPANT runtime-alignment
# =============================================================================

def test_adr284_d6_bundle_identity_references_standing_intent():
    """ADR-284 D8: every active/deferred bundle's review/IDENTITY.md must
    reference standing_intent.md. Without it the Reviewer persona prompt
    references a substrate file the bundle never tells operators about."""
    ...

def test_adr284_d6_bundle_principles_references_standing_intent():
    """ADR-284 D8: every active/deferred bundle's review/principles.md
    must reference standing_intent.md under the 'default posture' framing."""
    ...

def test_adr284_d6_judgment_recurrences_pair_with_standing_intent():
    """ADR-284 D6: every judgment-mode recurrence in every active/deferred
    bundle's _recurrences.yaml must pair stand-down with a standing-intent
    update directive in its prompt."""
    ...

def test_adr284_d3_persona_rows_have_occupant_attribution():
    """ADR-284 D3: every persona row whose bundle is active/deferred must
    declare expected.occupant_attribution + include review/OCCUPANT.md in
    expected.core_files."""
    ...
```

Future ADRs add new sections (`# ADR-XXX — ...`) with new test functions following the same pattern. When the test file fails on a new bundle, the failure message points at the ADR that introduced the requirement, so the bundle author knows what to add.

### D5 — Backfill alpha-author in the same commit

ADR-283 step 1-6 shipped the alpha-author bundle pre-ADR-284. The conformance test would fail on day one without backfill. The same commit that lands ADR-287 + the new test backfills alpha-author to satisfy:

- `review/IDENTITY.md` gains a `## Standing intent — my forward-looking substrate (ADR-284, 2026-05-17)` section parallel to alpha-trader's
- `review/principles.md` gains a standing-intent paragraph under "Default posture: act"
- `_recurrences.yaml` 4 judgment-mode prompts (`pre-ship-audit`, `corpus-coherence-check`, `revision-audit`, `outcome-reconciliation`) gain "AND update /workspace/review/standing_intent.md" clauses
- `docs/alpha/personas.yaml` two alpha-author rows gain `expected.occupant_attribution` block + `review/OCCUPANT.md` in `core_files`

The MANIFEST `reviewer_wake_envelope` role tags (ADR-285 D2) are backward-compatible defaults, so no backfill required — but the conformance test for ADR-285 D2 asserts the entries either declare a `role:` or fall through to the default. alpha-author can stay with the default; the test passes regardless.

### D6 — Out of scope (deferred)

- **Automated conformance fix-up** (a script that reads the test failures and patches the bundle). The discipline is operator-attention to ADR authoring — the test exists to *fail loudly*, not to silently fix things. A silent fixer would re-create the drift it's trying to eliminate.
- **Cross-ADR conformance dependencies** (e.g., "ADR-284 D6 requires ADR-281 §3 single-writer rule"). The test assertions are independent; if both ADRs apply, both tests run separately. No DAG required.
- **Per-bundle conformance overrides** (a way for a bundle to say "ADR-X D2 doesn't apply to me"). If a bundle truly doesn't need a kernel requirement, the kernel requirement isn't actually universal and the ADR should be amended. No override mechanism.
- **Historic-ADR backfill beyond ADR-283/284/285/286**. Older ADRs whose bundle requirements are already satisfied by alpha-trader and alpha-author silently pass; no need to add conformance walks for ADRs whose surface is already aligned. Conformance walks ship for ADRs going forward.

## Cascade plan (single atomic commit)

This ADR ships in one commit alongside the backfill + test fixes:

1. `docs/adr/ADR-287-bundle-conformance-discipline.md` (this file)
2. `api/test_adr230_bundle_substrate.py` bit-rot fixes (3 tests corrected)
3. `api/test_adr287_bundle_conformance.py` new (ADR-keyed conformance walks for ADR-284 + ADR-285 + ADR-286)
4. `docs/programs/alpha-author/reference-workspace/review/IDENTITY.md` standing-intent section
5. `docs/programs/alpha-author/reference-workspace/review/principles.md` standing-intent paragraph
6. `docs/programs/alpha-author/reference-workspace/_recurrences.yaml` 4 judgment-mode prompt amendments
7. `docs/alpha/personas.yaml` 2 alpha-author rows gain `occupant_attribution` + `OCCUPANT.md` core_file

Grep gate before commit:
```
api/venv/bin/python -m pytest api/test_adr230_bundle_substrate.py api/test_adr287_bundle_conformance.py -v
```

All assertions must pass for both alpha-trader and alpha-author bundles.

## Why this is structurally right

The pattern this ADR codifies is the same Singular Implementation discipline FOUNDATIONS Principle 7 establishes at the code layer, applied at the bundle layer:

- **Pre-ADR-287**: each ADR author hand-patches alpha-trader; every other bundle silently drifts. The drift surfaces only when an operator audits a specific bundle (as ADR-283 step 6 surfaced for alpha-author). The cost compounds with bundle count.
- **Post-ADR-287**: each ADR author writes a conformance assertion that runs against every bundle. Adding a new bundle (e.g., a future alpha-creator or alpha-recruiter) inherits the entire ADR-historical surface automatically — if the new bundle ships without the required substrate, CI fails on day one.

The conformance test becomes the documented contract between the kernel and any bundle that wants to be `status: active | deferred` in the registry. New bundle authors read the test, see what's required, ship it.

The cost of authoring ADR-287 + the test + the backfill is roughly the same as one round of "catch up alpha-author" hand-patching. The future cost saved is one hand-patch per new bundle per new ADR — which compounds quadratically with bundle count.

## Test gate

`api/test_adr287_bundle_conformance.py` per D4 above. Functions named by ADR + decision number. Walks every active/deferred bundle. Walks every persona row whose program is active/deferred.

Sibling regression: `api/test_adr230_bundle_substrate.py` post bit-rot fix — must pass for the ADR-287 commit to land.
