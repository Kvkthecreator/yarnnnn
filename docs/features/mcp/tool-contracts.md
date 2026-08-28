# MCP Tool Contracts — the file-native verbs

> **ADR-545 (2026-08-10) — the binding completes.** `edit` / `delete` / `move`
> bind the ADR-337 kernel verbs (the tree stops being grow-only; targeted
> changes stop being whole-file); `list` gains the change feed (`since`) +
> pagination; `save` refuses the truncated-read overwrite shape without stated
> intent (`confirm_full_replace`). Reconnect note applies again (ADR-533 §13).

> **ADR-543 (2026-08-10) — the surface is file-native, in full.** The memory
> verbs (`remember` / `recall` / `trace`, the ADR-169→368 strata) are retired;
> every verb is a binding of a kernel verb (ADR-512 D3: read · write · list ·
> search · revisions · share) and presents no object the kernel contract does
> not have. No aliases ship — a host holding a stale manifest gets
> tool-not-found on the dead verbs until it reconnects
> ([CONNECTING.md §"The surface changed"](CONNECTING.md)).

> **ADR-533 (2026-08-07) — the verb roster is DATA, and this doc is not its source.**
> The live roster is `_INTEROP_VERBS` in `api/mcp_server/server.py`; the connector's
> self-description derives its verb table from it, and `test_adr533_participant_contract.py`
> asserts the roster and the registered `@mcp.tool` set are the same set. **Do not
> maintain a verb count in prose.** ADR-533 also gave this surface the same commons
> contract the in-app lane teaches (composed from the kernel constants in
> `services/workspace_paths.py`, not re-authored here). What deliberately does NOT
> reach a foreign host: the workspace MANDATE (D6 — the commons contract is *how the
> workspace works*; the mandate is *what it is for*).

> **Parent**: [README.md](README.md)
> **Audience**: engineers implementing the MCP server tools, and LLM hosts (Claude, GPT, Gemini) that consume them
> **Scope**: exact signatures, parameter schemas, return shapes, contract semantics
> **Governing**: **ADR-543** (file-native surface) over **ADR-512** (the file is the
> unit of interop) + **ADR-310** (judged substrate — the framing). The implementation
> is `api/services/mcp_composition.py` + `api/mcp_server/server.py`.

---

## The surface in one screen

One species-blind file contract (ADR-512 D2), served compound (server-composed,
one round) per ADR-368 Correction 1's channel constraint.
**Authoritative roster: `_INTEROP_VERBS`.**

| Verb | User says | Nature | Composes (server-side) |
|---|---|---|---|
| `whoami` | "which workspace am I in?" | read · connection | resolve binding → workspace name + `binding` + attribution + authorized verbs (ADR-584) |
| `open` | "look at this doc" | read · exact | resolve handle → exact read + head attribution + revision summary |
| `list` | "what's in my workspace / that folder" | read · enumerate | workspace-scoped subtree listing with per-file attribution |
| `search` | "find what I have on X" | read · fuzzy | `QueryKnowledge` → ranked paths + excerpts + `confidence` |
| `save` | "save that back" / "new doc" | write · whole-file | head lookup (read-before-write CAS) → `WriteFile(expected_parent_version_id, derived_from)`; large-file guard (ADR-545 D4) |
| `edit` | "change this part" | write · anchored | `EditFile` (ADR-337 D1) — exact old→new replacement; anchor is the precondition, kernel head-read CAS closes the race |
| `delete` | "get rid of this" | write · tombstone | `DeleteFile` (ADR-337 D2) — attributed tombstone; chain retained; restore = revert-as-write |
| `move` | "rename / put it over there" | write · tombstone | `MoveFile` (ADR-337 D3) — content revision at destination + tombstone at origin; refuses overwrite |
| `history` | "how did this file change" | read · exact | resolve handle → `ListRevisions` → per-revision `DiffRevisions` + the `derived_from` walk |
| `share` | "share this with my team" | write | mint share row → link (host relays; yarnnn sends nothing outbound) |

Each verb returns a reason-ready result in **one round** from the host's
perspective — the multi-step composition lives server-side (inside YARNNN, an
agentic context), not in the round-limited consumer host.

**Exact vs fuzzy is the load-bearing split.** `open` / `history` take a
reference and never guess — an unknown path returns `found: false`. `list`
enumerates what exists. `search` is the only fuzzy verb, and it says how sure
it is (`confidence`). On the write side the split is whole-vs-part: `save`
rewrites wholesale (with the large-file guard), `edit` sends only the change.
Keeping the guarantees distinct is the point of having separate verbs.

---

## Design invariants

