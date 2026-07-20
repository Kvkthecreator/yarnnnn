"""
Validation Suite — ADR-427 Phase 2 (binary as a Category-1 revision)

The Phase-2 gate: a binary revision round-trips through the chain (trace) and
revert, with attribution, parent-pointers, CAS dedup, derived type (D5), no
stored capability (D4), and the tombstone fix.

Tests:
  1. Migration 219 landed: storage_key + byte_size columns exist
  2. write_revision(content_bytes=...) writes a binary revision
  3. The blob is a MARKER ROW: content='', storage_key=cas/<sha[:2]>/<sha>,
     byte_size = len(bytes)
  4. Bytes round-trip through the seam (get_blob == original; range read slices)
  5. workspace_files denorm: content='' (Category-2, text-only), content_type
     DERIVED from magic bytes (D5), content_url NOT stored (D4)
  6. A second binary revision parent-points at the first (trace)
  7. read_revision surfaces is_binary=True, content=None, byte_size
  8. Revert-as-write: re-writing rev-1's bytes makes head blob_sha == rev-1's
     sha (CAS dedup — no third blob)
  9. mint_serving_url returns a signed URL for binary, None for inline text
 10. delete_live_file tombstone carries the head's BINARY blob_sha (not the
     empty-string hash — the Phase-2 tombstone fix)
 11. Validation: content AND content_bytes → ValueError; neither → ValueError
 12. The text path is unchanged (inline content, is_binary=False)

Strategy: real DB + real workspace-cas bucket via service key, scratch paths.
Crosses Supabase Storage — this is the scriptable code-path proof; the UI
upload smoke (Phase 3) still needs a human click.

Usage:
    cd api && python3 test_adr427_phase2_binary.py
"""

from __future__ import annotations

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
logger = logging.getLogger(__name__)

TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
BIN_PATH = "/agents/_adr427-phase2-test/scratch.png"
TXT_PATH = "/agents/_adr427-phase2-test/scratch.md"
DEL_PATH = "/agents/_adr427-phase2-test/tombstone.png"

# Deterministic non-utf8 payloads with a real PNG magic (D5 derivation target).
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PAYLOAD_1 = PNG_MAGIC + bytes(range(256)) * 8
PAYLOAD_2 = PNG_MAGIC + bytes(reversed(range(256))) * 8

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    logger.info(f"{'✓' if ok else '✗'} {name}: {detail}")


def get_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL + SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


def cleanup(client) -> None:
    """Remove prior runs' scratch rows (revisions + live rows) so the chain
    assertions are deterministic. Blobs are CAS — left in place (dedup makes
    re-runs re-reference them)."""
    for p in (BIN_PATH, TXT_PATH, DEL_PATH):
        client.table("workspace_file_versions").delete().eq(
            "user_id", TEST_USER_ID
        ).eq("path", p).execute()
        client.table("workspace_files").delete().eq(
            "user_id", TEST_USER_ID
        ).eq("path", p).execute()


