# Archived testing docs

Completed one-time playbooks and validation notes for machinery that no longer
exists. Preserved for history; **none of it describes how to test YARNNN today.**

For live testing docs see [`../README.md`](../README.md) and
[`../TESTING-ENVIRONMENT.md`](../TESTING-ENVIRONMENT.md).

## Criterion

A testing doc belongs here when it is **finished work**, not stale prose:

- a playbook for a migration or rename that has **already shipped**, or
- validation notes for an ADR that is itself archived, or
- a manual test pass against a surface that no longer exists.

A doc that still describes a live surface stays in `../`, even if it is old.
Age is not the test — whether the thing it tests still exists is the test.

## Contents (archived 2026-08-13)

| Doc | Why |
|-----|-----|
| `POST_RENAME_PLAYBOOK.md` | E2E pass for the ADR-103 `deliverable → agent` rename, shipped March 2026; cites a migration already applied to production. |
| `tp-qualitative-tests.md` | Browser test pass for the 2026-03-05 structural overhaul; written in retired "TP" vocabulary. |
| `adr-117-feedback-substrate-tests.md` | Validation for ADR-117's feedback substrate, since re-cut by ADR-231. |
| `ADR-039-background-work.md` | Validation notes for ADR-039 — the ADR is in `adr/archive/`. |
| `ADR-040-semantic-matching.md` | Validation notes for ADR-040 — the ADR is in `adr/archive/`. |
| `phase1-3-validation-guide.md` | Phase 1–3 validation guide from the pre-ADR-231 task-pipeline era. |

## Moving something here

**Re-path every inbound link in the same commit.** Sibling docs link each other
bare (as `](` + a filename + `)`), and those resolve against `docs/testing/`, not this folder.
Skipping that step is what left 148 dead links across `docs/` before the
2026-08-13 sweep.

```bash
grep -rn "SOME-DOC\.md" --include='*.md' --include='*.py' docs/ api/ CLAUDE.md
```