1. **One ontology: files at paths** (ADR-543 D1). Every verb reads, writes,
   enumerates, searches, or histories files; every receipt names the path it
   touched. No phantom objects, no bespoke resolution machinery.
2. **`search` returns; it does not synthesize.** YARNNN returns material; the
   host LLM explains (retrieval, not delegation — ADR-368 D1's bright line,
   kept).
3. **Writes go through the write verbs under the grant** (`save` / `edit` /
   `delete` / `move` — one gate). The `mcp` caller is locked
   from `governance/` / `contract/` / `constitution/` / `persona/` / `system/`
   by `CALLER_WRITE_POLICY` (ADR-320/366); the ADR-307 gate at
   `execute_primitive` is the backstop. Ambient capture (a conversational
   conclusion worth keeping) is *taught in the instructions*, not a verb: the
   host saves it by meaning; an observation with no better home goes under
   Downloads.
4. **Every write is attributed + cited.** `authored_by="yarnnn:mcp:{client}"`
   (ADR-288); `derived_from` (ADR-448) records what a save was made from.
5. **Operator-visibility is session-independent** (ADR-368 D4). Every call
   emits a narrative entry even when no session is active, so the cross-room
   operator sees what entered.
6. **Zero LLM calls inside MCP.** Per-call cost ≈ $0; the host LLM is the sole
   synthesizer.

---

## `whoami` — where am I standing? (ADR-584)

```python
whoami() -> dict
```

The only verb whose subject is the **connection** rather than a file. Returns
`workspace` (the operator's chosen name, `null` while the row still wears the
mint default — see `workspace_named`), `workspace_id`, `binding`, `you` (the
attribution writes will carry), `client`, `scopes`, and `capabilities` (the
verbs this token actually authorizes, derived through the same `satisfied_by`
the gate calls, so the label cannot drift from the check).

**`binding` is the observability half.** A person can reach more than one
workspace and the `yarnnn://workspace/…` grammar is identical in all of them,
so no path can disambiguate:

| `binding` | Meaning |
|---|---|
| `chosen` | the workspace stamped at consent (ADR-573), honoured |
| `default` | no explicit choice on this connection → the principal's default |
| `fallback` | the stamped workspace is **unreachable** — writes land elsewhere, correctly and attributed. **Say so before writing.** |
| `unresolved` | resolution failed; treat the location as unconfirmed |

The `fallback` degrade is deliberate (`resolve_mcp_workspace`, ADR-573): the
operator is absent, and a connector that silently stops working is worse than
one that falls back to substrate it can always reach. What ADR-584 fixed is that
it was **unobservable** — correct, attributed, and invisible.

Scoped `files:read` — the weakest tier, by construction. Reads no file content,
mutates nothing, writes no narrative entry (an orientation call is not workspace
activity). Text-only by declaration: the answer orients the *model*, so its value
is in the model's next sentence, not in an iframe the human looks at.

## `open` — the exact read

```python
open(
    reference: str,      # yarnnn://workspace/{path} | /workspace/{path} | relative
    revisions: int = 5,  # recent revisions to summarize (max 10)
    offset: int = 0,     # character offset — pass next_offset to read on
) -> dict
```

