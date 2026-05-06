# ADR-249: Two-Intent File Handling — Ephemeral vs Persistent

> **Status**: Implemented (2026-05-06) — all 5 phases complete, 13/13 test gate passing
> **Date**: 2026-05-06
> **Authors**: KVK, Claude
> **Supersedes**: ADR-197 (`filesystem_documents` → `/workspace/uploads/` migration — absorbed and extended here)
> **Supersedes**: ADR-142 (Unified Filesystem upload intent — never implemented, dissolved into this ADR)
> **Amends**: ADR-162 Sub-phase B (recent uploads compact index signal — rewritten)
> **Dimensional classification**: **Substrate** (primary) + **Channel** (ephemeral path) + **Mechanism** (extraction pipeline)

---

## Context

### The broken experience

When an operator drops a file into the chat, YARNNN processes it into `filesystem_chunks` rows (chunked, embedded) but never surfaces the content in its context window. The compact index shows `"2 recent uploads — consider offering to process"` — a weak hint that YARNNN frequently ignores. The operator's intent ("read this document") is not fulfilled.

The root cause is architectural: one upload pipeline (`POST /documents/upload`) tried to serve two fundamentally different intents and served neither well.

### The two intents that have been conflated

**Type A — Ephemeral/conversational:** The operator drops a file *into a message* to give YARNNN context for that exchange. "Here's the brief — summarise it." The file's scope is the conversation turn. It should never persist in the workspace. Once the message is sent, the file has served its purpose.

**Type B — Persistent/workspace:** The operator deliberately adds a file to the workspace as durable knowledge. "Here are our brand guidelines — reference these for all future work." This file should persist, be findable across sessions, be readable by headless agents during task execution, and be listed in the compact index as a first-class workspace member.

### Why the existing pipeline failed both

- **For ephemeral use**: every chat attachment got persisted to DB, chunked, and embedded — wasteful processing for a file that was only needed for one message.
- **For persistent use**: the file was chunked into DB rows that YARNNN never read. The content was available in `filesystem_chunks` for semantic search but never injected into YARNNN's context. YARNNN was aware of the filename but not the content.

### What the Anthropic Files API enables

Modern Claude API natively reads PDF and image files via `file_id` content blocks — no pre-extraction needed for supported types. The Files API accepts a binary upload, returns a `file_id`, and that ID can be passed directly in message content. The model reads the file natively (preserving layout, tables, embedded images). Files expire after 24 hours by default (configurable).

This is the correct path for ephemeral attachments: zero extraction overhead, lossless reading, native multimodal.

---

## Decisions

### D1: Two intent paths, clean separation

**Ephemeral path (Type A)** — chat attachments:
- Frontend sends file bytes to a new `POST /api/chat/attach` endpoint
- Backend uploads to Anthropic Files API → returns `file_id` + `filename` + `mime_type`
- `file_id` is passed in the message's content blocks to Claude API at send time
- Nothing written to DB, nothing written to workspace filesystem
- Supported types: images (JPEG, PNG, GIF, WEBP) + PDF + TXT/MD
- DOCX: server-side text extraction → passed as text block (Claude API does not support DOCX natively)
- Files expire via Anthropic's TTL (24h); no cleanup needed on our side

**Persistent path (Type B)** — workspace uploads:
- `POST /documents/upload` endpoint retained but pipeline rewritten
- Binary stored in Supabase Storage bucket `documents` (unchanged path: `{user_id}/{doc_id}/original.{ext}`)
- A pointer + content file written to `/workspace/uploads/{slug}.md` via `write_revision` (ADR-209 attribution: `authored_by="operator"`)
- File structure: YAML frontmatter (metadata) + extracted text body
- `workspace_files.embedding` populated at file level (one vector per document) for `SearchFiles` findability
- YARNNN sees it immediately in compact index via `ListFiles` — no separate uploads signal
- Supported types: PDF, DOCX, TXT, MD (images in follow-on ADR — see D6)

### D2: `/workspace/uploads/{slug}.md` file structure

```markdown
---
slug: acme-brand-guidelines-2026-04
original_filename: Acme Brand Guidelines 2026-04.pdf
mime_type: application/pdf
uploaded_at: 2026-05-06T14:22:05Z
size_bytes: 184320
storage_path: {user_id}/{doc_id}/original.pdf
word_count: 3420
extraction_method: pdf-pypdf2
---

# Acme Brand Guidelines 2026-04

[Full extracted text, paragraph structure preserved.
This is the content YARNNN reads via ReadFile.
No chunking — the file IS the document.]
```

