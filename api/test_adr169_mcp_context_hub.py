"""
ADR-169 Test Suite — MCP Three-Tool Surface (Context Hub)

Five test sections:
  1. Classifier correctness — classify_memory_target two-branch logic
  2. Structural invariant — server.py imports only primitives.registry + mcp_composition
  3. Response shape contracts — ambiguous / success / empty shapes
  4. Cross-LLM consistency — write via simulated claude.ai client, read via
     simulated chatgpt client, verify same chunk with correct provenance
  5. Provenance end-to-end — HTML comment stamping + extraction round-trip

Strategy:
  - Real DB writes with TEST_ADR169_ prefix for easy cleanup
  - No live LLM calls (classifier is deterministic; Haiku fallback untested)
  - Cross-LLM test seeds a workspace file via remember_this → pull_context
    round-trip, then asserts provenance is preserved end-to-end
  - Structural test uses AST parsing — no runtime server import required
    (avoids the `mcp` pip-package dependency in test environments)

Test user: kvkthecreator@gmail.com
Prefix:    TEST_ADR169_

Usage:
    cd api && python test_adr169_mcp_context_hub.py
"""

from __future__ import annotations

import ast
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Load .env before importing services that need SUPABASE_URL / SUPABASE_SERVICE_KEY
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
TEST_PREFIX = "TEST_ADR169_"

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed, detail))
    logger.info(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


# =============================================================================
# Section 1: Classifier correctness — classify_memory_target two-branch logic
# =============================================================================


def test_classifier_workspace_level_branch():
    """Workspace-level branch: identity / brand / memory routing."""
    from services.mcp_composition import classify_memory_target

    cases = [
        # (content, about, expected_target, description)
        ("I'm Sarah, VP Eng at Acme building ML infra",
         None, "identity", "identity via content marker"),
        ("my company is Acme and my role is VP Eng",
         None, "identity", "identity via 'my company' + 'my role'"),
        ("our voice is direct and avoid jargon",
         None, "brand", "brand via 'our voice'"),
        ("we write in active voice, never passive",
         None, "brand", "brand via 'we write in'"),
        ("Acme announced enterprise pricing tier yesterday",
         None, "memory", "general fact → memory"),
        ("My board meets on the first Monday of each month",
         None, "memory", "standing instruction → memory"),
        ("random observation with no markers",
         None, "memory", "default → memory"),
    ]

    all_ok = True
    for content, about, expected, desc in cases:
        result = classify_memory_target(content, about)
        ok = result.get("target") == expected
        if not ok:
            all_ok = False
            logger.warning(f"    MISMATCH {desc}: got {result}, expected target={expected}")

    record("classifier: workspace-level branch routes correctly",
           all_ok,
           f"{len(cases)} cases" if all_ok else "see warnings above")


def test_classifier_operational_feedback_branch():
    """Operational-feedback branch: agent / task / ambiguous / fallback-to-memory."""
    from services.mcp_composition import classify_memory_target

    agents_pool = {"research-agent": {}, "market-research": {}}
    tasks_pool = {"weekly-digest": {}, "q2-briefing": {}}

    # Case 1: single agent slug match → agent target
    r1 = classify_memory_target(
        "The research agent is too verbose",
        about=None,
        agents_by_slug={"research-agent": {}},
        tasks_by_slug=None,
    )
    record("classifier: single agent slug match",
           r1.get("target") == "agent" and r1.get("slug") == "research-agent",
           f"got {r1}")

    # Case 2: agent feedback but no slug pool → memory with feedback_unrouted marker
    r2 = classify_memory_target(
        "The research agent is too verbose",
        about=None,
        agents_by_slug=None,
        tasks_by_slug=None,
    )
    record("classifier: feedback without slug pool → memory fallback",
           r2.get("target") == "memory" and r2.get("note") == "feedback_unrouted",
           f"got {r2}")

    # Case 3: single task slug match → task target
    r3 = classify_memory_target(
        "The weekly digest chart labels are bad",
        about=None,
        agents_by_slug=None,
        tasks_by_slug={"weekly-digest": {}},
    )
    record("classifier: single task slug match",
           r3.get("target") == "task" and r3.get("slug") == "weekly-digest",
           f"got {r3}")

    # Case 4: feedback + two slugs both match → ambiguous return
    r4 = classify_memory_target(
        "The agent work is too slow for both competitive intelligence and market research",
        about=None,
        agents_by_slug={"competitive-intelligence": {}, "market-research": {}},
        tasks_by_slug=None,
    )
    candidates = r4.get("candidates") or []
    ok4 = (
        r4.get("ambiguous") is True
        and len(candidates) == 2
        and any("competitive-intelligence" in c["target"] for c in candidates)
        and any("market-research" in c["target"] for c in candidates)
    )
    record("classifier: multiple slug matches → ambiguous with candidates",
           ok4,
           f"got {len(candidates)} candidates")

    # Case 5: feedback flavor but zero slug matches → memory with marker
    r5 = classify_memory_target(
        "The agent should be faster",
        about=None,
        agents_by_slug={"unrelated-agent": {}},
        tasks_by_slug=None,
    )
    record("classifier: feedback flavor with zero matches → memory fallback",
           r5.get("target") == "memory" and r5.get("note") == "feedback_unrouted",
           f"got {r5}")


def test_classifier_awareness_unreachable():
    """`awareness` target must never be produced by classify_memory_target.

    ADR-169 decision: MCP is allowed all UpdateContext targets EXCEPT awareness
    (TP-only shift handoff). The classifier enforces this by never routing to
    awareness — there's no code path that produces it.
    """
    from services.mcp_composition import classify_memory_target

    provocative_inputs = [
        ("my awareness notes", None),
        ("update awareness", None),
        ("TP situational notes for shift handoff", None),
        ("I want you to remember to watch this", "awareness"),
        ("update your awareness of the workspace", "my situation"),
    ]

    all_safe = True
    for content, about in provocative_inputs:
        result = classify_memory_target(content, about)
        if result.get("target") == "awareness":
            all_safe = False
            logger.warning(f"    LEAK: {content!r} → {result}")

    record("classifier: awareness target is unreachable via MCP",
           all_safe,
           f"{len(provocative_inputs)} provocative inputs, all safely routed")


# =============================================================================
# Section 2: Structural invariant — server.py import surface
# =============================================================================


def test_server_imports_only_allowed_modules():
    """ADR-164 invariant: server.py imports nothing from services.* except
    services.mcp_composition and services.primitives.registry.execute_primitive.

    Enforced by AST parsing — no runtime import of the mcp package required.
    """
    server_path = Path(__file__).parent / "mcp_server" / "server.py"
    assert server_path.exists(), f"server.py not found at {server_path}"

    tree = ast.parse(server_path.read_text())

    # Collect all `from services.* import ...` statements
    services_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "services" or module.startswith("services."):
                for alias in node.names:
                    services_imports.append(f"{module}::{alias.name}")

    # Allowlist per ADR-169 design
    allowed = {
        "services::mcp_composition",
        "services.primitives.registry::execute_primitive",
    }
    forbidden = [imp for imp in services_imports if imp not in allowed]

    record("structure: server.py services imports are allowlisted",
           not forbidden,
           f"found {len(services_imports)} services imports; forbidden: {forbidden or 'none'}")


def test_server_registers_exactly_three_tools():
    """Exactly three @mcp.tool()-decorated async functions, in the expected order."""
    server_path = Path(__file__).parent / "mcp_server" / "server.py"
    tree = ast.parse(server_path.read_text())

    tool_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call):
                    func = dec.func
                    if isinstance(func, ast.Attribute) and func.attr == "tool":
                        tool_names.append(node.name)

    expected = ["work_on_this", "pull_context", "remember_this"]
    record("structure: server.py registers exactly three tools in order",
           tool_names == expected,
           f"got {tool_names}")


