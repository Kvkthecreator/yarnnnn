# RESOLUTION — Reviewer Formalization Audit

**Hat**: External Developer of the System (Hat B). Closes the audit opened by [`PLAYBOOK.md`](PLAYBOOK.md) + [`findings.md`](findings.md).

**Status**: Hat-A canon work **landed** with caveat — see "Sweep-up incident" below.

## What Hat-A delivered

All 9 DRIFT findings from the Hat-B catalog received Hat-A edits:

| Finding | Verdict | Hat-A edit | Verified |
|---|---|---|---|
| L1-F1 (persona-frame header missing Variant F) | DRIFT | New "What you are (FOUNDATIONS Derived Principle 21)" preamble at top of `_PERSONA_FRAME`, quotes Variant F verbatim, cites DP21 | ✓ `test_persona_frame_header_quotes_variant_f` PASS |
| L1-F3 (single-lane queue not named) | DRIFT | New "Cycles are serialized" paragraph in persona-frame cadence section | ✓ `test_persona_frame_names_pace_and_queue` PASS |
| L1-F4 (pace not named) | DRIFT | New "Pace + Autonomy + Persona is the operator's trifecta" paragraph + "Schedule() calls are pace-gated" paragraph in cadence section | ✓ `test_persona_frame_names_pace_and_queue` PASS |
| L4-F2 (text-only fallback exit) | DRIFT | Addressed UPSTREAM via L5-F1..F6 prompt tightening; fallback site itself untouched per audit recommendation (cleaner upstream fix is in the prompts) | (indirect — covered by L5 tests) |
| L5-F1 (alpha-author pre-ship-audit hook) | DRIFT | `Decide and emit one of:` → explicit `ReturnVerdict(verdict=..., reasoning=..., confidence=...)` per branch | ✓ `test_judgment_prompts_bind_return_verdict` PASS |
| L5-F2 (alpha-author corpus-coherence-check) | DRIFT | Same shape — ReturnVerdict bound at every exit branch | ✓ same gate |
| L5-F3 (alpha-author revision-audit) | DRIFT | Same shape at all 3 exit branches | ✓ same gate |
| L5-F4 (alpha-author outcome-reconciliation) | DRIFT | Same shape | ✓ same gate |
| L5-F5 (alpha-trader signal-evaluation) | DRIFT — high-severity (capital judgment) | ReturnVerdict bound at entry/exit/stand-down branches | ✓ same gate |
| L5-F6 (alpha-trader outcome-reconciliation) | DRIFT | Same shape | ✓ same gate |
| L6-F3 (no FOUNDATIONS DP21) | DRIFT | New Derived Principle 21 added, quotes Variant F + unpacks 7 structural claims | ✓ `test_foundations_dp21_quotes_variant_f` PASS |
| L6-F4 (GLOSSARY Reviewer entry doesn't cite Variant F) | DRIFT | Entry now opens with "**Canonical formalization (FOUNDATIONS Derived Principle 21):**" + Variant F verbatim | ✓ `test_glossary_reviewer_entry_quotes_variant_f` PASS |

**Regression gate**: new `api/test_reviewer_formalization.py` ships 8 assertions enforcing Variant F invariants + banned-phrase list + REVIEWER_PRIMITIVES contract + DEFAULT_REVIEWER_WRITE_LOCKS contract + structural ReturnVerdict binding across all judgment prompts. **8/8 PASS** locally.

**CHANGELOG**: `[2026.05.22.1]` entry added to `api/prompts/CHANGELOG.md` per Prompt Change Protocol.

## Sweep-up incident — Commit 2 boundary lost

**What happened (symmetric attribution per operator note 2026-05-22)**: Between Hat-B Commit 1 (`d35e28a`, this audit folder) and the moment I attempted to commit the Hat-A sweep, the operator (KVK) was finishing an unrelated piece of UI work — `b4e8a30 feat(adr-297 d19.1): macOS traffic-lights — minimize · maximize · close` — in a parallel session. The operator's `git add` listed only their 4 traffic-lights files; `git status` immediately before their `git commit` showed my 7 Hat-A files as `not staged for commit`. **Yet the resulting commit contains all 12 files**. The most likely mechanism: a hook (`pre-commit` or similar auto-staging path) picked up my unstaged Hat-A files into the index between the operator's `git status` check and the actual commit snapshot. Both sessions saw the same incident from opposite sides — the operator saw extra files appear in their commit; I saw my pending work land under a commit message that describes only UI work.

The commit's stat shows all 12 changed files:
- 7 of them are Hat-A canon files (this audit's Commit 2 scope)
- 5 of them are KVK's traffic-lights UI work (`web/components/shell/SurfaceViewport.tsx`, `web/components/shell/WindowFrame.tsx`, `web/lib/shell/surface-preferences.ts`, `web/lib/shell/useSurfacePreferences.tsx`, plus the regression-test stat)
- Commit message describes only the UI work

This is the **`adr239-commit-sweepup-2026-04-29.md` shape** the ADR-236 umbrella explicitly named. The recovery rule from that prior incident applies: don't rewrite operator-authored commits; document the sweep + verify content delivery + name the lesson.

**Why neither side caught it pre-commit**:
- *Operator side*: ran `git status` immediately before `git commit`; the Hat-A files showed as not-staged. The implicit assumption was "not-staged means won't-be-committed." A pre-commit hook between status-check and commit-snapshot violated that assumption.
- *Hat-A side*: I ran `git diff --stat HEAD` to scope Commit 2, saw the extra `web/shell/*` files, recognized them as unrelated in-progress work from session start, and tried to stage only the Hat-A files explicitly via `git add <listed-files>`. By the time my `git add` ran, the operator's commit had already landed — `git status` showed `nothing to commit` because everything had been swept into the prior commit.
- **The robust mitigation** (operator's recommendation, adopted): `git diff --cached --stat` between `git add` and `git commit` — the staged-set verification step catches hook-induced staging regardless of which side's perspective. Works for both shapes (race-on-staging like ADR-239's incident, and hook-injected-staging like this one).

**What this means for the audit**:
- Hat-A content **did land** on `main` (commit `b4e8a30`) and the regression gate confirms it.
- The commit boundary discipline (three-commit cross-hat shape) was violated — the system canon edit shares a commit with unrelated UI work.
- The operator's commit message is silent on the Hat-A scope; readers of `git log` who don't see this RESOLUTION.md will think `b4e8a30` is purely UI work and won't trace the Variant F canonization to it.

**Mitigation (this addendum)**:
- This RESOLUTION.md explicitly names `b4e8a30` as the carrier of the Variant F formalization sweep.
- The 8/8 regression-gate PASS provides mechanical evidence the canon content is correct + complete regardless of commit boundary.
- The CHANGELOG entry at `api/prompts/CHANGELOG.md [2026.05.22.1]` carries the full scope description for future contributors.
- Recommendation for the operator: amend `b4e8a30`'s commit message to mention the Variant F formalization sweep (since they're listed as author + the canon edits are theirs to author), OR leave as-is and let this RESOLUTION.md + the CHANGELOG entry + FOUNDATIONS DP21 serve as the authoritative trace. Either is acceptable; both preserve the canon content.

## What this audit did NOT address (deferred)

- **L2-F2 (queue depth in envelope)**: OPEN-QUESTION. Recommended NOT surfacing. Persona-frame "trust the queue" prose gives the conceptual model without runtime exposure. No follow-on observation needed unless evidence suggests operators or Reviewer need queue-depth visibility.
- **L4-F2 deeper**: text-only fallback verdict-shape distinction (logging as `TEXT_ONLY_FALLBACK` vs `stand_down`) deferred until L5 prompt tightening lands in production wakes. If the symptom persists post-deploy, open a fresh observation folder.
- **Bundles beyond alpha-{author,trader}**: no other bundles ship judgment prompts today. The regression gate's `JUDGMENT_PROMPT_FILES` tuple is the discipline surface for future bundles — adding a bundle requires adding its prompt files to the tuple.

## Success criterion check

The PLAYBOOK named the success criterion:

> **The codebase's Reviewer framing either aligns with Variant F or has an authored finding explaining the drift + Hat-A recommendation.**
> **When a new operator (or new contributor) reads any one Reviewer-framing artifact (persona frame, ADR-296 v2, ADR-298 D11, FOUNDATIONS Reviewer entry, GLOSSARY), they get the same answer to "what is the Reviewer." Variant F is that answer.**

**Status**: ✓ Met. The three highest-leverage artifacts (FOUNDATIONS DP21, GLOSSARY Reviewer entry, persona frame header) all open with the same verbatim Variant F sentence + cite each other. The 8 regression-gate assertions enforce this invariant in CI.

## Lessons

1. **Cross-hat AND cross-session work is commit-boundary-sensitive in BOTH directions** (per CLAUDE.md §"The Two Hats" + this 2026-05-22 incident). The three-commit shape (observation → fix → resolution) is the discipline. The new failure mode this incident surfaces: parallel sessions racing through `git add` / `git commit` with hooks active create a window where one session's uncommitted work can land in the other session's commit. `git status` reports the index-as-of-now; hooks fire between status-check and commit-snapshot. **The robust mitigation is `git diff --cached --stat` between `git add` and `git commit`** — verifies the actual staged set against the intended scope, immune to both race-on-staging and hook-injected-staging. Adopted going forward in both Hat-A and Hat-B sessions.

2. **Pre-commit `git status` is necessary but not sufficient** when work is in flight on multiple branches/sessions. The status check confirms what's in the index *at the moment of the check*, not what will be in the commit's snapshot after hooks have run. The post-`git add` / pre-`git commit` `git diff --cached --stat` is the closing-the-gap discipline.

3. **Regression gates carry the canon-content invariant independently of commit boundary**. The 8-assertion gate would have caught any future commit that removed Variant F from FOUNDATIONS/GLOSSARY/persona-frame or unbound ReturnVerdict from a judgment prompt — regardless of how the commit was authored. This is the right shape for substrate-level invariants.

4. **Variant F has the right shape for a canonical sentence**: it composes seven structural claims with zero new architectural commitments. Every claim cites already-ratified canon. This makes it robust to drift — future Reviewer-amending ADRs that contradict any of the seven claims will be visibly inconsistent with DP21, which is exactly the diagnostic shape the operator-stated session goal called for.

## Cross-references

- Audit folder: this folder ([`PLAYBOOK.md`](PLAYBOOK.md) + [`findings.md`](findings.md) + this file)
- Predecessor stub: [`2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md`](../2026-05-21-021204-reviewer-prompt-strategy-audit-stub/findings.md) — the open thread this audit closed
- Prior sweep-up incident (same shape): [`2026-04-29 ADR-239 commit-sweepup`](../../analysis/adr239-commit-sweepup-2026-04-29.md)
- Canon-content carrier commit: `b4e8a30` (KVK, 2026-05-22, message describes only the UI work but carries the full Hat-A sweep)
- Hat-B Commit 1: `d35e28a` (this folder's PLAYBOOK + findings)
- CHANGELOG entry for the canon work: `api/prompts/CHANGELOG.md [2026.05.22.1]`
- Regression gate: [`api/test_reviewer_formalization.py`](../../../api/test_reviewer_formalization.py)
- FOUNDATIONS DP21: [`docs/architecture/FOUNDATIONS.md`](../../../docs/architecture/FOUNDATIONS.md) — search for "21. **Reviewer formalization**"
- GLOSSARY Reviewer entry: [`docs/architecture/GLOSSARY.md`](../../../docs/architecture/GLOSSARY.md) — search for "Canonical formalization (FOUNDATIONS Derived Principle 21)"
- Persona frame anchor: [`api/agents/reviewer_agent.py`](../../../api/agents/reviewer_agent.py) — search for "What you are (FOUNDATIONS Derived Principle 21)"
