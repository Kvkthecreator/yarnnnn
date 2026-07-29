"""ADR-495 gate — the Conversation is participants + turns.

Supersedes `test_adr492_rooms.py` (deleted with the fold). Every invariant that
gate asserted about rooms is asserted here about conversations, because the fold
did not weaken them — it removed the second object that carried them.

The load-bearing test is `test_no_species_branch_on_read_access`: the ADR-405 §5
rule mechanized. ADR-495 exists because its own first draft violated that rule
with a `scope: private|shared` column; a gate is the only thing that keeps the
correction from being re-derived away.

Run: python3 test_adr495_conversation.py
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent
WEB = ROOT.parent / "web"

_failures: list[str] = []


def _assert(cond: bool, msg: str) -> None:
    if cond:
        print(f"  ✓ {msg}")
    else:
        print(f"  ✗ {msg}")
        _failures.append(msg)


def _read(p: pathlib.Path) -> str:
    return p.read_text() if p.exists() else ""


# ---------------------------------------------------------------------------
# D1 — one object
# ---------------------------------------------------------------------------

def test_the_second_object_is_gone() -> None:
    print("\nD1 — one Conversation object")
    _assert(not (ROOT / "routes" / "rooms.py").exists(), "routes/rooms.py deleted")
    _assert(
        not (WEB / "components" / "chat-surface" / "RoomPanel.tsx").exists(),
        "RoomPanel.tsx deleted",
    )
    main = _read(ROOT / "main.py")
    _assert("rooms" not in main, "the rooms router is unregistered")

    mig = _read(ROOT.parent / "supabase" / "migrations" / "226_adr495_conversation_participants.sql")
    _assert("DROP TABLE IF EXISTS conversation_messages" in mig, "conversation_messages dropped")
    _assert("DROP TABLE IF EXISTS conversations" in mig, "conversations dropped")
    _assert(
        "REFERENCES chat_sessions(id)" in mig,
        "conversation_members re-points at chat_sessions",
    )

    client = _read(WEB / "lib" / "api" / "client.ts")
    _assert("api.rooms" not in client and "  rooms: {" not in client, "the FE rooms client is gone")


def test_no_scope_field_anywhere() -> None:
    """The deleted design must stay deleted — a scope column is the exact
    shape ADR-495 was rewritten to remove."""
    print("\nD1 — no scope field (the first draft's species law)")
    mig = _read(ROOT.parent / "supabase" / "migrations" / "226_adr495_conversation_participants.sql")
    _assert(
        not re.search(r"^\s*scope\s+text", mig, re.MULTILINE),
        "migration 226 declares no `scope` column",
    )
    cast = _read(ROOT / "services" / "conversation_cast.py")
    _assert(
        "'shared'" not in cast and '"shared"' not in cast,
        "conversation_cast has no shared/private scope values",
    )


# ---------------------------------------------------------------------------
# D2 — privacy is membership + window
# ---------------------------------------------------------------------------

def test_membership_is_read_permission() -> None:
    print("\nD2 — membership is read permission")
    lanes = _read(ROOT / "routes" / "lanes.py")
    _assert("visibility_floor" in lanes, "_get_lane consults the cast (visibility_floor)")
    _assert(
        'conversation_members' in lanes and '.eq("principal_id", auth.user_id)' in lanes,
        "the conversation list is cast-scoped, not owner-scoped",
    )
    # The old owner-only gate must be gone from the read path.
    _assert(
        'row.get("user_id") != auth.user_id' not in lanes.split("def _lane_envelope")[0]
        or "creator fallback" in lanes or "heal rather than lock out" in lanes,
        "owner-only read gate replaced by cast membership",
    )


def test_window_is_enforced_at_every_read() -> None:
    """A window that filters nothing is decoration. Three reads must clamp:
    the transcript, the model's history, and search."""
    print("\nD2 — the visibility window is enforced, not decorative")
    lanes = _read(ROOT / "routes" / "lanes.py")
    _assert(
        lanes.count('.gte("sequence_number"') >= 2,
        "transcript + model-history reads clamp on sequence_number",
    )
    _assert(
        "visible_from" in lanes and "_fetch_history" in lanes,
        "_fetch_history takes the acting participant's window",
    )
    _assert(
        "floors.get(sid, 0)" in lanes,
        "search never surfaces a turn below the viewer's window",
    )


def test_window_defaults_are_byte_identical_for_existing_rows() -> None:
    print("\nD2 — the backfill changes nothing for existing conversations")
    mig = _read(ROOT.parent / "supabase" / "migrations" / "226_adr495_conversation_participants.sql")
    _assert(
        "SELECT id, workspace_id, 'human', user_id, 0, user_id" in mig,
        "every existing conversation backfills its creator at window 0",
    )
    _assert(
        "context_metadata->'lane'->>'agent'" in mig,
        "lane_meta.agent retires into the cast",
    )


# ---------------------------------------------------------------------------
# D3 — ONE species-blind invite  (THE load-bearing test)
# ---------------------------------------------------------------------------

def test_one_invite_endpoint() -> None:
    print("\nD3 — one invite, not two")
    lanes = _read(ROOT / "routes" / "lanes.py")
    _assert(
        lanes.count('@router.post("/lanes/{lane_id}/participants")') == 1,
        "exactly one add-participant endpoint",
    )
    for banned in ("/invite-person", "/invite-agent", "/invite_human"):
        _assert(banned not in lanes, f"no species-specific endpoint ({banned})")


