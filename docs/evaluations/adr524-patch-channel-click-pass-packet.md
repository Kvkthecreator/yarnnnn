# ADR-524 click-pass packet — the patch channel and the previewed re-arrange

**Status**: OWED (human-only). Written 2026-08-06 alongside the implementation.
**Why human-only**: the canvas iframe is `allow-scripts` on an **opaque origin** — CDP
cannot read into it, so the browser lane cannot observe the canvas DOM. Same constraint as
the ADR-521 and ADR-523 packets.

**Build receipt in hand**: `next build` exit 0, 169/169 pages, from a worktree carrying only
these changes. Everything below is what the build cannot prove. Note this ADR's claims are
about **what does NOT happen** (no re-parse, no blink), which is why a build is especially
weak evidence here.

---

## Claims under test

| # | Claim | Decision |
|---|---|---|
| C1 | A block text commit does **not** re-parse the document | D1/D2 |
| C2 | The patch payload is projected — citations still render, no raw source | D3 |
| C3 | A live caret is never disturbed by a patch | D1 |
| C4 | Selection survives a patched edit | D1 |
| C5 | A structural op still works (full swap, unchanged) | D2 |
| C6 | A re-arrange moves the page **immediately**, before the model answers | D4 |
| C7 | The preview settles to the plan, and writes **one** revision, not two | D4 |
| C8 | A refused/unreachable plan leaves the mechanical result in place | D4 |

## The instrumented observation (C1 — the load-bearing one)

A re-parse is invisible to the eye if it is fast; do not judge C1 by feel. Make the frame
prove it:

1. Open a deck in `/studio`, select a text block, edit it, click out to commit.
2. In DevTools, watch the **iframe element** in the Elements panel. A full `srcDoc` swap
   removes and re-inserts the entire document subtree; a patch mutates a single node.
3. Equivalent: put a `console.count()`-style breadcrumb in the runtime's boot path (the
   injected script runs once per parse) and confirm it does **not** increment on a text
   commit. Before this ADR it incremented on every edit.

Substrate receipt: `ListRevisions` on the artifact — the edit must still land exactly one
attributed revision. **A patch that skips the write is a bug, not a feature.**

## Steps

**C2 — projection survives the patch.** Edit a block that sits next to a **cited** block
(`data-ref`). After the commit, the citation must still render resolved, not as raw source
or an empty island. Then edit the cited block itself and confirm the same.

**C3 — the caret.** Type into a block and keep typing past the idle-2s commit **without
clicking out**. The caret must not jump, drop, or land at the block start. (The runtime
declines any patch aimed at the block being edited; this tests that guard.)

**C4 — selection.** Select a block (bounding box visible), edit it, commit. The box must
still be on the same block afterwards.

**C5 — structural unchanged.** Insert a block, delete one, move one. These still full-swap;
they must behave exactly as before. **A regression here is the risk this ADR carries** — the
patch path must never have captured an op that is not block-local.

**C6 — the preview.** Select a slide with content, Re-arrange → pick a slotted arrangement.
The page must visibly re-lay **immediately**, and the toolbar button must read **"Refining…"**
while the judgment runs. Watch for the 2-4s: the layout should already have changed before
it elapses.

**C7 — one revision, not two.** After C6 settles, `ListRevisions`: there must be exactly
**one** new revision for the gesture. Two would mean the preview reached the write door,
which D4 forbids (ADR-209 — no revision nobody authored). Also confirm the settled layout is
the model's plan, not the mechanical one, when the two differ.

**C8 — degraded path.** Force the planner to fail (offline, or a workspace with an exhausted
balance). The page must keep the mechanical arrangement and land one revision; no error
banner, no reverted page.

## Recording

VERIFICATION.md's web-lane exit needs **both** a DOM observation and a substrate receipt
where the click writes. C1/C7 carry both. Record the run under `docs/evaluations/` and only
then `.claude/hooks/mark-validated.sh web`.
