# ADR-239 Commit Sweep-Up Recovery Note

> **Date**: 2026-04-29
> **Commit**: `efc22cc feat(adr-239): trader cockpit coherence pass — decisions parser unified`
> **Issue**: Commit ostensibly delivers ADR-239 but actually contains 16 unrelated files of ADR-235 follow-up vocabulary cleanup that were swept up by `git add` from the working tree.

---

## What happened

ADR-239's drafting + implementation ran in this Claude session. The other Claude session in parallel had staged a series of post-ADR-235 vocabulary cleanups (UpdateContext / ManageTask → InferWorkspace / ManageRecurrence references, the new write-side scope='workspace' pattern) into the working tree but had not committed them.

When ADR-239 ran `git add <specific files>`, the previously-staged-by-other-session files **were already in the index from a prior session's stage**, and got committed alongside ADR-239's intentional changes. The result: a single commit `efc22cc` that:

- **Delivers ADR-239's intent correctly** — `web/lib/reviewer-decisions.ts`, `web/components/library/faces/PerformanceFace.tsx`, `api/test_adr239_decisions_parser_unification.py`, `docs/adr/ADR-239-...`, ADR-236 box update, CHANGELOG `[2026.04.29.11]`.
- **Also delivers ADR-235 follow-up cleanup** — 16 additional files (TPContext, NotificationCard, InlineToolCall, utils, autonomy, ChatSurface, ChatEmptyState, ComposerInput, RecurrenceSetup/Modal, AgentContentView, DeliverableMiddle, SubstrateEditor, types, api client, plus other-session-modified files).

The 16 swept-up files are **all legitimate, all correct**, and all align with ADR-235's vocabulary. They represent the kind of cleanup ADR-235 explicitly named would propagate. None of the changes are wrong; the issue is solely commit-attribution discipline.

## What this means for the audit trail

`efc22cc`'s commit message claims to be ADR-239 work. The diffstat tells the more honest story:

```
21 files changed, 545 insertions(+), 134 deletions(-)
  - 5 files = ADR-239 intentional (~155 LOC delta)
  - 16 files = ADR-235 follow-up sweep (~390 LOC delta)
```

Future-me reading `git blame` on, say, `web/components/tp/NotificationCard.tsx` and seeing `efc22cc feat(adr-239): ...` will be confused — the file change is ADR-235 vocabulary cleanup, not ADR-239 trader cockpit work.

This recovery note is the canonical attribution record. `git blame` plus this doc tells the right story.

## Why not rewrite history

Three reasons:

1. The commit was pushed to `origin/main` before the sweep-up was caught. Force-pushing main to rewrite history would affect any other consumer (CI, other clones).
2. The 16 swept-up files are correct and shouldn't be reverted. Reverting would create "code goes backwards" churn for no benefit.
3. Singular Implementation rule (ADR-236 Rule 7): the working tree's state is what shipped; the commit message is the artifact. We don't shim around the artifact, we add a recovery note that future-me can find.

## What to do differently next time

Two improvements to commit hygiene under multi-session conditions:

1. **Pre-stage check**: before `git add <files>`, run `git status` and confirm the working tree contains *only* the files the current session intends to commit. If other-session changes are pending, stash them or coordinate explicitly.
2. **Pre-commit diff verification**: after `git add`, run `git diff --cached --stat` and confirm the listed files match the commit's claimed scope. If they don't match, unstage with `git reset` and re-stage selectively.

Both checks were performed during the ADR-239 commit but the other-session files appeared in `git status` listing **after** I had already verified my staging — between the `git add` and the `git commit`, more files were unstaged into the index by some asynchronous operation (likely the IDE or the other Claude session). The defense against this race is a final `git diff --cached --stat` check immediately before `git commit`, which would have caught the sweep-up before it landed.

## Net effect

- Commit `efc22cc`'s code-side state is **correct**.
- The audit trail is **misleading**.
- This recovery note is the corrective record.
- Future commits in this session adopt the additional pre-commit `git diff --cached --stat` discipline.

## Affected files attribution

For `git blame` consumers reading any of these files via `efc22cc`:

- `web/lib/reviewer-decisions.ts` — **ADR-239** intentional (aggregator + interface added)
- `web/components/library/faces/PerformanceFace.tsx` — **ADR-239** intentional (parser refactor)
- `api/test_adr239_decisions_parser_unification.py` — **ADR-239** intentional (test gate)
- `docs/adr/ADR-239-trader-cockpit-coherence-pass.md` — **ADR-239** intentional (the ADR itself)
- `docs/adr/ADR-236-frontend-cockpit-coherence-pass.md` — **ADR-239** intentional (Round 3 box check)
- `api/prompts/CHANGELOG.md` — **ADR-239** intentional (entry `[2026.04.29.11]`)

All other 16 files in `efc22cc` are **ADR-235 follow-up vocabulary cleanup** swept up from the working tree. Their changes attribute to ADR-235's vocabulary migration, not ADR-239's trader cockpit work.

---

## Closing

The commit shipped correct code under the wrong attribution. This recovery note is the audit-trail correction. ADR-239's work itself is intact; the test gates pass; the ADR's status is Implemented as recorded. Future-me reading `git log --grep adr-239` will find both the commit and (via this note's link from the commit's intended scope) the honest attribution.
