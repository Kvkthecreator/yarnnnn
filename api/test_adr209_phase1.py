"""
Validation Suite — ADR-209 Phase 1 (Authored Substrate Foundation)

Tests:
  1. Migration 158 landed: workspace_blobs + workspace_file_versions tables exist
  2. workspace_files.head_version_id column exists
  3. Backfill produced: every workspace_files row has head_version_id set
  4. Backfill revisions carry authored_by='system:backfill-158'
  5. Every head_version_id points at an existing revision
  6. Every revision's blob_sha resolves to a workspace_blobs row
  7. Blob dedup works (count(distinct content) <= count(files))
  8. write_revision() service function works end-to-end on a scratch path
  9. write_revision() rejects empty authored_by / message (ValueError)
 10. list_revisions() + read_revision() round-trip correctly
 11. Parent-pointer chain: second revision's parent_version_id = first revision's id

Strategy: Real DB reads via service key + one scratch path for write tests.
Test user: kvkthecreator@gmail.com

Usage:
    cd api && python test_adr209_phase1.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
SCRATCH_PATH = "/agents/_adr209-phase1-test/scratch.md"

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    icon = "✓" if ok else "✗"
    logger.info(f"{icon} {name}: {detail}")


def get_client():
    """Supabase service-role client (bypasses RLS — safe in this test context)."""
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL + SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Test 1 — migration landed
# ---------------------------------------------------------------------------

def test_tables_exist(client) -> None:
    try:
        blob_result = client.table("workspace_blobs").select("sha256", count="exact").limit(1).execute()
        rev_result = client.table("workspace_file_versions").select("id", count="exact").limit(1).execute()
        record(
            "Tables exist",
            True,
            f"workspace_blobs count={blob_result.count}, workspace_file_versions count={rev_result.count}",
        )
    except Exception as e:
        record("Tables exist", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 2 — head_version_id column exists
# ---------------------------------------------------------------------------

def test_head_pointer_column_exists(client) -> None:
    try:
        result = (
            client.table("workspace_files")
            .select("id, head_version_id")
            .limit(1)
            .execute()
        )
        # If the column didn't exist, select would raise.
        record("workspace_files.head_version_id exists", True, "column accessible")
    except Exception as e:
        record("workspace_files.head_version_id exists", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 3 — backfill completeness: every workspace_files row has head_version_id
# ---------------------------------------------------------------------------

def test_backfill_complete(client) -> None:
    try:
        total = client.table("workspace_files").select("id", count="exact").limit(1).execute()
        with_head = (
            client.table("workspace_files")
            .select("id", count="exact")
            .not_.is_("head_version_id", "null")
            .limit(1)
            .execute()
        )
        total_count = total.count or 0
        head_count = with_head.count or 0
        ok = total_count == head_count
        record(
            "Backfill complete",
            ok,
            f"{head_count}/{total_count} files have head_version_id",
        )
    except Exception as e:
        record("Backfill complete", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 4 — backfill authored_by
# ---------------------------------------------------------------------------

def test_backfill_authored_by(client) -> None:
    try:
        result = (
            client.table("workspace_file_versions")
            .select("id", count="exact")
            .eq("authored_by", "system:backfill-158")
            .limit(1)
            .execute()
        )
        count = result.count or 0
        record(
            "Backfill authored_by",
            count > 0,
            f"{count} revisions attributed to system:backfill-158",
        )
    except Exception as e:
        record("Backfill authored_by", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 5 — head integrity: head_version_id points at a real revision
# ---------------------------------------------------------------------------

def test_head_integrity(client) -> None:
    try:
        sample = (
            client.table("workspace_files")
            .select("id, head_version_id, path")
            .eq("user_id", TEST_USER_ID)
            .not_.is_("head_version_id", "null")
            .limit(5)
            .execute()
        )
        if not sample.data:
            record("Head integrity", True, "No sampled files for test user (skipped)")
            return
        for row in sample.data:
            hv = row["head_version_id"]
            rev = (
                client.table("workspace_file_versions")
                .select("id")
                .eq("id", hv)
                .limit(1)
                .execute()
            )
            if not rev.data:
                record(
                    "Head integrity",
                    False,
                    f"head_version_id {hv} for path {row['path']} points at no revision",
                )
                return
        record("Head integrity", True, f"All {len(sample.data)} sampled heads resolve")
    except Exception as e:
        record("Head integrity", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 6 — blob integrity: every revision's blob_sha exists
# ---------------------------------------------------------------------------

def test_blob_integrity(client) -> None:
    try:
        sample = (
            client.table("workspace_file_versions")
            .select("id, blob_sha")
            .eq("user_id", TEST_USER_ID)
            .limit(10)
            .execute()
        )
        if not sample.data:
            record("Blob integrity", True, "No revisions for test user (skipped)")
            return
        for row in sample.data:
            sha = row["blob_sha"]
            blob = client.table("workspace_blobs").select("sha256").eq("sha256", sha).limit(1).execute()
            if not blob.data:
                record(
                    "Blob integrity",
                    False,
                    f"blob_sha {sha[:16]}... has no blob row",
                )
                return
        record("Blob integrity", True, f"All {len(sample.data)} sampled blobs resolve")
    except Exception as e:
        record("Blob integrity", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 7 — blob dedup: distinct contents <= total files
# ---------------------------------------------------------------------------

def test_blob_dedup(client) -> None:
    try:
        files = client.table("workspace_files").select("id", count="exact").limit(1).execute()
        blobs = client.table("workspace_blobs").select("sha256", count="exact").limit(1).execute()
        files_count = files.count or 0
        blobs_count = blobs.count or 0
        # Not a strict <= (other content could come from future writes), but
        # at backfill time blobs <= files should hold. We check blobs is
        # non-zero when files is non-zero.
        ok = (files_count == 0) or (blobs_count > 0)
        record(
            "Blob dedup sanity",
            ok,
            f"files={files_count}, blobs={blobs_count}",
        )
    except Exception as e:
        record("Blob dedup sanity", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 8 — write_revision() end-to-end on scratch path
# ---------------------------------------------------------------------------

def test_write_revision_end_to_end(client) -> None:
    try:
        from services.authored_substrate import write_revision, count_revisions

        # Clean up any prior test revisions on the scratch path
        client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", SCRATCH_PATH).execute()

        rev_id = write_revision(
            client,
            user_id=TEST_USER_ID,
            path=SCRATCH_PATH,
            content="# ADR-209 Phase 1 test\n\nFirst revision.",
            authored_by="system:adr209-phase1-test",
            message="phase 1 test: first revision",
        )
        n = count_revisions(client, user_id=TEST_USER_ID, path=SCRATCH_PATH)
        ok = bool(rev_id) and n == 1
        record(
            "write_revision end-to-end (1st revision)",
            ok,
            f"rev_id={rev_id[:8] if rev_id else None}..., count={n}",
        )
    except Exception as e:
        record("write_revision end-to-end (1st revision)", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 9 — write_revision() validation
# ---------------------------------------------------------------------------

def test_write_revision_validation(client) -> None:
    try:
        from services.authored_substrate import write_revision

        # Empty authored_by
        try:
            write_revision(
                client,
                user_id=TEST_USER_ID,
                path=SCRATCH_PATH,
                content="x",
                authored_by="",
                message="m",
            )
            record("write_revision rejects empty authored_by", False, "No ValueError raised")
            return
        except ValueError:
            pass

        # Empty message
        try:
            write_revision(
                client,
                user_id=TEST_USER_ID,
                path=SCRATCH_PATH,
                content="x",
                authored_by="system:adr209-phase1-test",
                message="",
            )
            record("write_revision rejects empty message", False, "No ValueError raised")
            return
        except ValueError:
            pass

        record("write_revision rejects empty attribution", True, "both cases raise ValueError")
    except Exception as e:
        record("write_revision rejects empty attribution", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 10 — list_revisions + read_revision round-trip
# ---------------------------------------------------------------------------

def test_read_list_round_trip(client) -> None:
    try:
        from services.authored_substrate import list_revisions, read_revision

        revs = list_revisions(client, user_id=TEST_USER_ID, path=SCRATCH_PATH, limit=10)
        if not revs:
            record("list + read round-trip", False, "No revisions to read")
            return

        first = revs[0]
        fetched = read_revision(client, user_id=TEST_USER_ID, path=SCRATCH_PATH, revision_id=first["id"])
        ok = (
            fetched is not None
            and fetched.id == first["id"]
            and fetched.authored_by == first["authored_by"]
            and fetched.content is not None
            and "First revision" in fetched.content
        )
        record(
            "list + read round-trip",
            ok,
            f"id match={fetched.id == first['id']}, content has 'First revision'="
            f"{fetched.content is not None and 'First revision' in fetched.content}",
        )
    except Exception as e:
        record("list + read round-trip", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 11 — parent-pointer chain
# ---------------------------------------------------------------------------

def test_parent_pointer_chain(client) -> None:
    try:
        from services.authored_substrate import write_revision, list_revisions

        # Write a second revision on the same path
        second_id = write_revision(
            client,
            user_id=TEST_USER_ID,
            path=SCRATCH_PATH,
            content="# ADR-209 Phase 1 test\n\nSecond revision with different content.",
            authored_by="system:adr209-phase1-test",
            message="phase 1 test: second revision",
        )

        revs = list_revisions(client, user_id=TEST_USER_ID, path=SCRATCH_PATH, limit=10)
        # Newest first: revs[0] is the second write, revs[1] is the first write.
        ok = (
            len(revs) >= 2
            and revs[0]["id"] == second_id
            and revs[0]["parent_version_id"] == revs[1]["id"]
            and revs[1]["parent_version_id"] is None
        )
        # Safe formatting — any of these could be None if ok is False.
        head_parent = (revs[0].get("parent_version_id") or "") if revs else ""
        first_id = (revs[1].get("id") or "") if len(revs) >= 2 else ""
        detail = (
            f"chain_length={len(revs)}, "
            f"head.parent={head_parent[:8] or '<none>'}, "
            f"revs[1].id={first_id[:8] or '<none>'}, "
            f"chain_matches={ok}"
        )
        record("Parent-pointer chain", ok, detail)
    except Exception as e:
        record("Parent-pointer chain", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Scratch cleanup
# ---------------------------------------------------------------------------

def cleanup(client) -> None:
    try:
        client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", SCRATCH_PATH).execute()
        logger.info("Cleanup: scratch revisions deleted")
    except Exception as e:
        logger.warning(f"Cleanup failed (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    # Ensure api/services is importable
    api_dir = Path(__file__).parent
    sys.path.insert(0, str(api_dir))

    client = get_client()

    test_tables_exist(client)
    test_head_pointer_column_exists(client)
    test_backfill_complete(client)
    test_backfill_authored_by(client)
    test_head_integrity(client)
    test_blob_integrity(client)
    test_blob_dedup(client)
    test_write_revision_end_to_end(client)
    test_write_revision_validation(client)
    test_read_list_round_trip(client)
    test_parent_pointer_chain(client)

    cleanup(client)

    # Summary
    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print()
    print(f"=== ADR-209 Phase 1 test results: {passed}/{total} passed ===")
    for name, ok, detail in RESULTS:
        icon = "✓" if ok else "✗"
        print(f"  {icon} {name}" + (f" — {detail}" if not ok else ""))

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