**Chunks are eliminated.** `filesystem_chunks` dissolves entirely (D5). The workspace file is the single representation. Semantic search (`SearchFiles`) operates over `workspace_files.embedding` (file-level vector, written at upload time).

### D3: Compact index — "unread" signal replaces weak hint

`_get_recent_uploads_sync` is deleted. Replaced by `_get_workspace_uploads_sync` which lists files under `/workspace/uploads/` via `workspace_files`. The compact index entry changes from:

```
Recent uploads (2 in last 7 days) — consider offering to process via InferContext / InferWorkspace:
- report.pdf (uploaded 2026-05-03)
```

To:

```
Workspace uploads (2 files — content readable via ReadFile):
- /workspace/uploads/acme-brand-guidelines.md (3420 words, uploaded 2026-05-03)
- /workspace/uploads/q1-report.md (1820 words, uploaded 2026-05-01)
```

YARNNN now knows the content exists and exactly how to read it (`ReadFile(path="/workspace/uploads/acme-brand-guidelines.md")`). No "consider offering" ambiguity.

### D4: Download still works — pointer pattern

The `GET /documents/{id}/download` endpoint reads `storage_path` from the workspace file's YAML frontmatter instead of `filesystem_documents`. The Supabase Storage bucket `documents` is untouched. Binary originals are preserved.

Post-migration, the `/documents/{id}` path is replaced by workspace file paths. Frontend uses workspace file path as the identifier. The download endpoint is rewritten to accept a workspace file path and extract `storage_path` from frontmatter.

### D5: Full table drop — no legacy

`filesystem_chunks` — dropped entirely in Phase 4.
`filesystem_documents` — dropped entirely in Phase 4.
`get_document_with_stats` RPC — dropped in Phase 4.

No backwards-compat shims. Singular implementation.

### D6: Images in persistent path — follow-on ADR

Images (PNG/JPG/GIF/WEBP) as *persistent* workspace files are deferred. The correct representation is ambiguous: extracted text (OCR) loses visual content; storing a binary as a workspace file requires a different content type convention. A follow-on ADR will address this when the need surfaces in production. For now:
- Images in chat → ephemeral path (base64 inline, already working)
- Images uploaded via `/documents/upload` → rejected with clear error message: "Use chat to share images with YARNNN. Persistent image storage coming soon."

### D7: Existing documents — backfill migration script

A one-time backfill script (`api/scripts/migrate_documents_to_workspace.py`) reads all existing `filesystem_documents` rows, fetches chunk content, reconstructs full text, writes workspace files. Run once after Phase 3 deploy. Script deletes the source rows it migrates (atomic: write workspace file → delete DB row). Any row that fails migration is logged and left in DB for manual review.

---

## Phased implementation

### Phase 1 — Persistent path rewrite + compact index fix

**Scope:** Rewrite `process_document()` in `documents.py` to write `/workspace/uploads/{slug}.md` via `write_revision`. DB writes (to `filesystem_documents` status updates) retained as bridge. Compact index updated to `_get_workspace_uploads_sync`.

**Files touched:**
- `api/services/documents.py` — add workspace file write; keep DB status writes as bridge
- `api/services/working_memory.py` — replace `_get_recent_uploads_sync` + `_count_documents_sync` with `_get_workspace_uploads_sync`
- `api/prompts/CHANGELOG.md` — entry for compact index signal change

**Operator impact:** Immediate. New uploads are visible to YARNNN in the next chat turn. Old uploads invisible until backfill (Phase 4).

### Phase 2 — Ephemeral path

**Scope:** New `POST /api/chat/attach` endpoint. Frontend `useFileAttachments` wired to it for document drops. Images remain on existing base64 inline path (already working correctly).

**Files touched:**
- `api/routes/chat.py` — new `/chat/attach` endpoint (Anthropic Files API upload)
- `web/hooks/useFileAttachments.ts` — `uploadDocument()` → calls `/chat/attach`, stores `file_id` locally
- `web/lib/api/client.ts` — `api.chat.attach(file)` method
- `api/agents/yarnnn.py` / `api/routes/chat.py` — pass `file_id` blocks in message content

**Operator impact:** Chat document drops now work natively. YARNNN reads the file content in that turn.

### Phase 3 — Migrate readers

