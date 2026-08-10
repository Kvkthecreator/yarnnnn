# MCP Tool Contracts — the file-native verbs

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
| `open` | "look at this doc" | read · exact | resolve handle → exact read + head attribution + revision summary |
| `list` | "what's in my workspace / that folder" | read · enumerate | workspace-scoped subtree listing with per-file attribution |
| `search` | "find what I have on X" | read · fuzzy | `QueryKnowledge` → ranked paths + excerpts + `confidence` |
| `save` | "save that back" | write | head lookup (read-before-write CAS) → `WriteFile(expected_parent_version_id, derived_from)` |
| `history` | "how did this file change" | read · exact | resolve handle → `ListRevisions` → per-revision `DiffRevisions` + the `derived_from` walk |
| `share` | "share this with my team" | write | mint share row → link (host relays; yarnnn sends nothing outbound) |

Each verb returns a reason-ready result in **one round** from the host's
perspective — the multi-step composition lives server-side (inside YARNNN, an
agentic context), not in the round-limited consumer host.

**Exact vs fuzzy is the load-bearing split.** `open` / `history` take a
reference and never guess — an unknown path returns `found: false`. `list`
enumerates what exists. `search` is the only fuzzy verb, and it says how sure
it is (`confidence`). Keeping the guarantees distinct is the point of having
four read verbs.

---

## Design invariants

1. **One ontology: files at paths** (ADR-543 D1). Every verb reads, writes,
   enumerates, searches, or histories files; every receipt names the path it
   touched. No phantom objects, no bespoke resolution machinery.
2. **`search` returns; it does not synthesize.** YARNNN returns material; the
   host LLM explains (retrieval, not delegation — ADR-368 D1's bright line,
   kept).
3. **Writes go through `save` under the grant.** The `mcp` caller is locked
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

## `open` — the exact read

```python
open(
    reference: str,      # yarnnn://workspace/{path} | /workspace/{path} | relative
    revisions: int = 5,  # recent revisions to summarize (max 10)
) -> dict
```

Returns `found`, the canonical `reference` handle (ADR-512 D5), `path`,
`content` (capped; `truncated: true` when cut), `authored_by` (head),
`last_updated`, and `history` (recent revisions, newest first, no diffs —
`history` the verb has those). A miss is a miss: `found: false`, never a
search fallback.

## `list` — the enumeration (NEW, ADR-543)

```python
list(
    reference: str = None,  # folder; omit for the whole workspace
) -> dict
```

Returns `files` — every file under the folder, ordered by path, each with
`path` (workspace-relative), `reference` (open-able handle), `bytes`,
`last_updated`, and `authored_by` (head author). `truncated: true` when the
subtree exceeded the cap (narrow the folder). The listing is real enumeration,
not inference — closing the gap the 2026-08-10 external audit surfaced (an
external principal had to reconstruct the tree from search hits). Reads are
workspace-scoped, so a member or foreign LLM under a grant sees the shared
commons.

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

- **The reference grammar** (ADR-512 D5): `yarnnn://workspace/{path}` (the
  canonical handle; Studio's "Copy AI reference" emits it), `/workspace/{path}`
  (the ledger's absolute form), or a bare workspace-relative path. One parser
  (`parse_file_reference`) owns it.
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
