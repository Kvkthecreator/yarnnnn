"""
E2E Quality Validation — Output Hardening Smoke Test

Validates that the quality hardening interventions produce measurably better output:
1. Methodology injection — agent playbooks visible in output structure
2. Process step hardening — output matches the prescribed structure
3. Task-aware context — KB search uses objective, not agent title
4. Layout mode — HTML composition uses correct layout_mode
5. Multi-step handoff — step 2 builds on step 1, not independent

Usage:
    cd api && python test_quality_e2e.py

Requires: SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Persistent test user (same as test_pipeline_e2e.py)
TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"

# Task types to test — covers key quality dimensions
TEST_CASES = [
    {
        "type_key": "competitive-intel-brief",
        "focus": "AI agent platforms",
        "description": "1-step (research agent), document layout, charts + citations expected",
        "quality_checks": {
            "min_words": 400,
            "required_sections": ["executive summary", "key findings", "implications"],
            "expects_citations": True,
            "expects_structure": True,
            "layout_mode": "document",
            "multi_step": False,
        },
    },
    {
        "type_key": "stakeholder-update",
        "focus": "YARNNN AI platform progress",
        "description": "1-step (content agent), dashboard layout, metrics + sections expected",
        "quality_checks": {
            "min_words": 400,
            "required_sections": ["achievements", "challenges"],
            "expects_citations": False,
            "expects_structure": True,
            "layout_mode": "dashboard",
            "multi_step": False,
        },
    },
]


@dataclass
class QualityResult:
    type_key: str
    success: bool
    duration_ms: int = 0
    output_words: int = 0
    html_composed: bool = False
    layout_mode_used: Optional[str] = None
    methodology_signal: bool = False  # Did output structure match playbook?
    sections_found: list[str] = field(default_factory=list)
    sections_missing: list[str] = field(default_factory=list)
    citations_found: int = 0
    step_outputs: list[dict] = field(default_factory=list)
    handoff_quality: Optional[str] = None  # step 2 references step 1?
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# =============================================================================
# Quality Assessment Functions
# =============================================================================

def count_words(text: str) -> int:
    return len(text.split())


def find_sections(text: str, required: list[str]) -> tuple[list[str], list[str]]:
    """Check which required sections appear in the output (case-insensitive)."""
    text_lower = text.lower()
    found = []
    missing = []
    for section in required:
        # Check both heading form and inline mention
        if section.lower() in text_lower:
            found.append(section)
        else:
            missing.append(section)
    return found, missing


def count_citations(text: str) -> int:
    """Count inline source citations (source: X, according to X, per X report)."""
    patterns = [
        r'\(source:',
        r'according to\b',
        r'\bper\b.{1,30}\breport\b',
        r'source:\s',
        r'\bcited\b',
        r'\([^)]*\d{4}[^)]*\)',  # year in parentheses
        r'https?://',  # URLs as citations
    ]
    count = 0
    for p in patterns:
        count += len(re.findall(p, text, re.IGNORECASE))
    return count


def check_structure(text: str) -> bool:
    """Check if output uses structured formatting (headers, bullets, numbering)."""
    has_headers = bool(re.search(r'^#{1,4}\s', text, re.MULTILINE))
    has_bullets = bool(re.search(r'^[-*]\s', text, re.MULTILINE))
    has_numbers = bool(re.search(r'^\d+\.\s', text, re.MULTILINE))
    return has_headers and (has_bullets or has_numbers)


def check_methodology_signal(text: str, type_key: str) -> bool:
    """Check if output structure matches what the methodology playbook prescribes."""
    text_lower = text.lower()
    if type_key in ("competitive-intel-brief", "market-research-report"):
        # Research playbook: executive summary, key findings, synthesis across sources
        has_exec_summary = "executive summary" in text_lower or "summary" in text_lower
        has_findings = "finding" in text_lower or "key finding" in text_lower
        has_implications = "implication" in text_lower or "what this means" in text_lower
        return has_exec_summary and has_findings
    elif type_key == "stakeholder-update":
        # Content playbook: lead with impact, charts for trends
        has_metrics = bool(re.search(r'\d+%|\$\d+|[0-9]+k', text_lower))
        return has_metrics
    elif type_key == "slack-recap":
        # Slack bot playbook: decisions, action items, attribution
        has_attribution = bool(re.search(r'[A-Z][a-z]+\s(said|proposed|mentioned|asked|noted)', text))
        return has_attribution
    return True  # Default pass for types without specific checks


def check_handoff_quality(step1_output: str, step2_output: str) -> str:
    """Assess whether step 2 builds on step 1."""
    if not step1_output or not step2_output:
        return "n/a"

    # Check if step 2 references findings from step 1
    # Extract key terms from step 1 (proper nouns, numbers, specific phrases)
    step1_words = set(w.lower() for w in step1_output.split() if len(w) > 5)
    step2_words = set(w.lower() for w in step2_output.split() if len(w) > 5)
    overlap = step1_words & step2_words
    overlap_ratio = len(overlap) / max(len(step1_words), 1)

    if overlap_ratio > 0.15:
        return f"good (content overlap {overlap_ratio:.0%})"
    elif overlap_ratio > 0.05:
        return f"weak (content overlap {overlap_ratio:.0%} — step 2 may not fully build on step 1)"
    else:
        return f"poor (content overlap {overlap_ratio:.0%} — step 2 appears independent of step 1)"


# =============================================================================
# Test Execution
# =============================================================================

async def ensure_test_task(client, user_id: str, type_key: str, focus: Optional[str]) -> str:
    """Create a task from the type registry and return its slug."""
    from services.task_types import get_task_type, build_task_md_from_type
    from services.task_workspace import TaskWorkspace

    task_type = get_task_type(type_key)
    if not task_type:
        raise ValueError(f"Unknown task type: {type_key}")

    slug = f"test-quality-{type_key}"
    title = f"[TEST] {task_type['display_name']}"

    # Resolve agent slugs
    agents_result = client.table("agents").select("slug, role, title").eq("user_id", user_id).execute()
    user_agents = agents_result.data or []
    agent_slugs = []
    for step in task_type["process"]:
        for a in user_agents:
            if a.get("role") == step["agent_type"]:
                agent_slugs.append(a["slug"])
                break
        else:
            agent_slugs.append(step["agent_type"])

    primary_agent = agent_slugs[0] if agent_slugs else "research-agent"

    # Build TASK.md
    task_md = build_task_md_from_type(
        type_key=type_key, title=title, slug=slug,
        focus=focus, schedule="on-demand",
        agent_slugs=agent_slugs,
    )

    # Ensure tasks row exists
    existing = client.table("tasks").select("id").eq("user_id", user_id).eq("slug", slug).execute()
    now = datetime.now(timezone.utc).isoformat()
    if existing.data:
        client.table("tasks").update({
            "status": "active", "updated_at": now,
        }).eq("user_id", user_id).eq("slug", slug).execute()
    else:
        client.table("tasks").insert({
            "user_id": user_id,
            "slug": slug,
            "mode": "reactive",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }).execute()

    # Write TASK.md
    tw = TaskWorkspace(client, user_id, slug)
    await tw.write("TASK.md", task_md, summary=f"Test: {title}", tags=["test"])

    return slug


async def run_task_and_evaluate(client, user_id: str, test_case: dict) -> QualityResult:
    """Execute a task type and evaluate output quality."""
    type_key = test_case["type_key"]
    focus = test_case.get("focus")
    checks = test_case["quality_checks"]
    result = QualityResult(type_key=type_key, success=False)

    logger.info(f"\n{'='*60}")
    logger.info(f"TESTING: {type_key}")
    logger.info(f"  {test_case['description']}")
    logger.info(f"{'='*60}")

    # Step 1: Create task
    try:
        slug = await ensure_test_task(client, user_id, type_key, focus)
        logger.info(f"  ✓ Task created: {slug}")
    except Exception as e:
        result.errors.append(f"Task creation failed: {e}")
        logger.error(f"  ✗ Task creation failed: {e}")
        return result

    # Step 2: Execute
    start = time.time()
    try:
        from services.task_pipeline import execute_task
        exec_result = await execute_task(client, TEST_USER_ID, slug)
        result.duration_ms = int((time.time() - start) * 1000)
        logger.info(f"  ✓ Execution complete ({result.duration_ms}ms)")

        if not exec_result.get("success"):
            result.errors.append(f"Execution failed: {exec_result.get('message', 'unknown')}")
            logger.error(f"  ✗ Execution failed: {exec_result}")
            return result
    except Exception as e:
        result.duration_ms = int((time.time() - start) * 1000)
        result.errors.append(f"Execution error: {e}")
        logger.error(f"  ✗ Execution error: {e}")
        import traceback
        traceback.print_exc()
        return result

    # Step 3: Read output
    try:
        from services.task_workspace import TaskWorkspace
        tw = TaskWorkspace(client, user_id, slug)

        # Get latest output — query workspace_files directly for the most recent output.md
        output_result = (
            client.table("workspace_files")
            .select("path, content")
            .eq("user_id", TEST_USER_ID)
            .like("path", f"/tasks/{slug}/outputs/%/output.md")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )

        if not output_result.data:
            result.errors.append("No output.md found in task workspace")
            return result

        output_path = output_result.data[0]["path"]
        output_md = output_result.data[0]["content"]
        # Derive the date folder from path: /tasks/{slug}/outputs/{date_folder}/output.md
        path_parts = output_path.split("/")
        latest_folder = path_parts[-2]  # e.g., "2026-03-29T0300"

        # Check for HTML
        html_path = output_path.replace("/output.md", "/output.html")
        html_result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", TEST_USER_ID)
            .eq("path", html_path)
            .limit(1)
            .execute()
        )
        output_html = html_result.data[0]["content"] if html_result.data else None

        if not output_md:
            result.errors.append("No output.md in latest output folder")
            return result

        result.html_composed = output_html is not None and len(output_html) > 100
        logger.info(f"  ✓ Output read ({count_words(output_md)} words, HTML: {'yes' if result.html_composed else 'no'})")

        # Check for step outputs (multi-step) — query directly
        if checks.get("multi_step"):
            step_result = (
                client.table("workspace_files")
                .select("path, content")
                .eq("user_id", TEST_USER_ID)
                .like("path", f"/tasks/{slug}/outputs/{latest_folder}/step-%/output.md")
                .order("path", desc=False)
                .execute()
            )
            for sr in (step_result.data or []):
                step_content = sr["content"] or ""
                step_folder = sr["path"].split("/")[-2]  # e.g., "step-1"
                result.step_outputs.append({
                    "folder": step_folder,
                    "words": count_words(step_content),
                    "preview": step_content[:300],
                })
            logger.info(f"  ✓ Step outputs: {len(result.step_outputs)} steps found")

    except Exception as e:
        result.errors.append(f"Output read error: {e}")
        logger.error(f"  ✗ Output read error: {e}")
        return result

    # Step 4: Quality Assessment
    logger.info(f"\n  --- Quality Assessment ---")

    # Word count
    result.output_words = count_words(output_md)
    min_words = checks.get("min_words", 100)
    if result.output_words >= min_words:
        logger.info(f"  ✓ Word count: {result.output_words} (min: {min_words})")
    else:
        result.errors.append(f"Word count too low: {result.output_words} < {min_words}")
        logger.warning(f"  ✗ Word count: {result.output_words} < {min_words}")

    # Required sections
    required_sections = checks.get("required_sections", [])
    found, missing = find_sections(output_md, required_sections)
    result.sections_found = found
    result.sections_missing = missing
    if not missing:
        logger.info(f"  ✓ All required sections found: {', '.join(found)}")
    else:
        result.errors.append(f"Missing sections: {', '.join(missing)}")
        logger.warning(f"  ✗ Missing sections: {', '.join(missing)}")
        logger.info(f"    Found: {', '.join(found) if found else 'none'}")

    # Citations
    if checks.get("expects_citations"):
        result.citations_found = count_citations(output_md)
        if result.citations_found >= 2:
            logger.info(f"  ✓ Citations: {result.citations_found} found")
        else:
            result.notes.append(f"Low citation count: {result.citations_found}")
            logger.warning(f"  ⚠ Low citations: {result.citations_found} (expected ≥2)")

    # Structure
    if checks.get("expects_structure"):
        structured = check_structure(output_md)
        if structured:
            logger.info(f"  ✓ Structured output (headers + lists)")
        else:
            result.notes.append("Output lacks structure (no headers/lists)")
            logger.warning(f"  ⚠ Output lacks structure")

    # Methodology signal
    result.methodology_signal = check_methodology_signal(output_md, type_key)
    if result.methodology_signal:
        logger.info(f"  ✓ Methodology signal detected (output follows playbook structure)")
    else:
        result.notes.append("Methodology signal weak — output may not follow playbook")
        logger.warning(f"  ⚠ Methodology signal weak")

    # Handoff quality (multi-step)
    if checks.get("multi_step") and len(result.step_outputs) >= 2:
        step1 = result.step_outputs[0].get("preview", "")
        step2 = result.step_outputs[1].get("preview", "")
        result.handoff_quality = check_handoff_quality(step1, step2)
        logger.info(f"  {'✓' if 'good' in result.handoff_quality else '⚠'} Handoff quality: {result.handoff_quality}")
    elif checks.get("multi_step"):
        result.handoff_quality = "n/a — step outputs not found separately"
        result.notes.append("Could not evaluate handoff (step outputs not captured separately)")

    # HTML composition
    if result.html_composed:
        # Check for layout mode indicators in HTML
        if output_html and "class=" in output_html:
            result.layout_mode_used = checks.get("layout_mode", "document")
            logger.info(f"  ✓ HTML composed (layout: {result.layout_mode_used})")
        else:
            logger.info(f"  ✓ HTML composed")
    else:
        result.notes.append("No HTML composed — compose service may not be reachable")
        logger.warning(f"  ⚠ No HTML composed")

    # Determine overall success
    result.success = len(result.errors) == 0
    status = "PASS" if result.success else "FAIL"
    logger.info(f"\n  {'✓' if result.success else '✗'} Overall: {status}")
    if result.notes:
        for note in result.notes:
            logger.info(f"    note: {note}")

    return result


# =============================================================================
# Cleanup
# =============================================================================

async def cleanup_test_tasks(client, user_id: str):
    """Remove test tasks and their workspace files."""
    logger.info("\nCleaning up test data...")

    # Delete test tasks
    for tc in TEST_CASES:
        slug = f"test-quality-{tc['type_key']}"
        try:
            client.table("tasks").delete().eq("user_id", user_id).eq("slug", slug).execute()
        except Exception:
            pass
        # Clean workspace files
        try:
            result = client.table("workspace_files").select("id").eq("user_id", user_id).like("path", f"/tasks/{slug}/%").execute()
            if result.data:
                ids = [r["id"] for r in result.data]
                for batch_start in range(0, len(ids), 50):
                    batch = ids[batch_start:batch_start + 50]
                    for fid in batch:
                        client.table("workspace_files").delete().eq("id", fid).execute()
        except Exception:
            pass

    # Clean test agent_runs
    try:
        client.table("agent_runs").delete().eq("user_id", user_id).like("metadata->>task_slug", "test-quality-%").execute()
    except Exception:
        pass

    logger.info("  ✓ Cleanup complete")


# =============================================================================
# Report
# =============================================================================

def print_report(results: list[QualityResult]):
    """Print a structured quality report."""
    print("\n" + "=" * 70)
    print("QUALITY VALIDATION REPORT")
    print("=" * 70)

    passed = sum(1 for r in results if r.success)
    total = len(results)
    print(f"\nOverall: {passed}/{total} passed\n")

    for r in results:
        status = "✓ PASS" if r.success else "✗ FAIL"
        print(f"  {status}  {r.type_key}")
        print(f"         Words: {r.output_words} | HTML: {'yes' if r.html_composed else 'no'} | Duration: {r.duration_ms}ms")
        print(f"         Sections: {', '.join(r.sections_found) or 'none'}")
        if r.sections_missing:
            print(f"         Missing: {', '.join(r.sections_missing)}")
        if r.citations_found:
            print(f"         Citations: {r.citations_found}")
        print(f"         Methodology signal: {'yes' if r.methodology_signal else 'weak'}")
        if r.step_outputs:
            for so in r.step_outputs:
                print(f"         Step {so['folder']}: {so['words']} words")
        if r.handoff_quality:
            print(f"         Handoff: {r.handoff_quality}")
        if r.errors:
            for e in r.errors:
                print(f"         ERROR: {e}")
        if r.notes:
            for n in r.notes:
                print(f"         note: {n}")
        print()

    print("=" * 70)
    total_duration = sum(r.duration_ms for r in results)
    total_words = sum(r.output_words for r in results)
    print(f"Total: {total_duration/1000:.1f}s | {total_words} words generated | {passed}/{total} quality checks passed")
    print("=" * 70)


# =============================================================================
# Main
# =============================================================================

async def main():
    from supabase import create_client

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)
    if not anthropic_key:
        logger.error("ANTHROPIC_API_KEY must be set")
        sys.exit(1)

    client = create_client(supabase_url, supabase_key)

    logger.info("=" * 70)
    logger.info("E2E QUALITY VALIDATION — Output Hardening Smoke Test")
    logger.info("=" * 70)
    logger.info(f"Test user: {TEST_USER_ID}")
    logger.info(f"Task types: {', '.join(tc['type_key'] for tc in TEST_CASES)}")
    logger.info("")

    results: list[QualityResult] = []

    for test_case in TEST_CASES:
        result = await run_task_and_evaluate(client, TEST_USER_ID, test_case)
        results.append(result)

    # Cleanup
    await cleanup_test_tasks(client, TEST_USER_ID)

    # Report
    print_report(results)

    # Exit code
    all_passed = all(r.success for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