Reader migration order (least-risky first):

1. `working_memory.py` — already done in Phase 1
2. `context_inference.py` — `read_uploaded_documents()` rewritten to `ReadFile` from `/workspace/uploads/`
3. `primitives/refs.py` — `document:` ref enrichment reads workspace file instead of chunks
4. `primitives/search.py` — `SearchFiles(scope="uploads")` replaces chunk embedding search

Each reader migrated + smoke-tested before the next.

### Phase 4 — Drop the bridge (full singular implementation)

**Scope:** Remove all DB writes for documents. Drop tables. Remove purge cascade. Delete legacy types. Run backfill script.

**Files touched:**
- `api/services/documents.py` — remove `filesystem_documents`/`filesystem_chunks` writes; file is now the only write
- `api/routes/documents.py` — list/get endpoints rewritten to list workspace files; download reads frontmatter
- `api/routes/account.py` — remove `filesystem_documents` from purge cascade (workspace files purge via existing pattern)
- `api/scripts/purge_user_data.py` — remove `filesystem_documents` entry
- `api/scripts/verify_schema.py` — remove table references
- `supabase/migrations/NNN_drop_filesystem_documents_chunks.sql` — DROP TABLE both tables + RPC
- `web/types/index.ts` — delete `Document`, `DocumentDetail`, `DocumentUploadResponse`, `DocumentDownloadResponse`, `DocumentListResponse` types (replaced by workspace file types)
- `web/hooks/useDocuments.ts` — deleted entirely (functionality absorbed into workspace file primitives)
- `api/routes/documents.py` — `GET /documents` + `GET /documents/{id}` endpoints deleted; download endpoint rewritten
- `docs/adr/ADR-197-filesystem-documents-migration.md` — status updated to Superseded (by ADR-249)
- `docs/adr/ADR-142-unified-filesystem.md` — upload section marked Superseded (by ADR-249)

**Backfill:** Run `api/scripts/migrate_documents_to_workspace.py` against production.

### Phase 5 — Test gate + ADR flip

Test gate `api/test_adr249_two_intent_file_handling.py`:
- No live code references to `filesystem_documents` or `filesystem_chunks`
- No live code references to deleted primitives (`document:` ref enrichment via chunks)
- `/workspace/uploads/` listing returns uploaded files with word_count in frontmatter
- Compact index contains upload listing, not "consider offering" hint
- `/chat/attach` endpoint returns `file_id` for PDF
- `/chat/attach` endpoint returns extracted text block for DOCX
- Download endpoint reads `storage_path` from frontmatter (not DB)
- `useDocuments.ts` does not exist

ADR-249 → Implemented. ADR-197 → Superseded. ADR-142 upload section → Superseded.

---

## Writer/reader inventory

### Writers (before Phase 4)
| File | What it writes | Phase dropped |
|------|---------------|---------------|
| `api/services/documents.py` | `filesystem_documents` status + `filesystem_chunks` rows | Phase 4 |
| `api/routes/documents.py` | `filesystem_documents` insert on upload | Phase 4 |
| `api/routes/account.py` | Purge cascade | Phase 4 |
| `api/scripts/purge_user_data.py` | Admin purge | Phase 4 |

### Readers (before Phase 3)
| File | What it reads | Phase migrated |
|------|--------------|----------------|
| `api/services/working_memory.py` | `filesystem_documents` for upload listing | Phase 1 |
| `api/services/context_inference.py` | `filesystem_documents` + `filesystem_chunks` for inference | Phase 3 |
| `api/services/primitives/refs.py` | `filesystem_chunks` for `document:` ref enrichment | Phase 3 |
| `api/services/primitives/search.py` | `filesystem_chunks` for embedding search | Phase 3 |
| `api/routes/documents.py` | `filesystem_documents` for list/get/download | Phase 4 |

---

## What does NOT change

- Supabase Storage bucket `documents` — binary originals stay where they are
- Image handling in chat (base64 inline) — already correct, untouched
- `POST /share` endpoint (ADR-127) — writes to `/user_shared/`, unrelated
- `write_revision` / authored substrate (ADR-209) — used as-is for all workspace file writes
- `workspace_files` table and `workspace_files.embedding` column — used as-is

---

## Revision history

| Date | Change |
|------|--------|
| 2026-05-06 | v1 — Initial draft. Supersedes ADR-197 + ADR-142 upload section. Four-phase implementation plan. Full table drop committed (no legacy). |
