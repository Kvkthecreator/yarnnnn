"""
E2E Test: ADR-119 Phase 2 — Project Folders

Tests the full project lifecycle:
1. ProjectWorkspace creation + PROJECT.md write/read
2. Contributions from mock agents
3. Assembly with manifest
4. API routes (CRUD via direct function calls)
5. Context injection into contributing agents
6. Cleanup

Uses real Supabase operations against workspace_files table.
"""

import asyncio
import json
import os
import sys
import logging
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test user — same as other E2E tests
TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"

# Track test data for cleanup
test_paths = []


def get_service_client():
    """Get Supabase service client."""
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


def cleanup_test_data(client):
    """Remove all test workspace files created during this test."""
    for path_prefix in ["/projects/q2-business-review/", "/agents/mock-analyst/memory/projects.json",
                        "/agents/mock-writer/memory/projects.json"]:
        try:
            client.table("workspace_files").delete().eq(
                "user_id", TEST_USER_ID
            ).like("path", f"{path_prefix}%").execute()
        except Exception:
            pass
    # Clean exact paths too
    for path in ["/agents/mock-analyst/memory/projects.json",
                 "/agents/mock-writer/memory/projects.json"]:
        try:
            client.table("workspace_files").delete().eq(
                "user_id", TEST_USER_ID
            ).eq("path", path).execute()
        except Exception:
            pass
    logger.info("[CLEANUP] Test data removed")


