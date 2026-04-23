"""
Validation Suite — ADR-209 Phase 3 (Read-Side Primitives + Prompt Posture)

Tests:
  1. Three new primitives registered in CHAT_PRIMITIVES
  2. Three new primitives registered in HEADLESS_PRIMITIVES
  3. Three new primitives in HANDLERS dict
  4. ListRevisions handler returns revision chain newest-first
  5. ReadRevision handler with offset=-1 returns previous revision
  6. ReadRevision handler with revision_id returns exact revision
  7. ReadRevision handler rejects ambiguous (both offset + revision_id)
  8. DiffRevisions handler produces unified diff between two revisions
  9. DiffRevisions handler flags identical blobs
 10. ListFiles handler accepts authored_by filter and intersects correctly
 11. Recent authorship signal aggregates by cognitive-layer prefix
 12. Compact index renders the activity line when revisions present
 13. Compact index stays under 600-token ceiling with activity line
 14. Phase 1 + Phase 2 still pass (no regressions)

Usage:
    cd api && python test_adr209_phase3.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
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
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
SCRATCH_AGENT_SLUG = "_adr209-phase3-test-agent"
SCRATCH_PATH = f"/agents/{SCRATCH_AGENT_SLUG}/phase3-scratch.md"

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


def _cleanup_scratch(client) -> None:
    """FK order: workspace_files first, then workspace_file_versions."""
    client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", SCRATCH_PATH).execute()
    client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", SCRATCH_PATH).execute()


class _FakeAuth:
    """Minimal auth stub for handler tests. Real auth middleware not needed
    for primitive-level validation."""
    def __init__(self, client, user_id: str, agent_slug: str):
        self.client = client
        self.user_id = user_id
        self.agent = {
            "id": "phase3-test-agent-id",
            "title": "Phase 3 Test Agent",
            "role": "researcher",
        }
        self._agent_slug = agent_slug


def _get_agent_slug_stub():
    """Monkeypatch helper: stub get_agent_slug to return our scratch slug
    since our FakeAuth agent doesn't carry a real slug."""
    from services import workspace as ws_mod
    original = getattr(ws_mod, "get_agent_slug", None)

    def stubbed(agent):
        # When the test scaffolds revisions under SCRATCH_AGENT_SLUG, the
        # primitive handlers use get_agent_slug(auth.agent). Return our
        # scratch slug unconditionally.
        return SCRATCH_AGENT_SLUG

    ws_mod.get_agent_slug = stubbed
    return original


def _restore_agent_slug(original) -> None:
    from services import workspace as ws_mod
    if original is not None:
        ws_mod.get_agent_slug = original


# ---------------------------------------------------------------------------
# Tests 1–3 — registry wiring
# ---------------------------------------------------------------------------

def test_chat_registry_wiring() -> None:
    try:
        from services.primitives.registry import CHAT_PRIMITIVES
        names = {t["name"] for t in CHAT_PRIMITIVES}
        required = {"ListRevisions", "ReadRevision", "DiffRevisions"}
        missing = required - names
        record(
            "CHAT_PRIMITIVES includes ListRevisions/ReadRevision/DiffRevisions",
            not missing,
            f"missing: {sorted(missing)}" if missing else "all 3 present",
        )
    except Exception as e:
        record("CHAT_PRIMITIVES wiring", False, f"Error: {e}")


def test_headless_registry_wiring() -> None:
    try:
        from services.primitives.registry import HEADLESS_PRIMITIVES
        names = {t["name"] for t in HEADLESS_PRIMITIVES}
        required = {"ListRevisions", "ReadRevision", "DiffRevisions"}
        missing = required - names
        record(
            "HEADLESS_PRIMITIVES includes ListRevisions/ReadRevision/DiffRevisions",
            not missing,
            f"missing: {sorted(missing)}" if missing else "all 3 present",
        )
    except Exception as e:
        record("HEADLESS_PRIMITIVES wiring", False, f"Error: {e}")


