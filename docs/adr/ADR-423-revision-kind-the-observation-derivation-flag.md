# ADR-423: `revision_kind` — Provenance as a Flag on the Ledger (the Tag-in-Place Fold)

**Status**: Accepted (2026-07-08, operator-ruled scope "tag-in-place, thin"; **reframed 2026-07-09** by [the Files-model note](../analysis/the-files-model-directory-is-meaning-everything-else-is-metadata-2026-07-08.md) §5). The first buildable step of ADR-384 D3 (provenance is a revision-kind, not a namespace). Additive schema (migration 208) + a `revision_kind` column threaded through the write path and the three intake writers + `trace`/`ListRevisions` reading the column instead of scanning paths and content. **Does NOT** re-home raw into the meaning-file's chain, make `derived_from` a column, or build a derive step — those are the deferred second pass (§7).
> **Reframe (2026-07-09):** the *purpose* of `revision_kind='observation'` is not the (absent) observation-vs-derivation distinction — it is the **arrival badge** that lets the two raw lanes (`uploads/` + `inbound/`) unify under one **`Downloads/`** anchor and lets the `inbound/` *directory* dissolve (the Files-model note §3a/§5, the Finder-vocabulary target). This ADR ships the *mechanism*; the operator-facing `Downloads/` unification is the visible proof, landed in the tree-reshape pass (note §6 step 3). The technical decisions below are unchanged — only the headline *why* is now the category move, not a future derive step.
**Date**: 2026-07-08
**Dimension**: Substrate (Axiom 1 — *how* state's provenance is carried: on the revision, not the path)
**Relates to**: ADR-209 (the authored substrate + `write_revision` single write path + `workspace_file_versions` chain this extends), ADR-376 / FOUNDATIONS DP32 (the ledger-intake invariant `retain + attribute + cite` — this implements the mechanism its ⚠-banner already promised), ADR-384 D3 (provenance is a `revision_kind`, not the `inbound/` lane — this is its §7-step-2/4 buildable slice), ADR-393 (`193_adr393_capture_kind.sql` — the additive-discriminator-column-with-default pattern this copies), ADR-368 (the memory verbs + `trace`, the primary reader)
**Amends**: ADR-376 (its `inbound/`-as-namespace mechanism begins folding to the column its own banner names as "the separate mode"), ADR-384 (implements D3's buildable half at tag granularity), FOUNDATIONS DP32 (the `retain + attribute + cite` mechanism gains its column carrier — invariant unchanged)
**Preserves**: ADR-209 (no new write path — `revision_kind` is one more optional field on `write_revision`; raw and derived stay ordinary attributed revisions), ADR-286 (single-writer-per-path — untouched; raw stays where it lands), the `inbound/` paths themselves (nothing moves this pass), every non-intake `write_revision` caller (they keep the default `'authored'`)

---

## 1. Context — the invariant is live, the mechanism is path-and-string

ADR-376 (DP32) ratified the ledger-intake invariant: every contribution enters
as an attributed **raw observation**; what the workspace derives from it is a
separate attributed **derived act**; the raw is never rewritten and the derived
cites its source (`retain + attribute + cite`). ADR-384 D3 then ruled that the
raw-vs-derived distinction is **a property of a revision, not a location** — it
should be a `revision_kind` flag on the one ledger (`workspace_file_versions`),
not the separate `inbound/` namespace. ADR-376's own status banner already names
the implementation: *"the `revision_kind` (`observation` | `derivation`) columns
are the separate mode."*

Today (recon receipts, 2026-07-08) the distinction is reconstructed **without a
column**:

- **By path prefix** — `trace` treats anything under `inbound/` as raw
  (`if f"/{INBOUND_ROOT}" in path`, [`mcp_composition.py:968`](../../api/services/mcp_composition.py#L968)).
- **By content frontmatter** — "derived" is detected by string-scanning file
  content for a `derived_from:` line
  (`_extract_derived_from_list`, [`mcp_composition.py:415`](../../api/services/mcp_composition.py#L415);
  `_find_derived_from_raw` does an `ilike '%derived_from%'` scan,
  [`mcp_composition.py:508`](../../api/services/mcp_composition.py#L508)).

Both signals are brittle proxies for a fact the ledger should carry directly.
`derived_from` is **not** a column — it is a text convention inside file content.
And for the MCP `remember` lane specifically, **no live code produces a derived
file at all** — the "derive-and-cite" step is an LLM prompt contract, never
deterministic code (the raw lands via `WriteFile`, the seat is *instructed* to
derive when it wakes).

## 2. The decision in one sentence

**Provenance-kind becomes a column on the revision chain: `write_revision`
gains an optional `revision_kind` field; the three intake writers tag their
writes `'observation'`; everything else keeps the default `'authored'`; and
`trace`/`ListRevisions` read the column instead of scanning paths and content —
tagging what is already written where it already lands, not re-homing it.**

This is the **tag-in-place** reading of ADR-384 D3 (operator ruling,
2026-07-08). It ships the ledger substrate the re-founding needs and unblocks
the Files-surface "immutable raw" affordance (ADR-422 D2), while honestly
leaving the observation-and-derivation-in-one-chain collapse for when the derive
step is real code (§7).

## 3. Decisions

### D1 — `revision_kind` is an additive column with a legacy-safe default

Migration 208 copies the ADR-393 pattern
([`193_adr393_capture_kind.sql`](../../supabase/migrations/193_adr393_capture_kind.sql)):

```sql
ALTER TABLE workspace_file_versions
  ADD COLUMN revision_kind TEXT NOT NULL DEFAULT 'authored';
```

The value set is `'authored'` (the default — an ordinary attributed revision) ·
`'observation'` (a retained raw intake, immutable-by-intent) · `'derivation'`
(a derived act citing an observation; **reserved**, written by no live code this
pass — see §7). `NULL`/absent is impossible (NOT NULL DEFAULT), and every
existing revision reads as `'authored'` — **no backfill.** A partial index on
`revision_kind` is deferred until a query needs it (none do yet).

### D2 — The write-path threads one optional field

`write_revision` ([`authored_substrate.py:433`](../../api/services/authored_substrate.py#L433))
gains `revision_kind: str = 'authored'`, passed to `_insert_revision`
([`authored_substrate.py:299`](../../api/services/authored_substrate.py#L299),
one line in the `row` dict — the exact `workspace_id` precedent). This is the
**entire** column-plumbing surface. The ~40 existing callers are untouched (they
take the default).

The tombstone write in `delete_live_file`
([`authored_substrate.py:661`](../../api/services/authored_substrate.py#L661))
inherits `'authored'` — a delete is not an observation; deliberate, not an
oversight.

### D3 — Exactly three intake writers tag `'observation'`

The minimal writer set (recon-confirmed) — none call `write_revision` directly:

1. **MCP `remember`** → `inbound/mcp/{client}/` via
   `dispatch_remember_this` → `WriteFile` → `UserMemory.write` → `write_revision`.
   `revision_kind='observation'` must thread through the `WriteFile` primitive
   input and `UserMemory.write` (the two intermediary hops — the one real
   plumbing cost this pass).
2. **`CaptureConnector` / `SyncPlatformState`** → `inbound/{platform}/…`
   ([`capture_connector.py`](../../api/services/primitives/capture_connector.py),
   [`sync_platform_state.py`](../../api/services/primitives/sync_platform_state.py)).
   *(Dormant behind `CONNECTOR_CAPTURE_ENABLED` per ADR-404 — tagged anyway so it
   is correct when the lane re-lights; a dormant writer left untagged is a
   future bug.)*
3. **`TrackWebSources`** → `inbound/web/{source}/…`
   ([`track_web_sources.py`](../../api/services/primitives/track_web_sources.py)),
   `system:track-web-sources`.

The tagging discipline: **a write into `inbound/` is `'observation'`.** The path
and the kind agree by construction this pass (which is what makes the fold safe —
we are naming a fact the path already asserts, not moving anything).

### D4 — The readers consult the column

- `list_revisions` ([`authored_substrate.py:706`](../../api/services/authored_substrate.py#L706))
  adds `revision_kind` to its `.select(...)` — one line; the handler
  ([`revisions.py:197`](../../api/services/primitives/revisions.py#L197)) forwards
  dicts verbatim, so callers get the field with no handler change. The `Revision`
  dataclass + `read_revision` + `handle_read_revision` add the field for the
  read-single path (3 touch-points).
- `trace` (`compose_trace`, [`mcp_composition.py:923`](../../api/services/mcp_composition.py#L923))
  populates each history entry's kind **from the column** rather than inferring
  `raw_source: True` from `inbound/` path membership
  ([`mcp_composition.py:968`](../../api/services/mcp_composition.py#L968)). The
  content-scanning `derived_from` walk (lines 1006–1048) is **preserved this
  pass** — `derived_from` is still a frontmatter convention (§7), so `trace`'s
  provenance walk keeps reading it; only the observation/derivation *kind* signal
  moves from path/content to column. This keeps `trace` behavior byte-identical
  while removing its brittlest proxy (the path-prefix test).

## 4. What this does NOT do (the deferred second pass)

- **No `derived_from` column.** It stays a content-frontmatter convention
  (`_extract_derived_from_list`). Promoting it to a column is net-new schema
  *plus* a migration of the existing convention — scoped separately (§7).
- **No re-homing of raw into the meaning-file's chain.** Observation and
  derivation stay **separate files with separate chains**, linked by the
  `derived_from` content string — exactly as today. ADR-384 D3's worked example
  (`the-acme-deal/…` with `rev1 [observation] … rev4 [derivation]` in *one*
  chain) is the **second pass**, not this one. Tag-in-place tags where raw
  already lands.
- **No derive step.** For MCP `remember`, none exists (prompt-only). This ADR
  does not build one; `'derivation'` is a reserved value awaiting it.
- **No single-writer relaxation.** ADR-286 is untouched — because nothing moves
  into a shared chain, the multi-principal same-path merge (ADR-384 D4) is not
  triggered here. That coupling belongs to the second pass.
- **No FE change.** ADR-422 D2 reads `inbound/` membership (a path fact, still
  true) for its immutability affordance — it does not depend on this column. When
  the second pass re-homes raw, ADR-422's carve re-points to `revision_kind`.

## 5. Cascade / blast radius

- **Schema**: `supabase/migrations/208_adr423_revision_kind.sql` (one additive
  column, default `'authored'`, no backfill).
- **Backend write**: `authored_substrate.py` (`write_revision` + `_insert_revision`);
  `services/workspace.py` (`UserMemory.write`/`AgentWorkspace.write` pass-through);
  `primitives/workspace.py` (`handle_write_file` accepts + forwards `revision_kind`);
  `mcp_composition.py::dispatch_remember_this` (tag `'observation'`);
  `capture_connector.py` / `sync_platform_state.py` / `track_web_sources.py` (tag).
- **Backend read**: `authored_substrate.py` (`list_revisions` `.select` + `Revision`
  dataclass + `read_revision`); `primitives/revisions.py` (`handle_read_revision`
  dict); `mcp_composition.py::compose_trace` (kind from column, drop the
  path-prefix proxy).
- **Canon**: this ADR; ADR-376 status-banner note (mechanism fold begun);
  FOUNDATIONS DP32 (the column carrier); CLAUDE.md schema section
  (`workspace_file_versions` gains `revision_kind`).
- **Gate**: `api/test_adr423_revision_kind.py` — assert the three intake writers
  produce `revision_kind='observation'`; a default `WriteFile` produces
  `'authored'`; `list_revisions`/`trace` return the field; a legacy revision (no
  column value simulated) reads `'authored'`; `trace` output byte-identical to
  pre-change on a fixture chain (the path-proxy removal is behavior-preserving).

## 6. Why tag-in-place is the honest first pass

The full fold (ADR-384 D3's one-chain form) is *more* faithful to canon, but a
material part of it **cannot ship today**: the derive step for MCP `remember` is
prompt-only, so "author a `'derivation'` revision citing the observation" has no
deterministic code to write it. Building the column now — and having the raw
lane, `trace`, and `ListRevisions` all speak `revision_kind` — lays the ledger
substrate every later step reads, at near-zero risk (additive column, default
preserves all behavior, three writers tagged, one brittle path-proxy retired).
When the derive step becomes real code (its own ADR), the second pass re-homes
raw into the meaning-file chain and promotes `derived_from` to a column against a
ledger that already carries the kind. This is the ADR-384 sequencing discipline
(§7: cheapest-and-safest first, the unscriptable step named and deferred) applied
one level down.

## 7. The deferred second pass (named, not built)

When a deterministic derive step exists:

1. Promote `derived_from` from frontmatter convention → a column on
   `workspace_file_versions` (referencing the observation revision-id(s)), with a
   read-both migration for the existing convention.
2. Re-home raw so observation + derivation are revisions of the **same**
   meaning-file (ADR-384 D3 literal form) — this triggers the ADR-286→ADR-384 D4
   single-writer relaxation and the steward-seat merge.
3. Re-point ADR-422 D2's `inbound/`-membership carve to `revision_kind ==
   'observation'`.
4. `trace`'s content-scanning `derived_from` walk (retained in D4) retires in
   favor of the column.

Each is its own commit with its own gate; none is required for this pass to be
correct and useful.