async def run_tests():
    client = get_service_client()

    # Pre-clean
    cleanup_test_data(client)

    from services.workspace import ProjectWorkspace, AgentWorkspace, get_project_slug

    passed = 0
    failed = 0

    def check(label, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            logger.info(f"  ✓ {label}")
        else:
            failed += 1
            logger.error(f"  ✗ {label}")

    # =========================================================================
    # Phase 1: get_project_slug
    # =========================================================================
    logger.info("\n=== Phase 1: get_project_slug ===")

    slug = get_project_slug("Q2 Business Review")
    check("slug from title", slug == "q2-business-review")

    slug2 = get_project_slug("  Hello World!!! @#$ Test  ")
    check("slug normalizes special chars", slug2 == "hello-world-test")

    slug3 = get_project_slug("")
    check("slug fallback for empty", slug3 == "unnamed-project")

    # =========================================================================
    # Phase 2: ProjectWorkspace — write + read PROJECT.md
    # =========================================================================
    logger.info("\n=== Phase 2: ProjectWorkspace write/read ===")

    pw = ProjectWorkspace(client, TEST_USER_ID, "q2-business-review")

    # Write PROJECT.md
    success = await pw.write_project(
        title="Q2 Business Review",
        intent={
            "deliverable": "Executive presentation",
            "audience": "Leadership team",
            "format": "pptx",
            "purpose": "Quarterly performance review",
        },
        contributors=[
            {"agent_slug": "mock-analyst", "expected_contribution": "Revenue data + charts"},
            {"agent_slug": "mock-writer", "expected_contribution": "Executive summary narrative"},
        ],
        assembly_spec="Combine analyst charts into slide deck with writer narrative as speaker notes.",
        delivery={"channel": "email", "target": "ceo@example.com"},
    )
    check("write_project succeeds", success is True)

    # Read PROJECT.md
    project = await pw.read_project()
    check("read_project returns dict", project is not None)
    check("title parsed", project["title"] == "Q2 Business Review")
    check("intent.deliverable parsed", project["intent"].get("deliverable") == "Executive presentation")
    check("intent.audience parsed", project["intent"].get("audience") == "Leadership team")
    check("intent.format parsed", project["intent"].get("format") == "pptx")
    check("contributors count", len(project["contributors"]) == 2)
    check("contributor slug parsed", project["contributors"][0]["agent_slug"] == "mock-analyst")
    check("assembly_spec parsed", "slide deck" in project["assembly_spec"])
    check("delivery.channel parsed", project["delivery"].get("channel") == "email")

    # =========================================================================
    # Phase 3: Core I/O operations
    # =========================================================================
    logger.info("\n=== Phase 3: Core I/O ===")

    # exists
    check("PROJECT.md exists", await pw.exists("PROJECT.md"))
    check("nonexistent doesn't exist", not await pw.exists("nonexistent.md"))

    # write + read generic file
    await pw.write("memory/preferences.md", "- Prefers concise bullet points\n- No jargon",
                   summary="Project preferences")
    prefs = await pw.read("memory/preferences.md")
    check("write + read memory file", prefs is not None and "concise bullet" in prefs)

    # list
    files = await pw.list("")
    check("list root has PROJECT.md", "PROJECT.md" in files)
    check("list root has memory/", "memory/" in files)

    memory_files = await pw.list("memory/")
    check("list memory/ has preferences.md", "preferences.md" in memory_files)

    # delete
    await pw.write("working/scratch.md", "temp", lifecycle="ephemeral")
    check("scratch exists after write", await pw.exists("working/scratch.md"))
    await pw.delete("working/scratch.md")
    check("scratch deleted", not await pw.exists("working/scratch.md"))

    # =========================================================================
    # Phase 4: Contributions
    # =========================================================================
    logger.info("\n=== Phase 4: Contributions ===")

    # Analyst contributes
    await pw.contribute("mock-analyst", "revenue-chart.md",
                        "# Revenue Chart\n\nQ2 revenue: $2.4M (+15% QoQ)",
                        summary="Revenue data")
    await pw.contribute("mock-analyst", "data-export.csv",
                        "quarter,revenue\nQ1,2100000\nQ2,2400000",
                        content_type="text/csv")

    # Writer contributes
    await pw.contribute("mock-writer", "executive-summary.md",
                        "# Executive Summary\n\nQ2 showed strong growth across all segments.",
                        summary="Narrative")

    # List contributors
    contributors = await pw.list_contributors()
    check("list_contributors returns 2", len(contributors) == 2)
    check("mock-analyst is contributor", "mock-analyst" in contributors)
    check("mock-writer is contributor", "mock-writer" in contributors)

    # List contributions per agent
    analyst_files = await pw.list_contributions("mock-analyst")
    check("analyst has 2 files", len(analyst_files) == 2)

    writer_files = await pw.list_contributions("mock-writer")
    check("writer has 1 file", len(writer_files) == 1)

    # Read a contribution
    chart = await pw.read("contributions/mock-analyst/revenue-chart.md")
    check("can read contribution", chart is not None and "$2.4M" in chart)

    # =========================================================================
    # Phase 5: Assembly
    # =========================================================================
    logger.info("\n=== Phase 5: Assembly ===")

    assembly_path = await pw.assemble(
        content="# Q2 Business Review\n\nAssembled from analyst data and writer narrative.",
        rendered_files=[{
            "path": "q2-review.pptx",
            "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "content_url": "https://storage.example.com/q2-review.pptx",
            "size_bytes": 45000,
            "role": "rendered",
        }],
        version=1,
        sources=[
            "contributions/mock-analyst/revenue-chart.md",
            "contributions/mock-writer/executive-summary.md",
        ],
    )
    check("assemble returns path", assembly_path is not None)
    check("assembly path format", assembly_path.startswith("assembly/"))

    # Read assembly output
    output = await pw.read(f"{assembly_path}/output.md")
    check("assembly output.md readable", output is not None and "Q2 Business Review" in output)

    # Read assembly manifest
    manifest_str = await pw.read(f"{assembly_path}/manifest.json")
    check("assembly manifest readable", manifest_str is not None)
    manifest = json.loads(manifest_str)
    check("manifest has project_slug", manifest.get("project_slug") == "q2-business-review")
    check("manifest has 2 files", len(manifest.get("files", [])) == 2)
    check("manifest has sources", len(manifest.get("sources", [])) == 2)
    check("manifest has rendered file", any(f["path"] == "q2-review.pptx" for f in manifest["files"]))

    # List assemblies
    assemblies = await pw.list_assemblies()
    check("list_assemblies returns 1", len(assemblies) == 1)

    # =========================================================================
    # Phase 6: Context loading
    # =========================================================================
    logger.info("\n=== Phase 6: Context loading ===")

    ctx = await pw.load_context()
    check("load_context returns content", len(ctx) > 0)
    check("context includes PROJECT.md", "Q2 Business Review" in ctx)
    check("context includes memory", "concise bullet" in ctx)

    # =========================================================================
    # Phase 7: Context injection into contributing agents
    # =========================================================================
    logger.info("\n=== Phase 7: Context injection ===")

    # Seed a mock agent workspace with projects.json
    agent_ws = AgentWorkspace(client, TEST_USER_ID, "mock-analyst")
    await agent_ws.write("AGENT.md", "# Mock Analyst\nAnalyzes revenue data.",
                         summary="Agent identity")
    await agent_ws.write("memory/projects.json",
                         json.dumps([{
                             "project_slug": "q2-business-review",
                             "title": "Q2 Business Review",
                             "expected_contribution": "Revenue data + charts",
                         }], indent=2),
                         content_type="application/json",
                         summary="Project memberships")

    agent_ctx = await agent_ws.load_context()
    check("agent context includes project", "Q2 Business Review" in agent_ctx)
    check("agent context includes expected contribution", "Revenue data + charts" in agent_ctx)
    check("agent context includes project intent", "Executive presentation" in agent_ctx)

    # Cleanup mock agent files
    await agent_ws.delete("AGENT.md")
    await agent_ws.delete("memory/projects.json")

    # =========================================================================
    # Phase 8: Primitives (CreateProject + ReadProject)
    # =========================================================================
    logger.info("\n=== Phase 8: Primitives ===")

    from services.primitives.project import handle_create_project, handle_read_project

    # Mock auth
    class MockAuth:
        def __init__(self):
            self.client = client
            self.user_id = TEST_USER_ID

    auth = MockAuth()

    # ReadProject on existing project
    read_result = await handle_read_project(auth, {"project_slug": "q2-business-review"})
    check("ReadProject success", read_result.get("success") is True)
    check("ReadProject has project", read_result.get("project", {}).get("title") == "Q2 Business Review")
    check("ReadProject has contributions", len(read_result.get("contributions", {})) == 2)
    check("ReadProject has assemblies", len(read_result.get("assemblies", [])) == 1)

    # ReadProject on nonexistent
    missing = await handle_read_project(auth, {"project_slug": "nonexistent"})
    check("ReadProject 404", missing.get("success") is False)

    # CreateProject missing title
    no_title = await handle_create_project(auth, {"title": ""})
    check("CreateProject rejects empty title", no_title.get("success") is False)

    # =========================================================================
    # Phase 9: Cleanup
    # =========================================================================
    logger.info("\n=== Phase 9: Cleanup ===")
    cleanup_test_data(client)
    check("cleanup complete", True)

    # =========================================================================
    # Summary
    # =========================================================================
    total = passed + failed
    logger.info(f"\n{'='*60}")
    logger.info(f"ADR-119 Phase 2 E2E: {passed}/{total} passed, {failed} failed")
    logger.info(f"{'='*60}")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
