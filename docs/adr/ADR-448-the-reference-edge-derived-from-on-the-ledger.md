# ADR-448: The Reference Edge — `derived_from` on the Ledger, the Derive Step, and "Learn From"

**Status**: Accepted (2026-07-12, operator-ratified direction — "proceed in full"). Implements the
ADR-423 §7 second pass, items 1 + 4 (the column + the walk), whose trigger condition ("a
deterministic derive step exists") recon shows is **already satisfied** by ADR-395's upload
projection derive. Derivation: [the load-bearing-files note](../analysis/load-bearing-files-are-a-graph-fact-the-reference-edge-derive-step-and-design-system-2026-07-12.md).
**Date**: 2026-07-12
**Dimension**: Substrate (Axiom 1 — the ledger carries the edge a derived revision has to its
sources) + Channel (the Files dependents warning).

**Amends**: ADR-423 (its §7 items 1+4 land: `derived_from` becomes a column, read-both; its D3
writer set gains the upload-raw writer it missed; `'derivation'` gets its first live writers) ·
ADR-376 / DP32 (the `cite` leg becomes structural — a ledger column, not only a content
convention) · ADR-395 (the projection derive now cites via the column and tags
`revision_kind='derivation'`; the raw upload tags `'observation'`).
**Preserves**: ADR-209 (one write path — the edge is one more optional field on `write_revision`;
the lift happens inside the single door) · ADR-286 (single-writer — nothing re-homes; observation
and derivation stay separate files) · ADR-434 (protection stays the powerbox grant — this ADR adds
**no** permission mechanism) · the Files-model axiom (directory = meaning; the edge is metadata,
never namespace) · ADR-423 §7 item 2 (one-chain re-home stays deferred) · ADR-447 (the Skin/design-
system consumption contract is NOT taken here — named-deferred until 447 ratifies).

---

## 1. Context — three producers write the edge as content; the consumers need it as ledger

The provenance edge ("this was made from that") is produced deterministically in three places
today, all as *content*, none as *ledger*:

1. **ADR-395's upload derive** — `ExtractTextFromBlob` writes `.extracted.md` citing the raw via a
   `derived_from:` frontmatter line ([extract_text_from_blob.py:185](../../api/services/primitives/extract_text_from_blob.py#L185)).
   The raw upload write itself carries **no** `revision_kind='observation'` — a gap against
   ADR-423 D3's own discipline (an `inbound/` write, untagged).
2. **Studio artifacts** — every citation is a `data-ref` path in the artifact HTML
   ([projection.ts](../../web/components/workspace/viewers/projection.ts): living path + pin).
3. **The seat's derive acts** — prompt-instructed `derived_from:` frontmatter (MCP `remember`
   derivations, perception distillations — ADR-376 §9 list form).

The consumers that need the edge queryable: `trace`'s reverse walk (today an
`ilike '%derived_from%'` content scan — [mcp_composition.py:508](../../api/services/mcp_composition.py#L508),
the brittlest proxy left); the Files legibility register ("what was made from this?" — a dependents
count, a delete warning); and the design-system convention (post-ADR-447). ADR-423 §7 deferred the
column "until a deterministic derive step exists" — item 1 above **is** one, live since ADR-395.

## 2. The decision in one sentence

**`workspace_file_versions` gains a nullable `derived_from` column (a JSON list of absolute
workspace paths); `write_revision` accepts it as a parameter and — when absent — lifts it
deterministically from the two content conventions (head-anchored `derived_from:` frontmatter;
artifact `data-ref` attributes); the intake writers complete their tagging (upload raw =
`'observation'`, upload projection = the first live `'derivation'` writer); readers go
column-first/read-both; and a dependents query gives Files its "referenced by N" warning on
delete.**

## 3. Decisions

### D1 — The column: a JSON list of paths, written only when non-empty

Migration 215:

```sql
ALTER TABLE workspace_file_versions ADD COLUMN derived_from JSONB;
CREATE INDEX idx_wfv_derived_from ON workspace_file_versions
  USING GIN (derived_from jsonb_path_ops);
```

Entries are **absolute `/workspace/...` paths** — matching the live frontmatter convention (which
cites paths, not revision ids; ADR-423 §7's "revision-id(s)" sketch loses to the on-wire reality)
and the Studio `data-ref` (also a path; its revision pin stays in content as `data-ref-rev`).
Nullable, no default, **written only when non-empty** (the `revision_kind` precedent — byte-identical
for ordinary writes, safe against a not-yet-migrated DB). Edges are **historical facts about the
revision, not live foreign keys**: a later move/rename of a source does not rewrite the ledger; the
dependents query is best-effort over current paths (the same posture as `data-ref`'s dangling-path
fallback).

### D2 — `write_revision` threads the edge; an explicit edge defaults the kind to `'derivation'`

`write_revision(..., derived_from: Optional[List[str]] = None)`. Entries are normalized to
absolute `/workspace/` form and junk-filtered (a ref must contain a `/` — prose like
`derived_from: the meeting` never becomes an edge), deduplicated, capped. When the caller passes
edges explicitly and leaves `revision_kind` at its default, the kind becomes `'derivation'` — a
declared derive act. An explicit `revision_kind` always wins.

### D3 — The lift: the single write door reads the two content conventions

When no `derived_from` parameter is passed, `write_revision` lifts the edge from content,
deterministically, in one place (Singular Implementation — every door inherits it: `WriteFile`,
`EditFile`, `PATCH /api/workspace/file`, routes):

- **Frontmatter lift** (prose files): a `derived_from:` declaration within the **head** of the
  content (first ~12 lines — head-anchored so prose *about* the convention never grows edges),
  parsed by the same tolerant three-shape parser `trace` uses (bare scalar / inline list / block
  list). A frontmatter lift also defaults the kind to `'derivation'` — the convention's declared
  meaning. The parser **relocates** from `mcp_composition.py` to `authored_substrate.py` (the
  ledger owns its convention; `mcp_composition` imports it — no second parser).
- **Citation lift** (artifacts): for `.html` content, `data-ref="…"` attribute values become
  edges. The kind is **unchanged** — a citation is a reference edge, not a provenance class; a
  direct-edited artifact revision stays `'authored'` while still carrying its edges.

### D4 — The intake writers complete (the ADR-423 D3 gap closes)

- The upload **raw** write ([documents.py::process_document](../../api/services/documents.py))
  tags `revision_kind='observation'` — the writer ADR-423 D3 missed.
- The upload **projection** write (`ExtractTextFromBlob`) passes
  `derived_from=[raw_path]` + `revision_kind='derivation'` explicitly — **the first live
  `'derivation'` writer**, retiring the reserved-value-with-no-writer state.

### D5 — Readers go column-first, read-both

- `Revision` dataclass, `read_revision`, `list_revisions` select, and `handle_read_revision`
  surface `derived_from`.
- `trace`'s forward provenance walk reads the newest revision's column first, falling back to the
  content walk for legacy revisions (no backfill — read-both is the migration).
- `trace`'s reverse walk (`_find_derived_from_raw`) queries the column first (via the D6 dependents
  helper), keeping the content scan as the legacy fallback.

### D6 — The dependents query + the Files delete warning (the legibility register)

`authored_substrate.list_dependents(client, user_id, path)` — the files whose **head** revision
carries an edge to `path` (column containment via the GIN index, plus the content-scan fallback for
legacy heads, deduplicated). Served at `GET /api/workspace/file/dependents?path=…`. The Files
delete confirm consults it best-effort: when dependents exist, the dialog says so in macOS-plain
words ("N other files were made from this one…") — **a warning, never a block**; delete stays
trash-not-erase and the dependents keep working from history (the `data-ref` pin fallback).
Protection beyond a warning is the powerbox's job (ADR-434), not this ADR's.

### D7 — `WriteFile` carries the edge; "Learn from" is posture, not subsystem

The `WriteFile` primitive input + tool schema gain `derived_from` (list of workspace paths):
*"pass the source paths when authoring from a source — a Downloads arrival, a design system,
another file."* Posture guidance (tools_core) teaches derive-and-cite as a **parameter**, not only
a frontmatter convention — the seat's and lanes' derive acts become ledger-structural. The
operator-facing verb for the intake+derive flow is **"Learn from"** (the load-bearing-files note
§4); it ships as posture + parameter — no new primitive, no "Knowledge Acquisition" subsystem. The
Files-surface "Learn from this" button follows when a Files→chat seed mechanism exists
(named-deferred).

### D8 — Named-deferred (not taken here)

- **The design-system consumption contract** (Skin resolution + document-grain reference) — its
  own ADR, after ADR-447 ratifies.
- **One-chain re-home** (ADR-423 §7 item 2) and the ADR-286→ADR-384 D4 single-writer relaxation.
- **Repo/URL intake widening** for Learn-from (a one-shot URL fetch; a fetched repo archive) —
  additive intake writers when demanded; the upload lane covers PDF/PPT/docx today.
- **Backfill** of legacy frontmatter into columns — read-both makes it unnecessary; revisit only if
  the content-scan fallback ever costs.
- **Edge maintenance on MoveFile** — edges are historical; not rewritten.

## 4. Cascade / blast radius

- **Schema**: `supabase/migrations/215_adr448_derived_from.sql`.
- **Backend write**: `authored_substrate.py` (param + lift + parser relocation + `_insert_revision`
  row); `services/workspace.py` (`UserMemory.write` / `AgentWorkspace.write` pass-through);
  `primitives/workspace.py` (`WriteFile` schema + forward); `services/documents.py` (raw =
  observation); `primitives/extract_text_from_blob.py` (projection = derivation + explicit edge).
- **Backend read**: `authored_substrate.py` (`Revision` + selects + `list_dependents`);
  `mcp_composition.py` (column-first walks, parser import); `routes/workspace.py` (dependents
  endpoint).
- **FE**: `files/page.tsx` delete confirm (dependents line); `web/lib/api/client.ts` (dependents
  call). *(No edits to the in-flight `web/lib/workspace/{legibility,ownership}.ts` lane.)*
- **Canon**: this ADR; ADR-423 status banner (§7 items 1+4 landed); CLAUDE.md schema section;
  `api/prompts/CHANGELOG.md` (WriteFile tool-schema + posture change).
- **Gate**: `api/test_adr448_reference_edge.py` (structural, the ADR-423 harness style).

## 5. Why this shape

The alternative shapes were rejected in the note: a protected-folder class re-imports
permission-as-location one level up; a standalone ingestion subsystem stands up a second intake
beside the ledger; an edge table keyed on revision ids fights the live path-based convention and
the `data-ref` grain. One column on the one ledger, written at the one door, lifted from the
conventions that already exist — every producer keeps working, every consumer gets the same fact,
and the design system's "managed architecture" reduces to metadata the system already knows how to
render, warn on, and gate.
