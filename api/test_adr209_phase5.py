"""
Validation Suite — ADR-209 Phase 5 (Schema cleanup + final grep gate)

Tests:
  1. workspace_files.version column no longer exists
  2. workspace_files lifecycle check constraint excludes 'archived'
  3. No rows with path LIKE '%/history/%/v%.md' remain
  4. workspace_files.content column preserved (denormalization intact)
  5. FTS + embedding indexes still present on workspace_files.content
  6. Regression-guard test passes (test_adr209_no_filename_versioning.py)
  7. Inserting lifecycle='archived' is rejected by the DB
  8. Writing a new file after migration round-trips correctly (pipeline still works)
  9. Regression — Phases 1+2+3+4 still pass

Strategy: Real DB reads against the migrated schema + subprocess calls for
regression runs.
Test user: kvkthecreator@gmail.com

Usage:
    cd api && python test_adr209_phase5.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
SCRATCH_PATH = f"/agents/_adr209-phase5-smoke/scratch.md"

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    icon = "✓" if ok else "✗"
    logger.info(f"{icon} {name}: {detail}")


def get_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL + SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


def _pg_connstr() -> str:
    """Direct psycopg connection string for tests that need EXPLAIN / DDL
    introspection beyond what the Supabase Python client exposes."""
    return (
        "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24"
        "@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
    )


def _psql(sql: str) -> str:
    """Run a one-shot psql query and return stdout."""
    return subprocess.run(
        ["psql", _pg_connstr(), "-t", "-c", sql],
        capture_output=True, text=True,
    ).stdout.strip()


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

def test_version_column_dropped() -> None:
    try:
        out = _psql(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'workspace_files' AND column_name = 'version';"
        )
        ok = out == ""
        record(
            "workspace_files.version column dropped",
            ok,
            "column absent" if ok else f"column still present: {out!r}",
        )
    except Exception as e:
        record("version column dropped", False, f"Error: {e}")


def test_lifecycle_archived_excluded() -> None:
    try:
        out = _psql(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'workspace_files_lifecycle_check';"
        )
        has_archived = "'archived'" in out
        record(
            "lifecycle check constraint excludes 'archived'",
            not has_archived,
            f"constraint: {out!r}",
        )
    except Exception as e:
        record("lifecycle archived excluded", False, f"Error: {e}")


def test_no_history_artifact_rows(client) -> None:
    try:
        result = (
            client.table("workspace_files")
            .select("id", count="exact")
            .like("path", "%/history/%/v%.md")
            .limit(1)
            .execute()
        )
        count = result.count or 0
        record(
            "Zero /history/{...}/v{N}.md artifact rows remain",
            count == 0,
            f"count={count}",
        )
    except Exception as e:
        record("no history artifact rows", False, f"Error: {e}")


def test_content_column_preserved(client) -> None:
    try:
        out = _psql(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'workspace_files' AND column_name = 'content';"
        )
        ok = "text" in out.lower()
        record(
            "workspace_files.content column preserved (denormalization intact)",
            ok,
            f"data_type={out!r}",
        )
    except Exception as e:
        record("content column preserved", False, f"Error: {e}")


def test_fts_embedding_indexes_preserved() -> None:
    try:
        indexes = _psql(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'workspace_files';"
        )
        fts_ok = "idx_ws_fts" in indexes
        emb_ok = "idx_ws_embedding" in indexes
        record(
            "FTS + embedding indexes preserved on workspace_files",
            fts_ok and emb_ok,
            f"fts_ok={fts_ok}, embedding_ok={emb_ok}",
        )
    except Exception as e:
        record("fts/embedding indexes preserved", False, f"Error: {e}")


def test_archived_lifecycle_rejected(client) -> None:
    """After Migration 159, inserting lifecycle='archived' should fail the
    check constraint. Validate by attempting a direct insert with a rollback."""
    try:
        # Attempt insert with lifecycle='archived' via direct psql so we can
        # catch the constraint violation cleanly. The Supabase client raises
        # on constraint errors, but the error surface is inconsistent across
        # versions; psql is predictable.
        result = subprocess.run(
            ["psql", _pg_connstr(), "-c",
             "BEGIN; "
             "INSERT INTO workspace_files(user_id, path, content, lifecycle) "
             f"VALUES ('{TEST_USER_ID}', '/adr209-phase5-reject-test.md', 'x', 'archived'); "
             "ROLLBACK;"],
            capture_output=True, text=True,
        )
        # Constraint violation should be in stderr
        rejected = "violates check constraint" in result.stderr or "violates check constraint" in result.stdout
        record(
            "DB rejects inserts with lifecycle='archived'",
            rejected,
            "check constraint enforces ephemeral/active/delivered" if rejected else f"unexpected: rc={result.returncode}, err={result.stderr[:200]}",
        )
    except Exception as e:
        record("archived lifecycle rejected", False, f"Error: {e}")


def test_smoke_write_after_migration(client) -> None:
    """Ensure the Authored Substrate write path still works end-to-end after
    Migration 159 (column drop + constraint tighten). A write should land a
    revision and the workspace_files row should be properly populated."""
    try:
        from services.authored_substrate import write_revision
        # Cleanup scratch
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", SCRATCH_PATH).execute()
        client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", SCRATCH_PATH).execute()

        rid = write_revision(
            client,
            user_id=TEST_USER_ID,
            path=SCRATCH_PATH,
            content="# Phase 5 smoke — post-migration",
            authored_by="system:adr209-phase5-smoke",
            message="smoke test: write after migration 159",
        )
        # Verify workspace_files row
        row = (
            client.table("workspace_files")
            .select("head_version_id, content, lifecycle")
            .eq("user_id", TEST_USER_ID)
            .eq("path", SCRATCH_PATH)
            .limit(1)
            .execute()
        )
        data = row.data[0] if row.data else None
        ok = (
            data is not None
            and data["head_version_id"] == rid
            and "Phase 5 smoke" in (data["content"] or "")
            and data["lifecycle"] in ("active", "ephemeral", "delivered")
        )
        record(
            "Smoke write post-Migration 159 round-trips correctly",
            ok,
            f"head={rid[:8] if rid else None}, content_present={'Phase 5 smoke' in (data['content'] if data else '')}, lifecycle={data['lifecycle'] if data else None}",
        )
        # Cleanup
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", SCRATCH_PATH).execute()
        client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", SCRATCH_PATH).execute()
    except Exception as e:
        record("smoke write post-migration", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Regression-guard + prior-phase regression
# ---------------------------------------------------------------------------

def test_regression_guard() -> None:
    try:
        api_root = Path(__file__).parent
        result = subprocess.run(
            [sys.executable, str(api_root / "test_adr209_no_filename_versioning.py")],
            capture_output=True, text=True, timeout=120,
        )
        ok = result.returncode == 0
        final_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "?"
        record(
            "Filename-versioning regression guard passes",
            ok,
            final_line,
        )
    except Exception as e:
        record("regression guard", False, f"Error: {e}")


def test_prior_phase_regression() -> None:
    api_root = Path(__file__).parent
    for phase_num, path in [
        (1, api_root / "test_adr209_phase1.py"),
        (2, api_root / "test_adr209_phase2.py"),
        (3, api_root / "test_adr209_phase3.py"),
        (4, api_root / "test_adr209_phase4.py"),
    ]:
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True, text=True, timeout=240,
            )
            ok = result.returncode == 0
            score_line = next(
                (l for l in result.stdout.strip().splitlines() if "passed ===" in l),
                "?",
            )
            record(
                f"Phase {phase_num} regression",
                ok,
                score_line.strip() if score_line else f"rc={result.returncode}",
            )
        except Exception as e:
            record(f"Phase {phase_num} regression", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    api_dir = Path(__file__).parent
    sys.path.insert(0, str(api_dir))

    client = get_client()

    test_version_column_dropped()
    test_lifecycle_archived_excluded()
    test_no_history_artifact_rows(client)
    test_content_column_preserved(client)
    test_fts_embedding_indexes_preserved()
    test_archived_lifecycle_rejected(client)
    test_smoke_write_after_migration(client)
    test_regression_guard()
    test_prior_phase_regression()

    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print()
    print(f"=== ADR-209 Phase 5 test results: {passed}/{total} passed ===")
    for name, ok, detail in RESULTS:
        icon = "✓" if ok else "✗"
        print(f"  {icon} {name}" + (f" — {detail}" if not ok else ""))

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
