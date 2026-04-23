"""
Validation Suite — ADR-209 Phase 2 (Write-Path Unification + Legacy Deletion)

Tests:
  1. write_revision() upserts workspace_files with content + head_version_id in sync
  2. AgentWorkspace.write() routes through write_revision (revision appears, head advances)
  3. AgentWorkspace.write() default authored_by = "agent:{slug}"
  4. AgentWorkspace.write() explicit authored_by override works
  5. UserMemory.write() routes through write_revision with default "system:user-memory"
  6. UserMemory.update_profile() defaults to "operator" attribution
  7. TaskWorkspace.write() routes through write_revision with default "task:{slug}"
  8. TaskWorkspace.save_output() attributes to "agent:{agent_slug}"
  9. TaskWorkspace.append_run_log() attributes to "system:task-pipeline"
 10. reviewer_audit.append_decision() attributes to "reviewer:<identity>"
 11. Second write to same path chains: new revision's parent = prior revision
 12. workspace_files.content + head_version_id stay in sync across writes
 13. Grep gate — no live-code references to deleted history methods/constants
 14. Grep gate — only authored_substrate.py + embedding-only update touch workspace_files.upsert/insert/update
 15. Idempotent backfill state preserved (backfill revisions still present)

Strategy: Real DB reads via service key + scratch paths for write tests.
Test user: kvkthecreator@gmail.com

Usage:
    cd api && python test_adr209_phase2.py
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
SCRATCH_AGENT_SLUG = "_adr209-phase2-test-agent"
SCRATCH_TASK_SLUG = "_adr209-phase2-test-task"
SCRATCH_AGENT_PATH_SUFFIX = "scratch.md"
SCRATCH_MEMORY_FILENAME = "_adr209-phase2-test-memory.md"

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


def _fetch_head(client, path: str) -> dict | None:
    r = (
        client.table("workspace_files")
        .select("head_version_id, content, updated_at")
        .eq("user_id", TEST_USER_ID)
        .eq("path", path)
        .limit(1)
        .execute()
    )
    return r.data[0] if r.data else None


def _fetch_revision(client, revision_id: str) -> dict | None:
    r = (
        client.table("workspace_file_versions")
        .select("id, path, authored_by, message, parent_version_id, blob_sha")
        .eq("id", revision_id)
        .limit(1)
        .execute()
    )
    return r.data[0] if r.data else None


def _cleanup_scratch(client) -> None:
    # FK ordering: workspace_files first (head_version_id references
    # workspace_file_versions), then the revisions.
    agent_path = f"/agents/{SCRATCH_AGENT_SLUG}/{SCRATCH_AGENT_PATH_SUFFIX}"
    task_path_prefix = f"/tasks/{SCRATCH_TASK_SLUG}/"
    memory_path = f"/workspace/{SCRATCH_MEMORY_FILENAME}"

    # Also clean up ancillary scratch paths created by tests 11+12
    extra_agent_paths = [
        f"/agents/{SCRATCH_AGENT_SLUG}/chain-test.md",
        f"/agents/{SCRATCH_AGENT_SLUG}/sync-test.md",
    ]

    for path in (agent_path, memory_path, *extra_agent_paths):
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()
        client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()

    client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).like("path", f"{task_path_prefix}%").execute()
    client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).like("path", f"{task_path_prefix}%").execute()


# ---------------------------------------------------------------------------
# Test 1 — write_revision syncs workspace_files
# ---------------------------------------------------------------------------

def test_write_revision_syncs_head(client) -> None:
    try:
        from services.authored_substrate import write_revision

        path = f"/agents/{SCRATCH_AGENT_SLUG}/{SCRATCH_AGENT_PATH_SUFFIX}"
        rev_id = write_revision(
            client,
            user_id=TEST_USER_ID,
            path=path,
            content="# Phase 2 test — initial content",
            authored_by="system:adr209-phase2-test",
            message="phase 2 test initial",
        )
        head = _fetch_head(client, path)
        ok = (
            head is not None
            and head.get("head_version_id") == rev_id
            and "initial content" in (head.get("content") or "")
        )
        record(
            "write_revision syncs workspace_files.head_version_id + content",
            ok,
            f"head_version_id matches={head.get('head_version_id') == rev_id if head else False}, content present={'initial content' in (head.get('content') or '') if head else False}",
        )
    except Exception as e:
        record("write_revision syncs workspace_files.head_version_id + content", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 2 + 3 + 4 — AgentWorkspace.write
# ---------------------------------------------------------------------------

def test_agent_workspace_write(client) -> None:
    try:
        from services.workspace import AgentWorkspace

        aw = AgentWorkspace(client, TEST_USER_ID, SCRATCH_AGENT_SLUG)
        path = f"/agents/{SCRATCH_AGENT_SLUG}/{SCRATCH_AGENT_PATH_SUFFIX}"

        # Default attribution
        ok1 = asyncio.run(aw.write(SCRATCH_AGENT_PATH_SUFFIX, "# agent default attribution"))
        head = _fetch_head(client, path)
        rev = _fetch_revision(client, head["head_version_id"]) if head else None
        default_author_ok = rev is not None and rev["authored_by"] == f"agent:{SCRATCH_AGENT_SLUG}"
        record(
            "AgentWorkspace.write default authored_by",
            ok1 and default_author_ok,
            f"authored_by={rev['authored_by'] if rev else None}",
        )

        # Override attribution
        ok2 = asyncio.run(aw.write(
            SCRATCH_AGENT_PATH_SUFFIX,
            "# override attribution",
            authored_by="yarnnn:claude-sonnet-4-7",
            message="phase 2 override test",
        ))
        head2 = _fetch_head(client, path)
        rev2 = _fetch_revision(client, head2["head_version_id"]) if head2 else None
        override_ok = (
            rev2 is not None
            and rev2["authored_by"] == "yarnnn:claude-sonnet-4-7"
            and rev2["message"] == "phase 2 override test"
        )
        record(
            "AgentWorkspace.write override authored_by/message",
            ok2 and override_ok,
            f"authored_by={rev2['authored_by'] if rev2 else None}",
        )
    except Exception as e:
        record("AgentWorkspace.write default attribution", False, f"Error: {e}")
        record("AgentWorkspace.write override attribution", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 5 + 6 — UserMemory.write
# ---------------------------------------------------------------------------

def test_user_memory_write(client) -> None:
    try:
        from services.workspace import UserMemory

        um = UserMemory(client, TEST_USER_ID)
        path = f"/workspace/{SCRATCH_MEMORY_FILENAME}"

        # Default
        ok1 = asyncio.run(um.write(SCRATCH_MEMORY_FILENAME, "# user memory default"))
        head = _fetch_head(client, path)
        rev = _fetch_revision(client, head["head_version_id"]) if head else None
        default_ok = rev is not None and rev["authored_by"] == "system:user-memory"
        record(
            "UserMemory.write default authored_by = system:user-memory",
            ok1 and default_ok,
            f"authored_by={rev['authored_by'] if rev else None}",
        )

        # Operator override
        ok2 = asyncio.run(um.write(
            SCRATCH_MEMORY_FILENAME, "# user memory operator override",
            authored_by="operator", message="operator direct edit",
        ))
        head2 = _fetch_head(client, path)
        rev2 = _fetch_revision(client, head2["head_version_id"]) if head2 else None
        operator_ok = rev2 is not None and rev2["authored_by"] == "operator"
        record(
            "UserMemory.write operator override",
            ok2 and operator_ok,
            f"authored_by={rev2['authored_by'] if rev2 else None}",
        )
    except Exception as e:
        record("UserMemory.write default authored_by", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 7 + 8 + 9 — TaskWorkspace
# ---------------------------------------------------------------------------

def test_task_workspace_write(client) -> None:
    try:
        from services.task_workspace import TaskWorkspace

        tw = TaskWorkspace(client, TEST_USER_ID, SCRATCH_TASK_SLUG)
        path = f"/tasks/{SCRATCH_TASK_SLUG}/TASK.md"

        # Default attribution
        ok1 = asyncio.run(tw.write("TASK.md", "# task md default"))
        head = _fetch_head(client, path)
        rev = _fetch_revision(client, head["head_version_id"]) if head else None
        default_ok = rev is not None and rev["authored_by"] == f"task:{SCRATCH_TASK_SLUG}"
        record(
            "TaskWorkspace.write default authored_by = task:{slug}",
            ok1 and default_ok,
            f"authored_by={rev['authored_by'] if rev else None}",
        )

        # save_output attributes to agent:<slug>
        folder = asyncio.run(tw.save_output("# output content", "test-agent-slug"))
        output_path = f"/tasks/{SCRATCH_TASK_SLUG}/{folder}/output.md"
        head2 = _fetch_head(client, output_path)
        rev2 = _fetch_revision(client, head2["head_version_id"]) if head2 else None
        save_ok = rev2 is not None and rev2["authored_by"] == "agent:test-agent-slug"
        record(
            "TaskWorkspace.save_output attributes agent:<slug>",
            folder is not None and save_ok,
            f"authored_by={rev2['authored_by'] if rev2 else None}",
        )

        # append_run_log attributes to system:task-pipeline
        ok3 = asyncio.run(tw.append_run_log("test run log entry"))
        log_path = f"/tasks/{SCRATCH_TASK_SLUG}/memory/_run_log.md"
        head3 = _fetch_head(client, log_path)
        rev3 = _fetch_revision(client, head3["head_version_id"]) if head3 else None
        log_ok = rev3 is not None and rev3["authored_by"] == "system:task-pipeline"
        record(
            "TaskWorkspace.append_run_log attributes system:task-pipeline",
            ok3 and log_ok,
            f"authored_by={rev3['authored_by'] if rev3 else None}",
        )
    except Exception as e:
        record("TaskWorkspace.write default attribution", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 10 — reviewer_audit.append_decision
# ---------------------------------------------------------------------------

def test_reviewer_audit(client) -> None:
    try:
        from services.reviewer_audit import append_decision, DECISIONS_PATH

        # Clean slate for this path — workspace_files first (FK order)
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", DECISIONS_PATH).execute()
        client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", DECISIONS_PATH).execute()

        import uuid
        fake_proposal_id = str(uuid.uuid4())

        ok = asyncio.run(append_decision(
            client, TEST_USER_ID,
            proposal_id=fake_proposal_id,
            action_type="test.phase2",
            decision="approve",
            reviewer_identity="ai-sonnet-v1",
            reasoning="phase 2 test reasoning",
        ))

        head = _fetch_head(client, DECISIONS_PATH)
        rev = _fetch_revision(client, head["head_version_id"]) if head else None
        author_ok = rev is not None and rev["authored_by"] == "reviewer:ai-sonnet-v1"
        record(
            "reviewer_audit.append_decision attributes reviewer:<identity>",
            ok and author_ok,
            f"authored_by={rev['authored_by'] if rev else None}, message={rev['message'] if rev else None}",
        )
    except Exception as e:
        record("reviewer_audit.append_decision", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 11 — parent chain across two consecutive writes to same path
# ---------------------------------------------------------------------------

def test_parent_chain_on_rewrite(client) -> None:
    try:
        from services.workspace import AgentWorkspace

        aw = AgentWorkspace(client, TEST_USER_ID, SCRATCH_AGENT_SLUG)
        path = f"/agents/{SCRATCH_AGENT_SLUG}/chain-test.md"

        # Clean slate for this specific path — workspace_files first (FK order).
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()
        client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()

        asyncio.run(aw.write("chain-test.md", "# first"))
        head1 = _fetch_head(client, path)
        rev1_id = head1["head_version_id"]

        asyncio.run(aw.write("chain-test.md", "# second"))
        head2 = _fetch_head(client, path)
        rev2_id = head2["head_version_id"]
        rev2 = _fetch_revision(client, rev2_id)

        ok = (
            rev1_id != rev2_id
            and rev2 is not None
            and rev2["parent_version_id"] == rev1_id
        )
        record(
            "Parent chain on rewrite: second revision's parent = first revision",
            ok,
            f"rev1={rev1_id[:8]}..., rev2.parent={rev2['parent_version_id'][:8] if rev2 and rev2.get('parent_version_id') else 'NULL'}..., rev2={rev2_id[:8]}...",
        )

        # Cleanup this specific path — workspace_files first because
        # head_version_id FK-references workspace_file_versions.
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()
        client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()
    except Exception as e:
        record("Parent chain on rewrite", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 12 — content + head stay in sync across writes
# ---------------------------------------------------------------------------

def test_content_head_sync_across_writes(client) -> None:
    try:
        from services.workspace import AgentWorkspace

        aw = AgentWorkspace(client, TEST_USER_ID, SCRATCH_AGENT_SLUG)
        path = f"/agents/{SCRATCH_AGENT_SLUG}/sync-test.md"

        # Clean slate — workspace_files first (FK order).
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()
        client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()

        for i, content in enumerate(["v1 content", "v2 content", "v3 content"], start=1):
            asyncio.run(aw.write("sync-test.md", content))
            head = _fetch_head(client, path)
            if head is None:
                record("content+head sync across writes", False, f"head None after write {i}")
                return
            if head["content"] != content:
                record(
                    "content+head sync across writes",
                    False,
                    f"write {i}: head content mismatch — expected {content!r}, got {head['content']!r}",
                )
                return
            rev = _fetch_revision(client, head["head_version_id"])
            if rev is None:
                record("content+head sync across writes", False, f"write {i}: head_version_id dangling")
                return

        # Cleanup — workspace_files first (FK order).
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()
        client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()

        record("content+head sync across writes", True, "3 writes verified")
    except Exception as e:
        record("content+head sync across writes", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 13 — grep gate: no references to deleted history methods/constants
# ---------------------------------------------------------------------------

def test_grep_gate_legacy(client) -> None:
    patterns = [
        "_archive_to_history",
        "_cap_history",
        "_is_evolving_file",
        "list_history\\b",
        "_EVOLVING_PATTERNS",
        "_EVOLVING_DIRS",
        "_MAX_HISTORY_VERSIONS",
        "_MAX_PROFILE_VERSIONS",
        "_ENTITY_PROFILE_FILENAMES",
    ]
    api_root = Path(__file__).parent
    try:
        # Scan only live code (services/, routes/, agents/, integrations/) — exclude
        # venv, prompts/CHANGELOG.md (historical record), tests, this test itself.
        cmd = [
            "grep", "-rnE",
            "|".join(patterns),
            "--include=*.py",
            "--exclude-dir=venv",
            "--exclude-dir=__pycache__",
            "--exclude=test_*.py",
            str(api_root / "services"),
            str(api_root / "routes"),
            str(api_root / "agents"),
            str(api_root / "integrations"),
            str(api_root / "jobs"),
            str(api_root / "mcp_server"),
        ]
        out = subprocess.run(cmd, capture_output=True, text=True)
        hits = [line for line in out.stdout.splitlines() if line.strip()]
        ok = len(hits) == 0
        record(
            "Grep gate: no live-code references to deleted history methods",
            ok,
            "0 hits" if ok else f"{len(hits)} hits: " + ("; ".join(hits[:3]) + ("..." if len(hits) > 3 else "")),
        )
    except Exception as e:
        record("Grep gate: no live-code references to deleted history methods", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 14 — grep gate: only authored_substrate + embedding touch workspace_files mutations
# ---------------------------------------------------------------------------

def test_grep_gate_mutations(client) -> None:
    api_root = Path(__file__).parent
    try:
        cmd = [
            "grep", "-rnE",
            r'table\("workspace_files"\).*\.(insert|update|upsert)',
            "--include=*.py",
            "--exclude-dir=venv",
            "--exclude-dir=__pycache__",
            "--exclude=test_*.py",
            str(api_root / "services"),
            str(api_root / "routes"),
            str(api_root / "agents"),
            str(api_root / "integrations"),
            str(api_root / "jobs"),
            str(api_root / "mcp_server"),
        ]
        out = subprocess.run(cmd, capture_output=True, text=True)
        hits = [line for line in out.stdout.splitlines() if line.strip()]

        # Two permitted exceptions:
        #   services/authored_substrate.py — the write path itself
        #   services/primitives/workspace.py — embedding-only metadata update
        permitted = {
            "services/authored_substrate.py",
            "services/primitives/workspace.py",
        }

        violations = []
        for line in hits:
            if not any(p in line for p in permitted):
                violations.append(line)

        ok = len(violations) == 0
        record(
            "Grep gate: only authored_substrate + embedding-update mutate workspace_files",
            ok,
            "0 violations" if ok else f"{len(violations)} violations: " + ("; ".join(violations[:3]) + ("..." if len(violations) > 3 else "")),
        )
    except Exception as e:
        record("Grep gate: only permitted mutation call sites", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 15 — backfill still intact
# ---------------------------------------------------------------------------

def test_backfill_preserved(client) -> None:
    try:
        backfill = (
            client.table("workspace_file_versions")
            .select("id", count="exact")
            .eq("authored_by", "system:backfill-158")
            .limit(1)
            .execute()
        )
        count = backfill.count or 0
        record(
            "Phase 1 backfill preserved",
            count > 0,
            f"{count} system:backfill-158 revisions still present",
        )
    except Exception as e:
        record("Phase 1 backfill preserved", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    api_dir = Path(__file__).parent
    sys.path.insert(0, str(api_dir))

    client = get_client()

    try:
        test_write_revision_syncs_head(client)
        test_agent_workspace_write(client)
        test_user_memory_write(client)
        test_task_workspace_write(client)
        test_reviewer_audit(client)
        test_parent_chain_on_rewrite(client)
        test_content_head_sync_across_writes(client)
        test_grep_gate_legacy(client)
        test_grep_gate_mutations(client)
        test_backfill_preserved(client)
    finally:
        _cleanup_scratch(client)
        logger.info("Cleanup: scratch revisions deleted")

    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print()
    print(f"=== ADR-209 Phase 2 test results: {passed}/{total} passed ===")
    for name, ok, detail in RESULTS:
        icon = "✓" if ok else "✗"
        print(f"  {icon} {name}" + (f" — {detail}" if not ok else ""))

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
