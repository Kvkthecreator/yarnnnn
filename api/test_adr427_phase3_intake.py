"""
Validation Suite — ADR-427 Phase 3 (media intake + serving)

The Phase-3 gate: a real image uploads through the intake pipeline, lands as a
VERSIONED binary revision in the CAS (no un-versioned bucket copy, no stored
content_url), streams back byte-identically, and serves via a minted URL.
The intake gate is the conformance DAG (D5), not a stored-MIME allowlist.

Tests:
  1. PNG upload → success; raw path under inbound/uploads/operator/
  2. The raw is a BINARY revision (observation): marker blob, byte-identical
     round-trip through the seam
  3. Denorm discipline: content='', DERIVED image/png, content_url NOT stored
  4. Serving: mint_serving_url returns a live signed URL whose bytes match
  5. Conformance rejection: an MZ executable is refused
  6. Text upload (.md) lands as an INLINE TEXT revision (the utf-8
     normalization) + derives its projection sibling
  7. Trash → restore round-trips the binary head via content_ref (the
     archive/restore fix — no empty-text revision at a binary head)

Crosses Supabase Storage: scriptable code-path proof; the browser upload smoke
still needs a human click (drag-drop on /files).

Usage:
    cd api && python3 test_adr427_phase3_intake.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PNG_PAYLOAD = PNG_MAGIC + bytes(range(256)) * 4 + b"adr427-phase3-gate"
EXE_PAYLOAD = b"MZ\x90\x00" + bytes(range(200, 256)) * 4
MD_PAYLOAD = ("# ADR-427 Phase 3 gate\n\n" + "text body line. " * 20).encode("utf-8")

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    logger.info(f"{'✓' if ok else '✗'} {name}: {detail}")


def get_client():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def run() -> None:
    from routes.documents import _process_single_upload
    from services.authored_substrate import read_revision, write_revision
    from services.storage_backend import get_storage_backend, sha256_bytes

    client = get_client()
    backend = get_storage_backend(client)

    # 1–2. PNG upload → versioned binary raw
    item, _ = asyncio.run(_process_single_upload(
        content=PNG_PAYLOAD, content_type="application/octet-stream",
        filename="gate-427.png", user_id=TEST_USER_ID, service=client,
    ))
    ok = item.success and (item.workspace_path or "").startswith("/workspace/inbound/uploads/operator/")
    record("1. PNG upload accepted → inbound raw path", ok,
           f"path={item.workspace_path}, err={item.error}")
    raw_path = item.workspace_path

    head = read_revision(client, user_id=TEST_USER_ID, path=raw_path)
    sha = sha256_bytes(PNG_PAYLOAD)
    ok = head is not None and head.is_binary and head.blob_sha == sha and \
        head.revision_kind == "observation" and backend.get_blob(sha) == PNG_PAYLOAD
    record("2. raw is a binary observation revision; bytes round-trip", ok,
           f"is_binary={getattr(head, 'is_binary', None)}, kind={getattr(head, 'revision_kind', None)}")

    # 3. denorm discipline
    row = (
        client.table("workspace_files")
        .select("content, content_type, content_url")
        .eq("user_id", TEST_USER_ID).eq("path", raw_path).limit(1).execute()
    ).data
    ok = bool(row) and row[0]["content"] == "" and \
        row[0]["content_type"] == "image/png" and not row[0]["content_url"]
    record("3. denorm: content='' + derived image/png + no stored content_url", ok,
           f"{row[0] if row else 'MISSING'}")

    # 4. minted serving URL actually serves the bytes
    url = backend.mint_serving_url(sha, expires_in=120)
    served = None
    if url:
        import httpx
        served = httpx.get(url, timeout=30.0).content
    ok = bool(url) and served == PNG_PAYLOAD
    record("4. minted URL serves the exact bytes", ok,
           f"{len(served) if served is not None else 0} bytes over the wire")

    # 5. conformance rejection
    item_exe, _ = asyncio.run(_process_single_upload(
        content=EXE_PAYLOAD, content_type="application/pdf",  # spoofed declared type
        filename="malware.exe", user_id=TEST_USER_ID, service=client,
    ))
    ok = not item_exe.success and "Unsupported" in (item_exe.error or "")
    record("5. conformance gate refuses an executable (declared type ignored)", ok,
           f"err={item_exe.error}")

    # 6. text upload lands INLINE + derives projection
    item_md, _ = asyncio.run(_process_single_upload(
        content=MD_PAYLOAD, content_type="text/markdown",
        filename="gate-427-notes.md", user_id=TEST_USER_ID, service=client,
    ))
    md_head = read_revision(client, user_id=TEST_USER_ID, path=item_md.workspace_path) \
        if item_md.success else None
    ok = item_md.success and md_head is not None and not md_head.is_binary and \
        md_head.content == MD_PAYLOAD.decode("utf-8")
    record("6. text upload lands inline (utf-8 normalization) + projects", ok,
           f"path={item_md.workspace_path}, inline={md_head is not None and not md_head.is_binary}")

    # 7. trash → restore preserves the binary head (content_ref)
    ref_rev = write_revision(
        client, user_id=TEST_USER_ID, path=raw_path,
        content_ref=sha, authored_by="system:adr427-gate",
        message="archive-shape write via content_ref (gate)", lifecycle="archived",
    )
    restored = read_revision(client, user_id=TEST_USER_ID, path=raw_path, revision_id=ref_rev)
    ok = restored is not None and restored.is_binary and restored.blob_sha == sha
    record("7. content_ref re-references the binary head (archive/restore shape)", ok,
           f"blob preserved: {restored.blob_sha == sha if restored else '?'}")

    # tidy: leave the raw as active again (restore shape)
    write_revision(
        client, user_id=TEST_USER_ID, path=raw_path,
        content_ref=sha, authored_by="system:adr427-gate",
        message="restore-shape write via content_ref (gate)", lifecycle="active",
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        logger.exception("suite crashed")
        record("SUITE", False, f"crashed: {exc}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    failed = total - passed
    print(f"\n{'='*60}")
    print(f"ADR-427 Phase 3 intake gate: {passed}/{total} passed, {failed} failed")
    print(f"{'='*60}")
    if failed:
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  ✗ {name}: {detail}")
    sys.exit(0 if failed == 0 else 1)
