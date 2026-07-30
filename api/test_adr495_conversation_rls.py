"""Migration 228 gate — a conversation is readable by its CAST, in the DATABASE.

ADR-495 D2 said readability follows cast membership. Until migration 228 that
was an APPLICATION promise: `chat_sessions`/`session_messages` RLS was
`user_id = auth.uid()` (migration 008, written before conversations had a cast),
so every read was routed around it through the service client. 20 of
`routes/lanes.py`'s 24 queries ran with RLS off and the entire read binding was
Python.

This gate asserts the migration's shape and the code's alignment with it. It is
a STATIC gate — it reads SQL and source text, so it cannot prove the policies
behave. The behavioural proof is the psql probe in the commit message (9 checks
against the live DB inside a rolled-back transaction: both cast members read,
a non-participant reads nothing, the window holds and is inclusive at its floor,
the steward rail survives, the definer function refuses an outsider and allows a
participant, and the system's own writes are unaffected). Re-run that probe, not
just this file, when touching the policies.

Run: python3 test_adr495_conversation_rls.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
MIG = ROOT.parent / "supabase" / "migrations" / "228_adr495_conversation_rls_follows_the_cast.sql"

_failures: list[str] = []


def _assert(cond: bool, msg: str) -> None:
    if cond:
        print(f"  ✓ {msg}")
    else:
        print(f"  ✗ {msg}")
        _failures.append(msg)


def _sql() -> str:
    return MIG.read_text() if MIG.exists() else ""


def _sql_code() -> str:
    """The migration's SQL with `--` comments stripped.

    This file's own comments quote the shapes being retired (`FOR ALL`,
    `user_id = auth.uid()`) to record what was wrong — so a naive substring
    assert matches the prose and fails correct SQL. Same trap as the ADR-502
    gate's first cut; a gate that greps prose is testing the prose.
    """
    out = []
    for line in _sql().splitlines():
        s = line.split("--", 1)[0] if line.lstrip().startswith("--") else line
        out.append(s)
    return "\n".join(out)


def _lanes() -> str:
    return (ROOT / "routes" / "lanes.py").read_text()


def test_the_creator_only_policies_are_replaced_not_supplemented() -> None:
    """Two policies answering one question is the dual approach that let the
    creator-scoped assumption survive ADR-495."""
    print("\nSingular implementation — the 008 policies are gone")
    sql = _sql()
    _assert(
        'DROP POLICY IF EXISTS "Users own their chat sessions"' in sql,
        "the migration-008 chat_sessions FOR ALL policy is dropped",
    )
    _assert(
        'DROP POLICY IF EXISTS "Users can access messages in their sessions"' in sql,
        "the migration-008 session_messages FOR ALL policy is dropped",
    )
    # And nothing recreates a blanket FOR ALL (code only — the comments quote
    # the retired shape by name).
    _assert(
        "FOR ALL" not in _sql_code(),
        "no FOR ALL policy is introduced (per-command only)",
    )


def test_read_is_cast_membership_not_workspace_membership() -> None:
    """ADR-495 D2 is explicit: 'readable by its participants. Full stop. Not by
    workspace grant-holders at large.' A workspace member outside the cast must
    read nothing — this is the one place 228 diverges from migration 227."""
    print("\nADR-495 D2 — the cast reads, not the workspace")
    sql = _sql()
    _assert(
        "is_conversation_participant" in sql,
        "a cast predicate exists (not is_workspace_member alone)",
    )
    # The workspace grant is an ADDITIONAL bound, so both appear — and the cast
    # predicate must be the leading test, ANDed with the grant.
    _assert(
        "public.is_conversation_participant(id)" in sql
        and "public.is_workspace_member(workspace_id)" in sql,
        "the workspace grant bounds the cast rule, it does not replace it",
    )


def test_the_window_is_enforced_by_the_policy() -> None:
    """The ADR-495 D2 window was an application promise at four call sites — and
    it leaked at four more (commit 68b12a5). The table answers now."""
    print("\nADR-495 D2 — the visibility window, in the policy")
    sql = _sql()
    _assert(
        "conversation_visibility_floor" in sql,
        "a window predicate exists",
    )
    _assert(
        "sequence_number\n                >= public.conversation_visibility_floor" in sql
        or "sequence_number >= public.conversation_visibility_floor" in sql,
        "session_messages SELECT filters on the caller's floor",
    )


def test_non_lane_sessions_keep_the_creator_rule() -> None:
    """THE BLACKOUT THIS PREVENTS: 13 live `thinking_partner` rows (the steward
    rail) have ZERO cast rows and are read through the USER client on
    `user_id = auth.uid()`. A cast-only policy makes the steward conversation
    unreadable — a whole-feature outage. `chat_sessions` is workspace-wide
    substrate that chat HAPPENS to use (ADR-495 D4); only `lane` rows have a
    cast."""
    print("\nOnly `lane` rows have a cast — the steward rail survives")
    sql = _sql()
    _assert(
        "session_type = 'lane'" in sql,
        "the policies discriminate on session_type",
    )
    _assert(
        sql.count("user_id = auth.uid()") >= 1,
        "non-lane sessions keep the creator rule",
    )


def test_the_definer_function_checks_what_it_bypasses() -> None:
    """`append_session_message` was SECURITY DEFINER with NO membership check
    since migration 008 — the way around any INSERT policy."""
    print("\nappend_session_message — a definer function must check")
    sql = _sql()
    _assert(
        "CREATE OR REPLACE FUNCTION append_session_message" in sql,
        "the function is re-created with a check",
    )
    _assert(
        "insufficient_privilege" in sql,
        "a non-participant append raises rather than lands",
    )
    _assert(
        "auth.uid() IS NOT NULL" in sql,
        "the service client (no JWT) is unaffected — the system still writes",
    )
    _assert(
        "SET search_path = public" in sql,
        "the definer function pins search_path (a definer without it is a hole)",
    )


def test_the_dead_column_is_now_load_bearing() -> None:
    """`conversation_members.workspace_id` was written on every insert and never
    read as a filter, so the cast primitive was workspace-blind and the binding
    lived only in callers (the ADR-501 finding-4 shape)."""
    print("\nconversation_members.workspace_id — dead column retired")
    sql = _sql()
    _assert(
        "ALTER COLUMN workspace_id SET NOT NULL" in sql,
        "the column cannot be NULL",
    )
    _assert(
        "conversation_members_workspace_id_fkey" in sql
        and "REFERENCES workspaces(id)" in sql,
        "an FK stops it drifting from its parent",
    )
    _assert(
        "idx_conversation_members_workspace" in sql,
        "the authorization lookup it now serves is indexed",
    )
    # And the app no longer stamps the INVITER's workspace onto a cast row.
    lanes = _lanes()
    _assert(
        'ws = lane.get("workspace_id") or _acting_workspace(auth)' not in lanes,
        "add-participant takes the CONVERSATION's workspace, never the inviter's",
    )
    cast = (ROOT / "services" / "conversation_cast.py").read_text()
    _assert(
        "a participant needs the CONVERSATION's workspace_id" in cast,
        "the service refuses a workspace-less participant with a legible error",
    )


def test_castless_conversations_are_healed_before_the_policy_binds() -> None:
    """A castless conversation is invisible to EVERYONE under a cast policy.
    Live read 2026-07-30 found 7 (all created on the ADR-495 rollout day, all
    with 0 turns). Healing beats deleting: the creator is always a participant,
    and healing is reversible in a way DELETE is not."""
    print("\nNo conversation is stranded by the cutover")
    sql = _sql()
    heal = sql.index("INSERT INTO conversation_members")
    policy = sql.index('CREATE POLICY "Cast reads the conversation"')
    _assert(heal < policy, "the heal runs BEFORE the policy binds")
    _assert(
        "NOT EXISTS (\n    SELECT 1 FROM conversation_members m WHERE m.conversation_id = s.id\n  )"
        in sql,
        "it targets conversations with no cast at all",
    )


def test_reads_use_the_user_client() -> None:
    """The point of the migration: RLS is the floor, not application code."""
    print("\nThe application reads THROUGH the policy")
    lanes = _lanes()
    _assert(
        "def _cast_read_client" not in lanes,
        "the read workaround is deleted, not left beside its replacement",
    )
    _assert(
        'auth.client.table("session_messages")' in lanes
        and 'auth.client.table("chat_sessions")' in lanes,
        "conversation reads go through the user client",
    )
    # The service client survives only for the withheld writes. Check the whole
    # STATEMENT, not the line: a chained call puts `.select(` on the NEXT line,
    # so a per-line test passed a read regressed back onto the service client
    # (verified by falsification — the first version of this check missed it).
    lines = lanes.splitlines()
    for i, line in enumerate(lines):
        if "_conversation_write_client(auth)" not in line:
            continue
        stmt = "\n".join(lines[i : i + 6])
        verb_is_write = (".update(" in stmt) or (".delete()" in stmt)
        _assert(
            verb_is_write and ".select(" not in stmt,
            f"service-client use is a write, not a read (line {i + 1})",
        )


if __name__ == "__main__":
    print("=" * 60)
    print("Migration 228 — conversation RLS follows the cast")
    print("=" * 60)
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\n" + "=" * 60)
    if _failures:
        print(f"FAIL: {len(_failures)} check(s)")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    print("PASS")
