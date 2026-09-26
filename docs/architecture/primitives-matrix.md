# Primitives Matrix — the kernel's verbs, and who holds them

**Status:** Canonical — **v2.0 (2026-09-12, the post-steward recut; v1 archived verbatim at [previous_versions/primitives-matrix-v1-2026-09-12.md](previous_versions/primitives-matrix-v1-2026-09-12.md))**
**Source of truth:** [api/services/primitives/registry.py](../../api/services/primitives/registry.py) (`PRIMITIVES` — the tool definitions — and `HANDLERS`) · [api/services/primitives/permission.py](../../api/services/primitives/permission.py) (`READ_ONLY_PRIMITIVES` + `GATE_QUEUEABLE_PRIMITIVES`) · [api/services/lane_runner.py](../../api/services/lane_runner.py) (`LANE_TOOL_NAMES` + `LANE_SURFACE_EXTRA` + `lane_tool_names`) · [api/mcp_server/server.py](../../api/mcp_server/server.py) (`_INTEROP_VERBS`) + [api/services/mcp_composition.py](../../api/services/mcp_composition.py)
**Governing ADRs:** ADR-168 (the axes + naming) · ADR-209 (every write is a revision) · ADR-307 (the one permission gate; read-only vs consequential) · ADR-337 (the working-tree verbs) · ADR-411/467 (the uniform lane surface) · ADR-512/543/545 (the file-native interop verbs) · ADR-588 (folders) · ADR-603/639 (the toolless standing run) · ADR-615/635 (turn reach; attached connectors) · ADR-632 (the steward's rosters deleted) · ADR-643 (one access decider)

> **Recut (2026-09-12).** v1's Full Matrix listed three modes (chat · headless · MCP) and three rosters (`CHAT_PRIMITIVES` · `HEADLESS_PRIMITIVES` · `REVIEWER_PRIMITIVES`) that no longer exist, and nine verbs deleted with them (`Schedule`, `ManageHook`, `FireInvocation`, `Clarify`, `GetSystemState`, `Compose`, `DispatchSpecialist`, `InferContext`, `platform_*`). The registry today is ONE list of tool definitions (`PRIMITIVES`, 27) and ONE handler map (`HANDLERS`, 31); **who holds a verb is a fact about the SURFACE, not a roster on the primitive.** The matrix below is derived from those sources on the date above; when it and the code disagree, the code wins and this doc adjusts.

---

## Dimensional framing (FOUNDATIONS v10)

Primitives are the **vocabulary of the Mechanism dimension** (Axiom 5). An agent speaks through primitives — typed verbs with substrate and permission scope; the frame is the other half of Mechanism's vocabulary (it tells the agent what it holds — [agent-composition.md](agent-composition.md) §3.1 row 4). Designing one without the other is a dimensional conflation (DP9).

| FOUNDATIONS dimension | How primitives encode it |
|---|---|
| Substrate (what) | the family column — `file` / `folder` / `revisions` / `entity` / `domains` / `proposals` / `projection` / `external` / `introspection` / `perception` |
| Identity (who) | **the surface that holds the verb** — a lane (the member through an agent), the interop face (a connected LLM as the member), a route (the member's own click). Never a roster on the primitive. |
| Purpose (why) | `read-only` vs `consequential` (ADR-307); consequential path-addressed verbs are **queueable** by the witness dial |
| Trigger (when) | the caller — a member's turn, an interop call, a click; a standing run holds no verbs at all |
| Channel (where) | the return shape — a revision, a listing, a proposal row, an image, a search result |

---

## The surfaces

| Surface | Who | Verbs | How the set is decided |
|---|---|---|---|
| **Lane** (attended) | the member, through an agent, under the member's grant | `LANE_TOOL_NAMES` — `ReadFile` · `WriteFile` · `EditFile` · `DeleteFile` · `MoveFile` · `DeleteFolder` · `MoveFolder` · `Restore` · `SearchFiles` · `ListFiles` — plus `LANE_SURFACE_EXTRA` — `GenerateImage` · `QueryKnowledge` · `WebSearch` · `list_integrations` · `DeclareWork` — plus the member's read-only **turn reach** (`turn_reach_tool_names`, ADR-615) and the member's **attached connectors'** tools (`mcp__{slug}__{tool}`, per-tool aperture — ADR-635) — plus, on a turn whose page asked and holds the extension (yarnnn on the web in Chrome, or the desktop app), the five **browser tools** (`BrowserOpen` · `BrowserRead` · `BrowserClick` · `BrowserFill` · `BrowserBack`, `services/primitives/browser.py`), which the yarnnn Chrome extension on the member's machine PERFORMS — reached from yarnnn in Chrome, or relayed by the desktop app — and the kernel never executes (`client_tools.offered`, ADR-662 D14/D15) | `lane_tool_names(reach, platforms, attached, client_tools)` — ONE computation feeds the declared payload, the execution allowlist and the frame's prose (ADR-467 D4). **Uniform for every lane and every agent**: capability is not a character trait. Gate: [test_verb_families_are_one_set.py](../../api/test_verb_families_are_one_set.py). |
| **Interop** (MCP) | a connected LLM acting as the member (Claude.ai · ChatGPT · Claude Desktop/Code) | `whoami` | each verb is a server-side **composition** over the kernel verbs (`mcp_composition.py` → `execute_primitive`; the kernel verbs it dispatches: ). The grant, the scopes (ADR-563) and the workspace binding (ADR-573) vary per principal; the verb ontology does not (ADR-512 D2). A host chains only a few tool rounds, so composition lives inside yarnnn. |
| **Standing run** (unattended) | a member's standing declaration | **none — toolless** | the target's head and the declared sources ride the message (ADR-603/639); the run answers once |
| **The desktop** | the member's own click | `Restore` (Trash) · `DuplicateFile` · `MoveFile` / `MoveFolder` / `DeleteFolder` (the Files menu, the fan-outs) · `ExecuteProposal` / `RejectProposal` (Reach → Leaving, Notifications → To do) | the routes call the same handlers the lane does — one act, one head-blob form |

**What no surface holds.** `DiffRevisions`, `ListRevisions`, `ReadRevision`, `Embed`, `SyncPlatformState`, `TrackRegime`, `TrackUniverse`, `TrackWebSources` are registered with handlers but composed into no live surface and called from no live route — the residue of the steward's rosters. ADR-632 §3 left each to its own caller audit; until one lands they are inert, and a doc that lists them as available is wrong.

---

## The permission gate (ADR-307 · ADR-643)

Every primitive is **read-only** (reads and narration — `READ_ONLY_PRIMITIVES`) or **consequential** (everything else; unlisted = consequential, fail closed). Consequential path-addressed verbs are **queueable** (`GATE_QUEUEABLE_PRIMITIVES`): the one gate at `execute_primitive` (`permission.resolve_permission`) resolves **apply / queue / deny** from the witness dial × the path's grant — under `bounded`/`manual` they queue to `action_proposals` (`family='substrate'`), under `autonomous` they apply; a locked path denies. **Whether a principal may touch a path is answered by ONE decider** (`_is_path_locked_for_principal`, ADR-643), never by a carve law in a route.

⚠️ The gate's name sets still carry names of deleted verbs (`DiscoverAgents` · `ReadAgentFile` · `SearchEntities` in `READ_ONLY_PRIMITIVES`; `Schedule` · `ManageHook` · `ManageAgent` in `GATE_QUEUEABLE_PRIMITIVES`). They are keyed by name and fail closed, so the residue is harmless — it is named here so nobody reads them as live verbs.

---

## The Full Matrix (derived from the registry, 2026-09-12)

**Legend:** ● held on that surface · ○ not held. *Reached by* names every live caller beyond the lane and interop surfaces; **none** means the verb is registered but composed nowhere.

| Primitive | Family | Gate class | Lane | Interop | Reached by | Purpose |
|---|---|---|:---:|:---:|---|---|
| `DeleteFile` | file | queueable | ● | ○ | `authored_substrate` (the archive act) | Move a file to TRASH; the revision chain retains everything (ADR-337 D2). |
| `DuplicateFile` | file | consequential | ○ | ○ | `routes/documents` (the Files menu) | Duplicate a workspace file as an attributed derivation (ADR-514 D1). |
| `EditFile` | file | queueable | ● | ○ | — | Surgically replace a string within a workspace file (file layer, ADR-337 D1). An OFFICE file (`.docx`/`.xlsx`/`.pptx`) is edited IN PLACE at the addresses ReadFile shows — `anchor.at` / `anchor.after` / `edits` / `style` (ADR-671 D3). |
| `ListFiles` | file | read-only | ● | ○ | — | List the workspace filesystem as a tree with metadata (file layer, path-based). |
| `MoveFile` | file | queueable | ● | ○ | `folder_organize` (the fan) · `routes/documents` | Move/rename a workspace file to a new path as one attributed operation (ADR-337 D3). |
| `QueryKnowledge` | file | read-only | ● | ○ | — | Search accumulated workspace context (ADR-151, ADR-174). |
| `ReadFile` | file | read-only | ● | ○ | — | Read a file from the workspace filesystem (file layer, path-based). |
| `Restore` | file · folder | queueable | ● | ○ | the Trash view (`restore_group`) | Put a file or folder BACK from Trash (the inverse of DeleteFile / DeleteFolder). |
| `SearchFiles` | file | read-only | ● | ○ | — | Search the workspace filesystem for content (file layer). |
| `WriteFile` | file | queueable | ● | ○ | `routes/documents` (Save as, ADR-395 am.2 §11.11) | Write a file to the workspace filesystem (file layer, path-based). An OFFICE path (`.docx`/`.pptx`/`.xlsx`) is WRITTEN in that format from a source — `content`, or `content=''` + one `derived_from` — via `services/office/create.py`; MCP `save` inherits it. CREATION only: a path already holding an office file is refused (`office_file_exists`) — it is edited in place (ADR-671 D1). |
| `DeleteFolder` | folder | queueable | ● | ○ | `routes/documents` (the fan) | Move a whole FOLDER to Trash — one attributed revision per file inside it. |
| `MoveFolder` | folder | queueable | ● | ○ | `routes/documents` (the fan) | Move or RENAME a whole FOLDER — the same act, addressed differently (ADR-337 D3 at folder grain). |
| `DiffRevisions` | revisions | read-only | ○ | ○ | **none — registered, no live surface** | Compare two revisions of the same workspace file. |
| `ListRevisions` | revisions | read-only | ○ | ○ | **none — registered, no live surface** | List the revision chain for a workspace file. |
| `ReadRevision` | revisions | read-only | ○ | ○ | **none — registered, no live surface** | Read a specific historical revision of a workspace file. |
| `ExecuteProposal` | proposals | consequential | ○ | ○ | `routes/proposals` (the member's click) | Approve-and-execute a previously proposed action by its proposal_id (ADR-193 + ADR-194 v2 Phase 2a). |
| `ProposeAction` | proposals | consequential | ○ | ○ | the trading emit contract; the operator-proxy harness (Hat B) | Propose a write action for user approval instead of executing it directly (ADR-193). |
| `RejectProposal` | proposals | consequential | ○ | ○ | `routes/proposals` (the member's click) | Reject a pending proposal by its proposal_id (ADR-193 + ADR-194 v2 Phase 2a). |
| `Embed` | projection | queueable | ○ | ○ | **none — registered, no live surface** | Make a file AI-ready: compute its embedding so QueryKnowledge can semantically rank it (ADR-325). |
| `ExtractTextFromBlob` | projection | consequential | ○ | ○ | `services/documents` (intake projection) | Derive a model-consumable TEXT projection from a retained raw blob, citing the raw (ADR-395 / DP34). |
| `GenerateImage` | external | queueable | ● | ○ | — | Generate an image from a text description and save it to the workspace. |
| `DeclareWork` | standing | consequential | ● | ○ | `routes/standing_work` (`POST`/`PATCH /api/standing` call the same door) | Set up or change standing work through the one door (`services/standing_door.py`, ADR-667 D2); `sites` makes it browser work in the acting member's browser. `WriteFile`/`EditFile` refuse `_standing.yaml`. |
| `SyncPlatformState` | external | consequential | ○ | ○ | **none — registered, no live surface** | Mirror external-system state into substrate (ADR-264). |
| `WebSearch` | external | read-only | ● | ○ | — | Search the public web. |
| `list_integrations` | introspection | read-only | ● | ○ | — | List the member's connected platforms — the SAME facts as the reach section of your frame, at any time. |
| `TrackRegime` | perception | consequential | ○ | ○ | **none — registered, no live surface** | ADR-271 Thread A — the trading program's regime tracker; handler only. |
| `TrackUniverse` | perception | consequential | ○ | ○ | **none — registered, no live surface** | ADR-271 Thread A — the trading program's universe tracker; handler only. |
| `TrackWebSources` | perception | consequential | ○ | ○ | **none — registered, no live surface** | ADR-336 — the perception field's web-source watch (enacts ADR-335 D7); handler only. |

Artifact cards: a lane's call on `EditFile` · `GenerateImage` · `MoveFile` · `WriteFile` · `DeclareWork` is carded as a deep link to the file (`LANE_ARTIFACT_VERBS`; for `DeclareWork`, the `CONTRACT.md` it wrote); `DeleteFile`, `MoveFile`'s source and both folder verbs are deliberately not carded — after the act there is nothing at the path to open (the reasoning is in the standing disciplines below).

---

## The substrate families

- **`file`** — the virtual filesystem over Postgres (`workspace_files`), path-based; every write an attributed revision through `write_revision` (ADR-209). `ReadFile` is capped with a notice and a real `offset` (ADR-648). Two scopes on the file verbs: `workspace` (the shared commons by meaning-path — the grant governs whether a path is yours) and `agent` (the caller's own home).
- **`folder`** — a folder is a marker row plus whatever files share its prefix (ADR-588), so a folder verb is a **fan-out**: one attributed revision per file, locked children refused and named, capped at `MAX_FAN_OUT` (500). `Restore` puts back one file or one trashed folder as a unit.
- **`revisions`** — the chain (`ListRevisions` / `ReadRevision` / `DiffRevisions`); revert is `ReadRevision` + `WriteFile` (ADR-209 D7), never a pointer flip.
- **`proposals`** — the witness gate's queue (ADR-307): an agent `ProposeAction`s; the member executes or rejects from Reach or Notifications; the verdict lands in the judgment log (the verdict-giver is the member — ADR-632 D2).
- **`projection`** — a non-text raw becomes model-consumable only as a cited projection (`ExtractTextFromBlob`, ADR-395 / DP34); `Embed` makes a file rankable by `QueryKnowledge` (ADR-325).
- **`external`** — `WebSearch`; `GenerateImage` (rented generation, ADR-568 — the only generation verb, ADR-417); `SyncPlatformState` (ADR-264 — registered, unreached).
- **`standing`** — `DeclareWork` (ADR-667): the conversation's door to standing work — the same `declare`/`revise` the routes call, so a click and a conversation make one declaration shape, and no caller names whose browser.
- **`introspection`** — `list_integrations` returns the SAME rows the frame's reach section and the Reach page render (ADR-644).
- **`perception`** — the trading program's `TrackRegime` / `TrackUniverse` and the web-source watch `TrackWebSources` (ADR-271/336): handlers only, reached by no surface since the recurrence dispatch went (ADR-603/632).

**Repo-analogy mapping (ADR-337)** — names + safety semantics are YARNNN's; parameter contracts follow Claude Code's tool shapes where a trained model prior exists:

| Claude Code / repo verb | YARNNN primitive | Divergence |
|---|---|---|
| `Read` | `ReadFile` | — |
| `Write` | `WriteFile` | every write is an attributed revision (ADR-209) |
| `Edit` | `EditFile` | same contract (`old_string`/`new_string`/`replace_all`); may not empty a file. **ADR-609 adds an optional `anchor`** — `{block_id}` (HTML artifacts) or `{start, end}` source offsets (prose) — which CONFINES the edit to the member's selected span; with no `old_string` the span is replaced wholesale. Unanchored calls are byte-identical to the borrowed prior. |
| `rm` | `DeleteFile` | view-only removal — tombstone revision; chain retained; restore = revert-as-write |
| `mv` | `MoveFile` | one attributed operation; refuses destination overwrite; both paths lock-checked |
| Put Back | `Restore` | one verb, both grains — a single trashed file, or a folder trashed as a unit (resolved from `trashed_with`, never from the caller) |
| `rm -r` | `DeleteFolder` | **a FAN-OUT, not one act** — one archive revision per file; group restores as ONE unit; locked children refused + reported; capped at 500 (`MAX_FAN_OUT`) |
| `mv` (dir) | `MoveFolder` | the same fan over `MoveFile`; rename is a sibling move; both roots lock-checked |
| `grep -F` | `SearchFiles(match='exact')` | case-insensitive literal substring over content + path |
| `git log` / `show` / `diff` | `ListRevisions` / `ReadRevision` / `DiffRevisions` | — |
| `git revert` | `ReadRevision` + `WriteFile` | ADR-209 D7 revert-as-write (no pointer-flip) |
| `cp` | — | excluded (demand-pull; no demonstrated need — ADR-337 D6) |
| `Bash` | — | excluded by design: every mutation passes a typed, gateable verb (ADR-307) |

---

> ### ⭐ Standing discipline — ONE delete, ONE meaning
>
> **Delete = move to Trash, whoever pulls the lever.** `archive_live_file`
> (`services/authored_substrate.py`) is the single act: the row stays with
> `lifecycle='archived'`, the file appears in Trash, and **`Restore`** puts it
> back — one verb, both grains, bound to the same `restore_group` the Trash
> view calls.
>
> **Why it is a rule (2026-08-21).** Delete used to mean two different things.
> The Files surface archived; the `DeleteFile` primitive REMOVED the live row.
> Both honoured "attributed and retained" — the chain kept everything either
> way — so both looked correct in isolation. But they meant different things TO
> THE OPERATOR: their own click put a file in Trash, an agent's `DeleteFile`
> made it vanish from Trash too, restorable only by hand. Measured before the
> fix: **27 archived rows vs 13 row-removal tombstones** — two populations of
> "deleted" with different recoverability and nothing telling them apart.
>
> ⚠️ **`delete_live_file` REMAINS, and is still correct for MOVE.** A move's
> source row must genuinely go: the file lives at its destination, and
> archiving the source would put a moved file in Trash as well. The two acts
> are not redundant — they answer different questions. **At BOTH grains**: a
> moved folder's source marker tombstones-and-removes too (it used to archive,
> leaving an empty ghost folder in Trash that `Restore` would resurrect at the
> old path).
>
> **One act each, one head-blob form.** `archive_live_file` /
> `restore_live_file` in `services/authored_substrate.py` are called by the
> single-file route, the folder fan-out AND the `Restore` primitive. Each used
> to carry its own write plus its own copy of the ADR-427 head-blob form; they
> agreed, which is not the same as being singular.
>
> **Trashed is a STATE, not an absence.** A read of a trashed path answers
> *"`{path}` is in Trash (moved {date}), as part of the folder `{root}`…"* via
> `describe_if_trashed`, never "File not found". The filter that stops deleted
> content leaking would otherwise turn a deletion into an absence — and the
> model then tells the operator the file never existed while it sits in Trash,
> intact. Metadata only: the bytes stay behind `ReadRevision`, because "deleted
> but still readable in one call" is the ambiguity the filter removed.
>
> The OS lesson this encodes: in a desktop, trashed is a **place you can open**,
> with Put Back beside it — the reversibility is VISIBLE, which is what makes it
> trustworthy. A hidden lifecycle flag has two failure modes and we shipped
> both: readers that forget it serve deleted content; readers that respect it
> report absence.
>
> ⭐ **Interop resolves the grain — against the LIVE tree (2026-08-26).** The
> kernel has two grains; the MCP roster deliberately has ONE `delete` and ONE
> `move`, and `mcp_composition._names_a_folder` picks the fan-out, so a foreign
> caller never has to learn our taxonomy. That resolver must ask about the
> **live** tree, because that is the only tree the fan-outs act on
> (`folder_organize.enumerate_subtree` excludes archived rows by contract). It
> did not, and the two disagreed: `delete` on an already-trashed folder resolved
> as a folder, fanned out over nothing, and answered `success: True · "0 moved
> to Trash"` — an **incorrect success** (ADR-373 D6), where the file grain would
> have refused with `file_not_found`. The resolver now reads with the same
> `lifecycle in (active, delivered)` filter `compose_list` uses: **one definition
> of "what is live"**, so a third reader cannot invent a fourth.
>
> ⭐ **A silently-resolved grain must be a LOUDLY-described one.** Because the
> caller does not choose the grain, the only place the blast radius can be
> declared is the verb's own prose — and ADR-337's safety model is exactly that
> *the descriptive name carries the radius*. Both interop entries said "a
> **file**" while the code fanned out over a subtree up to `MAX_FAN_OUT` (500);
> the kernel's `DELETE_FOLDER_TOOL` had stated its radius since the day it
> shipped. Roster entry and tool docstring now both name the folder grain and
> the sweep. Gate: [test_adr337_interop_folder_grain.py](../../api/test_adr337_interop_folder_grain.py)
> — it DRIVES the resolver (a grep for a missing filter passes for the wrong
> reason) and pins the grain phrase, not the word "folder" (`move`'s docstring
> already said "a better folder", about the destination, and passed vacuously).

> ### ⭐ Standing discipline — a trashed file does not read back
>
> Delete is a **lifecycle transition, not a row removal** (ADR-337 D2 /
> ADR-400): a trashed file KEEPS its `workspace_files` row, which is exactly
> what makes it restorable. So **"the row exists" and "the file is live" are
> different questions**, and every read must ask the second one explicitly via
> `services/workspace_context.py::live_files_filter`.
>
> **Why it is a rule (2026-08-21).** The operator moved 20 briefs to Trash. The
> delete was correct — all 20 archived, chain intact. They kept appearing in the
> Text app's Recents, opened at their URL with full content, read back through
> `ReadFile`, and matched in `SearchFiles`, so the delete looked broken. Four
> read paths never asked. The predicate was a STRING hand-copied into six sites
> and absent from four, in two incompatible dialects —
> `.or_("lifecycle.is.null,lifecycle.neq.archived")` (canonical) and
> `.in_("lifecycle", ["active","delivered"])` (excludes NULL). They agree only
> while the column stays fully backfilled, which is why the divergence hid.
>
> ⚠️ **`_exact_search` filters in Python, not with the helper** — deliberately.
> Its match already occupies the query's one `.or_()` slot, and a second
> `.or_()` REPLACES the first rather than ANDing, which would silently turn a
> substring search into "everything not archived".
>
> The ranked/semantic paths filter **in SQL** (migration 218) so a new caller
> inherits the behaviour — a Python-side filter cannot reach inside an RPC.
>
> Gate: [test_trashed_file_does_not_read_back.py](../../api/test_trashed_file_does_not_read_back.py)
> — asserts the BEHAVIOUR, never the spelling (a gate on the string would pass
> on the wrong dialect).

> ### ⭐ Standing discipline — a verb FAMILY is ONE SET, whoever holds it
>
> Two families today: **file** (`ReadFile` · `WriteFile` · `EditFile` ·
> `DeleteFile` · `MoveFile` · `SearchFiles` · `ListFiles`) and **folder**
> (`DeleteFolder` · `MoveFolder`). Each is **one set**. Any surface that reaches
> the workspace on a principal's behalf holds the WHOLE family — or the
> narrowing is a deliberate decision **with its reason recorded in this
> document**, never an accident of which roster someone remembered to edit.
>
> **Why it is a rule and not a preference (2026-08-21).** The same defect landed
> twice in one day. First: a member asked their lane to delete two config files
> and was told *"my available file tools do not include a file deletion
> primitive"* — true of that surface, false of the system. Then, one grain up:
> asked to delete the FOLDER, the lane said the primitives *"only operate
> file-by-file"* and advised running **`rm -rf` in a terminal** — which would not
> have touched the files at all, the substrate being Postgres rather than disk.
> The fan-out had shipped that week; only the Files surface could reach it.
>
> Nothing caught either because **no gate compared the rosters**: each was
> internally consistent, and the divergence was the defect. A divergence has no
> home unless something asserts *across* surfaces.
>
> ADR-337 named this failure in advance, ruling out a `Bash` primitive: *"it is
> also why missing verbs hurt so much here — there is no shell escape hatch —
> which argues for COMPLETING THE VERB SET, not adding the hatch."* A missing
> verb does not degrade gracefully; it becomes a confident refusal plus a
> workaround that corrupts the operator's model of where their substrate lives.
>
> **No extra ceremony in front of a folder verb, deliberately.** The first
> instinct was to make a lane's folder-delete queue for approval, or cap its fan
> below the operator's. Both were rejected on ADR-337's own first principles:
> the descriptive names ARE the safety model, and the safety here is structural.
> `trash_folder` writes one attributed archive revision PER FILE — nothing is
> removed, the group restores as ONE unit, locked children are refused and
> reported. That is safer than the `rm -rf` the model reached for, and safer
> than `WriteFile`, which can truncate content and flows freely. Gating the
> safest destructive verb while the lossy one runs unimpeded is incoherence,
> not caution.
>
> The comparison is now gated by
> [test_verb_families_are_one_set.py](../../api/test_verb_families_are_one_set.py),
> which derives **both** sides (never a hand-kept expected list, which would
> reproduce the failure it guards) and asserts the load-bearing one directly:
> *a foreign LLM must not be able to do to a member's files what the member's
> own lane cannot.*
>
> Three narrowings are deliberate and stated here:
> - **`DuplicateFile` (ADR-514 D1) is NOT on the lane or MCP surfaces** — it is
>   a convenience over `ReadFile` + `WriteFile` (which both surfaces hold), so
>   its absence costs no capability. On the surfaces that DO carry it the stack
>   is complete and reachable: primitive → `/api/documents/duplicate` →
>   `api.documents.duplicate` → `useFileOrganizeVerbs.onDuplicate` → the Files
>   context menu (`FileContextMenu.tsx`, file targets only) and the Studio
>   artifact menu. Verified 2026-08-21.
> - **`DeleteFile` is not in `LANE_ARTIFACT_VERBS`** — an artifact card is a
>   deep link to a file to open, and after a delete there is nothing there.
>   The call still shows as a labelled tool row; the chain stays walkable.
> - **`MoveFile` cards its DESTINATION** — its result carries both paths and
>   `path` is the source, which no longer exists once the move succeeds.
> - **Neither folder verb is carded** — `DeleteFolder` for `DeleteFile`'s reason
>   (nothing remains at the path); `MoveFolder` because its result names a
>   FOLDER, and an artifact card deep-links a FILE to open. Both still show as
>   labelled tool rows, and their results carry the honest partial
>   (`{archived|moved, locked, failed}`) for the lane to report.

**Hard boundaries (live).**

- **A lane cannot schedule work, dispatch agents, or write out to external platforms.** It reads the commons (by meaning, `QueryKnowledge`), the web, and the member's own connections under the member's grant (ADR-615), and writes only to the commons. Standing work is declared through a skill in prose (ADR-639), never a verb; publishing is the member's click on the artifact's pane (ADR-628).
- **Interop holds no kernel machinery.** A connected LLM is userspace with a filesystem (ADR-311 §5): the file, revision and share verbs, never an entity, domain or lifecycle verb. What varies per principal is the grant and the scopes (`CALLER_WRITE_POLICY["mcp"]`, ADR-563), never the ontology.
- **A standing run holds nothing.** Toolless by design (ADR-603 D6): a declaration's contract is checked by the kernel, not enforced by prose.
- **No `Bash`, no shell.** Every mutation passes a typed, gateable verb (ADR-307/337) — which is why a missing verb hurts (a confident refusal plus a workaround) and argues for completing the family, never for a hatch.

---

## Enumerations

### `WriteFile.scope` / `ReadFile.scope` (ADR-321)

| Scope | Reaches | Default for |
|---|---|---|
| `workspace` | the shared commons by meaning-path — `operation/` and the member-named folders, `inbound/`, `uploads/`, the agent homes under their grants | the lane, interop |
| `agent` | the calling agent's own home (`agents/{slug}/`) | an agent writing its `memory/` |

## Rename protocol

When renaming, adding or removing a primitive, sweep these in the **same commit** as the code change:

- **Backend** — `api/services/primitives/registry.py` (`PRIMITIVES` + `HANDLERS`) · `api/services/primitives/*.py` (the definition) · `api/services/primitives/permission.py` (`READ_ONLY_PRIMITIVES` / `GATE_QUEUEABLE_PRIMITIVES`) · `api/services/lane_runner.py` (`LANE_TOOL_NAMES` / `LANE_SURFACE_EXTRA` / `LANE_ARTIFACT_VERBS` and the tools-line prose) · `api/services/mcp_composition.py` + `api/mcp_server/server.py` (`_INTEROP_VERBS`) · `api/services/workspace_paths.py` (a participant constant that names the verb) · the gates `test_verb_families_are_one_set.py`, `test_adr533_participant_contract.py`, `test_adr337_file_verbs.py`.
- **Frontend** — grep the name: the tool-label maps that render tool rows and artifact cards (`web/components/chat/`, `web/lib/`). A deleted verb's label may stay to render HISTORICAL turns (the `ManageRecurrence` precedent).
- **Docs** — this file first; [SERVICE-MODEL.md](SERVICE-MODEL.md) · [agent-composition.md](agent-composition.md) · [docs/design/WORKSPACE.md](../design/WORKSPACE.md) · `docs/features/mcp/*`; ADRs are reference-only (a note in the superseding ADR's header, never a rewrite); CLAUDE.md if a cited path changes.
- **Changelog** — an entry in [api/prompts/CHANGELOG.md](../../api/prompts/CHANGELOG.md) per CLAUDE.md's protocol (a tool definition is LLM-facing content).

---

## Deleted primitives — the migration ledger

| Old name | Replaced by | Superseding ADR | Rationale |
|---|---|---|---|
| `LookupEntity` | (none — the two DB-backed objects it addressed, `platform` and `session`, are read by their own routes) | ADR-632 §3 caller audit *(2026-09-13)* | Registered, no live surface, no caller in routes/jobs/mcp/lanes/capture. Deleted with `refs.py`. |
| `EditEntity` | (none) | ADR-632 §3 caller audit *(2026-09-13)* | Same audit — no caller anywhere. |
| `ListEntities` | (none) | ADR-632 §3 caller audit *(2026-09-13)* | Same audit — no caller anywhere. |
| `ManageDomains` | (none — a context domain is a FOLDER under `operation/`, made by the folder verbs) | ADR-632 §3 caller audit *(2026-09-13)* | ADR-155/157 onboarding scaffold; the pure-genesis ADR-414 D4 left it unreached. |
| `TrackForeign` | `services/attached_connectors.py` (the member's attached MCP connector, reached in their own turn — not a primitive, a surface the lane composes) | ADR-635 D8 *(2026-09-03)* | The steward-era mechanical MCP watch (ADR-335 Crawl-B / ADR-356) was on no live surface after ADR-632 and production held zero watch-bound rows. The attached connector is the ONE MCP binding, read through the ADR-577 credential path; `foreign_read.py` and `_resolve_binding` went with it. |
| `CaptureConnector` | `services/connectors.py::drain_due_connector_captures` (a direct scheduler walk, not a primitive) | ADR-582 *(2026-08-19)* | The connector is a WRITER, not a pipeline: its only production caller was a `@primitive:` directive string seeded into `_captures.yaml` (production carried zero seeded rows), reading a `_watch.yaml` mirror of a selection the DB row already held. The fan-out insight (per-selector reads over a declared aperture) survives inside the walk. Files `primitives/capture_connector.py` + `services/connector_watch.py` deleted. |
| `RuntimeDispatch` | (none — generation retired) | ADR-417 *(2026-07-08)* | The render service (yarnnn-render) is decommissioned — generation is rented, not owned; yarnnn hosts no generation engine. Asset generation (chart/mermaid/image/video) retired; the `designer` role collapses to compose-only; `has_asset_capabilities()` returns `False` universally. Compose (section→HTML) moved in-API (`services/compose/engine.py`). File `primitives/runtime_dispatch.py` deleted. |
| `RepurposeOutput` | (none — a lane judgment act producing a NEW cited artifact, ADR-579 D8) | ADR-579 D9 *(2026-08-18)* | Broken (`NameError` after the paid LLM call), zero FE consumers since ADR-185 (closed refused), and doctrinally refused by ADR-333 D5 — a second production pass over finished content. File `primitives/repurpose.py` deleted; `/recurrences/{slug}/repurpose` route and the `repurpose` system-call row deleted with it. |
| `UpdateSharedContext` | `UpdateContext(target="identity"\|"brand")` | ADR-146 | One verb, typed target |
| `SaveMemory` | `UpdateContext(target="memory")` | ADR-146 | One verb, typed target |
| `WriteAgentFeedback` | `UpdateContext(target="agent")` | ADR-146 | One verb, typed target |
| `WriteTaskFeedback` | `UpdateContext(target="task")` | ADR-146 | One verb, typed target |
| `TriggerTask` | `ManageTask(action="trigger")` | ADR-146 | One verb, typed action |
| `UpdateTask` | `ManageTask(action="update")` | ADR-146 | One verb, typed action |
| `PauseTask` | `ManageTask(action="pause")` | ADR-146 | One verb, typed action |
| `ResumeTask` | `ManageTask(action="resume")` | ADR-146 | One verb, typed action |
| `Write` | Specialized primitives (ManageAgent, ManageTask, UpdateContext) | ADR-146 | P1: no remaining unique purpose  **File deleted 2026-09-12** — `services/primitives/write.py` outlived this row: unregistered since ADR-146, unreferenced, and its `agent` branch called a function the ADR-596 retirement had removed (found by `test_no_undefined_names.py`). |
| `RefreshPlatformContent` | (none — flow dissolved) | ADR-153 | Platform sync removed; data flows through tracking tasks |
| `Execute` | `ManageTask(action="trigger")` / `UpdateContext(target="agent")` / `ManageTask(action="update")` | ADR-168 Commit 2 *(shipped 2026-04-09)* | Actions dissolve into typed verbs. Also removed: `action` + `system` entity types from `refs.py` (vestigial — only served Execute's action-discovery surface). |
| `CreateTask` | `ManageTask(action="create", title="...", type_key="..."\|agent_slug="...")` | ADR-168 Commit 3 *(shipped 2026-04-09)* | Symmetry with ManageAgent. Absorbed `title`, `type_key`, `agent_slug`, `focus`, `objective`, `success_criteria`, `output_spec` fields into `MANAGE_TASK_TOOL.input_schema`. Helpers (`_slugify`, `_build_custom_task_md`) moved into `manage_task.py`. File `primitives/task.py` deleted. |
| `Read` | `LookupEntity` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Name was ambiguous with file-layer read |
| `List` | `ListEntities` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Name was ambiguous |
| `Search` | `SearchEntities` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Name was ambiguous |
| `Edit` | `EditEntity` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Name was ambiguous |
| `ReadWorkspace` | `ReadFile` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Substrate-first naming |
| `WriteWorkspace` | `WriteFile` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Substrate-first naming |
| `SearchWorkspace` | `SearchFiles` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Substrate-first naming |
| `ListWorkspace` | `ListFiles` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Substrate-first naming |
| `ReadAgentContext` | `ReadAgentFile` | ADR-168 Commit 4 *(shipped 2026-04-09)* | Name was vague; it's a file read with `agent_slug` + `path` |
| `entity:memory` type | (file substrate — `/workspace/memory/*.md` via ReadFile/WriteFile) | ADR-196 *(shipped 2026-04-20)* | Semantic content → filesystem per Axiom 0. `user_memory` table dropped. Stale branches in `refs.py`, `read.py`, `write.py`, `edit.py`, `list.py` stripped in same commit. |
| `entity:domain` type | (file substrate — `/workspace/context/{domain}/` via ReadFile/WriteFile/QueryKnowledge) | ADR-196 *(shipped 2026-04-20)* | Same rationale — pointed at `user_memory`; semantic content lives in filesystem context domains per ADR-151. |
| `ManageTask` | `Schedule` (lifecycle) + `FireInvocation` (run-now) | ADR-231 Phase 3.7 *(shipped 2026-04-29)* | Tasks-as-units dissolved; recurrences are YAML declarations at natural-home substrate paths. ManageTask's 8 actions split: lifecycle to ManageRecurrence, trigger to FireInvocation. |
| `UpdateContext` | `InferContext` (identity/brand merge) + `InferWorkspace` (first-act scaffold) + `WriteFile(scope='workspace', ...)` (mandate/autonomy/precedent/awareness/feedback) + `Schedule` (recurrence lifecycle) | ADR-235 *(shipped 2026-04-29)* | Three categorically different cognitive shapes (inference-merged write, substrate write, lifecycle action) hidden under one verb name. Splitting them honors what they are. ADR-209's `write_revision` already unifies the substrate-level write path; the consolidation rationale of ADR-146 is preserved at the substrate level, not at the primitive-name level. |
| `ManageAgent(action="create")` | (no feed-surface successor) | ADR-235 D2 *(shipped 2026-04-29)* | The systemic agent roster is fixed at signup; no feed-surface pathway to author new agents. Service code (`agent_creation.create_agent_record`) preserved for the kernel/signup path. |
| `ManageAgent` (the whole primitive) | (none — an agent is no longer an editable row) | *(shipped 2026-08-26)* | Deleted with the pre-ADR-596 agent model it managed. It wrote lifecycle actions to the `agents` table, which production held EMPTY, for a concept an agent is no longer: a BEING is a row in `services/agents_registry.AGENTS` (ADR-596/600), and authority over a being is UNREPRESENTABLE by the ADR-460 D3.a cliff — so there is deliberately no successor verb. `services/primitives/coordinator.py` deleted; the `/api/agents` router deleted with it. The NAME survives in `GATE_QUEUEABLE_PRIMITIVES` (keyed by name, fails closed) and in FE tool-label maps that render HISTORICAL turns — the ADR-603 D5 `ManageRecurrence` precedent. |
| `SearchEntities` | (none — nothing left to search) | *(shipped 2026-08-26)* | Deleted with the agent model. Its scope enum was ONLY `agent`/`version`/`all` (and `all` resolved to agents), and `SEARCH_FIELDS` carried no other type — so every scope it accepted was backed by the two EMPTY tables. It returned `Found 0 result(s)` to every possible query while occupying tool budget on all three rosters. `platform` and `session`, the surviving entity types, were never searchable, so there is nothing for a successor to search. `services/primitives/search.py` deleted. |
| `DiscoverAgents` + `ReadAgentFile` | (none) | *(shipped 2026-08-26)* | The ADR-116 inter-agent pair, deleted together. `DiscoverAgents` read the empty `agents` table and returned `{"count": 0, "agents": []}` universally; `ReadAgentFile` could only answer `agent_not_found`, since its own description said "use after DiscoverAgents" and that verb returned nothing. "Which agents exist" is now answered by the kernel register (`services/agents_registry.AGENTS`) — static data named in the frame itself, needing no tool. |
| entity types `agent` + `version` | (none — an agent is not an entity) | *(shipped 2026-08-26)* | Removed from `ENTITY_TYPES` + `TABLE_MAP` in `refs.py`. They addressed `agents` / `agent_runs`, so every ref resolved to `None` (or `[]` for a collection query) and every downstream branch — `EditEntity`'s four agent paths, `LookupEntity`'s slug-vs-UUID guard, `_resolve_version_ref` — sat unreachable behind the not-found gate. The /proc core is now `platform` + `session`. ⚠️ `ENTITY_TYPES` and `TABLE_MAP` are two literals that must be edited together; the retirement gate asserts they agree. |
| `Schedule` · `ManageHook` · `FireInvocation` | the **standing declaration** (`{folder}/_standing.yaml` + `CONTRACT.md`, declared in prose through the `declaring-standing-work` skill, ADR-639) | ADR-603 D5 *(2026-08-24)* + ADR-632 *(2026-09-02)* | Recurrences and hooks were the steward's wake configuration; a schedule with no contract was a scheduled interruption. `services/recurrence.py`, `wake_sources/`, the walkers and the dispatch went with the seat. The names survive in `GATE_QUEUEABLE_PRIMITIVES` (keyed by name, fail closed) and in FE labels for historical turns. |
| `Clarify` | (none — a lane asks in prose) | ADR-632 *(2026-09-02)* | The ask-gate (ADR-352) resolved apply/deny from the witness dial for the seat; a lane has the member present and simply asks. |
| `GetSystemState` | `list_integrations` for reach (ADR-644); the frame for everything else | ADR-632 *(2026-09-02)* | The steward's `ps aux` had no reader after the seat. |
| `Compose` · `DispatchSpecialist` | the in-API compose engine (`services/compose/engine.py`, ADR-417); an agent does its production work inline | ADR-417 *(2026-07-08)* + ADR-632 | Generation is rented, not owned; the specialist escape hatch had zero roles. |
| `InferContext` | (none — an application-level merge, relocated to `context_inference.author_identity_merge`) | ADR-324 | It was a workflow, not a primitive. |
| `platform_*` (the headless dynamic set) | `turn_reach_tool_names` — the member's read-only platform tools composed per turn from their own connections | ADR-615 *(2026-08-28)* | Reach follows the acting principal; a per-agent capability bundle was a clock on an agent. |

---

## Reading order

1. **The surfaces** — who holds what, and that a standing run holds nothing.
2. **The Full Matrix** — scan once; note the *Reached by* column.
3. **The standing disciplines** — the three rules the 2026-08-21 defects taught.
4. **Rename protocol** — before you change anything.
5. **The ledger** — when legacy code names a verb you cannot find.

## Cross-references

- [agent-composition.md](agent-composition.md) — how the frame tells an agent what it holds (§3.1) and where prose about a verb goes (§3.3).
- [SERVICE-MODEL.md](SERVICE-MODEL.md) — the system-level description; this doc is the verb-level deep dive.
- [docs/features/mcp/README.md](../features/mcp/README.md) — the interop face.
- [WORKSPACE.md](WORKSPACE.md) — the filesystem the `file` and `folder` families operate on.
- [api/prompts/CHANGELOG.md](../../api/prompts/CHANGELOG.md) — behavioral change history.
