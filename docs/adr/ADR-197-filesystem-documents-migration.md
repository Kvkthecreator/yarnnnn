# ADR-197: `filesystem_documents` → `/workspace/uploads/` Migration

> **Status**: Proposed (2026-04-19). **Not in scope for the current commit cycle.** Implementation sequenced as a future phased effort.
> **Date**: 2026-04-19
> **Authors**: KVK, Claude
> **Extends**: FOUNDATIONS v5.1 Axiom 0 (filesystem is the substrate), ADR-106 (Agent Workspace Architecture), ADR-142 (Unified Filesystem — the original-but-unimplemented specification)
> **Triggered by**: Axiom 0 audit of FOUNDATIONS v5.1 identified `filesystem_documents` + `filesystem_chunks` as a LIVE table pair holding semantic content (uploaded document text). Under singular-implementation discipline, this needs a migration plan to resolve.

---

## Context

### The current state

Uploaded documents flow today through a DB-native pair of tables:

- `filesystem_documents` — per-upload row with `user_id`, `filename`, `mime_type`, `status` (processing / indexed / failed), `metadata`. Written on upload.
- `filesystem_chunks` — one row per extracted text chunk, with `document_id`, `chunk_index`, `content`, `embedding`. Written during chunk processing.

**Writers:**
- `api/routes/documents.py:168` — INSERT into `filesystem_documents` on upload.
- `api/services/documents.py:201-278` — UPDATE status + INSERT chunks during processing.

**Readers:**
- `api/services/working_memory.py:249,275` — surfaces recent uploads into the YARNNN compact index (ADR-162 Sub-phase B).
- `api/services/context_inference.py:514,520` — reads document metadata + chunk content for context inference.
- `api/services/primitives/search.py:157–188` — `SearchEntities` document search reads both tables.
- `api/services/primitives/refs.py:290` — enriches document references with chunk content.
- `api/routes/documents.py:223,307,350,370` — list / get / download / delete endpoints.

**Purge references:** `api/routes/account.py:473,629` (cascade on account deletion).

### Why this is an Axiom 0 violation

Uploaded documents are **semantic content** — the extracted text, chunked and embedded, represents what the operator has shared with the workspace. Under Axiom 0, semantic content lives in the filesystem, not in DB rows.

### Why ADR-142 didn't fix it

ADR-142 (2026-03-25, Proposed) specified exactly this migration: uploads extract text → `/workspace/uploads/{filename}.md`, `filesystem_documents` + `filesystem_chunks` dissolve. The ADR is **Proposed, not Implemented.** No code writes to `/workspace/uploads/` today. The directory is aspirational — `routes/workspace.py:164` reads from it but always gets an empty listing.

ADR-197 picks up ADR-142's unfinished business, sharpens the migration plan with the Axiom 0 framing, and sequences it as a proper phased effort.

### Why NOT in the current commit cycle

Under singular-implementation discipline, migrating `filesystem_documents` requires touching five+ writer/reader sites *simultaneously* to avoid dual-write during the transition. Rushing this into the current Axiom 0 commit cycle (which is already doing the Reviewer-substrate + money-truth refactor + `user_memory` drop) would:

- Compress risk surface of a 5-site refactor into a single day.
- Mix it with table drops that have zero live dependents (the already-dead `user_memory` + never-queried `action_outcomes`), lowering reviewer attention on the riskier work.
- Produce a transitional dual-write state that violates the discipline we're trying to canonize.

Doing this correctly requires:

1. A phase that extends writers to *also* write to `/workspace/uploads/` (temporary dual-write, a deliberate discipline exception flagged up-front).
2. A phase that migrates readers one at a time, verifying each.
3. A phase that removes the original writes and drops the tables.

Each phase deserves its own commit cycle with its own validation gate. The total effort is ~3 phased cycles; compressing into one cycle exchanges quality for speed we don't need.

---

## Decision

### 1. Canonical home is `/workspace/uploads/{slug}.md`

Per ADR-142 and Axiom 0. One markdown file per uploaded document. File structure:

```markdown
---
# YAML frontmatter — document metadata
slug: acme-thesis-2026-04
original_filename: Acme Thesis 2026-04.pdf
mime_type: application/pdf
uploaded_at: 2026-04-18T14:22:05Z
uploaded_by: <user_id>
size_bytes: 184320
extraction_method: pdf-text-extract-v2
---

# Acme Thesis 2026-04

[Extracted document text here, preserving paragraph structure.
Chunks are NOT separate entities — the file IS the document.
Semantic search works over the file content directly.]
```

**Chunks become implicit.** `filesystem_chunks` dissolves entirely. Embeddings are computed per-paragraph (or per-section, whichever granularity search needs) and stored as file-level metadata or in a rebuilt search index, not as parallel rows.

### 2. Naming discipline

