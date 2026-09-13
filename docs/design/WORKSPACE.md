---
title: Workspace (Design)
counterpart: docs/architecture/WORKSPACE.md
scope: design — member-facing surface contracts, CRUD shapes, affordances
status: Canonical
version: v4.0 (2026-09-12 — the post-steward recut: the inventory derived from the registry, the deleted surfaces collapsed; v3.0 archived at ../architecture/previous_versions/WORKSPACE-design-v3.0-2026-09-12-pre-recut.md)
last_updated: 2026-09-12
---

# Workspace — Design

**Counterpart (architecture):** [docs/architecture/WORKSPACE.md](../architecture/WORKSPACE.md) — the substrate these surfaces read.
**Governed by:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — Surface Contracts and CRUD Principles.

> **Recut (2026-09-12).** v3.0 (2026-06-10) described a fifteen-surface inventory around Home, Feed, Recurrence, Queue and seven thin config surfaces, an Agents surface built on the System Agent and the Reviewer, and a four-phase hardening changelog. Home was deleted (ADR-435), Feed folded and its doors closed (ADR-370/632), Recurrence retired (ADR-603 D5), Queue absorbed by Reach (ADR-642), the config surfaces folded and then deleted with the seat (ADR-340/632), and the agent model replaced (ADR-596). The old contracts are archived verbatim at [../architecture/previous_versions/WORKSPACE-design-v3.0-2026-09-12-pre-recut.md](../architecture/previous_versions/WORKSPACE-design-v3.0-2026-09-12-pre-recut.md). The **Files** and **Reach** contracts below are carried over as last maintained (2026-08-20/21, 2026-09-07/12); everything else states the live form.

**The surface roster churns.** This doc names the surfaces as of its `last_updated`; the live set is `api/services/kernel_surfaces.py::KERNEL_SURFACES` (stage, register, route) and `web/components/shell/SurfaceRegistry.tsx`. When they disagree with this doc, the registry wins and this doc adjusts.

---

## Purpose

This is the single design reference for the member's desktop. It answers four questions, in order:

0. **How does the shell work?** (window manager + the kernel/app seam)
1. **What surfaces exist, and what does each do?** (inventory + per-surface contracts)
2. **How is mutation expressed?** (CRUD matrix + six rules)
3. **What affordances live where?** (affordance cookbook)

When a design decision spans two surfaces, both contracts must allow it. When the answer would require branching FE code on a program or an agent, the contract is wrong — apps specialize through their own row (`AppDescriptor`, ADR-636), never through FE conditionals.

---

## Part 0 — The Shell: Window Manager + the App Seam

### The surface model (ADR-297)

The authenticated desktop is a **window manager** (macOS-literal), not a tab bar:

- **A surface is a mountable React component bound to substrate**, addressed by surface state (`slug` + params), rendered into the shell's viewport (ADR-297 D11). URLs are optional addressing transport (deep-links), not identity — and a deep link must win over remembered state (2026-09-07: a pane link rewritten to the last-visited pane is not shareable).
- **`HOME_ROUTE = /desktop`** (ADR-297 D17) — login boots to the Desktop; **Chat holds the dock-anchor and default-landing roles** (ADR-435, inherited from the deleted Home). Last-session windows restore from the member's open-surfaces registry (D13).
- **Multi-mount lifecycle** (D13): opened surfaces stay mounted; exactly one is foregrounded. Closing is explicit; no LRU eviction.
- **Window chrome** (D14): every open surface renders inside a `WindowFrame`; the Dock shows kept + open surfaces, each mark carrying its own hue (ADR-641 — accent is identity; red and amber are reserved for state).
- **Navigation primitive** (D19.5): `navigateToSurface(slug, params)` is the single cross-surface verb (`useSurfacePreferences`, `web/lib/shell/surface-preferences.ts`); `router.push` is transport. Redirect stubs are pure server `redirect()` (ADR-308), hand-listed in `middleware.ts` (ADR-592's obligation). Full contract: [compositor.md § Navigating between surfaces](../architecture/compositor.md).

**Shell components** (`web/components/shell/`): `ShellCompositor` · `SurfaceViewport` · `SurfaceRegistry` · `Launcher` · `AuthenticatedLayout`. Content rendering is three-layered (ADR-245): L1 raw view · L2 content-shape parsers (`web/lib/content-shapes/`) · L3 structured affordances (`web/components/library/`).

### The app seam (ADR-562 · 592 · 636 · 646)

An **app** is one row on the server (`register_app(slug, resident, posture)`) and one `AppDescriptor` on the client (`web/lib/apps/registry.ts`); `APP_SURFACES`, `servesIndex` and the authoring rows are derived from it. **A client row never carries the resident, engine, stage, tier or anything authority-shaped** — those are the server's (ADR-460 D3.a). The server scopes which artifact types an app opens (`kinds_for_app`, ADR-646); an unowned type opens in the generic viewer, never a default app. Exposure is one `stage` per row (`internal` · `search-only` · `beta` · `primary`); `internal` removes the row from the served roster, which *is* the hide.

### Refuses (shell-wide)

- **No FE branch on a program or an agent.** Specialization is the app row.
- **No second window manager, no second navigation verb, no client-side authority.**
- **No `'use client'` redirect stubs** (ADR-308).

---

## Part 1 — Surface Inventory + Per-Surface Contracts

Derived from `KERNEL_SURFACES` on 2026-09-12. Registers: **application** (the work) · **os-config** (the OS configuring itself) · chrome (no route).

| Surface | Route | Register | Stage | Archetype | Reads (substrate) |
|---|---|---|---|---|---|
| **Chat** | `/chat` | application | primary | stream | the viewer's lanes (`chat_sessions` · `session_messages`); the workspace through the agent's tool calls |
| **Text** | `/text` | application | primary | document | `.md` / `.txt` artifacts (ADR-571) |
| **Slides** | `/slides` | application | primary | document | deck artifacts (ADR-599) |
| **Images** | `/images` | application | primary | document | artboards (ADR-472/633) |
| **Blogger** | `/blogger` | application | primary | document | the publish medium's artifacts (ADR-627/628) |
| **Files** | `/files` | application | primary | browser | `workspace_files` + `workspace_file_versions` |
| **Agents** | `/agents` | application | primary | roster | the one register (`AGENTS`) + faces |
| **Reach** | `/reach` | application | primary | dashboard | `platform_connections` · the proposal queue's boundary families · the timeline under `?lens=boundary` |
| **Notifications** | `/notifications` | application | search-only | dashboard | the witness queue + mentions (derived per viewer) · `execution_events` · the standing declarations |
| **Settings** | `/settings` | os-config | — | dashboard | account: billing (`/billing`) · usage (`/usage`) · notification settings — panes |
| **Workspace settings** | `/workspace-settings` | application | — | dashboard | the workspace's dials |
| *(internal)* connectors · sources | `/connectors` · `/sources` | os-config | internal | dashboard | rows kept off the roster (ADR-592); Reach owns the connection acts (ADR-645) |
| *(chrome)* `top-bar` · `launcher` · `chat-drawer` | `""` | — | — | chrome / navigator / input | — |

Every retired route (`/home` · `/feed` · `/recurrence` · `/queue` · `/activity` · `/mandate` · `/principles` · `/identity` · `/autonomy` · `/budget` · `/program` · `/workspace` · `/studio` · `/strings` …) is a redirect stub into a live surface.

### Surface: Files

**Route:** `/files` · **Register:** application · **Archetype:** Browser. (slug `files`, operator label "Files" per ADR-180; legacy `/context` is a redirect stub per `web/lib/routes.ts`, 2026-06-01)

- **Archetype:** Dashboard (primary, per ADR-198 §3) — live substrate slice, read-primary. Detail view of a file is a Document archetype when the file is a composed output.
- **Reads:** `workspace_files` (entire filesystem), `workspace_file_versions` (revision chain per ADR-209), `workspace_blobs` indirectly via revision reads.
- **List mode** (no `?path=`): filesystem tree grouped by the **ADR-320 five-root topology** (2026-06-10 correction — the prior grouping read stale `_shared/` · `context/` · `review/` · `memory/` roots that ADR-320 dissolved, so the Persona + System regions silently rendered empty). Groups, ordered Intent-first:
  - **Identity** — the operator's own declarations, when present: `constitution/MANDATE.md`, `operation/BRAND.md`; the dials in `governance/`.
  - **Context** — accumulated domain knowledge, **disk-derived** from `operation/{domain}/` (any `operation/` folder that isn't `reports/` or `specs/`). NOT registry-derived — program domains (`portfolio`, `trading`) are created by work demand and aren't in the kernel registry; the registry only enriches display names. A program's domains may hold `_money_truth.md` (ADR-195), `_tracker.md`, `_feedback.md` (ADR-181).
  - **Reports** — composed outputs at `operation/reports/{slug}/` (the folder shape survives from the recurrence era; recurrences themselves are retired, ADR-603 D5).
  - **Persona** — legacy `persona/` (the retired seat's files, ADR-632; present only on older workspaces).
  - **System** — the kernel's region (`system/`): the mirrors (`skills/`, `agents/{slug}/face.png`) + runtime state; not member-writable.
  - **Agents** — the agent homes (`agents/{slug}/`: `memory/` + the two grant sidecars — ADR-624).
  - **Uploads** — operator-contributed documents (`uploads/`).
  - **The tree lists FOLDERS ONLY** (2026-08-20 two-pane recut, see "TWO PANES, TWO GRAMMARS" below). The groups above name the *branches* the tree renders; their **files** appear in the **centre pane** when you navigate into them, never in the left rail. Only `operation/signals` (high-churn temporal log) stays hidden entirely. Empty groups (Persona/System/Reports/Agents/Uploads) omit-if-empty.
  - **System files are visible, not hidden** (ADR-320 correction): `_`-prefixed machine-config files (`_principles.yaml`, `_autonomy.yaml`, `_account.yaml`, `_tracker.md`…) are reachable rather than vanishing — the prior hide-rule made the surface unable to "follow" a deep-link or Get-Info into the very files Home/cockpit link to. **Since the two-pane recut this plays out in the centre pane, not the tree**: the ADR-422 D1 lock / archive glyphs and the de-emphasis went with the tree's file rows, and the same statement reaches the operator on the listing row and in Get-Info. The kernel roots themselves stay folded under the collapsed "System files" branch.
- **Detail mode** (`?path=/workspace/...`):
  - Rendered file content (markdown, HTML, or binary via `content_url`)
  - Inference-meta caption (ADR-162 sub-phase D) when present
  - Head-revision author glance ("Last edited by …") on the file header (ADR-329 D1)
  - **Node Details ("Get Info")** — per-node provenance property (ADR-329 Amendment 1), opened via header ⓘ toggle or tree right-click. File → revision chain (`authored_by` trail, diff, restore per ADR-209 P4); folder → subtree recent-changes. Replaced the deleted standing "Recently authored" left-rail feed.
  - Substrate-native edit affordance when `authored_by=operator` is appropriate (IDENTITY, BRAND, CONVENTIONS, principles, MANDATE, uploaded documents)
- **TWO PANES, TWO GRAMMARS** (2026-08-20, third cut — supersedes the one-grammar section and the second cut, both landed earlier the same day).

  **The three defects, in order.**

  1. **The fused state.** One piece of state (`selectedPath`) meant BOTH *"the highlighted item"* and *"the document the centre pane renders"*. Naming a file rendered its whole body — measured on production: a single click with `detail: 1` on a tree file rendered a 19,462-character file body inline. So a plain click could not be inert. **A click that always goes somewhere is not a selection**, and with no selection there is no multi-select, no shift-range, no bulk verb, no drag-a-group — *the entire vocabulary of file operations was unreachable through the surface.*

  2. **One grammar over two panes.** The fix for (1) applied the file-browser selection model to *both* panes. They are not two renderers of the same thing. Windows Explorer and macOS Finder both show **folders only** in the left tree, so *"does clicking a file there open it?"* never arises — it was a question only this surface had to keep answering, and it answered it by bleeding a selection into a pane with nothing to select. Operator-observed on production: clicking a **file in the tree** raised a floating Move…/Open/Clear chip beside Properties.

  3. **A THIRD file surface the model never reached.** The grammar was written for "the folder listing" and wired to the folder listing — but the centre pane has **more than one file browser in it**. **Recents** is the same grid of the same tiles in the same pane, gathered by *recency* instead of by *folder*, and it was still handed `onSelectPath={openPath}`: a single click on a Recents tile went straight through the one door and **opened the file**. The exact behaviour (1) had just removed, surviving one renderer over. Operator-observed on production. **The lesson is the scoping one**: a grammar belongs to a **kind of pane**, not to the one renderer that first implemented it — so the rule below is stated over *every centre-pane view*, and the gate counts the renderers.

  **The panes, and what lives in each.**

  | Pane | What it is | Grammar |
  |---|---|---|
  | **Left tree** (`WorkspaceTree`) | a **NAVIGATOR** — the folder hierarchy you move *through* | **FOLDERS ONLY, at every depth.** A single click navigates the centre pane to that folder *and* unfolds its branch — one gesture, one meaning. No selection, no multi-select, no open. |
  | **Centre pane — folder listing** (`ContentViewer`) | a **FILE BROWSER** — the contents of the folder you are standing in | the gestures below, in full |
  | **Centre pane — Recents** (`RecentRevisions` → `RecentsView`) | a **FILE BROWSER** — the same files, gathered by **recency** instead of by folder | **identical**, in full. The only difference is *which sequence* it draws, and that is not a difference the member's hands can feel. |
  | **Centre pane — Trash** (`TrashView`) | **NOT a browser — a VERB LIST.** Each row is a deleted file with its two acts (Restore · Delete Permanently) rendered as buttons | **no click grammar at all.** A row is not clickable; there is nothing to select and nowhere to open (the file is not in the workspace). It was checked for the same defect and does not have it. |

  **The rule, stated so a fourth view cannot miss it: any centre-pane view that renders a grid or list of LIVE FILES is a file browser and takes the grammar below in full.** A view that renders *acts* (Trash) is not one. If a new view is neither cleanly, it is the view that is wrong, not the rule.

  **The tree consequence is deliberate: it can no longer open a file at all.** The centre pane is the only route to a document. The tree draws exactly one highlight — the folder `viewPath` is showing ("you are here"), which is a position, not a pick.

  The folders-only filter is applied **at render**, inside `WorkspaceTree`, not by its caller: the same `treeNodes` array feeds the Move picker and resolves what the centre pane shows, and pruning at the source would starve both.

  **TWO STATES, never one.**

  | State | Means | Moved by |
  |---|---|---|
  | `viewPath` | what the centre pane RENDERS — a folder's listing, an opened file's body, or the Recents view | **only an OPEN** (`openPath`, the ADR-452 funnel) — including a tree click, which is a folder open |
  | `selection` | what is PICKED — an ordered SET, in the listing's visual order | **centre-pane** gestures only; it renders as a **highlight and nothing else** |

  **The centre pane's gestures** — the same in **every** browser view of it (folder listing and Recents alike).

  | Gesture | Means |
  |---|---|
  | single click (fine pointer) | **SELECT** — highlight it. Nothing else happens. A single click must be able to lead **nowhere**. |
  | ⌘ / Ctrl-click | **TOGGLE** one member in or out of the set |
  | shift-click | take the **RANGE** from the anchor to here, over the listing's current visual order |
  | double click | **OPEN** — the one gesture that leads somewhere |
  | Enter | OPEN the selection (double-click's keyboard peer) |
  | Escape · background click | **CLEAR** the selection |
  | single tap (coarse pointer) | **OPEN** — touch is unchanged |
  | right-click | **THE VERBS** — the shared `FileContextMenu` |

  - **THE VERBS LIVE IN THE RIGHT-CLICK MENU.** There is no selection toolbar. A selection should *look* selected; it does not need a chip announcing itself. `FileContextMenu` already carried Open · Open With ▸ · Properties · Share… · Rename… · Move to… · Duplicate · Move to Trash — the strip was a second, smaller, worse copy of a menu the surface already had, and it appeared from a *tree* click.
  - **Menu scope follows the OS rule.** Right-clicking **inside** a multi-selection acts on the whole set and leaves it intact (Move takes the set); right-clicking **outside** it **replaces** the selection with the row you hit — otherwise the menu names one file while a set-taking verb moves nine.
  - **Download is a context-menu verb** (2026-08-20), following the cloud-provider convention (Dropbox · Drive · OneDrive). It resolves asynchronously and simply does not render when there is nothing to save. See **THE DOWNLOAD MATRIX** below for what resolves and what deliberately does not.
  - **`FileActions` (the preview-header Open + Download buttons) is DELETED** from all three mounts. Download moved to the menu; **Open was deleted outright** — it opened the blob in a new tab, answering *"what does this look like?"* with a second copy of what the pane directly beside it was already rendering. (`Open With ▸` is a different act — it routes the file to a yarnnn app — and stays.) The chat surface's `FileOpenModal` keeps its "Open in Files" link: one door to where the verbs live.
  - **Where content is read: Files is purely a BROWSER.** Opening a `.md` goes to Text, a `.html` to Studio (ADR-451/473); unclaimed formats fall to the inline viewer. **Quick Look (a bounded in-pane preview) is deliberately NOT built** — half of one would be worse than none.
  - **What the pane shows while you select: the folder listing, unchanged.** The item highlights and the view does not move. A picked file's metadata lives in **Properties**, which the selection SCOPES rather than replaces.
  - **The branch is on INPUT CAPABILITY, never viewport width.** `useCoarsePointer()` (`(pointer: coarse)`) is the signal; `useViewport().isMobile` (a 640px WIDTH threshold) is *not* interchangeable with it — a narrow desktop window still has a mouse; a large tablet does not.
  - **Touch is single-tap, not double-tap.** Double-tap is not a touch idiom: it fires unreliably, competes with double-tap-to-zoom, and is undiscoverable. Every touch OS opens on one tap. **Touch gets no selection grammar and no new action model** — the same shape the ADR-400 kebab parity took.
  - **A folder in the LISTING takes the double-click, exactly like a file**: the listing is a grid of peers, and a member drawing a selection across it must be able to include a folder without being navigated away mid-gesture. (In the *tree* it is single-click — see above. A tree that demanded a double-click to expand a branch reads as broken.)
  - **A range is over the ACTIVE VIEW's own published visual order**, not any underlying tree order — otherwise the highlight and the rectangle the gesture drew can disagree, which is worse than having no range. **Each browser view publishes its own**: the folder listing publishes sorted, folders-first; Recents publishes **recency**, de-duplicated (the revision feed can carry one path twice, and the selection is a set of paths, so an un-deduplicated order would range to the wrong end). Whichever view is mounted is the one that published, so the range always runs over what is on screen.
  - **ONE CLICK GRAMMAR, ONE FUNCTION.** Every browser view routes to the *same* `handleFileClick` — Recents through a one-line adapter that lifts its path into the shape that function already reads. **A second selection model per renderer is the failure this surface has been burned by twice**; a renderer reports the intent (`FileClickIntent`) and decides nothing.
  - **SELECTED READS AS A RING, NOT A FILL** (operator-observed, 2026-08-20: *"the select highlight background shouldn't be so dark, closer just to image screen"*). The cause was not the colour value — a selected tile **stacked three treatments over the same pixels**: the shell's `bg-primary/10`, the preview zone's *own* `bg-primary/10` painted on top of it, and a ring over both. Two washes at `/10` do not read as one wash at `/10`. **Exactly one element carries the selected ground**, at a `/5` wash barely off the neutral; what actually says *selected* is the **border + ring**, which is what carries it in Finder too, and the fill is only there to group a multi-selection at a glance. **The preview zone keeps `TILE_PREVIEW_GROUND` unchanged**, so a selected tile's image sits on the same neutral it always sits on — the exact comparison the operator drew. **Both view modes carry the same wash and the same ring**: a selection must look like one state, not two, whichever toggle the member last hit. Gated on the **construct and the count**, never on a colour spelling — a palette change must be free to move every value, while a re-added second fill must not.
  - **The verbs act on the SELECTION.** That is what makes selection worth having. The set-Move takes it (sequential, partial results said honestly — ADR-553 D2), and **dragging a row that is part of a multi-selection drags the whole GROUP**; a dragged row outside the selection moves alone. The tree is a drop **destination** only — nothing in it is draggable, because nothing in it is a file.
  - **Arriving at a path is an OPEN, not a select.** A deep link (`?files.path=`, `?files.domain=`) is someone handing you a document, so it goes through the one door and lands rendered — **including a link to a FILE**, which no longer travels through the tree at all. Gated (`files_arrival_door.mjs` A10–A12), because "should be unaffected" is exactly the claim that silently stops being true.
  - **The way OUT is part of the feature, not a follow-up.** ADR-519 shipped an inescapable multi-selection to production once. **Escape clears at ANY size** (a selection of one is as much a state to get out of as a selection of nine), a **background click** on the listing's empty ground clears, the background canvas menu carries a visible **Deselect** naming the count (the Finder home for it, and where the deleted chip's visible exit went), and any single-target verb ends the set before it acts.
  - **THE ONE DOOR still holds**: every branch that OPENS calls `openPath` (ADR-452) — the tree's navigate included. The funnel resolves a path **without consulting the tree**, which is what keeps it correct now that the tree holds no files.
  - **ADR-553 D1 is SUPERSEDED here.** That decision made ⌘-click the *only* way into a multi-selection, on accident-prevention grounds. **That reasoning only held because a plain click was destructive** — it navigated the surface into an app. Now that a plain click is inert, plain-click-to-select is safe, expected, and the way every file browser works. ADR-553 D2 (the set-Move, its sequential loop, its honest partial reporting) and D3 (the ways out) stand and are extended. The ADR itself is unamended — canon records what was decided then.
  - **Deleted, not kept beside**: the `linkTo` deep-link branch, from `FileTile`, `FileListRow`, and `RecentsView`. It was the "Home mount" alternative to selecting — and **Home was deleted by ADR-435**, so the ternary that chose it (`onSelectPath ? undefined : rev.path`) had been permanently parked in the `undefined` arm. A branch no caller can reach is not a second mode; it is dead code claiming to be one, and here it was the code that made "does a click in this grid navigate or select?" look like a live question.
- **A FOLDER VERB IS A FAN-OUT** (2026-08-21).

  Right-clicking a folder offered Open · Properties · Share · Keep-this-current · New Folder — **no Rename, no Move, no Move to Trash**. That gap was **structural, not arbitrary**: since **ADR-588** a folder is a **marker row** (`content_type='inode/directory'`) plus whatever files share its path prefix. There is no folder object holding children, so a folder verb cannot be one row update. It is a **fan-out over the subtree**, one attributed revision per file, and no fan existed.

  The fan lives in **`api/services/folder_organize.py`**, reached by three routes (`GET /documents/folder/preflight` · `POST /documents/folder/trash` · `POST /documents/folder/move`).

  | Verb | What it does | Through |
  |---|---|---|
  | **Move to Trash** | one `lifecycle='archived'` revision **per file** under the prefix, plus the folder's own marker | `write_revision`, the ADR-209 single write path |
  | **Move** | a revision at the new path + a tombstone at the old, **per file** | `MoveFile`, the ONE mover (ADR-337 D3) — which also carries an upload's `.extracted.md` projection with its raw (ADR-554 D1), so a bespoke bulk mover would have silently dropped it |
  | **Rename** | **the same act as Move**, with a new leaf instead of a new parent | the same route — one implementation, so the two verbs cannot drift |
  | **Duplicate** | **still file-only.** Deep-copying a subtree with a `derived_from` edge per file is a different act with its own naming and attribution questions; out of scope, and a half-working entry would be worse than its absence | — |

  **`isFile` is no longer the organize gate.** It still branches three things, each for its own reason: **Duplicate** (file-only, above), **New Folder** (folder-only — the Explorer "New > Folder" grammar), and **Download** (file-only, below).

  **THE BLAST RADIUS IS IN THE LABEL, BEFORE THE CLICK.** The menu item reads **"Move to Trash (40 items)"**, not a bare label — a folder verb wearing a file verb's label is one word hiding forty acts. The count is resolved when the **menu opens** (the same lifecycle as the download href: an entry that names a consequence has to know it before it is clicked), and it comes from **the same server-side enumeration the act performs** (`enumerate_subtree`), so the number shown is the number performed. A count from a second, subtly different query would be a promise the act does not keep. The label counts **what will actually move**, not what the folder holds — promising 40 and moving 38 is the same broken promise with a number on it.

  **LOCKED CHILDREN ARE REPORTED, NEVER SILENTLY SKIPPED.** `operator_can_organize` refuses `system/`, raw `inbound/` (except `inbound/uploads/`), and `_*.yaml`/`_*.json` leaves, so a folder holding any of those can only be **partially** organized. The carve is named **in the confirm, before consent** ("2 items are managed by the system and will stay where they are") and again **in the result** ("38 moved to Trash · 2 are managed by the system and stayed"). Silently moving 38 of 40 and saying "Moved" is the incorrect-success shape: the operator believes the folder is empty while two of their files are still in it. The **backend composes the sentence** (it holds the enumeration) and the surface reports it verbatim — two builders of one sentence is how they drift. Same report shape as the set-Move (ADR-553 D2), not a second one.

  **TRASH GROUPS BY THE DELETED ROOT.** Fanning 40 files into Trash as 40 loose rows makes the folder unrecoverable **as a folder** — 40 restores and a hand-rebuilt shape. So each archived row carries a grouping key naming the deleted root, and Trash collapses them into **one restorable unit** ("ai-frontier · 40 items · Restore all"). Trash mirrors the act the operator performed: they deleted one folder, so they see one thing. Members of a group are **not** repeated as loose rows. The group restore is addressed **by the key, never by a path prefix** — a file trashed separately *after* the folder went would match the prefix but was not part of that act.

  **The grouping key is `workspace_files.metadata['trashed_with']`, deliberately not a new column.** It is per-row presentation state about one archive act, which is what that JSONB is for; a column would need a migration against live substrate for a grouping affordance, on the most-guarded write seam in the system. It is written with a **read-merge-write** (the `set_launch_handler` precedent) — a blind replace would destroy a file's ADR-514 D2.4 Open-With binding on its way to the Trash, and Restore would bring back a file that had forgotten how to open. Metadata-only, so it mints no revision: the ADR-209 declared exception. **No schema change, so no ADR** — the fan is an implementation of verbs ADR-400 already ratified, over a substrate shape ADR-588 already established.

  **Bounded.** One fan-out is capped (`MAX_FAN_OUT = 500`); past that the routes refuse with a 413 and say so. A folder verb is an operator gesture, not a migration, and half-performing a thousand-file act inside one request is worse than declining it.

  **Self-containment is refused by construction, not by a 400.** The Move picker greys the folder being moved and everything under it, with the reason on the row. The backend refuses it too (that is the actual boundary; the picker is courtesy) — but a refusal met only *after* choosing is a dead end wearing a live affordance.

  **A folder is not draggable, and that is now a CHOICE.** The comment on `tileDnd` used to read "there is no backend folder-move"; there is one. The drag gesture is held back until it grows a containment guard: a picker cannot offer a destination inside the thing being moved, but a drop target can, and a fan-out chasing its own tail is the wrong thing to discover by accident.

- **THE DOWNLOAD MATRIX** (2026-08-21).

  | Target | Downloads? | How, and why |
  |---|---|---|
  | **Binary file** | ✅ | the bytes live in the content-addressed blob store; a **signed URL** + `download={filename}`. The filename is **load-bearing**: the CAS is keyed by **content address**, so a bare `download` attribute saved the blob as its 64-char SHA with no extension (fixed in `1069fe3`, preserved here). |
  | **Text file** (`.md` · `.csv` · `.yaml` · `.html` · `.txt` · `.json`) | ✅ | its bytes **are** the `content` column — it has **no `content_url` at all**. Downloaded as a typed `Blob` from content already in the payload the surface just fetched. The MIME type must be **stated**: an untyped Blob saves as `application/octet-stream`, which the OS shows as a nameless binary even when the extension is right. |
  | **Folder** | ❌ | see below |
  | **Multi-selection** | ❌ | see below |

  **The text lane was the real gap.** `downloadFor` resolved only a file with a `content_url`, so right-clicking `gtm-strategy.md` offered **no Download at all** and nothing explained why. That is an affordance **absent rather than refused** — the incorrect-success shape: the operator concludes the product cannot do it, when the content was sitting in the response it had just received.

  **No zip, and no zip is coming.** Dropbox · Drive · OneDrive all zip a folder server-side. We deliberately do not, for two reasons worth recording:
  - **ADR-417 — generation is rented, not owned.** yarnnn hosts no generation/rendering engine. A zip builder sits near enough that boundary to need **its own decision**, not to arrive as a side effect of a menu fix.
  - **The bulk door already exists and is strictly better.** `GET /api/workspace/export` (ADR-328 D4) produces a **real git repo** of the workspace **with history and attribution**. A zip has neither.

  So the entry **simply does not render** for a folder or a multi-selection. **No dead affordance, no disabled-looking row** — an entry that does nothing when clicked is the same defect at a different address. An "Export workspace…" item is **not** added to the folder menu: the operator did not ask for it, and a **subtree** export is a separate future ADR.

  The object URL a text download mints is **revoked on unmount**. `URL.createObjectURL` is held by the document until explicitly revoked — never GC'd while the page lives — so twenty right-clicks would leak twenty file bodies. It cannot be revoked at mint (that invalidates the href before the anchor is followed) nor on menu close (the click that closes the menu **is** the navigation).

  - **Gated** in `api/test_files_selection_model.py` (the centre-pane grammar, **39 checks** — claims 12 and 13 added for Recents and the highlight), `api/test_folder_verbs_and_download.py` (the fan-out + the download matrix, **43 checks**), `web/scripts/gates/adr553_multi_select.mjs` (the ways out, 20 checks), `web/scripts/gates/files_arrival_door.mjs` (the arrival door, 12 checks) and `api/test_adr452_studio_landing.py` (the open funnel + the pointer branch). The Python gates are script-style: `python3 <file>` from `api/`; the FE gates run from the repo root.

- **`+` menu / writes (ADR-649, 2026-09-12 — supersedes the line this replaces and the 2026-07-09 "no visible buttons" cut):** the two canvas verbs — **New Folder** (`NewFolderModal`, ADR-424 D2/ADR-588 marker) and **Add Files** (`UploadModal`, ADR-555) — live in ONE `CanvasContextMenu` with **two ways in**: the background right-click (Finder's gesture) and a quiet **"+" in the Explorer header at every pointer** (Finder hides its verbs behind a right-click because a menu bar stands behind them; this shell has no menu bar, so the gesture alone left a new member with no door). Drag-drop is the third import path. **The cold-start empty state** (Recents, ADR-329 Am. 2) **carries both doors** and is now reachable: Recents excludes `system/` (the kernel mirrors were the first 15 "recent changes" every new workspace showed). **A new folder from nowhere lands in Documents**; an arrival from nowhere lands in Downloads (ADR-555 D3). **Documents and Downloads always show in the tree**, `exists:false` until written — the same two homes every agent is told exist. No chat seeders.
- **Deep-links out:** every file path is a stable URL (`/files?path=...`), linked from chat (the files a lane touched), the notifications timeline, and Reach's Crossed lens.
- **Refuses:**
  - Standing-work orchestration (→ Notifications → Standing work), agent authoring (agents come from the one register — ADR-600), proposal decisions (→ Reach)
  - "Edit in chat" buttons on substrate files (per R3) — Files is where substrate gets edited; Chat would invoke `WriteFile(scope='workspace', ...)` and produce the same write with less clear provenance
  - Duplicate rendering of composed outputs (an output exists in one canonical place; Files links rather than embeds per ADR-198 I2)

### Surface: Chat — the lanes (ADR-411 · 412 D3 · 558)

**Route:** `/chat` · **Register:** application · **Archetype:** Stream. The dock anchor and default landing (ADR-435).

- **Reads:** the VIEWER's lanes in the acting workspace (member-experience scope, `(workspace, principal)`-keyed), work-first recents; the conversation panel (`LanePanel`).
- **What a lane is:** one conversation with one agent under the member's grant, attributed `member:{user_id} via {model}`. Lanes are isolated conversations; **the workspace is the shared memory** — agents collaborate through files with attribution, never through each other's transcripts. Chat is the **engine** surface (an unbound lane names an engine; `create_lane` refuses an `agent` for an unbound lane); who replies is the **cast**, joined from inside the conversation (ADR-495/558), never chosen at the door. A bound lane carries its artifact and the member's focus declaration (ADR-452/606).
- **Writes:** only through the agent's tool calls (the file verbs, the app's verbs); every write attributed, on the timeline. A lane sees what it reads — a binary `ReadFile` on an image appends the pixels (ADR-623).
- **Deep-links out:** the files a lane touched (→ Files / the app); never inward to another transcript.
- **Refuses:** generic chat parity (grounding · provenance · multi-engine are the floor); a second log; a persona chrome (ADR-632).

### Surface: Agents — the register (ADR-558 · 600 · 640)

**Route:** `/agents` · **Register:** application · **Archetype:** Roster.

- **Reads:** the one register (`AGENTS`, `api/services/agents_registry.py`) sectioned by app, with provenance served (which app, which resident, whether offered); the member's own `agents/{slug}/face.png` wins over the kernel's face (ADR-641 am.2).
- **Shows:** who the agents *are* — identity, character, engine, the craft in reach and the tending the member has done. **Nothing attributed to an agent**: no work list, output, cost or history (ADR-640). An agent is met, not audited.
- **Writes:** none. The cast is joined from inside a conversation, never here.
- **Deep-links out:** open a lane with the agent (→ Chat); the agent's app.
- **Refuses:** an agent record; an authority-shaped field on the client row (ADR-636); a second roster; the retired System Agent / Reviewer cards.

### Surface: Notifications — attention, activity, standing work (ADR-410 · 605 · 639)

**Route:** `/notifications` · **Register:** application · **Stage:** search-only · **Archetype:** Dashboard.

- **Panes:** **To do** — what wants me: the witness queue + `@mentions`, derived per viewer with ONE cursor that visiting advances (`mark_read_up_to`; Dismiss = clear without opening, never the only exit — ADR-605/637) · **Activity** — the workspace timeline (`execution_events` + revisions; the one log, Axiom 9) · **Standing work** — the roster of standing declarations with Run now / Pause (`routes/standing_work.py`, `/api/standing` — ADR-639).
- **Writes:** Run now / Pause; the proposal decisions (the same body Reach mounts, filtered).
- **Refuses:** a stored notification table (attention is derived, DP29/35); a second attention floor; a per-agent record.

### Surface: Reach (application) — the boundary's door (ADR-642, 2026-09-07)

- **Reach** (`/reach`, application, **Dashboard** archetype, `stage: primary`, pinned) — the Channel dimension's one front door. Three panes, everything DERIVED (DP29): **Connected** (every connection, platform + attached: target · reads · writes · capture freshness · which standing declarations read it — and every consent act: connect · select · aperture · disconnect, ADR-645 D2; Settings → Connectors is deleted) · **Leaving** (the proposal queue filtered to the boundary families `external-write` + `capital`; `QueueBody families=…`, one body, three mounts) · **Crossed** (the workspace timeline under `?lens=boundary`: observations in, `_publish.yaml` receipts and decided boundary proposals out, receipts attached with D7 reachability + D8 read-back). **Writes:** the two proposal decisions and the connection acts. **Refuses:** Run now / Pause (→ Notifications → Standing work); any publish act (→ the artifact's own pane, ADR-628 D2); any per-agent record (ADR-640); a second log (Crossed is a lens over the one timeline, Axiom 9).
- ~~**Queue** (`/queue`)~~ — **ABSORBED by Reach (ADR-642 D4).** `/queue` is a redirect stub → `/reach?reach.pane=leaving`, hand-listed in middleware. The proposal body still mounts unfiltered on Notifications → To do.
- **Activity** (Notifications → Activity; `/activity` is a redirect stub, ADR-603 D5 — **Stream** archetype) — the workspace-wide execution ledger. Reads `execution_events` (ADR-250 + ADR-265). The execution lens; the declaration lens is Notifications → Standing work. Rows deep-link to the kept file. **Refuses:** declaration mutation (→ Notifications → Standing work); conversation (→ Chat).

### The apps — Text · Slides · Images · Blogger

One `AppDescriptor` per app (ADR-636) mirroring `register_app` (resident · posture · stage — ADR-562/592). Each is a pane over the artifact types the server scopes to it (ADR-646): **Text** (`.md` / `.txt`, resident Editor, ADR-571), **Slides** (decks, Editor, ADR-599/620), **Images** (artboards, Designer, ADR-472/633 — the rail is `layers`, z authored by intent), **Blogger** (the publish medium, Blogger, ADR-627/628 — Publish is the member's click, receipted). The kernel chrome is shared; the object rail, noun and inspector rows are app-scoped (`objectModel`: `flow` | `pages` | `layers`, ADR-633). A bound lane sits beside the canvas (ADR-606); an act on the artifact is judged, not merely applied (ADR-612/613). Their contracts live in the ADRs named — this doc does not restate them.

### Settings · Workspace settings

`/settings` is the account window (billing · usage · notification settings, reached from the user menu — ADR-347). `/workspace-settings` holds the workspace's dials. **Connections are not here**: Reach owns every connection act (ADR-645) and Settings → Connectors is deleted.

### Retired surfaces

**Home** (ADR-435) · **Feed** (folded by ADR-370; doors closed by ADR-632 D4) · **Recurrence** and the `/work` → `/recurrence` view (ADR-603 D5) · **Queue** (absorbed by Reach, ADR-642 D4) · **Activity** as a surface (Notifications → Activity) · the thin **intent / os-config** surfaces mandate · principles · identity · autonomy · budget · program (folded by ADR-340 P2, deleted with the seat) · **Studio** (dissolved into the apps, ADR-599) · **strings** (ADR-639) · the **`/workspace`** container (ADR-297). Their routes are redirect stubs; their last contracts are in the archived v3.0.

---

## Part 2 — The CRUD Matrix

Four shapes. One rule per verb-object pair. Every mutation on the desktop picks exactly one shape.

| Shape | When | Surface | Example |
|---|---|---|---|
| **Direct** | High-precision, well-specified, one-step, reversible | In-place button on the object's own surface | Approve a proposal · Run a standing declaration now · Pause it · Restore a revision · Move to Trash · Publish (the member's click) |
| **Modal** | High-precision, multi-field, a **creation flow** the member arrives at with a blueprint | The canvas menu / `+` | New Folder · Add Files (ADR-649) · Connect a platform (Reach) |
| **Chat** | Judgment-shaped, needs the agent's context | A seeded prompt in a lane | Declare standing work (the skill) · rewrite a mandate · refine an artifact |
| **Substrate** | Content that IS a file | Open the file in its app (Text · Slides · Images · Blogger) — every write attributed | MANDATE.md · BRAND.md · an uploaded document · any artifact |

### The six rules

- **R1 — One verb, one shape per object.** "Declare standing work" is always Chat (the skill). "Edit a file" is always Substrate. "Approve a proposal" is always Direct.
- **R2 — Create is Modal or Chat. Update/Delete is Direct or Chat, never Modal.** No "edit modal" anywhere on the desktop.
- **R3 — Substrate operations bypass Chat.** If the thing being edited IS a file, the edit surface is its app. Chat would invoke `WriteFile(scope='workspace')` anyway, and the direct edit produces the same write with clearer provenance.
- **R4 — The `+` / canvas menu is a modal launcher, never a chat seeder.** Chat-shaped mutations live in the lane beside the object.
- **R5 — One label: "Edit in chat".** Chat is the lane; the agent is the member's colleague; the member is editing *in a surface*, not *through a brand*.
- **R6 — Surfaces never branch on a program or an agent.** Specialization is the app row (ADR-636); bypassing it for "just one conditional" undoes the seam.

---

## Part 3 — Affordance Cookbook

Quick lookup for verb-object pairs. When adding an affordance, add it here in the same commit it lands in code.

| Verb | Object | Shape | Location | Notes |
|---|---|---|---|---|
| Create | Folder | Modal | Files canvas menu / header `+` → `NewFolderModal`; lands in Documents from nowhere | ADR-588/649 |
| Add | Files | Modal | Files → `UploadModal`; drag-drop; lands in Downloads from nowhere | ADR-555/649 |
| Declare | Standing work | Chat | any lane → the `declaring-standing-work` skill | ADR-639 |
| Run now / Pause | Standing declaration | Direct | Notifications → Standing work | ADR-639 |
| Edit | The operator's declarations (MANDATE · BRAND) | Substrate | open in Text | ADR-329 D5 |
| Edit | An artifact | Substrate | its app; a judged act in the bound lane | ADR-612/613 |
| Approve / Reject | Proposal | Direct | Reach → Leaving (or Notifications → To do) | ADR-307/642 |
| Move / Rename / Trash | File or folder | Direct | Files right-click menu (a folder verb is a fan-out, count in the label) | ADR-553/588 |
| Restore | File revision · trashed folder | Direct | Files Get-Info → Restore; Trash → Restore all | ADR-329 |
| Download | File | Direct | Files right-click → Download (no zip; export is the git door) | ADR-328 D4 |
| Connect / disconnect · select · aperture | Platform | Modal / Direct | Reach → Connected | ADR-645 |
| Publish · Send | Artifact | Direct | the artifact's own pane (Blogger → Publish; Text → Send to Slack) | ADR-628 |
| Share | Workspace / file | Direct | the share verb (governance's reflexive verb) | ADR-517 |
| Open a lane with an agent | Agent | Direct | Agents → the agent; Chat | ADR-558 |

---

## Related docs

- [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — governs this doc
- [ADR-297](../adr/ADR-297-surfaces-as-substrate-mirror.md) — the surface model: windowed Desktop, `navigateToSurface`
- [ADR-198](../adr/ADR-198-surface-archetypes.md) — archetype vocabulary
- [ADR-209](../adr/ADR-209-authored-substrate.md) — the revision chain, `authored_by`
- [ADR-558](../adr/ADR-558-chat-is-the-engine-surface-agents-are-personified.md) · [ADR-600](../adr/ADR-600-one-register-hireability-is-a-field.md) · [ADR-640](../adr/ADR-640-an-agent-has-no-record-of-its-own.md) — Chat and Agents
- [ADR-605](../adr/ADR-605-a-mention-reaches-its-person.md) · [ADR-639](../adr/ADR-639-standing-work-is-a-kernel-lane.md) — Notifications
- [ADR-642](../adr/ADR-642-the-boundary-has-a-door.md) · [ADR-645](../adr/ADR-645-reach-is-the-connection-surface.md) — Reach
- [ADR-636](../adr/ADR-636-an-app-declares-itself-once-on-each-side-of-the-wire.md) · [ADR-646](../adr/ADR-646-the-server-scopes-the-type.md) · [ADR-633](../adr/ADR-633-the-artboard-is-a-stack-of-layers.md) — the apps
- [ADR-649](../adr/ADR-649-the-files-surface-has-a-first-day.md) · [ADR-588](../adr/ADR-588-folders-are-first-class-and-the-told-name-is-an-address.md) — Files
- [docs/architecture/compositor.md](../architecture/compositor.md) · [docs/architecture/lane-frame.md](../architecture/lane-frame.md)
