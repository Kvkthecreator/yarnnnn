# ADR-427 Phase 3 — end-to-end upload smoke (deployed API)

**Date**: 2026-07-20 · **Deploy**: `dep-d9es24a8qa3s73etq910` (commit `e88841b`), status `live`
**Method**: a real 4,898-byte PNG (valid IHDR/IDAT/IEND, not a magic-byte stub) driven through
the **deployed** `https://yarnnn-api.onrender.com` with a **real user JWT** (magic-link →
`verify_otp`), i.e. the same HTTP path and auth the browser uses — not the local venv, not the
service key.

## Results — 7/7

| # | Check | Result |
|---|---|---|
| 1 | `POST /api/documents/upload` (multipart, `image/png`) | ✅ `succeeded:1` → `/workspace/inbound/uploads/operator/smoke-427.png` |
| 2 | `GET /api/workspace/file` derives the type + mints a capability | ✅ `content_type: image/png`, denorm `content: None`, `content_url` = signed **`/workspace-cas/`** URL with `token=` (D4 minted-never-stored) |
| 3 | Minted URL serves the bytes | ✅ HTTP 200, 4,898 bytes, **sha256 byte-identical** to the uploaded file, valid PNG header |
| 4 | HTTP Range read over the wire (D2a) | ✅ `Range: bytes=0-7` → `8950 4e47 0d0a 1a0a` (exactly the PNG signature) |
| 5 | Trash → Restore round-trip (**the corruption class this arc fixed**) | ✅ both 200; after restore the re-minted URL still serves **byte-identical** bytes — no empty-TEXT revision at the binary head |
| 6 | Revision chain / ledger | ✅ 3 revisions, parent-pointers intact: `upload` (**kind=observation**) → `Archived by operator` → `Restored from trash`; head `is_binary=True`, `byte_size=4898`; **origin blob == head blob** (restore preserved the blob, did not re-write it) |
| 7 | Live-row discipline | ✅ `content=''`, `content_type='image/png'` (derived), `content_url=NULL` (never stored) |

Cleanup: both smoke files trashed via the API. Gates re-run after: seam 9/9 · phase2 12/12 ·
phase3 7/7 · reader ratchet PASS.

## What this closes and what it does not

**Closes** the honest gap the code-path gates could not: the Supabase config layer (the
`workspace-cas` bucket exists, is private, accepts the object, and signs a working URL) and the
real request path (multipart parsing, user-JWT auth, the powerbox read-scope consult, minting).
This is the class of failure migration 217 taught us only a real request finds.

**Does not close**: the *visual* browser confirmation — a human dragging a file onto `/files`
and seeing the thumbnail paint in the surface. Everything server-side of that is now proven;
what remains unproven is the FE render of a binary file row.