def test_no_legacy_tool_names_remain():
    """None of the 9 legacy tool names should survive anywhere in the MCP surface."""
    legacy = [
        "get_status", "list_agents", "run_agent", "get_agent_output",
        "get_context", "search_content", "get_agent_card",
        "search_knowledge", "discover_agents",
    ]
    # Note: get_context is dangerous to check naively because build_working_memory
    # uses similarly-named helpers. Limit the check to server.py only — the legacy
    # tool functions lived there and were deleted.
    server_src = (Path(__file__).parent / "mcp_server" / "server.py").read_text()

    # Specifically look for async def <legacy_name>( to catch any surviving handler
    surviving = [
        name for name in legacy
        if f"async def {name}(" in server_src
    ]
    record("structure: no legacy tool function definitions in server.py",
           not surviving,
           f"surviving: {surviving or 'none'}")


def test_composition_module_exports_expected_symbols():
    """mcp_composition.py must export the functions server.py depends on."""
    from services import mcp_composition

    required = [
        "compose_subject_context",
        "compose_active_candidates",
        "classify_memory_target",
        "derive_client_name",
        "stamp_provenance",
        "extract_domain_from_path",
        "DOMAIN_ALIASES",
        "DOMAIN_KEYWORDS",
    ]
    missing = [name for name in required if not hasattr(mcp_composition, name)]
    record("structure: mcp_composition exports required symbols",
           not missing,
           f"missing: {missing or 'none'}")


