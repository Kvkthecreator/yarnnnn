"""ADR-492 rooms gate — the shared Conversation object.

Behavioral where pure (history composition, mention parsing, runner
signature — imported and CALLED); text-gated where the wiring is
route/SQL/manifest. Run: pytest api/test_adr492_rooms.py  (or python3 directly).
"""

from __future__ import annotations

import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel: str) -> str:
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Behavioral — pure pieces, imported and CALLED
# ---------------------------------------------------------------------------

def test_compose_history_roles_and_labels():
    """The answering Agent's own turns are assistant; every other voice is a
    labeled user turn (attribution visible to the model)."""
    from routes.rooms import _compose_history

    msgs = [
        {"id": "1", "author_principal_id": "u1", "via_model": None,
         "agent_slug": None, "content": "hello"},
        {"id": "2", "author_principal_id": "u1", "via_model": "openai/gpt-5",
         "agent_slug": "critic", "content": "a critique"},
        {"id": "3", "author_principal_id": "u2", "via_model": None,
         "agent_slug": None, "content": "hi from the peer"},
        {"id": "4", "author_principal_id": "u1", "via_model": "gemini/gemini-2.5-pro",
         "agent_slug": "scout", "content": "research notes"},
    ]
    hist = _compose_history(msgs, answering_slug="critic",
                            labels={"u1": "kvk@x.com", "u2": "seul@x.com"})
    assert hist[0] == {"role": "user", "content": "[kvk@x.com]: hello"}
    assert hist[1] == {"role": "assistant", "content": "a critique"}          # own voice
    assert hist[2] == {"role": "user", "content": "[seul@x.com]: hi from the peer"}
    assert hist[3]["role"] == "user" and "scout" in hist[3]["content"]        # the OTHER agent is not "assistant"


def test_mention_regex_finds_agent_slugs():
    from routes.rooms import _MENTION_RE
    found = [s.lower() for s in _MENTION_RE.findall("hey @Critic and @scout — thoughts? not-an-@")]
    assert "critic" in found and "scout" in found


def test_runner_gained_ledger_slug_default_lane():
    """Rooms meter under their own slug; lanes stay byte-identical (default)."""
    from services.lane_runner import run_lane_turn, run_lane_turn_stream
    for fn in (run_lane_turn, run_lane_turn_stream):
        p = inspect.signature(fn).parameters.get("ledger_slug")
        assert p is not None and p.default == "lane", fn.__name__


def test_room_routes_exist():
    import routes.rooms as r
    paths = {route.path for route in r.router.routes}
    assert {"/rooms", "/rooms/{room_id}", "/rooms/{room_id}/messages",
            "/rooms/{room_id}/invite", "/rooms/{room_id}/archive"} <= paths


# ---------------------------------------------------------------------------
# Invariants — text-gated wiring
# ---------------------------------------------------------------------------

def test_never_ambient_plain_turn_returns_before_engine():
    """A plain message returns BEFORE any engine machinery is touched."""
    src = _read("api/routes/rooms.py")
    body = src.split("async def post_room_message", 1)[1]
    plain_return = body.index("if not address:")
    engine_call = body.index("run_lane_turn(")
    assert plain_return < engine_call
    assert "never-ambient" in body[plain_return - 300: plain_return + 200].lower()


def test_engine_turn_is_draw_gated_and_metered_as_room():
    src = _read("api/routes/rooms.py")
    body = src.split("async def post_room_message", 1)[1]
    assert "check_draw" in body and body.index("check_draw") < body.index("run_lane_turn(")
    assert 'ledger_slug="room"' in body
    assert "unpriced_lane_model" in body


def test_attribution_engine_turn_is_the_members_hands():
    """The engine row's author is the ADDRESSING member (via_model + face)."""
    src = _read("api/routes/rooms.py")
    assert '"author_principal_id": auth.user_id,   # the addressing member\'s hands' in src


def test_rooms_never_write_notifications():
    """ADR-492 D3 — Chat writes addressed acts; the OS routes attention."""
    src = _read("api/routes/rooms.py")
    assert 'table("notifications")' not in src
    assert "send_notification" not in src


def test_migration_shape():
    sql = _read("supabase/migrations/225_adr492_conversations.sql")
    assert "author_principal_id  uuid NOT NULL" in sql          # never-ambient: no authorless rows
    assert "member_kind = 'agent' AND agent_slug IS NOT NULL" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "binding" in sql and "resolved_at" in sql            # D4 comment threads ride the same store
    # No consequential-authority shape anywhere near membership (ADR-460 D3.a).
    assert "authority" not in sql.lower()


def test_scope_manifest_declares_content():
    import yaml
    manifest = yaml.safe_load(_read("api/services/scope_manifest.yaml"))
    stores = manifest["stores"]
    for t in ("conversations", "conversation_members", "conversation_messages"):
        assert stores[t]["scope"] == "content", t


def test_router_registered():
    src = _read("api/main.py")
    assert "rooms.router" in src


def test_membership_requires_workspace_grant():
    """Humans join rooms only from the grant roster (the commons boundary)."""
    src = _read("api/routes/rooms.py")
    assert src.count("does not hold a grant on this workspace") >= 2  # create + invite


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✓ {name}")
            except AssertionError as exc:
                failures += 1
                print(f"✗ {name}: {exc}")
    sys.exit(1 if failures else 0)