def run() -> None:
    from services.authored_substrate import (
        delete_live_file,
        list_revisions,
        read_revision,
        write_revision,
    )
    from services.storage_backend import (
        ByteRange,
        cas_key,
        get_storage_backend,
        sha256_bytes,
    )

    client = get_client()
    cleanup(client)
    backend = get_storage_backend(client)
    sha1 = sha256_bytes(PAYLOAD_1)
    sha2 = sha256_bytes(PAYLOAD_2)

    # 1. migration landed
    try:
        client.table("workspace_blobs").select("sha256, storage_key, byte_size").limit(1).execute()
        record("1. migration 219 landed (storage_key + byte_size)", True, "columns queryable")
    except Exception as e:
        record("1. migration 219 landed (storage_key + byte_size)", False, str(e))
        return

    # 2. binary write through the single door
    rev1 = write_revision(
        client,
        user_id=TEST_USER_ID,
        path=BIN_PATH,
        content_bytes=PAYLOAD_1,
        authored_by="system:adr427-gate",
        message="binary revision 1 (gate)",
    )
    record("2. write_revision(content_bytes) → revision id", bool(rev1), f"rev={rev1[:8]}…")

    # 3. marker row
    blob_row = (
        client.table("workspace_blobs")
        .select("content, storage_key, byte_size")
        .eq("sha256", sha1)
        .limit(1)
        .execute()
    ).data
    ok = bool(blob_row) and blob_row[0]["content"] == "" and \
        blob_row[0]["storage_key"] == cas_key(sha1) and \
        blob_row[0]["byte_size"] == len(PAYLOAD_1)
    record("3. blob is a marker row (content='', storage_key, byte_size)", ok,
           f"{blob_row[0] if blob_row else 'MISSING'}"[:100])

    # 4. bytes round-trip + range
    got = backend.get_blob(sha1)
    sliced = b"".join(backend.open_read_stream(sha1, ByteRange(0, 8)))
    ok = got == PAYLOAD_1 and sliced == PNG_MAGIC
    record("4. bytes round-trip via seam + range read", ok,
           f"{len(got)} bytes back, range[0:8]={sliced!r}")

    # 5. denorm discipline: content='', derived type, no stored capability
    file_row = (
        client.table("workspace_files")
        .select("content, content_type, content_url")
        .eq("user_id", TEST_USER_ID)
        .eq("path", BIN_PATH)
        .limit(1)
        .execute()
    ).data
    ok = bool(file_row) and file_row[0]["content"] == "" and \
        file_row[0]["content_type"] == "image/png" and \
        not file_row[0]["content_url"]
    record("5. denorm: content='' + DERIVED type + no stored content_url", ok,
           f"{file_row[0] if file_row else 'MISSING'}")

    # 6. second revision parent-points at the first (trace)
    rev2 = write_revision(
        client,
        user_id=TEST_USER_ID,
        path=BIN_PATH,
        content_bytes=PAYLOAD_2,
        authored_by="system:adr427-gate",
        message="binary revision 2 (gate)",
    )
    chain = list_revisions(client, user_id=TEST_USER_ID, path=BIN_PATH, limit=10)
    ok = len(chain) == 2 and chain[0]["id"] == rev2 and \
        chain[0]["parent_version_id"] == rev1 and chain[1]["id"] == rev1
    record("6. parent-pointer chain across binary revisions", ok,
           f"chain={[c['id'][:8] for c in chain]}")

    # 7. read_revision binary awareness
    r1 = read_revision(client, user_id=TEST_USER_ID, path=BIN_PATH, revision_id=rev1)
    ok = r1 is not None and r1.is_binary and r1.content is None and \
        r1.byte_size == len(PAYLOAD_1) and r1.blob_sha == sha1
    record("7. read_revision: is_binary, content=None, byte_size", ok,
           f"is_binary={getattr(r1, 'is_binary', None)}, byte_size={getattr(r1, 'byte_size', None)}")

    # 8. revert-as-write: rev-1's bytes come back as head; CAS dedups
    blobs_before = (
        client.table("workspace_blobs").select("sha256", count="exact")
        .in_("sha256", [sha1, sha2]).execute()
    ).count
    rev3 = write_revision(
        client,
        user_id=TEST_USER_ID,
        path=BIN_PATH,
        content_bytes=PAYLOAD_1,
        authored_by="system:adr427-gate",
        message="revert to revision 1 (gate)",
    )
    head = read_revision(client, user_id=TEST_USER_ID, path=BIN_PATH)
    blobs_after = (
        client.table("workspace_blobs").select("sha256", count="exact")
        .in_("sha256", [sha1, sha2]).execute()
    ).count
    ok = head is not None and head.id == rev3 and head.blob_sha == sha1 and \
        blobs_before == blobs_after == 2
    record("8. revert-as-write round-trips; CAS dedup holds", ok,
           f"head.blob_sha==sha1: {head.blob_sha == sha1 if head else '?'}, blobs {blobs_before}→{blobs_after}")

    # 9. minted serving URL (binary: signed URL; text: None)
    url = backend.mint_serving_url(sha1, expires_in=120)
    txt_rev = write_revision(
        client,
        user_id=TEST_USER_ID,
        path=TXT_PATH,
        content="plain text — the unchanged lane",
        authored_by="system:adr427-gate",
        message="text control (gate)",
    )
    txt_sha = read_revision(client, user_id=TEST_USER_ID, path=TXT_PATH).blob_sha
    txt_url = backend.mint_serving_url(txt_sha, expires_in=120)
    ok = bool(url) and url.startswith("http") and txt_url is None
    record("9. mint_serving_url: signed for binary, None for inline text", ok,
           f"binary={'minted' if url else None}, text={txt_url}")

    # 10. tombstone fix: delete carries the head's BINARY sha
    write_revision(
        client,
        user_id=TEST_USER_ID,
        path=DEL_PATH,
        content_bytes=PAYLOAD_2,
        authored_by="system:adr427-gate",
        message="to be deleted (gate)",
    )
    tomb = delete_live_file(
        client,
        user_id=TEST_USER_ID,
        path=DEL_PATH,
        authored_by="system:adr427-gate",
        message="delete binary (gate)",
    )
    tomb_row = (
        client.table("workspace_file_versions")
        .select("blob_sha")
        .eq("id", tomb)
        .limit(1)
        .execute()
    ).data
    empty_sha = sha256_bytes(b"")
    ok = bool(tomb_row) and tomb_row[0]["blob_sha"] == sha2 and \
        tomb_row[0]["blob_sha"] != empty_sha
    record("10. tombstone reuses the head's binary blob_sha", ok,
           f"tombstone blob={tomb_row[0]['blob_sha'][:12] if tomb_row else '?'}… (expected {sha2[:12]}…)")

    # 11. validation — one content form exactly
    try:
        write_revision(
            client, user_id=TEST_USER_ID, path=BIN_PATH, content="x",
            content_bytes=b"\xff\xfe", authored_by="system:adr427-gate", message="both",
        )
        both_raises = False
    except ValueError:
        both_raises = True
    try:
        write_revision(
            client, user_id=TEST_USER_ID, path=BIN_PATH,
            authored_by="system:adr427-gate", message="neither",
        )
        neither_raises = False
    except ValueError:
        neither_raises = True
    record("11. validation: both/neither content forms raise", both_raises and neither_raises,
           f"both→ValueError: {both_raises}, neither→ValueError: {neither_raises}")

    # 12. text lane unchanged
    tr = read_revision(client, user_id=TEST_USER_ID, path=TXT_PATH, revision_id=txt_rev)
    txt_file = (
        client.table("workspace_files").select("content")
        .eq("user_id", TEST_USER_ID).eq("path", TXT_PATH).limit(1).execute()
    ).data
    ok = tr is not None and not tr.is_binary and \
        tr.content == "plain text — the unchanged lane" and \
        bool(txt_file) and txt_file[0]["content"] == "plain text — the unchanged lane"
    record("12. text lane byte-identical (inline content, is_binary=False)", ok,
           f"content={tr.content!r}" if tr else "missing")


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
    print(f"ADR-427 Phase 2 binary gate: {passed}/{total} passed, {failed} failed")
    print(f"{'='*60}")
    if failed:
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  ✗ {name}: {detail}")
    sys.exit(0 if failed == 0 else 1)