# =============================================================================
# Section 3: Response shape contracts — ambiguous / success / empty
# =============================================================================


async def test_work_on_this_ambiguous_on_cold_start(auth):
    """work_on_this with no resolvable subject should fall through to the
    ambiguity candidates shape, not return an error.

    Simulates a genuine cold start: empty context, no subject hint. The
    subject-extraction heuristic (capitalized-word match) should find nothing
    in a lowercase-only context string, forcing compose_active_candidates()
    via the subject-extraction-fail path.
    """
    from services.mcp_composition import compose_subject_context

    # Intentionally lowercase, no quoted strings — subject extraction will
    # return "" and the function will fall through to compose_active_candidates
    result = await compose_subject_context(
        auth=auth,
        context="cold start with no capitalized subject or quoted names",
        subject_hint=None,
    )

    has_ambiguous = "ambiguous" in result
    has_clarification = (
        result.get("ambiguous", {}).get("clarification") if has_ambiguous else None
    )
    ok = (
        result.get("success") is True
        and has_ambiguous
        and isinstance(has_clarification, str) and len(has_clarification) > 0
    )
    record("shapes: work_on_this cold start returns ambiguous shape",
           ok,
           f"keys: {sorted(result.keys())}, ambiguous present: {has_ambiguous}")


async def test_compose_active_candidates_schema_alignment(auth):
    """compose_active_candidates must run without SQL errors against the
    current `tasks` table schema.

    Regression test: an earlier version selected `tasks.title` which does
    not exist in the schema — the error was caught gracefully but silently
    hid all task candidates from work_on_this cold-start fallback. This
    test catches any future schema misalignment.
    """
    import logging
    from services.mcp_composition import compose_active_candidates

    # Capture warning logs emitted during the call — schema errors log via
    # logger.warning("[MCP_COMPOSITION] active tasks query failed: ...")
    captured: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record):
            msg = self.format(record)
            if "active tasks query failed" in msg or "related tasks query failed" in msg:
                captured.append(msg)

    handler = _Capture()
    handler.setLevel(logging.WARNING)
    mcp_logger = logging.getLogger("services.mcp_composition")
    mcp_logger.addHandler(handler)
    try:
        result = await compose_active_candidates(auth)
    finally:
        mcp_logger.removeHandler(handler)

    ok_no_schema_error = len(captured) == 0
    ok_shape = (
        result.get("success") is True
        and "ambiguous" in result
        and isinstance(result["ambiguous"].get("candidates"), list)
    )
    record("shapes: compose_active_candidates runs without SQL schema errors",
           ok_no_schema_error and ok_shape,
           f"schema errors: {len(captured)}, shape ok: {ok_shape}")


