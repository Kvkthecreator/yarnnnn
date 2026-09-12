# ADR-649 — The Files surface has a first day

**Status**: Accepted · 2026-09-12
**Amends** [ADR-329 Amendment 2](ADR-329-files-as-first-class-work-legibility-surface.md) (Recents is the centre pane's empty state), [ADR-388 D1](ADR-388-files-as-a-filesystem-native-surface.md) (the roots endpoint), [ADR-424 D2](ADR-424-the-pure-os-filesystem-model-for-all-participants.md) (the New Folder scope) and the Finder-parity cut of 2026-07-09 (the header buttons). Respects [ADR-555 D2/D3](ADR-555-arrival-has-a-here.md) (Documents is the default home, not a gate; an arrival lands where the drop says) and [ADR-395](ADR-395-model-consumable-projection-and-upload-intake-conformance.md) (the legacy upload root shows only when it holds files).

---

## 1. The ask

> "can you check the files surface, and if we have a empty state like
> consideration here? than, i'm considering if i need an explicit button for
> add file, folder to make it even more straightforward for a completely new
> user"

and the ruling on the findings:

> "aligned on exclude system from recents. ok on both doors (keep it minimal,
> and screen sizes) — that can end up being the single + style you mentioned.
> yes, i'd like ideally the documents and download … so that they essentially
> land on documents (much like you would on a mac OS if you started from
> scratch)"

## 2. What a new member actually saw

The empty state was designed (ADR-329 Amendment 2: the Recents view, with an
honest "Nothing authored yet") and it never rendered. A read-only census of the
six newest prod workspaces on 2026-09-12:

| workspace | minted | files | under `system/` | Documents | Downloads |
|---|---|---|---|---|---|
| 7b81f067 | 2026-09-12 | 17 | 17 | 0 | 0 |
| 6bb86699 | 2026-09-12 | 17 | 17 | 0 | 0 |
| a9acd1ef | 2026-09-12 | 17 | 17 | 0 | 0 |
| d38376f4 | 2026-08-18 | 17 | 17 | 0 | 0 |
| cb3e6ec9 | 2026-07-11 | 17 | 17 | 0 | 0 |

The 17 are the kernel skills mirror (ADR-630: 11 `SKILL.md` + a manifest) and
the kernel faces mirror (ADR-641 am.2: 3 `face.png` + a manifest), written into
every workspace by the scheduler within five minutes of minting. Three things
followed, each from a rule that was right on its own:

1. **Recents showed them.** `_is_authored_substrate_path` hid `_`-prefixed
   files and one signal-log prefix (spelt `context/signals`, a pre-ADR-320 name
   that matched nothing). `SKILL.md` and `face.png` passed. The first thing a
   new member saw in Files was a grid of 15 files they did not write, labelled
   "System". The Text app had already met this and patched it at its own
   consumer (`isTextEditable`), which is the second home for one rule.
2. **The sidebar's only node was "System files".** A root renders only once a
   file exists under it (ADR-388 D1, filesystem-literal); only `agents/` was
   always-shown. `operation/` and `inbound/` — the two homes every participant
   is TOLD exist (`PARTICIPANT_FILESYSTEM_MODEL`: "Documents", "Downloads") —
   were invisible to the member until an agent wrote something.
3. **No visible way to create anything on desktop.** The 2026-07-09 cut moved
   New Folder / Add Files out of the header into the canvas right-click menu,
   "like Finder". Finder can do that because a menu bar stands behind the
   gesture (File → New Folder); this shell has no menu bar, so the gesture
   was the only door. The ⌘⇧N the menu's docstring cited was never wired. A
   coarse pointer got two header buttons; a mouse got nothing.

⭐ **A designed empty state that never renders is not a design.** It was
shadowed by kernel writes the feed did not know to exclude, and the two
affordances a first day needs were behind a gesture nobody is taught.

## 3. Decisions

### D1 — Recents is what members and agents wrote