def test_handlers_wiring() -> None:
    try:
        from services.primitives.registry import HANDLERS
        required = {"ListRevisions", "ReadRevision", "DiffRevisions"}
        missing = required - set(HANDLERS.keys())
        record(
            "HANDLERS dict includes handle_list_revisions/read_revision/diff_revisions",
            not missing,
            f"missing: {sorted(missing)}" if missing else "all 3 present",
        )
    except Exception as e:
        record("HANDLERS wiring", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Tests 4–9 — primitive handler behavior
# ---------------------------------------------------------------------------

def _seed_scratch_revisions(client, *authors: str) -> list[str]:
    """Write N revisions to SCRATCH_PATH, returning their ids in write order."""
    from services.authored_substrate import write_revision

    _cleanup_scratch(client)
    ids = []
    for i, author in enumerate(authors, start=1):
        rid = write_revision(
            client,
            user_id=TEST_USER_ID,
            path=SCRATCH_PATH,
            content=f"# Phase 3 test revision {i} (author={author})",
            authored_by=author,
            message=f"phase 3 test rev {i}",
        )
        ids.append(rid)
    return ids


def test_list_revisions_handler(client) -> None:
    try:
        from services.primitives.revisions import handle_list_revisions

        ids = _seed_scratch_revisions(client, "operator", "yarnnn:test", "agent:test")
        auth = _FakeAuth(client, TEST_USER_ID, SCRATCH_AGENT_SLUG)

        result = asyncio.run(handle_list_revisions(auth, {"path": SCRATCH_PATH}))
        revisions = result.get("revisions") or []

        ok = (
            result.get("success") is True
            and len(revisions) == 3
            and revisions[0]["id"] == ids[2]  # newest first
            and revisions[1]["id"] == ids[1]
            and revisions[2]["id"] == ids[0]
            and revisions[0]["authored_by"] == "agent:test"
        )
        record(
            "ListRevisions returns chain newest-first with correct attribution",
            ok,
            f"count={len(revisions)}, head.authored_by={revisions[0]['authored_by'] if revisions else None}",
        )
    except Exception as e:
        record("ListRevisions handler", False, f"Error: {e}")


def test_read_revision_by_offset(client) -> None:
    try:
        from services.primitives.revisions import handle_read_revision

        ids = _seed_scratch_revisions(client, "operator", "yarnnn:test", "agent:test")
        auth = _FakeAuth(client, TEST_USER_ID, SCRATCH_AGENT_SLUG)

        # offset=-1 → previous revision (id[1])
        result = asyncio.run(handle_read_revision(auth, {"path": SCRATCH_PATH, "offset": -1}))
        rev = result.get("revision") or {}

        ok = (
            result.get("success") is True
            and rev.get("id") == ids[1]
            and rev.get("authored_by") == "yarnnn:test"
            and "yarnnn:test" in (rev.get("content") or "")
        )
        record(
            "ReadRevision offset=-1 returns previous revision",
            ok,
            f"id={rev.get('id', '')[:8]}..., authored_by={rev.get('authored_by')}",
        )
    except Exception as e:
        record("ReadRevision by offset", False, f"Error: {e}")


def test_read_revision_by_id(client) -> None:
    try:
        from services.primitives.revisions import handle_read_revision

        ids = _seed_scratch_revisions(client, "operator", "yarnnn:test", "agent:test")
        auth = _FakeAuth(client, TEST_USER_ID, SCRATCH_AGENT_SLUG)

        result = asyncio.run(handle_read_revision(auth, {"path": SCRATCH_PATH, "revision_id": ids[0]}))
        rev = result.get("revision") or {}
        ok = result.get("success") is True and rev.get("id") == ids[0] and rev.get("authored_by") == "operator"
        record(
            "ReadRevision by revision_id returns exact revision",
            ok,
            f"id match={rev.get('id') == ids[0]}, authored_by={rev.get('authored_by')}",
        )
    except Exception as e:
        record("ReadRevision by id", False, f"Error: {e}")


def test_read_revision_rejects_ambiguous(client) -> None:
    try:
        from services.primitives.revisions import handle_read_revision

        _seed_scratch_revisions(client, "operator")
        auth = _FakeAuth(client, TEST_USER_ID, SCRATCH_AGENT_SLUG)

        result = asyncio.run(handle_read_revision(auth, {
            "path": SCRATCH_PATH,
            "offset": -1,
            "revision_id": "any",
        }))
        ok = result.get("success") is False and result.get("error") == "ambiguous_reference"
        record(
            "ReadRevision rejects both offset + revision_id",
            ok,
            f"success={result.get('success')}, error={result.get('error')}",
        )
    except Exception as e:
        record("ReadRevision rejects ambiguous", False, f"Error: {e}")


def test_diff_revisions_handler(client) -> None:
    try:
        from services.primitives.revisions import handle_diff_revisions

        ids = _seed_scratch_revisions(client, "operator", "yarnnn:test")
        auth = _FakeAuth(client, TEST_USER_ID, SCRATCH_AGENT_SLUG)

        # from = previous (ids[0]), to = head (ids[1])
        result = asyncio.run(handle_diff_revisions(auth, {
            "path": SCRATCH_PATH,
            "from_rev": -1,  # previous
            "to_rev": 0,     # head
        }))
        diff = result.get("diff") or ""
        ok = (
            result.get("success") is True
            and "+" in diff
            and "-" in diff
            and "yarnnn:test" in diff  # from file headers include author-part in filename@sha
            and result.get("identical") is False
        )
        record(
            "DiffRevisions produces unified diff between two revisions",
            ok,
            f"diff_len={len(diff)}, identical={result.get('identical')}",
        )
    except Exception as e:
        record("DiffRevisions handler", False, f"Error: {e}")


def test_diff_identical_blobs(client) -> None:
    try:
        from services.primitives.revisions import handle_diff_revisions
        from services.authored_substrate import write_revision

        _cleanup_scratch(client)
        # Two revisions with the same content → same blob_sha
        rid1 = write_revision(
            client, user_id=TEST_USER_ID, path=SCRATCH_PATH,
            content="identical content",
            authored_by="operator", message="first",
        )
        rid2 = write_revision(
            client, user_id=TEST_USER_ID, path=SCRATCH_PATH,
            content="identical content",
            authored_by="operator", message="second (same content)",
        )
        auth = _FakeAuth(client, TEST_USER_ID, SCRATCH_AGENT_SLUG)

        result = asyncio.run(handle_diff_revisions(auth, {
            "path": SCRATCH_PATH,
            "from_rev": rid1,
            "to_rev": rid2,
        }))
        ok = result.get("success") is True and result.get("identical") is True and result.get("diff") == ""
        record(
            "DiffRevisions flags identical blobs (empty diff, identical=True)",
            ok,
            f"identical={result.get('identical')}, diff_empty={result.get('diff') == ''}",
        )
    except Exception as e:
        record("DiffRevisions identical", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 10 — ListFiles filter
# ---------------------------------------------------------------------------

def test_list_files_authored_by_filter(client) -> None:
    original_slug = _get_agent_slug_stub()
    try:
        from services.primitives.workspace import handle_list_files
        from services.authored_substrate import write_revision

        # Seed two files under /agents/{SCRATCH_AGENT_SLUG}/ with distinct authors
        path_op = f"/agents/{SCRATCH_AGENT_SLUG}/operator-file.md"
        path_agent = f"/agents/{SCRATCH_AGENT_SLUG}/agent-file.md"

        # FK-order cleanup
        for p in (path_op, path_agent):
            client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", p).execute()
            client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", p).execute()

        write_revision(client, user_id=TEST_USER_ID, path=path_op,
                       content="operator", authored_by="operator", message="operator authored")
        write_revision(client, user_id=TEST_USER_ID, path=path_agent,
                       content="agent", authored_by="agent:test", message="agent authored")

        auth = _FakeAuth(client, TEST_USER_ID, SCRATCH_AGENT_SLUG)

        # Filter: only operator-authored
        result = asyncio.run(handle_list_files(auth, {
            "path": "",
            "authored_by": "operator",
        }))
        files = result.get("files") or []
        filters = result.get("filters_applied") or {}

        ok = (
            result.get("success") is True
            and "operator-file.md" in files
            and "agent-file.md" not in files
            and filters.get("authored_by") == "operator"
        )
        record(
            "ListFiles with authored_by=operator filter returns only operator-authored",
            ok,
            f"files={files}, filters_applied={filters}",
        )

        # Cleanup
        for p in (path_op, path_agent):
            client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", p).execute()
            client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", p).execute()
    except Exception as e:
        record("ListFiles authored_by filter", False, f"Error: {e}")
    finally:
        _restore_agent_slug(original_slug)


# ---------------------------------------------------------------------------
# Test 11 — recent authorship aggregation
# ---------------------------------------------------------------------------

def test_recent_authorship_aggregation(client) -> None:
    try:
        from services.working_memory import _get_recent_authorship_sync

        # The DB has been accumulating revisions from Phase 1/2 backfill + test runs.
        # Sanity check: the aggregator returns the expected shape and buckets
        # authors correctly by prefix.
        result = _get_recent_authorship_sync(TEST_USER_ID, client)
        ok = (
            isinstance(result, dict)
            and "window_hours" in result
            and "total" in result
            and "by_layer" in result
            and result["window_hours"] == 24
            and isinstance(result["by_layer"], dict)
        )
        # Verify at least one bucket is a known cognitive-layer prefix
        layers = set(result.get("by_layer", {}).keys())
        known = {"operator", "yarnnn", "agent", "specialist", "reviewer", "system"}
        ok = ok and (not layers or layers.issubset(known))
        record(
            "_get_recent_authorship_sync returns correct shape + buckets by layer",
            ok,
            f"total={result.get('total')}, layers={sorted(layers)}",
        )
    except Exception as e:
        record("Recent authorship aggregation", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 12 + 13 — compact index activity line + token ceiling
# ---------------------------------------------------------------------------

def test_compact_index_activity_line() -> None:
    try:
        from services.working_memory import format_compact_index

        # Build a minimal working_memory with a populated recent_authorship
        working_memory = {
            "workspace_state": {
                "identity": "rich",
                "brand": "rich",
                "documents": 2,
                "context_domains": 1,
                "tasks_active": 1,
                "tasks_stale": 0,
                "balance_usd": 5.0,
                "balance_exhausted": False,
            },
            "active_tasks": [],
            "context_domains": [],
            "agents": [],
            "platforms": [],
            "recent_uploads": [],
            "recent_authorship": {
                "window_hours": 24,
                "total": 23,
                "by_layer": {
                    "operator": 3,
                    "yarnnn": 12,
                    "system": 8,
                },
            },
        }

        output = format_compact_index(working_memory)
        ok = (
            "Recent activity (24h, 23 revisions)" in output
            and "operator (3)" in output
            and "yarnnn (12)" in output
            and "system (8)" in output
            and "ListRevisions/ReadRevision/DiffRevisions" in output
        )
        record(
            "Compact index renders the activity line correctly",
            ok,
            f"contains_activity_line={'Recent activity' in output}",
        )

        # Token ceiling check (400 tokens ~= 1600 chars — well below 600/2400)
        char_count = len(output)
        token_ok = char_count < 2400
        record(
            "Compact index stays under 600-token ceiling (2400 chars)",
            token_ok,
            f"char_count={char_count}, approx_tokens={char_count // 4}",
        )
    except Exception as e:
        record("Compact index activity line", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 14 — regression check
# ---------------------------------------------------------------------------

def test_no_regression_phases_1_and_2() -> None:
    """Run prior phase suites via subprocess. If either fails, Phase 3 broke something."""
    api_root = Path(__file__).parent
    for name, path in [
        ("Phase 1", api_root / "test_adr209_phase1.py"),
        ("Phase 2", api_root / "test_adr209_phase2.py"),
    ]:
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True, text=True, timeout=180,
            )
            ok = result.returncode == 0
            # Extract final score from output
            out_lines = result.stdout.strip().splitlines()
            score_line = next((l for l in out_lines if "passed ===" in l), "?")
            record(
                f"{name} regression check (full suite re-run)",
                ok,
                score_line.strip() if score_line else f"rc={result.returncode}",
            )
        except Exception as e:
            record(f"{name} regression check", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    api_dir = Path(__file__).parent
    sys.path.insert(0, str(api_dir))

    client = get_client()

    try:
        # Registry wiring (no DB)
        test_chat_registry_wiring()
        test_headless_registry_wiring()
        test_handlers_wiring()

        # Primitive handlers (DB)
        test_list_revisions_handler(client)
        test_read_revision_by_offset(client)
        test_read_revision_by_id(client)
        test_read_revision_rejects_ambiguous(client)
        test_diff_revisions_handler(client)
        test_diff_identical_blobs(client)
        test_list_files_authored_by_filter(client)

        # Compact index + aggregation
        test_recent_authorship_aggregation(client)
        test_compact_index_activity_line()

        # Regression
        test_no_regression_phases_1_and_2()
    finally:
        _cleanup_scratch(client)

    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print()
    print(f"=== ADR-209 Phase 3 test results: {passed}/{total} passed ===")
    for name, ok, detail in RESULTS:
        icon = "✓" if ok else "✗"
        print(f"  {icon} {name}" + (f" — {detail}" if not ok else ""))

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