def test_no_species_branch_on_read_access() -> None:
    """ADR-405 §5, mechanized.

    `member_kind` may route a row to a column or pre-select a default. It may
    NOT decide whether someone can read, or how much. This walks the cast
    service's AST and checks that no function computing access branches on the
    participant's class.
    """
    print("\nD3 — no code path branches on species to decide read access")
    src = _read(ROOT / "services" / "conversation_cast.py")
    tree = ast.parse(src)

    ACCESS_FUNCS = {"visibility_floor", "find_participant", "list_participants"}
    checked = 0
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in ACCESS_FUNCS):
            continue
        checked += 1
        # A BRANCH on the class is the violation — not merely naming the
        # column. `select("member_kind, ...")` reads the field; `if kind ==
        # 'human'` decides with it. Only the second is species law, so this
        # inspects comparison/test nodes rather than grepping the source.
        branched = False
        for sub in ast.walk(node):
            if isinstance(sub, (ast.If, ast.IfExp)):
                test_src = ast.dump(sub.test)
                if "member_kind" in test_src or "'human'" in test_src or "'agent'" in test_src:
                    branched = True
        _assert(
            not branched,
            f"{node.name}() does not branch on the participant's class to decide access",
        )
    _assert(checked == len(ACCESS_FUNCS), f"all {len(ACCESS_FUNCS)} access functions inspected")

    # `default_window` is ALLOWED to read the class — a default is a dial
    # setting (ADR-405 D4), not a rule. But it must be overridable.
    _assert(
        "visible_from_sequence is not None" in src,
        "an explicit window always overrides the class default",
    )
    _assert(
        "def default_window" in src and "PRE-SELECTED" in src,
        "the class-keyed function is named + documented as a default, not a rule",
    )


def test_no_fork_no_settle_on_invite() -> None:
    """Adding a participant must not cost a metered call or spawn an object."""
    print("\nD3 — adding a participant forks nothing and costs nothing")
    lanes = _read(ROOT / "routes" / "lanes.py")
    add_block = lanes[lanes.index('@router.post("/lanes/{lane_id}/participants")'):]
    add_block = add_block[: add_block.index("@router.delete")]
    # Strip comments + docstrings: the prose SAYS "no metered settle", which is
    # the opposite of calling one. Assert on code, never on the commentary.
    code = "\n".join(
        ln for ln in add_block.splitlines() if not ln.strip().startswith(("#", '"""', "*", '"'))
    )
    _assert("settle_lane" not in code, "no settle is invoked on invite")
    _assert("check_draw" not in code, "no draw gate — an invite is not a billable act")
    _assert(
        'table("chat_sessions").insert' not in code,
        "no second conversation is created",
    )


# ---------------------------------------------------------------------------
# Invariants that survive the fold (ADR-492's gate, carried forward)
# ---------------------------------------------------------------------------

def test_never_ambient_survives() -> None:
    print("\nCarried forward — never-ambient + attribution")
    runner = _read(ROOT / "services" / "lane_runner.py")
    _assert("ledger_slug" in runner, "the runner still separates conversation spend by slug")
    _assert('member_label' in runner, "turns attribute as the member (member:{id} via {model})")


def test_conversations_write_no_notification() -> None:
    print("\nCarried forward — Chat writes no attention surface (ADR-492 D3)")
    lanes = _read(ROOT / "routes" / "lanes.py")
    _assert(
        'table("notifications")' not in lanes,
        "the conversation routes never write the notifications table",
    )


def test_falsifier_sees_every_conversation_turn() -> None:
    """The W0 instrument must not go blind on the widened slug set."""
    print("\nStep 5 — the falsifier instrument sees the folded world")
    f = _read(ROOT / "services" / "falsifiers.py")
    _assert("CONVERSATION_SLUGS" in f, "the conversation slug set is named")
    _assert('"room"' in f and '"lane"' in f, "both ledger slugs are read")
    _assert('.eq("slug", "lane")' not in f, "the single-slug filter is gone")


def test_last_human_cannot_be_removed() -> None:
    print("\nSafety — a conversation cannot be orphaned")
    lanes = _read(ROOT / "routes" / "lanes.py")
    _assert("last person in this conversation" in lanes, "the last human may not be removed")


if __name__ == "__main__":
    print("ADR-495 — the Conversation: participants + turns")
    print("=" * 60)
    for fn in [
        test_the_second_object_is_gone,
        test_no_scope_field_anywhere,
        test_membership_is_read_permission,
        test_window_is_enforced_at_every_read,
        test_window_defaults_are_byte_identical_for_existing_rows,
        test_one_invite_endpoint,
        test_no_species_branch_on_read_access,
        test_no_fork_no_settle_on_invite,
        test_never_ambient_survives,
        test_conversations_write_no_notification,
        test_falsifier_sees_every_conversation_turn,
        test_last_human_cannot_be_removed,
    ]:
        fn()
    print("\n" + "=" * 60)
    if _failures:
        print(f"FAIL: {len(_failures)} check(s)")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    print("PASS")
