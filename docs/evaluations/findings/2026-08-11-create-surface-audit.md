# Create-surface audit — Files has no New, and the deliberate door was broken (2026-08-11)

Hat B (evaluation). Audited at `7a18bd7`, clean tree. Every claim carries a
file:line receipt; the two design gaps at the end are **recommendations, not
changes** — a finding recommends, it does not decide.

**Operator's two questions:**
1. Files has no "create new" — should it?
2. Docs/Studio default-designate a path at creation; it should either allow
   blank creation or make the path explicit.

**The short answer: Q1 is a real gap, and Q2's premise was half-right in a way
that mattered.** Blank creation already exists and works (ADR-470's immediate
door). What was broken was the *explicit* door — in three separate ways at once,
none of which any gate could see, because each defect lived in the **gap between
two modules that were each correct read alone.**

---

## Part 1 — the five defects (FIXED; see the ADR-470 amendment)

| # | Defect | Receipt |
|---|---|---|
| F1 | The destination picker gated on **permission**, the server on **region** — 4 of 5 offered folders 403'd after Create | `NewArtifactModal.tsx:355-359` vs `routes/studio.py:1053` |
| F2 | The two doors disambiguated differently, while the helper's **docstring asserted they could not** | `routes/studio.py:991-993` vs `:1069` |
| F3 | One folder, two names in one dialog (`operation` vs `Documents`) | `NewArtifactModal.tsx:54` vs `workspace_paths.py:194` |
| F4 | The typed folder name was **silently rewritten**, no preview | `routes/documents.py:1054-1062` |
| F5 | The immediate door had no `catch` — every refusal swallowed | `StudioSurface.tsx:3981-3984` |

Blast radius ×3: Docs, Studio, and Images all mount one `StudioSurface`
(`StudioSurface.tsx:305-319`), so each defect shipped three times.

### Why the gates could not see any of them

This is the reusable part. Every one of the five was a **relational** defect:

- **F1** — two predicates, each defensible alone. Nothing compared them. A gate
  per module passes; the door is still broken. *The fix's gate executes both and
  asserts agreement over a folder set.*
- **F2** — the invariant was asserted **in a docstring written in the same commit
  as the code that violated it**, and read as evidence for five months. Third
  occurrence of `feedback_documented_limitation_is_not_a_gate`.
- **F4** — the FE and server agreed on nothing because the FE had no opinion; the
  rewrite was invisible rather than wrong.
- **F5** — an absence. Nothing asserts a `catch` that was never there.

A first draft of the new gate **passed while F1 was fully reverted**: it checked
`modalCode.includes('isArtifactRegion')` file-wide, which the surviving *import*
satisfied. Re-cut per predicate. A file-wide presence check cannot defend a
per-site invariant — `feedback_counting_gate_cannot_defend_per_site`, caught here
only because every claim was falsified before being trusted.

---

## Part 2 — what was deliberately NOT changed

**The two slug rules stay apart.** `path_slug` ASCII-folds (`한글 문서` →
`untitled`); `_sanitize_folder_segment` keeps Unicode (`한글-문서`). This looks
like drift and is not: ADR-469's own test is *does this name something a member
reads*. An artifact carries its readable name in its `<title>`, so its key may be
opaque. **A folder has no title carrier — its segment IS its name.** Folding it
would erase the only name it has, which is the §1 grade-3 erasure ADR-469 exists
to prevent. Unifying them would have been a plausible-looking regression;
recorded in ADR-469 §5 with a gate defending the difference.

**The region fence itself.** Relaxing `STUDIO_ARTIFACT_REGION` is an ADR, not a
bug fix — see Part 3.

---

## Part 3 — the design gaps (RECOMMENDATIONS — not decided, not built)

### G1 — Files has no create verb, and the app registry has no create axis

Files creates exactly two things: **New folder** (`CanvasContextMenu.tsx:54`) and
**Add files** (`:57`). There is **no `POST /documents/file`** — the full route
roster in `routes/documents.py` is upload · restore · permanent-delete ·
trash/empty · move · launch-handler · duplicate · folder. Creating a *file* is
not a Files verb at all.

The structural reason: ADR-514's LaunchServices cut answers *"what app opens this
file"* (`apps.tsx` rows are `ownsTypes` + `renderer`). Nothing declares *"what app
CREATES this type."* That is why Open, Open With, and per-file defaults all
shipped while New could not. **It is the missing half of the LaunchServices
model**, and ADR-514 §6's deferred-lane list never named it.

Two things make this cheap when it is decided:
- Files already reasons in Finder folder-window grammar — *"the background of an
  open REAL folder creates inside that folder"* (`files/page.tsx:1208`) — which
  is exactly the scoping a New Document row needs, already implemented.
- One surface change covers Docs/Studio/Images (one `StudioSurface`).

**Blocked by the fence**: a peer folder like `the-acme-deal/` is precisely where
Files would want New Document, and `create_artifact` 403s it today.

### G2 — the fence contradicts ADR-424 D2

`create_folder` honours peer folders (`documents.py:1067` — *"including a
TOP-LEVEL PEER … you don't ask permission to `mkdir ~/projects`"*).
`create_artifact` fences to `operation/`. **One filesystem, two placement laws,
and the artifact one is the pre-ADR-424 one.** This is the root cause under F1,
F3, and G1 — relaxing it fixes the class rather than the instances.

### G3 — no empty state offers a way to create

Not one of six empty states on Files has a create CTA. The cold-start view — the
first thing a new member ever sees — reads *"Nothing authored yet. As the system
writes to your workspace, recent changes show here"* (`RecentsView.tsx:169-181`).
It frames the member as a **passive observer of a system that writes on their
behalf**. For a product whose ESSENCE is an attributed commons where the member
is a principal, that is a positioning defect, not a missing button.

Related, smaller: on a **desktop pointer** both create verbs are right-click-only
(`files/page.tsx:1014` gates the buttons behind `coarse`).

---

## Receipts I could not obtain

- **No click-pass.** The five fixes are verified by executing the real predicates
  and by 27/0 gate with all six claims falsified and restored — but **not against
  the running system**. The F1 403 matrix in particular is proven by derivation.
  A browser pass on "Name it first…" (pick a non-`operation` folder; confirm it
  is now refused *in the picker* rather than after Create) is owed.
- **DB-backed pytests cannot run in this shell** (401 regardless of tree), so the
  `_redirect_to_free_key` disambiguation is proven by executing its logic against
  the real `disambiguate`/`path_slug`, not against Postgres.