Uploaded document filename → slug via the existing slug convention used elsewhere (kebab-case, lowercased, suffixed with upload-date when collision). Preserves original filename in frontmatter for download.

### 3. Search substrate

`SearchEntities` for documents becomes `SearchFiles` scoped to `/workspace/uploads/` (per ADR-168's primitive matrix — file-layer search is an existing primitive). The embedding path needs a rebuilt index that points at file paths, not chunk-table rows. The index itself is a Axiom-0-permitted "audit ledger"–like construct (or could live as file-level metadata in a manifest); detailed in Phase 2.

### 4. Purge alignment

Account deletion cascades file deletion via `workspace_files` cleanup (already the pattern for all other filesystem state). The `user_memory`-style direct table purge becomes unnecessary.

---

## Phased plan (future cycles, not current)

### Phase 1 — Dual-write bridge (explicit exception)

**Scope:** extend upload pipeline to write to BOTH `filesystem_documents`/`filesystem_chunks` AND `/workspace/uploads/{slug}.md`. No readers migrate yet.

**Files touched:**
- `api/services/documents.py` — add workspace-file write alongside existing chunk inserts.
- `api/routes/documents.py` — no change (still returns DB rows for list/get).

**Status gate:** verify new uploads produce both representations; reconcile existing documents into filesystem via one-time backfill script.

**Singular-implementation caveat:** this phase is an explicit transient dual-write. The rest of the architecture operates on Axiom 0. This is the *one* exception; it must be narrow and short-lived.

### Phase 2 — Migrate readers

**Scope:** switch every reader from DB-backed reads to filesystem reads, one at a time, verifying each.

**Reader migration order** (least-risky first):
1. `context_inference.py` — new document reads flow from `/workspace/uploads/` via `ReadFile` primitive.
2. `working_memory.py` compact-index — switches to filesystem listing via `ListFiles`.
3. `primitives/search.py` — switches to `SearchFiles` scoped to uploads (requires file-layer embedding search — TBD).
4. `primitives/refs.py` document-ref enrichment — switches to file read.
5. `routes/documents.py` list/get endpoints — switch to filesystem.

Each reader migrates in its own commit with its own smoke-test.

### Phase 3 — Drop the bridge

**Scope:** remove the dual-write, drop the tables.

**Files touched:**
- `api/services/documents.py` — remove `filesystem_documents` + `filesystem_chunks` writes; keep only filesystem write.
- `api/routes/documents.py` — the download path now serves from S3/workspace storage directly (matches other artifacts).
- Migration: `DROP TABLE filesystem_chunks CASCADE; DROP TABLE filesystem_documents CASCADE;`
- `api/routes/account.py` — remove DB-cascade entries.

### Phase 4 — Canonize

**Scope:** Update ADR-142 status from Proposed → Superseded (by ADR-197 — Implemented). Update FOUNDATIONS revision history.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Notes |
|--------|--------|-------|
| **E-commerce** | Forward-helps | Brand guides, campaign-history documents, competitor-product PDFs all become first-class workspace-readable files. Same axioms as context domains already work with. |
| **Day trader** | Forward-helps | Strategy docs, trading journals, historical analysis PDFs become filesystem-native. AI Reviewer (ADR-194 v2) can natively read them. |
| **AI influencer** | Forward-helps | Content calendars, brand briefs, style guides become filesystem-native. |
| **International trader** | Forward-helps | Shipment manifests, compliance docs, counterparty records become filesystem-native. |

No domain hurt. All forward-help — aligns uploaded-documents substrate with how every other accumulated-context substrate works.

---

## Open questions (deferred to Phase 2)

1. **Embedding search substrate.** Today, semantic search over chunks uses pgvector on `filesystem_chunks.embedding`. Under v2, search is filesystem-backed. Options: pgvector over a compact `upload_embeddings` index table (Axiom 0 permitted as audit-ledger-like), or a manifest-based per-file embedding stored alongside the file. Defer decision to Phase 2 kickoff.
2. **Binary format preservation.** Do we retain original PDF/DOCX bytes, or only extracted text? Today DB stores no bytes (extraction is lossy + one-way). Under v2, we can preserve originals in S3 alongside the markdown. Defer.
3. **Large-document handling.** Current chunk model scales via row-level pagination. Filesystem scales differently (single-file reads). Ingesting a 500-page PDF as one file requires paging-on-read or section splitting. Defer to Phase 2.
4. **Context-inference pipeline changes.** `context_inference.py` operates per-chunk today. Migration path TBD — either work per-file or re-chunk at read time. Defer.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-19 | v1 — Initial draft. Sequenced as a future phased effort (Phase 1 dual-write bridge → Phase 2 reader migration → Phase 3 drop). Explicitly NOT in scope for the current commit cycle. Carries forward ADR-142's unfinished intent under FOUNDATIONS v5.1 Axiom 0. |
