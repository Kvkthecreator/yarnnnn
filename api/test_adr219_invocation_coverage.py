"""
Final coverage gate — ADR-219 Commit 6.

Per ADR-219 Validation: "every invocation site in the codebase routes
through write_narrative_entry()." This test makes that commitment
mechanically enforceable.

An invocation per FOUNDATIONS Axiom 9 §1 is a cycle that visits the
Trigger dimension — the atom of action. The greppable invocation
entry points in YARNNN today:

  Periodic-pulse:
    1. api/services/task_pipeline.py::execute_task() — scheduled task runs
    2. api/services/back_office/*.py::run() — back-office executors
       (workspace_cleanup, agent_hygiene, proposal_cleanup,
        outcome_reconciliation, reviewer_calibration, reviewer_reflection,
        narrative_digest)

  Reactive-pulse:
    3. api/services/review_proposal_dispatch.py — Reviewer fires on
       proposal landing
    4. api/services/notifications.py::_insert_chat_notification — email
       send fires the chat card

  Addressed-pulse:
    5. api/routes/chat.py::append_message — operator turn + YARNNN reply
    6. api/mcp_server/server.py — work_on_this / pull_context / remember_this

This gate asserts each entry point either calls write_narrative_entry
directly or routes through one of the named helper shims. It does NOT
attempt full AST traversal — that's what the Commit 2 coverage gate
(api/test_adr219_narrative_write_path.py B1) already does for the
write-path side. This file is the SITE-side mirror: the helper exists
AND each known invocation entry point reaches it.

Failure points to a specific file + missing reference so the next
change can correct it.

Usage:
    cd api && python test_adr219_invocation_coverage.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text()


# Each entry: (file path, [acceptable references — at least one must be present]).
# The references are either:
#   - direct calls to write_narrative_entry / find_active_workspace_session
#   - imports of services.narrative
#   - calls to a known shim that delegates to the helper:
#       routes/chat.py::append_message
#       services/reviewer_chat_surfacing.py::write_reviewer_message
#       api/mcp_server/server.py::_emit_mcp_narrative
COVERAGE_SITES: list[tuple[str, list[str], str]] = [
    (
        "api/services/task_pipeline.py",
        ["from routes.chat import append_message", "_append_message"],
        "Task pipeline writes the task_complete narrative card via "
        "chat.append_message (which routes through write_narrative_entry).",
    ),
    (
        "api/services/back_office/narrative_digest.py",
        [
            "from services.narrative import",
            "write_narrative_entry",
        ],
        "Back-office narrative-digest executor emits the rolled-up "
        "material entry directly via write_narrative_entry.",
    ),
    (
        "api/services/review_proposal_dispatch.py",
        [
            "from services.reviewer_chat_surfacing import write_reviewer_message",
            "write_reviewer_message",
        ],
        "Reviewer dispatch surfaces verdicts via write_reviewer_message "
        "(which routes through write_narrative_entry per Commit 2).",
    ),
    (
        "api/services/primitives/propose_action.py",
        [
            "from services.reviewer_chat_surfacing import write_reviewer_message",
            "write_reviewer_message",
        ],
        "Approve/reject proposal handlers route through "
        "write_reviewer_message → write_narrative_entry.",
    ),
    (
        "api/services/notifications.py",
        [
            "from services.narrative import write_narrative_entry",
            "write_narrative_entry",
        ],
        "Notification chat-card insertion routes through write_narrative_entry "
        "(replaced direct append_session_message RPC in Commit 2).",
    ),
    (
        "api/routes/chat.py",
        [
            "from services.narrative import write_narrative_entry",
            "write_narrative_entry",
        ],
        "Chat append_message helper is a thin shim over write_narrative_entry "
        "(Commit 2) — every operator turn + YARNNN reply lands here.",
    ),
    (
        "api/routes/memory.py",
        [
            "from routes.chat import",
            "append_message",
        ],
        "workspace_init_complete system card writes via chat.append_message "
        "(routes through write_narrative_entry per Commit 2).",
    ),
    (
        "api/services/reviewer_chat_surfacing.py",
        [
            "from services.narrative import",
            "write_narrative_entry",
        ],
        "Reviewer chat surfacing collapsed to a single write_narrative_entry "
        "call in Commit 2.",
    ),
    (
        "api/mcp_server/server.py",
        [
            "from services.narrative import",
            "_emit_mcp_narrative",
            "write_narrative_entry",
        ],
        "MCP server (Commit 6) emits external:<client> narrative entries "
        "for work_on_this / pull_context / remember_this via the local "
        "_emit_mcp_narrative shim that delegates to write_narrative_entry.",
    ),
]


def test_invocation_sites_reach_helper() -> None:
    """Every named invocation entry point reaches write_narrative_entry."""
    failures: list[str] = []
    for path, candidates, reason in COVERAGE_SITES:
        try:
            src = _read(path)
        except FileNotFoundError:
            failures.append(
                f"{path} — file missing (expected to host an invocation site)\n  reason: {reason}"
            )
            continue
        if not any(c in src for c in candidates):
            cand_list = "\n      - ".join(candidates)
            failures.append(
                f"{path} — none of the expected helper references found.\n"
                f"  reason: {reason}\n"
                f"  expected at least one of:\n      - {cand_list}"
            )
    if failures:
        msg = "\n\n".join(failures)
        raise AssertionError(
            "ADR-219 Commit 6 coverage gate — invocation site does not "
            "reach write_narrative_entry:\n\n"
            f"{msg}\n\n"
            "Each invocation in YARNNN must emit exactly one narrative "
            "entry per FOUNDATIONS Axiom 9. Either call "
            "write_narrative_entry directly, route through one of the "
            "Commit 2 shims (chat.append_message, reviewer_chat_surfacing.write_reviewer_message), "
            "or — for new MCP-shaped sites — go through "
            "mcp_server.server._emit_mcp_narrative."
        )


def test_three_mcp_tools_emit_narrative() -> None:
    """Each of the three MCP tools must emit a narrative entry on its
    primary path (success path; failure paths covered by the file-level
    test above)."""
    src = _read("api/mcp_server/server.py")
    # Each tool must invoke _emit_mcp_narrative at least once
    occurrences = src.count("_emit_mcp_narrative(")
    # Three tools × at least one emission each = ≥3. We expect more
    # because failure/ambiguous branches also emit, but the floor is 3.
    assert occurrences >= 3, (
        f"Expected ≥3 _emit_mcp_narrative calls in mcp_server/server.py "
        f"(one per tool); found {occurrences}."
    )

    # Spot-check that each tool name appears as a `tool=` argument to the helper.
    for tool_name in ("work_on_this", "pull_context", "remember_this"):
        assert f'tool="{tool_name}"' in src, (
            f"MCP tool {tool_name!r} does not pass tool=\"{tool_name}\" to "
            f"_emit_mcp_narrative — narrative coverage incomplete."
        )


def test_helper_signature_stable() -> None:
    """The write_narrative_entry signature is the load-bearing API. If
    a future change renames a parameter, every caller breaks silently
    — guard the named-keyword shape here."""
    src = _read("api/services/narrative.py")
    # Required positional + keyword params per ADR-219 D2.
    for needle in [
        "def write_narrative_entry(",
        "session_id: str",
        "role: NarrativeRole",
        "summary: str",
        "pulse: NarrativePulse",
        "weight: Optional[NarrativeWeight]",
        "invocation_id: Optional[str]",
        "task_slug: Optional[str]",
        "provenance: Optional[list[dict[str, Any]]]",
        "extra_metadata: Optional[dict[str, Any]]",
    ]:
        assert needle in src, (
            f"write_narrative_entry signature drift: {needle!r} not found in services/narrative.py"
        )


def test_external_role_only_used_by_mcp() -> None:
    """role='external' is the Identity slot for foreign LLM callers per
    ADR-219 D1 + Axiom 2. Today the MCP server is the only legitimate
    emitter. If a non-MCP file starts using role='external', it's
    likely a copy-paste mistake and the coverage gate flags it."""
    import subprocess

    result = subprocess.run(
        ["git", "grep", "-lE", r'role="external"|role=\x27external\x27'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 1:
        return  # no matches; rare but acceptable
    if result.returncode != 0:
        raise RuntimeError(f"git grep failed: {result.stderr}")

    allowed = {
        # The MCP server is the only legitimate emitter today.
        "api/mcp_server/server.py",
        # Tests reference the role legitimately in fixtures/grep gates.
        "api/test_adr219_invocation_coverage.py",
        "api/test_adr219_narrative_write_path.py",
        "api/test_adr219_commit3_narrative_digest.py",
        "api/test_adr219_commit4_narrative_by_task.py",
        "api/test_adr219_commit5_chat_rendering.py",
        # ADR doc + canon doc legitimately discuss the role.
        "docs/adr/ADR-219-invocation-narrative-implementation.md",
        "docs/architecture/invocation-and-narrative.md",
        # CHANGELOG records the migration that added the enum value.
        "api/prompts/CHANGELOG.md",
    }
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    violators = [f for f in files if f not in allowed]
    if violators:
        raise AssertionError(
            "Files using role='external' outside the allowlist (likely "
            "non-MCP code emitting narrative entries with the wrong "
            "Identity slot):\n  " + "\n  ".join(violators)
        )


# =============================================================================
# Driver
# =============================================================================

def main() -> int:
    tests = [
        ("A1 every invocation site reaches write_narrative_entry", test_invocation_sites_reach_helper),
        ("A2 three MCP tools emit narrative", test_three_mcp_tools_emit_narrative),
        ("A3 write_narrative_entry signature stable", test_helper_signature_stable),
        ("A4 role='external' only used by MCP server (allowlist)", test_external_role_only_used_by_mcp),
    ]

    failed: list[tuple[str, BaseException]] = []
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except BaseException as exc:  # noqa: BLE001
            failed.append((name, exc))
            print(f"  ✗ {name}: {exc}")

    print()
    if failed:
        print(f"FAILED — {len(failed)}/{len(tests)} tests failed")
        return 1
    print(f"PASSED — {len(tests)}/{len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