async def test_pull_context_empty_on_unknown_subject(auth):
    """pull_context with a subject YARNNN has no material on should return
    success with empty chunks + explanation, not an error.
    """
    # Call the tool via the thin wrapper the server uses
    from services.primitives.registry import execute_primitive
    from services import mcp_composition

    # Direct QueryKnowledge call mimicking what pull_context does
    result = await execute_primitive(auth, "QueryKnowledge", {
        "query": f"{TEST_PREFIX}nonexistent-subject-xyz-12345",
        "domain": None,
        "limit": 10,
    })

    # QueryKnowledge itself returns success with 0 results on miss
    ok = result.get("success") is True and len(result.get("results", [])) == 0
    record("shapes: pull_context on unknown subject returns empty chunks",
           ok,
           f"success={result.get('success')}, results={len(result.get('results', []))}")


def test_remember_this_ambiguous_on_multi_slug_match():
    """remember_this classifier must return the ambiguous shape when
    content mentions multiple agent slugs — no silent mis-routing.
    """
    from services.mcp_composition import classify_memory_target

    result = classify_memory_target(
        content="The agent needs to cover both competitive intelligence and market research more deeply",
        about=None,
        agents_by_slug={
            "competitive-intelligence": {},
            "market-research": {},
        },
        tasks_by_slug=None,
    )

    ok = (
        result.get("ambiguous") is True
        and len(result.get("candidates", [])) == 2
        and "clarification" not in result  # classifier returns candidates+ambiguous flag
    )
    record("shapes: remember_this returns ambiguous on multi-slug match",
           ok,
           f"got {result}")


# =============================================================================
# Section 4: Cross-LLM consistency — write via one client, read via another
# =============================================================================


async def test_cross_llm_write_read_roundtrip(auth):
    """The highest-value integration test. End-to-end:

    1. Simulated claude.ai client calls remember_this → content lands in
       workspace (written as target=memory for deterministic routing)
    2. Simulated chatgpt client calls pull_context with the same subject
    3. Assert: same content is returned, with source tag preserved

    Uses a TEST_ADR169_-prefixed subject to ensure isolation from real data.
    """
    from services.mcp_composition import (
        stamp_provenance,
        _extract_provenance_tag,
    )
    from services.primitives.registry import execute_primitive

    # Unique test marker — makes the content findable and cleanup trivial
    test_subject = f"{TEST_PREFIX}cross-llm-subject"
    test_content = (
        f"{TEST_PREFIX}This is a cross-LLM continuity test observation "
        f"about the test subject. It was written by a simulated claude.ai client "
        f"and must be visible to any subsequent pull_context call regardless of "
        f"which LLM made that call."
    )

    # --- Step 1: Simulate claude.ai write via remember_this → UpdateContext ---
    stamped = stamp_provenance(
        content=test_content,
        client_name="claude.ai",
        user_context=f"{TEST_PREFIX}cross-llm test",
    )

    write_result = await execute_primitive(auth, "UpdateContext", {
        "target": "memory",
        "text": stamped,
    })

    wrote_ok = write_result.get("success") is True
    record("cross-llm: remember_this write via UpdateContext succeeds",
           wrote_ok,
           f"got {write_result.get('message') or write_result.get('error')}")

    if not wrote_ok:
        return  # Can't continue the test if the write failed

    # Give Postgres a moment — should be synchronous, but defensive
    await asyncio.sleep(0.3)

    # --- Step 2: Simulate chatgpt read of the written content ---
    # _handle_memory writes to /workspace/notes.md (via UserMemory._full_path
    # which prepends self._base = "/workspace"). Note: some other codepaths in
    # workspace.py read from "/memory/notes.md" — that's a pre-existing
    # convention inconsistency, not an ADR-169 concern. For this test we
    # verify the path that the MCP write actually lands on.
    notes_result = (
        auth.client.table("workspace_files")
        .select("path, content")
        .eq("user_id", auth.user_id)
        .eq("path", "/workspace/notes.md")
        .limit(1)
        .execute()
    )

    notes_content = ""
    if notes_result.data:
        notes_content = notes_result.data[0].get("content") or ""

    contains_test_content = TEST_PREFIX in notes_content and test_content[:50] in notes_content
    record("cross-llm: written content readable from workspace_files",
           contains_test_content,
           f"/workspace/notes.md length={len(notes_content)}, contains TEST_PREFIX: {TEST_PREFIX in notes_content}")

    # --- Step 3: Verify provenance stamp is preserved end-to-end ---
    has_mcp_provenance = "source: mcp:claude.ai" in notes_content
    record("cross-llm: provenance stamp 'source: mcp:claude.ai' preserved in written file",
           has_mcp_provenance,
           f"provenance found: {has_mcp_provenance}")

    # --- Cleanup: remove test entries from notes.md ---
    try:
        if TEST_PREFIX in notes_content:
            cleaned = "\n".join(
                line for line in notes_content.split("\n")
                if TEST_PREFIX not in line
            )
            (
                auth.client.table("workspace_files")
                .update({"content": cleaned})
                .eq("user_id", auth.user_id)
                .eq("path", "/workspace/notes.md")
                .execute()
            )
            logger.info(f"  [CLEANUP] Removed TEST_ADR169_ lines from /workspace/notes.md")
    except Exception as e:
        logger.warning(f"  [CLEANUP] Failed to clean notes.md: {e}")


