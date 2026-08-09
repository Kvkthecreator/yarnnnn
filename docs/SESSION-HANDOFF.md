# Session handoff — 2026-08-08

`origin/main` @ `db1a70f`. Working tree clean, local in sync with remote.
All studio + share gates PASS at HEAD; `next build` clean.

## Shipped this session

**ADR-536 — the list is a kind, and align comes home** (`2e06a2f`).
Operator-surfaced from a Docs screenshot. Two defects, one shape: both a control
the canon *promised* with no door onto it.

- **D1** — `STUDIO_BLOCKS` had no ordinary list (`checklist` is a *checkbox*
  list). `PROMOTE_KIND` therefore mapped `UL`/`OL` → `prose`, which is why a
  pasted numbered list reported as **prose** in the properties pane. Added
  `list` + `numbered` rows (unscoped), kernel CSS, kernel version 14 → 15.
- **D2** — align/indent were lost in ADR-528 D2's re-cut, not withdrawn.
  ADR-527 D3 assigned them to a Text section; the only mount for a block-grain
  token lived in `object` scope, so flow's `range` scope could never reach them.
  Now mounted in `TextSection`, derived from the served `block-flow` grain.

`test_adr536_lists_and_align.py` **31/31**, 5 falsifiers each executed.

## ⚠️ OWED — do these before calling ADR-536 closed

1. **The click-pass.** Not driven in a browser. Green gates prove the room, not
   the doorway.
   - Insert a bulleted list · `Tab`/`⇧Tab` to nest · Turn into numbered ·
     align a paragraph.
   - **Use a SINGLE caret in one paragraph.** Align/indent *withdraw* over a
     multi-block range by design (single-subject op — the `d878242` rule), so a
     drag-selection will show nothing and that is correct, not a bug.
   - **Tell that the post-536 bundle has landed:** the multi-block notice now
     reads *"the heading ramp, Turn into, **and align/indent**"*. If it omits
     align/indent, you are on an old bundle — check `git status -sb` first.
   - Mark with `.claude/hooks/mark-validated.sh` per `docs/evaluations/VERIFICATION.md`.

2. **The ADR-537 share-sheet click-pass** (`db1a70f`, concurrent lane).
   `ShareDialog.tsx` was substantially rewritten (~638 lines) into two
   scope-divided tabs — Link (this file) / People (the workspace). Gates pass
   (`test_adr537_share_sheet_tabs.py`) and the build is clean, but a dialog
   rewrite of that size is precisely the case where green gates prove the room
   and not the doorway. Drive both tabs, the reuse-first link, Revoke, and the
   join-link disclosure.

3. **Unexplained: OAuth state error on prod.** Seen in the operator's URL:
   `yarnnn.com/settings?provider=notion&status=error&error=Invalid+or+expired+OAuth+state&docs.file=operation%2Fhello%2Fdocument-copy.html`
   A failed Notion handshake riding a `/settings` URL that *also* carries a
   `docs.file` address — an OAuth callback and a docs-file address collided in
   one URL. **Not investigated.** ADR-531 territory, unrelated to ADR-536.

## Note for whoever picks this up

ADR-536 was reported "done" on green gates + a clean build while sitting
**unpushed** — prod ran the old bundle and the operator saw no change. When a
shipped change is invisible on production, check `git status -sb` for `[ahead N]`
**before** re-reading code or theorising about caching. Diagnose in the order:
unpushed → not-yet-built → actually broken.

A concurrent lane (ADR-534 share work, deck kernel backfill) was active in this
repo throughout. Commit with explicit paths; never `git add -A`.
