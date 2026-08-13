# Archived ADRs

Dead history, preserved. Nothing here is live canon — if an archived ADR still
describes how the system behaves, it is in the wrong folder.

## What belongs here

An ADR is archived only when **both** hold:

1. The **entire** ADR is dead — superseded, withdrawn, or absorbed. A live ADR
   with one amended clause stays in `../`, stamped `Live · <clause> → ADR-N`.
2. **Nothing references it as a live clause.** Historical citations are fine;
   a doc that depends on it to explain current behavior is not.

When in doubt, **stamp in place and leave it in `../`**. Archiving is the
irreversible-feeling move, and a wrongly-archived ADR is harder to find than a
correctly-stamped stale one.

## The rule that keeps breaking

**Moving an ADR breaks every relative link that points at it.** Sibling ADRs
link each other bare (`](ADR-311-foo.md)`), and those resolve against `docs/adr/`,
not `docs/adr/archive/`.

Before 2026-08-13 this step was skipped, and the result was **148 broken links**
across `docs/` — including 10 in the ADR index itself, pointing at files that had
been archived and never re-pathed.

So: **in the same commit that moves an ADR, rewrite every inbound link.**

```bash
# find every reference before moving
grep -rn "ADR-NNN-slug\.md" --include='*.md' --include='*.py' docs/ api/ web/ CLAUDE.md

# after moving, verify nothing dangles
grep -rn "](.*ADR-NNN-slug\.md" --include='*.md' docs/ CLAUDE.md | grep -v 'archive/'
```

From inside `docs/adr/`, the correct form is `](archive/ADR-NNN-slug.md)`.
From `docs/architecture/`, it is `](../adr/archive/ADR-NNN-slug.md)`.

## Contents

Pre-209 history (ADR-001 → ADR-058 and the early bands), plus later ADRs that
were fully superseded. The 2026-08-13 sweep added 16 whole-dead ADRs whose
supersession verdicts were already recorded in [`../README.md`](../README.md) or
on their own Status line: 111, 166, 218, 228, 240, 247, 251, 252, 273, 280, 300,
311, 313, 334, 359, 419.

Two of those (218, 252) already had a **stale pre-supersession copy** here. The
newer root version — the one carrying the supersession banner — won; the stale
snapshot was replaced.

For the live decision log, see [`../README.md`](../README.md).