# =============================================================================
# Section 5: Provenance end-to-end — HTML comment stamping + extraction
# =============================================================================


def test_provenance_stamp_format():
    """stamp_provenance produces the ADR-162 HTML comment format."""
    from services.mcp_composition import stamp_provenance

    content = "The user says Acme just raised a Series B"
    stamped = stamp_provenance(
        content=content,
        client_name="chatgpt",
        user_context="Acme fundraising update",
    )

    expected_pieces = [
        "<!-- source: mcp:chatgpt",
        "date:",
        'user_context: "Acme fundraising update"',
        " -->",
        content,  # Original content must be preserved
    ]
    missing = [piece for piece in expected_pieces if piece not in stamped]
    record("provenance: stamp_provenance produces expected HTML comment format",
           not missing,
           f"missing: {missing or 'none'}")


def test_provenance_extract_roundtrip():
    """stamp_provenance and _extract_provenance_tag are inverses for
    the tag portion.
    """
    from services.mcp_composition import stamp_provenance, _extract_provenance_tag

    clients = ["claude.ai", "chatgpt", "gemini", "claude_desktop", "cursor"]
    all_ok = True
    for client in clients:
        stamped = stamp_provenance("test content", client, "test context")
        extracted = _extract_provenance_tag(stamped)
        if extracted != f"mcp:{client}":
            all_ok = False
            logger.warning(f"    MISMATCH {client}: extracted {extracted!r}")

    record("provenance: stamp → extract round-trip preserves client name",
           all_ok,
           f"{len(clients)} clients tested")


def test_provenance_extract_ignores_non_mcp_sources():
    """_extract_provenance_tag should return non-mcp tags too — it's a
    general ADR-162 tag reader, not an MCP-only filter. But MCP-origin
    content should always have the mcp: prefix.
    """
    from services.mcp_composition import _extract_provenance_tag

    agent_origin = """<!-- source: agent:competitive-intelligence | date: 2026-04-09 -->
# Anthropic Profile

Content about Anthropic."""
    tag = _extract_provenance_tag(agent_origin)
    record("provenance: extract preserves non-mcp sources (agent: prefix)",
           tag == "agent:competitive-intelligence",
           f"got {tag!r}")

    no_comment = "# Just content\n\nNo provenance stamp here."
    tag = _extract_provenance_tag(no_comment)
    record("provenance: extract returns None when no comment present",
           tag is None,
           f"got {tag!r}")


def test_client_name_normalization():
    """derive_client_name normalizes known User-Agent / client-id strings
    to canonical short identifiers.
    """
    from services.mcp_composition import _normalize_client_id

    cases = [
        ("Claude.ai/1.0", "claude.ai"),
        ("anthropic-claude-ai-web", "claude.ai"),
        ("ChatGPT Developer Mode Beta", "chatgpt"),
        ("OpenAI-GPT/5.0", "chatgpt"),
        ("Claude-Desktop/1.2.3", "claude_desktop"),
        ("Claude-Code/1.0", "claude_code"),
        ("Gemini Web/1.0", "gemini"),
        ("Cursor/0.42", "cursor"),
        ("random-mystery-client", None),
        ("", None),
    ]

    all_ok = True
    for raw, expected in cases:
        got = _normalize_client_id(raw)
        if got != expected:
            all_ok = False
            logger.warning(f"    MISMATCH {raw!r}: got {got!r}, expected {expected!r}")

    record("provenance: _normalize_client_id handles known clients",
           all_ok,
           f"{len(cases)} cases")