`_RECENT_REV_EXCLUDE_DIRS = ("/workspace/operation/signals", "/workspace/system/")`.
The kernel's mirrors are residue — the tree already folds them under "System
files" and calls them that — so Recents calling them "recent changes" was the
fifth face of one fact. A member's own `skills/{name}/SKILL.md` is authored
substrate and stays. The stale `context/signals` literal is replaced by the
prefix the tree actually hides. **One home for the rule**: the Text app's
consumer-side carve stays harmless, but the feed no longer needs it.

Every consumer of `GET /workspace/recent-revisions` inherits this — Files
Recents, the Text landing, the Learn-from and Design-system pickers.

### D2 — The roots always show the two homes

`always_show = {"operation", "inbound", "agents"}`. Documents and Downloads
exist in the sidebar on day one, `exists: false`, `file_count: 0`, Documents
first (the `WORKSPACE_ROOTS` order). ADR-395's reason for removing `uploads`
from this set — an empty DUPLICATE beside Intake — does not transfer: these
are the homes themselves, and the FE already merges arrival roots under one
"Downloads". The legacy `uploads/` root still shows only when it holds files.

### D3 — One visible create door, at every pointer

The Explorer header carries one quiet "+" beside its group label, on every
pointer type. It opens the **same** `CanvasContextMenu` the background
right-click opens (New Folder · Add Files · Deselect when a selection stands),
anchored under the button. One menu, two ways in; drag-drop stays the third.
The two touch-only header buttons and their `coarse &&` gate are deleted. The
pointer capability still governs tap-to-open (ADR-452) — only the create door
stopped depending on it.

### D4 — The empty state carries both doors

The cold-start branch of `RecentsView` — now reachable — renders "New folder"
and "Add files" under its copy, wrapping on a narrow pane. They are optional
props threaded from the Files page; a self-hiding kernel slot never renders
the branch, so it never shows them. The copy names the thing: *"Nothing here
yet. Files you and your agents write show up here, newest first."*

### D5 — A new folder from nowhere lands in Documents

`newFolderScope()`: the real folder the canvas is showing, else Documents. The
old fallback was the top-level peer (ADR-424 D2's "no honest here"), which
read as *"You can't create a folder here"* from a grouping and put a new
member's first folder BESIDE the home every agent is told to use. Now Recents,
a virtual group and an open file all resolve to Documents, and the modal says
so ("It will be created inside Documents"). The label is read off the served
roots, never spelt twice. `openNewFolder(null)` keeps meaning "top level" for
the API; no door on the surface passes it. **Arrivals are unchanged**: Add
Files with nothing open still lands under Downloads (ADR-555 D3, the server's
intake default) — an import is an arrival, not authored work, as on macOS. The
upload modal's fallback label now says "Downloads", the tree's own name for it,
instead of "Intake".

## 4. What this does NOT do

- **No first-run wizard, no onboarding overlay.** ADR-190/215: onboarding is
  conversational; Files gets two buttons and a sentence.
- **No new menu component.** The "+" reuses the canvas menu.
- **No change to what an agent is told** — `PARTICIPANT_FILESYSTEM_MODEL`
  already said Documents and Downloads exist; the member now sees the same.
- **No top-level-peer door for members.** A peer folder at the workspace root
  remains an agent's act (the told model asks it to name one for a topic) or
  a Move. If a member ever needs it, the NewFolderModal grows a destination
  picker — not a second fallback.

## 5. Verification

- Gate: `api/test_adr649_files_has_a_first_day.py` — §1 and §2 DRIVEN (the
  path predicate; the roots handler against an empty substrate through a fake
  client), §3/§4 structural on comment-stripped source. Falsified in place
  five ways (each server rule reverted; the empty-state door removed; the "+"
  re-gated on `coarse`; the empty-state folder sent to the top level).
- Neighbours green: `test_files_selection_model`, `test_adr452_studio_landing`,
  `test_adr588`, `test_adr643`, `test_adr555`, `test_trashed_file_does_not_read_back`,
  `test_image_listings_serve_a_thumbnail`. `test_adr388_files_surface` (3/14)
  and `test_adr571_text_app` (115/279) are red at HEAD identically — stale
  gates, untouched.
- The click-pass on a fresh workspace is the real check of D3/D4 and is
  recorded in the session handoff.
