# Session handoff — 2026-08-12 (the arrival + organisation arc, ADR-549…553)

`origin/main` @ `70fd2e7`. Five ADRs shipped across two arcs in one session.

## 1. What landed

**Arc A — creation (ADR-549 + amendments).** Operator's receipt was
`operation/asdfadsf/document.html`: a keyboard-mash folder, permanent and
attributed. Two `+ New` rows named **one thing and a toll**.

| Commit | What |
|---|---|
| `2f516f1` | the create door offers what the server accepts; both doors disambiguate |
| `70b16f3` | the `u`-flag regex the build refused; two gates that could not go red |
| `7cbc8ec` | **ADR-549** — one door, name required, derived work lands beside its source |
| `e7746c5` | the shape-choice check was presence, not behaviour |
| `11c084c` | **D5.1** — on a paged layout the KICKER is the name-bearer |

**Arc B — arrival + organisation (ADR-550…553).** Operator asked whether Files
needs a "New" verb. The audit said **no** — Finder has none, Explorer's
`ShellNew` is a legacy wart — and that the real gap was getting things IN.

| Commit | ADR | What |
|---|---|---|
| `51a7394` | 550 | the projection follows its raw; hiding on the derive EDGE, not the lane |
| `27aea5d` | 551 | arrival gets a "here"; ONE placement law for every create/receive verb |
| `00600d3` | 552 | the grid + details list drag (closes ADR-400's named deferral) |
| `70fd2e7` | 553 | the file set — and four independent ways out |

## 2. The three findings worth carrying

1. **`upload_documents` authorized nothing.** No `operator_can_organize` at all
   — a hardcoded destination had nothing to authorize. The moment a caller can
   name one it needs a check, or ADR-549's F1 defect ships twice.
2. **Moving an upload silently detached its searchable text.** The `.extracted.md`
   projection stayed behind, still hidden, citing a dead path — in the workflow
   the system tells members to use. Two rules each correct alone (ADR-422 D2 +
   ADR-395's lane anchor) made a broken pair.
3. **An arrival is badged on the LEDGER, not by its path.** ADR-448 already said
   so verbatim in the code. That is what made `inbound/uploads/` a default
   rather than a law.

## 3. Corrections made mid-implementation (both against my own proposal)

- *"the listing already selects `content`"* — true of the uploads listing,
  **false** of the tree and recents. Switched to the path-pair form rather than
  pulling file bodies into a tree query for a cosmetic rule.
- The **de-emphasis item was dropped**: executed `fileLegibilityState` and
  `inbound/uploads/` already classifies `operator`. The audit claim was wrong,
  so nothing was changed.

## 4. OWED — the click-passes (nothing is verified against the running system)

Every one of the nine commits is gate-verified and build-verified; **none is
browser-verified.** Highest value first:

1. **Drop a PDF onto a folder ROW in the tree** — was silently swallowed; must
   now import there.
2. **Drag a file from the TREE onto a GRID tile** — the one-MIME-token
   invariant; a regression here breaks only the cross-pane case.
3. **⌘-click three files → Escape → Clear → plain click.** All four exits.
4. **A deck in a peer folder** (`the-acme-deal/`) — the relaxed fence.
5. Learn-from from a file in `ai-frontier/briefs/` defaults there.
6. New Folder `R&D` previews "Saved as rd".

## 5. Landmarks

- **`test_adr209` is red at HEAD** (2 banned-pattern hits: `_archive_to_history`,
  `list_history`). Pre-existing, confirmed by stash — another lane's.
- **One placement law now**: `operator_can_organize`, asked by `create_folder`,
  `create_artifact` and `upload_documents` alike. `STUDIO_ARTIFACT_REGION`
  survives as the DEFAULT home, not a gate. If you re-fence one of them, the
  other two are wrong.
- **The drag MIME is declared ONCE** (`TILE_DRAG_MIME`, in `FileTile.tsx`) and
  imported by the tree and list. Re-declaring it breaks cross-pane drags while
  every per-module test stays green.
- **A file set is state beside the selection**, never a scope (ADR-519 D4.1).
  Every `FileVerbs` signature is still single-target.
