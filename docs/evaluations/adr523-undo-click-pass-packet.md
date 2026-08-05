# ADR-523 click-pass packet — undo as a lineage

**Status**: OWED (human-only). Written 2026-08-06 alongside the implementation.
**Why human-only**: the Studio/Docs canvas is an iframe sandboxed to `allow-scripts`
with an **opaque origin** — CDP cannot reach into it, so the browser lane cannot
observe the canvas DOM. Same constraint as the ADR-521 packet.

**Build receipt already in hand**: `next build` exit 0, 169/169 pages, isolated
worktree. Everything below is what the build *cannot* prove.

---

## What shipped (the claims under test)

| # | Claim | Decision |
|---|---|---|
| C1 | Holding ⌘Z rewinds many steps without the redo branch dying | fix `b65c910` |
| C2 | An own **retitle** does not discard undo history | D4 |
| C3 | A **non-structural** undo does not blink/reload the canvas | D1 |
| C4 | ⌘Z after typing rewinds a **phrase**, not the whole paragraph | D3 |
| C5 | Undo returns the member to **where** the edit happened | D1 |
| C6 | A **live flow caret** keeps native keystroke undo (not ours) | ADR-482 D2 |
| C7 | A **foreign** write still clears history (accepted ceiling) | D4 |

## Setup

One authenticated principal. Open **both** `/studio` (a deck) and `/docs` (a
document) — they are one implementation (ADR-518), so each claim should be
checked on at least one and C4/C6 on Docs specifically.

## Steps

**C1 — rapid multi-undo.** In Studio, make 5 discrete structural edits (insert
block ×2, move, delete, insert). Hold ⌘Z until it stops. *Expect*: the document
walks back through all five. Then ⌘⇧Z repeatedly. *Expect*: it walks forward
through all five — **the redo must not die after the first step** (that was the
defect). Substrate receipt: the revision trail shows an `undo`/`redo` revision
per step.

**C2 — retitle preserves history.** Make 2 edits → rename the artifact → ⌘Z.
*Expect*: the last edit reverts. *Before the fix this was a silent no-op.*

**C3 — no blink on non-structural undo.** In Docs, type into a paragraph, click
out (blur commits), then ⌘Z. *Expect*: the text reverts **without** the canvas
flashing blank, without scroll jumping to the top. Contrast: delete a block
(structural) and ⌘Z — a reload here is expected and correct.

**C4 — phrase-grain rewind.** In Docs, type a sentence, **pause ~1s**, type a
second sentence, click out. Press ⌘Z once. *Expect*: only the second sentence's
run is removed, not the entire paragraph. (Typing with no pause coalesces into
one entry — that is intended.)

**C5 — selection restore.** Select a block, edit it, select a *different* block,
then ⌘Z. *Expect*: the restored state re-points at the block that was edited.

**C6 — the caret guard (a MUST-NOT).** In Docs, click into a paragraph so the
caret is live, type several characters, and press ⌘Z **without clicking out**.
*Expect*: the browser's native keystroke-level undo removes the last characters —
our surface stack must **not** fire and must not rewind a whole op. This is the
ADR-482 D2 trap; a failure here is a regression, not a nicety.

**C7 — foreign write clears history (expected loss).** Have a lane/agent write to
the open artifact. *Expect*: the canvas reloads authoritatively and ⌘Z no longer
walks past that point. This is the accepted ceiling (ADR-523 §2), not a defect.

## Recording

Per VERIFICATION.md the web lane's exit needs **both** a DOM observation and a
substrate receipt where the click writes. Undo writes a revision, so C1/C2/C3
each have a receipt available (`ListRevisions` on the artifact path). Record the
run under `docs/evaluations/` and only then mark the lane via
`.claude/hooks/mark-validated.sh web`.
