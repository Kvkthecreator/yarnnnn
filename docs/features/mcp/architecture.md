# MCP Architecture — Dispatch, Composition, Cost, Provenance

> **Parent**: [README.md](README.md)
> **Audience**: engineers working on the MCP server and its composition layer
> **Scope**: how the verbs route through the kernel, what each composes
> server-side, auth, attribution, cost
> **Governing**: **ADR-543** (file-native surface) over ADR-512 (the file is the
> unit of interop) + ADR-310 (judged substrate / multi-user auth) + ADR-164
> (runtime-agnostic primitives). Rewritten 2026-08-10 — the prior version was a
> 2026-04-09 ADR-169 body under two supersession banners; this is the
> current-truth cut.

---

## The shape in one paragraph

The MCP server (`api/mcp_server/server.py`) is a **thin binding of the kernel
verb contract** (ADR-512 D3). Each `@mcp.tool` resolves per-request identity,
delegates to a `compose_*` function in `api/services/mcp_composition.py`, emits
one narrative entry, and wraps the result in the presentation envelope
(`_present`, ADR-372). The composition layer chains kernel primitives
server-side — never an LLM call — so a round-limited consumer host gets a
reason-ready result in one round (ADR-368 Correction 1). No MCP tool
introduces a new primitive.

## Runtime-agnostic dispatch (ADR-164)

Primitives are runtime-agnostic: `execute_primitive(auth, name, input)`
dispatches to one handler regardless of caller. The MCP composition layer is
one of its callers, beside chat and the scheduler/wake paths — one pipeline,
same auth, same audit path, same ADR-307 consequential gate. Where a
composition needs a *read shape* the primitives don't offer (exact row by
path, the workspace-scoped listing), it queries the substrate directly under
`_substrate_scope(auth)` — the workspace-keyed scope every read composition
shares (the ADR-407/501 member read-path lesson: a member or foreign LLM under
a grant sees the shared commons, never its own row set).

## Verb-to-kernel mapping (ADR-543 D2)

| Verb | Kernel verb | Composes (server-side) |
|---|---|---|
| `open` | read | direct scoped read of the exact path + `ListRevisions` summary |
| `list` | list | scoped subtree query (paths + `content_bytes` + head author via the `head_version_id` join), capped with an honest `truncated` flag |
| `search` | search | `QueryKnowledge` → ranked results + the `confidence` derivation (zero added inference) |
| `save` | write | head lookup → `WriteFile(expected_parent_version_id, derived_from)` — the ADR-406 linearity guard makes the CAS atomic |
| `history` | revisions + provenance | `ListRevisions` → per-revision `DiffRevisions` → the `derived_from` walk (ADR-448, column-first with the content-convention fallback) |
| `share` | share (grant act) | reach check + mint gate (`assert_may_mint_share`) → share row → link |

Two module-level facts worth knowing before editing:

- **The reference grammar has one parser.** `parse_file_reference` /
  `format_file_reference` own the `yarnnn://workspace/…` handle (ADR-512 D5).
  The ledger's `normalize_workspace_ref` owns `/workspace/` prefixing at the
  write door. Two parsers, each owning its grammar, neither duplicating the
  other.
- **Paths are stored absolute.** `workspace_file_versions` keys on
  `/workspace/…`; a bare relative path matches zero rows (the 2026-06-25
  lesson — the chain silently came back empty).

## Auth — per-request, multi-user (ADR-310 D4)

Transport: OAuth 2.1 (claude.ai, ChatGPT — auto-approve, tokens in
`mcp_oauth_*`) with a static-bearer fallback (Claude Desktop/Code). Identity
is resolved **per request**: `resolve_request_client()` reads the access
token's `user_id`; `MCP_USER_ID` survives only as the stdio/static-bearer
fallback. `/authorize` requires a real yarnnn login binding the Supabase user
to the auth code. Data isolation is the workspace grant, not the transport.

## Attribution + client identity

Every write lands `authored_by="yarnnn:mcp:{client}"` (ADR-288) — the room is
named, not just "an MCP write". The client id resolves from the OAuth
registration (`derive_client_name_from_token`; the User-Agent path is the
fallback), mapped through the single Host Profile registry
(`mcp_server/presentation/hosts.py`, ADR-379) — a new host is a registry
entry, never a new `if`.

Every call — read or write — also emits one **session-independent narrative
entry** (`_emit_mcp_narrative`, ADR-368 D4): the cross-room operator sees what
entered even with no YARNNN tab open, attributed to the acting host by name.

## The discovery contract (ADR-533 §13)

The server declares `capabilities.tools.listChanged: true` (the SDK default
lied `false`, so hosts cached the manifest forever — two frozen vintages were
measured live). A host that already cached still needs the human reconnect
step after a surface change: [CONNECTING.md §"The surface changed"](CONNECTING.md).
This is load-bearing for ADR-543: the memory verbs are gone without aliases,
so a stale host gets tool-not-found until it re-fetches the manifest.

## Presentation (ADR-372/379)

`_present` returns a `CallToolResult` with both channels (text JSON +
`structuredContent`) whenever a tool has an affordance **or** a declared
output schema — a bare dict under a declared schema trips the SDK's
"outputSchema defined but no structured output returned" error (the 2026-08-03
live break). The widget pointer (`_meta`) attaches only for a
widget-rendering host; discovery and resource reads are host-gated the same
way (`HostGatedFastMCP`). Detail: [presentation.md](presentation.md).

## Cost model

Zero YARNNN-side LLM calls on the serving path. `search` rides the
embeddings/FTS the substrate already maintains; `history`'s diffs are computed
per call from stored revisions; everything else is row reads and one write.
Per-call cost ≈ $0, which is why MCP calls take no work-budget accounting and
no tier differentiation — the value scales cross-LLM, not per-call. Rate cap:
1000 calls/day/user across all connected hosts.

## What was deliberately removed (tombstones)

- **The memory ontology** (ADR-543): `remember`/`recall`/`trace`, the
  `resolve_*_path` store/fetch-by-key machinery, `stamp_provenance`, the
  domain-alias table. Observations arrive as ordinary attributed `save`
  writes; ADR-376 §5's capture/understanding split survives as convention +
  grant, not a verb.
- **The eager per-write derive wake** (ADR-428): no wake fires on a foreign
  write. When a real deterministic derive step ships it re-attaches as its own
  mechanism (`revision_kind='derivation'` + `derived_from`);
  `compose_history`'s walk already reads that chain.
- **The ADR-169 intent tools and the pre-169 nine-tool CRUD surface** —
  historical strata; see the ADR ledger.