Returns `found`, the canonical `reference` handle (ADR-512 D5), `path`,
`content` (one page from `offset`), `truncated` + `next_offset`, `offset`,
`content_chars` (the file's full length), `authored_by` (head),
`last_updated`, and `history` (recent revisions, newest first, no diffs —
`history` the verb has those). A miss is a miss: `found: false`, never a
search fallback.

**A large file is paged, not lost.** `truncated: true` always carries
`next_offset`; call again until it is false. This is the same continuation
`list` has had since ADR-545 D3 — `open` simply never got it, and the cap's
comment wrongly promised that "history/search stay available for the rest"
(`search` returns an excerpt and points back at `open`; `history` carries
revision messages, not body text). A file past the cap had **no path to its
own tail**.

**An artifact NAMES WHAT IT CITES** (ADR-617 D3). Some documents (`.html`
artifacts) cite workspace files rather than containing them: an element carrying
`data-ref="<path>"` (+ `data-ref-kind`, and `data-ref-rev` as its pin). The cited
content is **projected from the source at render**, so the element is usually
EMPTY in what `open` returns — a working citation, not missing content. The
`citations` rider names each one (`path`, `kind`, `pinned`, `projected`) and the
explanation says so in prose, so a caller knows what it has NOT seen and can
`open` the cited file. Paths only: resolving them server-side would re-copy the
bytes the citation form exists to avoid. A marked `<style>` wearing `data-ref`
is excluded — it carries the attribute as a trace edge, not a projection.

**An artifact is read as its content, not its stylesheet** (ADR-574 §2b,
closed 2026-08-28). A Studio artifact inlines a versioned kernel sheet
(~20–31KB) and a design skin ahead of `<body>`, so the cap used to land
mid-CSS: `open` returned styling and **zero authored content**, under
`success: true, found: true`. Both MARKED sheets (`data-kernel` / `data-skin`)
are now elided on read — they are machine-composed and re-stamped on every
write, so no authored byte is lost, and the explanation says how much was
elided. The **unmarked layout `<style>` survives**: it is baked once at
creation and never retrofitted, so it is the one sheet that could hold an
authored edit. Elision is read-only — the stored file is untouched, and a
round-trip through `edit`/`save` still matches the stored bytes.

## `list` — the enumeration + the change feed (ADR-543 / ADR-545 D3)

```python
list(
    reference: str = None,  # folder; omit for the whole workspace
    since: str = None,      # ISO timestamp — only files changed after this
    limit: int = 500,       # page size (cap 500)
    offset: int = 0,        # page start in path order
) -> dict
```

Returns `files` — every matching file, ordered by path, each with `path`
(workspace-relative), `reference` (open-able handle), `bytes`, `last_updated`,
and the resolved head author. `since` is the CHANGE FEED: "what moved since I
was last here" in one call — the asynchronous multi-principal coordination
primitive. `truncated: true` + `next_offset` page the rest. The listing is
real enumeration, not inference; reads are workspace-scoped, so a member or
foreign LLM under a grant sees the shared commons.

## `search` — the fuzzy read

```python
search(
    query: str,       # what to find (topic, entity, keywords)
    limit: int = 10,  # max results (hard cap 30)
) -> dict
```

Returns `results` — ranked matches, each with `path`, `reference`, `excerpt`,
`last_updated`, and `similarity` (semantic path only) — plus `total_matches`,
`returned`, `citations`, and **`confidence`** (always present; see
[honest-state-contract.md](honest-state-contract.md)):

| `confidence` | Meaning | Host action |
|---|---|---|
| `high` | a clear, dominant match | use it |
| `ambiguous` | several match, none dominates | surface candidates + ASK which they mean |
| `weak` | only loose matches below the bar | a lead, not an answer |
| `none` | nothing matched (a true miss; `results` empty) | answer from own knowledge, or `list` |

## `save` — the attributed write

```python
save(
    reference: str,                     # same grammar as open
    content: str,                       # FULL new content (overwrite, not a patch)
    base_revision: Optional[str],       # head id from `open` — REQUIRED for an existing file
    message: Optional[str],             # one-line change description
    derived_from: Optional[list[str]],  # ADR-533 D3 — source references this was made FROM
) -> dict
```

Read-before-write is the contract (ADR-512 §8a): an existing file requires
`base_revision` (the head id `open` returned); a lost race returns
`stale_write` with who holds the head — re-open, merge, save again. Omit
`base_revision` only to create. Returns the new head `revision_id` so a
follow-up save can chain.

**The citation ruling reaches the write doors (ADR-617 D4).** *A cited object's
content is projected from its source; it is never authored inside the document*
(ADR-440 D5) — a rule the Studio UI enforces in three client-side layers, so a
human literally cannot break it. MCP is the door built after that ruling, and now
carries it: `edit` refuses an anchor that removes or halves a citation
(content-free, from `old`/`new` alone), and `save` refuses a whole-file write that
DROPS a head citation or FILLS an empty one (the helpful-paste — those bytes are
overwritten at the next render, so the file and every screen disagree silently).
Both return `citation_damage` naming the remedy: to change what a citation shows,
**edit the cited file**. Stated limits: `edit` cannot see an anchor lying wholly
inside an island, and neither door repairs artifacts that already carry inlined
citation content.

**The honest save (ADR-545 D4)**: a save over an existing file LARGER than one
`open` page is refused (`large_file_overwrite`) unless the caller passes
`confirm_full_replace=true`. The guard **stays now that `open` pages**: paging
makes a full read *possible*, not certain, and the server cannot tell a caller
who paged to the end from one who read page 1 and saved. What changed is the
remedy the refusal names — page through it (`offset=next_offset` until
`truncated` is false), or use `edit` for targeted changes; the flag states
wholesale intent.

## `edit` — the anchored write (ADR-545 D1, binds `EditFile`)

```python
edit(
    reference: str,            # same grammar as open
    old: str,                  # exact current text (verbatim; unique unless replace_all)
    new: str,                  # replacement
    replace_all: bool = False,
    message: Optional[str],
) -> dict
```

Only the change travels. The ANCHOR is the precondition — no `base_revision`:
a stale view fails loudly (`old_string_not_found` → re-open and re-anchor;
`old_string_not_unique` → add context or `replace_all`), never guesses, and
the kernel's internal head-read CAS closes the apply-window race (ADR-406 D4).
Content the client never read is never in the payload — the truncated-read
data-loss class does not exist on this verb, and concurrent edits to
different regions of one file don't conflict. Returns `replacements`.

## `delete` — the tidy verb (ADR-545 D2, binds `DeleteFile`)

```python
delete(reference: str, message: Optional[str]) -> dict
```

A VIEW change, not information loss (ADR-337 D2 / ADR-209 D7): an attributed
tombstone records who and why; the revision chain (including the content at
deletion) is retained; `history` still walks the path; restore is
revert-as-write. Governance locks apply as for `save`. Returns
`tombstone_revision_id`.

## `move` — move/rename (ADR-545 D2, binds `MoveFile`)

```python
move(reference: str, new_reference: str, message: Optional[str]) -> dict
```

One attributed operation: the content lands at `new_reference`, the old path
keeps a tombstone pointing there, both chains retained. Refuses to overwrite
an existing destination — replacing a file is `delete` first, by explicit
intent.

**`derived_from`** (ADR-533 D3): cite the workspace sources the content was
made from, in the same handle grammar as `reference`. A citation that does not
parse is dropped, never fatal (the edge is provenance, not a gate). The
revision joins the graph the Files surface renders and the delete-guard warns
against.

## `history` — the attributed revision chain

```python
history(
    reference: str,   # same grammar as open — EXACT, never a topic
    limit: int = 10,  # max revisions (hard cap 30)
) -> dict
```

Returns `found`, `reference`, `path`, and `history` — the file's revision
chain newest first, each entry carrying `authored_by`, `when`, `change`,
`revision_id`, `revision_kind` (ADR-423), and `diff` (unified diff vs the
predecessor; oldest is `null`). If the file cites sources (`derived_from`,
ADR-448), each cited file's chain is appended with `cited_source: true` +
`source_path` — the complete provenance fan-in. This is YARNNN's
distinguishing capability: a plain storage connector cannot show
who-changed-what-when. An unknown path returns `found: false` — `search`
first when you only know the topic.

## `share` — the grant act

```python
share(
    reference: str = None,   # file to share; omit for the workspace
    access: str = "member",  # "member" (full) | "viewer" (read-only)
) -> dict
```

Mints a share row and returns `share_link` for the host to RELAY (yarnnn
sends nothing outbound — ADR-404). Gate parity with the cockpit origin
(ADR-517 D3): reach check, then mint authority.

---

## Shared conventions

- **The reference grammar** (ADR-512 D5, completed by ADR-587):
  `yarnnn://workspace/{path}` (the canonical handle), `/workspace/{path}` (the
  ledger's absolute form), or a bare workspace-relative path — three honest
  spellings of one name.

  **One implementation per runtime, and both directions.** Python:
  `parse_file_reference` / `format_file_reference` (`services/mcp_composition.py`).
  Browser: `parseFileReference` / `formatFileReference` / `formatAiReference`
  (`web/lib/interop/fileHandle.ts`). The two are held in lockstep by
  `api/test_adr587_handle_grammar_parity.py`, which DRIVES both over one table
  — refusals included — rather than comparing their source; a grammar that
  differs on `..` between the two halves is a security question, not a style
  one, and that is precisely what the falsification run caught.

  Before ADR-587 the browser only EMITTED the handle (Studio, Text) and could
  not parse one, so a name the app handed to an external AI could not be
  brought back. Every door now speaks the grammar in both directions: the app
  emits it (Studio/Text "Copy AI reference", the Files path field), and accepts
  it (the Files arrival door, Launcher quick-open).
- **Attribution**: every revision names its author. `history` returns
  `authored_by` per revision; `list` returns the head author per file. This is
  the mechanism that makes cross-LLM contribution visible — the host can say
  "from your ChatGPT conversation last Tuesday".
- **Error handling**: three shapes per verb — success, honest empty/miss
  (`found: false`, `confidence: "none"`, `count: 0` — the tool working as
  designed, not an error), and rare real errors (auth/network/rate-limit,
  standard MCP shapes). The host continues naturally on an empty.

---

## Deferred

- **Delegation-from-foreign-LLM** (ADR-368 §6) — an addressed wake into the
  operation (YARNNN does work, reports back). Additive when it lands.
- **Second protocol bindings** (A2A, direct-API) of the same file-native
  contract.