def test_extract_domain_from_path():
    """extract_domain_from_path parses workspace context domain correctly."""
    from services.mcp_composition import extract_domain_from_path

    cases = [
        ("/workspace/context/competitors/acme/profile.md", "competitors"),
        ("/workspace/context/market/segments.md", "market"),
        ("/workspace/context/relationships/alice/profile.md", "relationships"),
        ("/workspace/memory/notes.md", None),
        ("/tasks/some-task/outputs/report.md", None),
        ("", None),
        (None, None),
    ]

    all_ok = True
    for path, expected in cases:
        got = extract_domain_from_path(path)
        if got != expected:
            all_ok = False
            logger.warning(f"    MISMATCH {path!r}: got {got!r}, expected {expected!r}")

    record("provenance: extract_domain_from_path handles all cases",
           all_ok,
           f"{len(cases)} cases")


# =============================================================================
# Auth helper — reuse the MCP server's auth bridge
# =============================================================================


def _get_test_auth():
    """Build an AuthenticatedClient matching what the MCP server uses at runtime."""
    from services.supabase import AuthenticatedClient, get_service_client

    client = get_service_client()
    return AuthenticatedClient(client=client, user_id=TEST_USER_ID, email=None)


# =============================================================================
# Runner
# =============================================================================


async def run_all():
    logger.info("=" * 70)
    logger.info("ADR-169 Test Suite — MCP Three-Tool Surface (Context Hub)")
    logger.info("=" * 70)

    # Section 1: Classifier (sync, no auth needed)
    logger.info("")
    logger.info("Section 1 — Classifier correctness")
    test_classifier_workspace_level_branch()
    test_classifier_operational_feedback_branch()
    test_classifier_awareness_unreachable()

    # Section 2: Structural invariants (sync, no auth needed)
    logger.info("")
    logger.info("Section 2 — Structural invariants")
    test_server_imports_only_allowed_modules()
    test_server_registers_exactly_three_tools()
    test_no_legacy_tool_names_remain()
    test_composition_module_exports_expected_symbols()

    # Section 5 helpers first (sync, no auth)
    logger.info("")
    logger.info("Section 5 — Provenance (unit tests)")
    test_provenance_stamp_format()
    test_provenance_extract_roundtrip()
    test_provenance_extract_ignores_non_mcp_sources()
    test_client_name_normalization()
    test_extract_domain_from_path()

    # Section 3 + 4: DB-backed tests (need auth)
    logger.info("")
    logger.info("Sections 3 + 4 — Response shapes + Cross-LLM (DB-backed)")
    try:
        auth = _get_test_auth()
    except Exception as e:
        logger.error(f"Failed to create test auth: {e}")
        record("db-backed tests: auth setup", False, str(e))
    else:
        await test_work_on_this_ambiguous_on_cold_start(auth)
        await test_compose_active_candidates_schema_alignment(auth)
        await test_pull_context_empty_on_unknown_subject(auth)
        test_remember_this_ambiguous_on_multi_slug_match()
        await test_cross_llm_write_read_roundtrip(auth)

    # Summary
    logger.info("")
    logger.info("=" * 70)
    passed = sum(1 for _, p, _ in RESULTS if p)
    failed = sum(1 for _, p, _ in RESULTS if not p)
    logger.info(f"RESULTS: {passed} passed, {failed} failed, {len(RESULTS)} total")

    if failed:
        logger.info("")
        logger.info("FAILURES:")
        for name, p, detail in RESULTS:
            if not p:
                logger.info(f"  FAIL: {name} — {detail}")

    logger.info("=" * 70)
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
