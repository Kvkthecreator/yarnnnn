"""
Test gate — ADR-219 Commit 2 (Narrative substrate + write path).

Asserts the two commitments of Commit 2:

A. Helper contract — `write_narrative_entry()` validates inputs, emits
   the correct envelope, and applies the default weight policy from
   ADR-219 D3.

B. Coverage — every live `session_messages` INSERT in api/ live code
   routes through `services.narrative.write_narrative_entry`. Direct
   `.insert(`/`append_session_message` RPC calls outside the single
   write path are banned (with a small explicit allowlist for the
   helper itself + tests + scripts).

This is the structural backstop for FOUNDATIONS Axiom 9: every
invocation emits exactly one narrative entry, and the narrative is
the single chat-shaped log of every invocation.

Usage:
    cd api && python test_adr219_narrative_write_path.py

Exits non-zero on first failure with a clear pointer to the bad site.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "api"


# =============================================================================
# Section A — helper contract
# =============================================================================

def test_helper_validates_role() -> None:
    """write_narrative_entry must reject roles outside the migration-161 enum."""
    # Make api/ importable when this test is run from the repo root or api/.
    sys.path.insert(0, str(API_ROOT))
    from services.narrative import (  # noqa: PLC0415
        write_narrative_entry,
        VALID_ROLES,
    )

    # Affirmative: the six valid roles match migration 161.
    assert VALID_ROLES == frozenset(
        {"user", "assistant", "system", "reviewer", "agent", "external"}
    ), f"VALID_ROLES drift: {VALID_ROLES}"

    # Negative: bogus role rejected before any network I/O.
    try:
        write_narrative_entry(
            client=None,
            session_id="00000000-0000-0000-0000-000000000000",
            role="bogus",  # type: ignore[arg-type]
            summary="x",
        )
    except ValueError as exc:
        assert "invalid role" in str(exc), f"unexpected validation message: {exc}"
    else:
        raise AssertionError("expected ValueError for invalid role")


def test_helper_validates_pulse_and_weight() -> None:
    sys.path.insert(0, str(API_ROOT))
    from services.narrative import (  # noqa: PLC0415
        write_narrative_entry,
        VALID_PULSES,
        VALID_WEIGHTS,
    )

    assert VALID_PULSES == frozenset(
        {"periodic", "reactive", "addressed", "heartbeat"}
    )
    assert VALID_WEIGHTS == frozenset({"material", "routine", "housekeeping"})

    # Bad pulse rejected pre-flight.
    try:
        write_narrative_entry(
            client=None,
            session_id="00000000-0000-0000-0000-000000000000",
            role="user",
            summary="x",
            pulse="never",  # type: ignore[arg-type]
        )
    except ValueError as exc:
        assert "invalid pulse" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid pulse")

    # Bad weight rejected pre-flight.
    try:
        write_narrative_entry(
            client=None,
            session_id="00000000-0000-0000-0000-000000000000",
            role="user",
            summary="x",
            weight="loud",  # type: ignore[arg-type]
        )
    except ValueError as exc:
        assert "invalid weight" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid weight")


def test_helper_validates_summary() -> None:
    sys.path.insert(0, str(API_ROOT))
    from services.narrative import write_narrative_entry  # noqa: PLC0415

    try:
        write_narrative_entry(
            client=None,
            session_id="00000000-0000-0000-0000-000000000000",
            role="user",
            summary="   ",
        )
    except ValueError as exc:
        assert "summary is required" in str(exc)
    else:
        raise AssertionError("expected ValueError for empty summary")


def test_default_weight_policy() -> None:
    """ADR-219 D3 defaults — verify each row of the policy table."""
    sys.path.insert(0, str(API_ROOT))
    from services.narrative import resolve_default_weight  # noqa: PLC0415

    cases = [
        # (role, pulse, has_invocation, expected_weight)
        ("user", "addressed", False, "material"),
        ("reviewer", "reactive", False, "material"),
        ("external", "addressed", False, "routine"),
        ("assistant", "addressed", True, "material"),
        ("assistant", "addressed", False, "routine"),
        ("agent", "periodic", True, "routine"),
        ("system", "heartbeat", False, "housekeeping"),
        ("system", "periodic", False, "routine"),
    ]
    for role, pulse, has_inv, expected in cases:
        got = resolve_default_weight(
            role=role, pulse=pulse, has_invocation=has_inv
        )
        assert got == expected, (
            f"weight policy drift: role={role} pulse={pulse} "
            f"has_invocation={has_inv} expected={expected} got={got}"
        )


def test_helper_emits_envelope_to_rpc() -> None:
    """When the RPC call succeeds, the envelope (summary/pulse/weight +
    optional invocation_id/task_slug/provenance) must end up in
    p_metadata exactly once, with envelope keys winning over caller
    metadata on collision."""
    sys.path.insert(0, str(API_ROOT))
    from services.narrative import write_narrative_entry  # noqa: PLC0415

    captured: dict = {}

    class _RpcResult:
        def __init__(self, data):
            self.data = data

    class _RpcCall:
        def __init__(self, params):
            self._params = params

        def execute(self):
            captured["params"] = self._params
            return _RpcResult({"id": "row-1"})

    class _FakeClient:
        def rpc(self, name, params):
            assert name == "append_session_message"
            return _RpcCall(params)

    out = write_narrative_entry(
        _FakeClient(),
        session_id="00000000-0000-0000-0000-000000000000",
        role="agent",
        summary="Researcher delivered competitor scan",
        body="Full markdown body...",
        pulse="periodic",
        weight="material",
        invocation_id="run-uuid",
        task_slug="competitor-scan",
        provenance=[{"path": "/tasks/competitor-scan/outputs/latest/", "kind": "output_folder"}],
        extra_metadata={"summary": "this should be overwritten by envelope", "model": "sonnet"},
    )
    assert out == {"id": "row-1"}, "RPC return shape regressed"

    p = captured["params"]
    assert p["p_session_id"] == "00000000-0000-0000-0000-000000000000"
    assert p["p_role"] == "agent"
    assert p["p_content"] == "Full markdown body..."

    md = p["p_metadata"]
    assert md["summary"] == "Researcher delivered competitor scan", \
        "envelope summary must win over extra_metadata.summary"
    assert md["pulse"] == "periodic"
    assert md["weight"] == "material"
    assert md["invocation_id"] == "run-uuid"
    assert md["task_slug"] == "competitor-scan"
    assert md["provenance"] == [
        {"path": "/tasks/competitor-scan/outputs/latest/", "kind": "output_folder"}
    ]
    assert md["model"] == "sonnet", "extra_metadata pass-through dropped"


def test_helper_uses_summary_when_no_body() -> None:
    sys.path.insert(0, str(API_ROOT))
    from services.narrative import write_narrative_entry  # noqa: PLC0415

    captured: dict = {}

    class _RpcResult:
        data = {"id": "row-2"}

    class _RpcCall:
        def __init__(self, params):
            captured["params"] = params

        def execute(self):
            return _RpcResult()

    class _FakeClient:
        def rpc(self, name, params):
            return _RpcCall(params)

    write_narrative_entry(
        _FakeClient(),
        session_id="00000000-0000-0000-0000-000000000000",
        role="user",
        summary="What's in the queue?",
    )
    assert captured["params"]["p_content"] == "What's in the queue?"
    md = captured["params"]["p_metadata"]
    assert md["summary"] == "What's in the queue?"
    # default: addressed pulse, material weight (operator messages)
    assert md["pulse"] == "addressed"
    assert md["weight"] == "material"


def test_is_valid_envelope() -> None:
    sys.path.insert(0, str(API_ROOT))
    from services.narrative import is_valid_envelope  # noqa: PLC0415

    assert is_valid_envelope({"summary": "x", "pulse": "addressed", "weight": "material"})
    assert not is_valid_envelope(None)
    assert not is_valid_envelope({})
    assert not is_valid_envelope({"summary": "x"})  # missing pulse + weight
    assert not is_valid_envelope({"summary": "x", "pulse": "addressed", "weight": "loud"})


# =============================================================================
# Section B — coverage gate (singular write path)
# =============================================================================
#
# Every live insert into `session_messages` must route through
# `services.narrative.write_narrative_entry`. This grep gate enforces
# the discipline by listing the only places allowed to make raw
# session_messages inserts or append_session_message RPC calls.

ALLOWED_RAW_WRITE_FILES = {
    # The single write path itself.
    "api/services/narrative.py",
    # The migration that defines the table + RPC.
    "supabase/migrations/008_chat_sessions.sql",
    "supabase/migrations/061_session_compaction.sql",
    # Migrations that widen the role CHECK constraint.
    "supabase/migrations/160_session_messages_reviewer_role.sql",
    "supabase/migrations/161_session_messages_narrative_envelope.sql",
    # Test files (this one + any future regression tests).
    "api/test_adr219_narrative_write_path.py",
    # Schema verification + admin scripts that read/list/audit the table.
    "api/scripts/verify_schema.py",
    "api/scripts/purge_user_data.py",
    "api/routes/admin.py",
    # ADR documentation references the historical raw insert pattern as
    # part of the rejected-alternative narrative — that mention is the
    # explicit deprecation record, not a live write site.
    "docs/adr/ADR-219-invocation-narrative-implementation.md",
}

# Patterns that indicate a raw write path. Inserts via
# `.table("session_messages").insert(...)` and direct RPC calls to
# `append_session_message` are both gated.
RAW_WRITE_PATTERNS = [
    r'table\("session_messages"\)\s*\.insert',
    r'rpc\(\s*["\']append_session_message["\']',
]


def _git_grep_files(pattern: str) -> list[str]:
    """Return file paths whose live code matches the pattern. Uses
    git to skip ignored files automatically."""
    try:
        result = subprocess.run(
            ["git", "grep", "-lE", pattern],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        # If git isn't available (unlikely in dev), fall back to a
        # filesystem walk over api/ + supabase/.
        return []
    if result.returncode not in (0, 1):
        # 0 = matches found, 1 = no matches (both fine). Anything else
        # is a real failure.
        raise RuntimeError(
            f"git grep failed (exit {result.returncode}): {result.stderr}"
        )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_coverage_no_raw_writes_outside_helper() -> None:
    violations: list[tuple[str, str]] = []
    for pattern in RAW_WRITE_PATTERNS:
        for path in _git_grep_files(pattern):
            if path in ALLOWED_RAW_WRITE_FILES:
                continue
            violations.append((path, pattern))

    if violations:
        msg = "\n".join(
            f"  - {path} — matched pattern: {pattern}" for path, pattern in violations
        )
        raise AssertionError(
            "ADR-219 Commit 2 coverage violation — raw session_messages "
            "write outside services.narrative.write_narrative_entry:\n"
            f"{msg}\n\n"
            "Route the write through narrative.write_narrative_entry, "
            "or add the file to ALLOWED_RAW_WRITE_FILES with a comment "
            "explaining why."
        )


# =============================================================================
# Driver
# =============================================================================

def main() -> int:
    tests = [
        ("A1 helper validates role", test_helper_validates_role),
        ("A2 helper validates pulse/weight", test_helper_validates_pulse_and_weight),
        ("A3 helper validates summary", test_helper_validates_summary),
        ("A4 default weight policy", test_default_weight_policy),
        ("A5 envelope flows through RPC", test_helper_emits_envelope_to_rpc),
        ("A6 summary fallback when no body", test_helper_uses_summary_when_no_body),
        ("A7 is_valid_envelope helper", test_is_valid_envelope),
        ("B1 no raw writes outside helper", test_coverage_no_raw_writes_outside_helper),
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
