"""
ADR-249: Two-Intent File Handling — Test Gate

Verifies:
1. No live code references to filesystem_documents or filesystem_chunks
2. No live code references to deleted types (Document, DocumentUploadResponse, etc.)
3. documents.py uses write_revision (workspace path) not chunk inserts
4. working_memory uses workspace_files for upload listing
5. context_inference reads from workspace_files
6. primitives/refs.py uses workspace_files for document enrichment
7. primitives/search.py uses workspace_files for document search
8. useDocuments.ts does not exist
9. FileAttachment + /chat/attach endpoint exist in chat.py
10. Migration 166 drops both tables
11. ADR-249 exists and is under docs/adr/
"""

import os
import re
import ast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_ROOT = os.path.join(ROOT, "api")
WEB_ROOT = os.path.join(ROOT, "web")


def read(path):
    with open(path) as f:
        return f.read()


def grep_live_code(pattern: str, extensions=(".py",), exclude_dirs=("venv", "__pycache__", "test_adr249")):
    """Search live code (not tests, not venv) for pattern."""
    matches = []
    for dirpath, dirnames, filenames in os.walk(API_ROOT):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fname in filenames:
            if not any(fname.endswith(e) for e in extensions):
                continue
            if "test_adr249" in fname:
                continue
            fpath = os.path.join(dirpath, fname)
            content = read(fpath)
            if re.search(pattern, content):
                matches.append(fpath.replace(ROOT + "/", ""))
    return matches


def grep_web(pattern: str, extensions=(".ts", ".tsx")):
    matches = []
    for dirpath, dirnames, filenames in os.walk(WEB_ROOT):
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".next")]
        for fname in filenames:
            if not any(fname.endswith(e) for e in extensions):
                continue
            fpath = os.path.join(dirpath, fname)
            content = read(fpath)
            if re.search(pattern, content):
                matches.append(fpath.replace(ROOT + "/", ""))
    return matches


failures = []


def check(desc, condition, detail=""):
    if not condition:
        failures.append(f"FAIL: {desc}" + (f"\n      {detail}" for _ in [1]).__next__() if detail else f"FAIL: {desc}")
        print(f"  ✗ {desc}")
        if detail:
            print(f"      {detail}")
    else:
        print(f"  ✓ {desc}")


print("\n=== ADR-249 Test Gate ===\n")

# 1. No live Python code references filesystem_documents
hits = grep_live_code(r'table\(["\']filesystem_documents["\']')
check(
    "No live .table('filesystem_documents') calls in api/",
    len(hits) == 0,
    f"Found in: {hits}" if hits else "",
)

# 2. No live Python code references filesystem_chunks
hits = grep_live_code(r'table\(["\']filesystem_chunks["\']')
check(
    "No live .table('filesystem_chunks') calls in api/",
    len(hits) == 0,
    f"Found in: {hits}" if hits else "",
)

# 3. documents.py uses write_revision
doc_service = read(os.path.join(API_ROOT, "services", "documents.py"))
check(
    "services/documents.py calls write_revision",
    "write_revision" in doc_service,
)
check(
    "services/documents.py does not insert into filesystem_chunks",
    '.table("filesystem_chunks")' not in doc_service and ".table('filesystem_chunks')" not in doc_service,
)

# 4. working_memory reads workspace_files for uploads
wm = read(os.path.join(API_ROOT, "services", "working_memory.py"))
check(
    "working_memory._get_workspace_uploads_sync reads workspace_files",
    "_get_workspace_uploads_sync" in wm and "workspace_files" in wm,
)
check(
    "working_memory compact index says 'read via ReadFile' not 'consider offering'",
    "read via ReadFile" in wm,
)
check(
    "working_memory does not read filesystem_documents for uploads",
    "filesystem_documents" not in wm,
)

# 5. context_inference reads workspace_files
ci = read(os.path.join(API_ROOT, "services", "context_inference.py"))
check(
    "context_inference.read_uploaded_documents reads workspace_files",
    "workspace_files" in ci and "filesystem_chunks" not in ci,
)

# 6. primitives/refs.py uses workspace_files
refs = read(os.path.join(API_ROOT, "services", "primitives", "refs.py"))
check(
    "primitives/refs.py document enrichment reads workspace_files not filesystem_chunks",
    "workspace_files" in refs and "filesystem_chunks" not in refs,
)

# 7. primitives/search.py uses workspace_files
search = read(os.path.join(API_ROOT, "services", "primitives", "search.py"))
check(
    "primitives/search.py document search uses workspace_files not filesystem_chunks",
    "workspace_files" in search and "filesystem_chunks" not in search,
)

# 8. useDocuments.ts does not exist
use_docs_path = os.path.join(WEB_ROOT, "hooks", "useDocuments.ts")
check(
    "web/hooks/useDocuments.ts does not exist",
    not os.path.exists(use_docs_path),
)

# 9. FileAttachment and /chat/attach endpoint exist in chat.py
chat = read(os.path.join(API_ROOT, "routes", "chat.py"))
check(
    "chat.py defines FileAttachment model",
    "class FileAttachment" in chat,
)
check(
    "chat.py defines /chat/attach endpoint",
    '"/chat/attach"' in chat or "chat/attach" in chat,
)
check(
    "chat.py passes file_attachments to Claude API as document blocks",
    "file_id" in chat and '"document"' in chat,
)

# 10. Migration 166 drops both tables
migration = read(os.path.join(ROOT, "supabase", "migrations", "166_drop_filesystem_documents_chunks.sql"))
check(
    "Migration 166 drops filesystem_chunks",
    "DROP TABLE" in migration and "filesystem_chunks" in migration,
)
check(
    "Migration 166 drops filesystem_documents",
    "DROP TABLE" in migration and "filesystem_documents" in migration,
)

# 11. ADR-249 exists
adr_path = os.path.join(ROOT, "docs", "adr", "ADR-249-two-intent-file-handling.md")
check(
    "ADR-249-two-intent-file-handling.md exists",
    os.path.exists(adr_path),
)

# 12. No web references to deleted Document types (excluding WorkspaceUpload, DocumentDownload which are new)
hits = grep_web(r'\bDocumentUploadResponse\b|\bDocumentListResponse\b|\bDocumentDetail\b')
check(
    "No web references to deleted Document* types",
    len(hits) == 0,
    f"Found in: {hits}" if hits else "",
)

# 13. account.py does not purge filesystem_documents
account = read(os.path.join(API_ROOT, "routes", "account.py"))
check(
    "account.py does not call _delete_rows for filesystem_documents",
    '_delete_rows(client, "filesystem_documents"' not in account,
)

print(f"\n{'='*40}")
if failures:
    print(f"\n{len(failures)} FAILURE(S):\n")
    for f in failures:
        print(f"  {f}")
    raise SystemExit(1)
else:
    print(f"\n13/13 assertions passed. ADR-249 singular implementation confirmed.\n")
