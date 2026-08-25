"""ADR-605 gate — a mention reaches its person.

Run script-style from api/:  python3 test_adr605_mentions_attention.py

What it defends, per decision:
  D1  the stamp is WIRED at the turn route (both row kinds, author excluded)
  D2  the derivation core resolves by reply/Done, respects the window,
      and never clears by scroll-by; the resolution cursor is monotonic
  D3  the kind is wired through the one chokepoint, with recipient dedupe
      and ledger-derived email suppression that fails SUPPRESSING
  FE  people are live @ targets, the bell and workbench mount the source,
      and the refusal chrome is gone

Checks are behavioral where the code is pure (the functions are CALLED) and
AST-anchored on wired call sites where it is routing — never on comments.
"""

from __future__ import annotations

import ast
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_pass = 0
_fail = 0


def _assert(cond: bool, label: str) -> None:
    global _pass, _fail
    if cond:
        _pass += 1
        print(f"  ✓ {label}")
    else:
        _fail += 1
        print(f"  ✗ {label}")


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
        return f.read()


def _strip_comments_py(src: str) -> str:
    """Source with comments removed, so a check can never match its own
    explanation (the recorded gate-craft failure class)."""
    out = []
    for line in src.splitlines():
        i = line.find("#")
        out.append(line[:i] if i >= 0 else line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# D3a — the kind registry is wired
# ---------------------------------------------------------------------------

def test_kind_wired() -> None:
    print("\n[D3] the mentions kind is wired through the registry")
    from typing import get_args

    from services.notifications import (
        EMAIL_DIAL_DEFAULTS, NOTIFICATION_KINDS, NotificationKind,
        validate_notification_prefs as v,
    )

    row = {k["key"]: k for k in NOTIFICATION_KINDS}["mentions"]
    # Operator-ruled 2026-08-25 (ADR-605 amendment): OPT-IN — internal
    # notifications stabilize before outbound expansion; email is never a
    # default the system assumes. 'all' here would re-ship the unflagged
    # upgrade this ruling corrected.
    _assert(row["email_default"] == "none",
            "mentions email is OPT-IN (wired dial, quiet default)")
    _assert(row["email_note"] is None,
            "the 'not wired yet' refusal is retired from the registry")
    _assert(EMAIL_DIAL_DEFAULTS.get("mentions") == "none",
            "EMAIL_DIAL_DEFAULTS derives the wired kind")
    _assert("mentions" in get_args(NotificationKind),
            "send_notification's kind type admits 'mentions'")
    _assert(v({"email": {"mentions": "all"}}) == [],
            "a mentions pref is accepted at the one writer")
    _assert(v({"email": {"mentions": "loud"}}) != [],
            "a typo'd mentions dial is still refused")
    _assert(v({"email": {"runs": "all"}}) != [],
            "runs stays the declared-unwired probe (refused)")


# ---------------------------------------------------------------------------
# D1 — the stamp is wired at the route (AST over the real call sites)
# ---------------------------------------------------------------------------

def test_stamp_wired_at_the_chokepoint() -> None:
    """Layer-1 G1 (ADR-593 §6): the stamp lives at the ONE conversation-write
    site — `write_narrative_entry` — so EVERY writer gets it (the first cut
    stamped only in routes/lanes.py, leaving five writers silent: a live
    MCP-authored @mention routed nowhere)."""
    print("\n[D1/G1] the stamp lives at the ONE write chokepoint")
    nar = _read("api/services/narrative.py")
    nar_nc = _strip_comments_py(nar)
    _assert("stamp_and_route_mentions" in nar_nc,
            "write_narrative_entry calls the stamp seam")
    tree = ast.parse(nar)
    wne = [n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name == "write_narrative_entry"]
    _assert(bool(wne), "write_narrative_entry exists")
    if wne:
        seg = ast.get_source_segment(nar, wne[0]) or ""
        _assert("stamp_and_route_mentions" in _strip_comments_py(seg)
                and 'metadata["mentions"]' in seg,
                "the stamp lands on the metadata INSIDE the write function (wired)")

    lanes_nc = _strip_comments_py(_read("api/routes/lanes.py"))
    _assert("mentioned_humans" not in lanes_nc and "notify_mentioned" not in lanes_nc,
            "routes/lanes.py carries NO mention code — per-caller stamping "
            "was the defect shape; one site only")

    # Behavioral: the seam itself, with every collaborator faked.
    import services.mentions as m
    import services.conversation_cast as cc

    class _Q:
        def __init__(self, data=None): self._data = data or []
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            class R: data = []
            return R()

    class _Svc:
        def table(self, name): return _Q()

    calls = {"cast": 0}
    def _fake_cast(sid):
        calls["cast"] += 1
        return [
            {"member_kind": "human", "principal_id": "u1", "display_name": "Kevin Kim"},
            {"member_kind": "human", "principal_id": "u2", "display_name": "Seul Kim"},
        ]

    real_cast, real_svc, real_enrich = cc.list_participants, m._svc, m.enrich_cast_labels
    try:
        cc.list_participants = _fake_cast
        m._svc = lambda: _Svc()
        m.enrich_cast_labels = lambda c: c  # labels already present
        none = m.stamp_and_route_mentions("s1", "no at-sign here", {})
        _assert(none is None and calls["cast"] == 0,
                "no '@' → no stamp AND no cast fetch (the cheap pre-check, proven)")
        got = m.stamp_and_route_mentions(
            "s1", "@KevinKim please look", {"author_principal_id": "u2"})
        _assert(got == ["u1"], "a cast human's mention stamps, by any author")
        self_stamp = m.stamp_and_route_mentions(
            "s1", "@KevinKim note to self", {"authored_by": "member:" + "1" * 8 + "-1111-1111-1111-" + "1" * 12})
        _assert(self_stamp == ["u1"],
                "a member:{uuid} authored_by parses for exclusion (different member → still stamps)")
        excl = m.stamp_and_route_mentions(
            "s1", "@KevinKim ping", {"author_principal_id": "u1"})
        _assert(excl is None,
                "the present author is excluded (ADR-405 D4), at the chokepoint")
    finally:
        cc.list_participants, m._svc, m.enrich_cast_labels = real_cast, real_svc, real_enrich

    # The seam still never accepts a client (the wrong-client class, proven live).
    src_m = _read("api/services/mentions.py")
    t2 = ast.parse(src_m)
    nm = [n for n in ast.walk(t2)
          if isinstance(n, ast.AsyncFunctionDef) and n.name == "notify_mentioned"]
    _assert(bool(nm) and not nm[0].args.args and not nm[0].args.posonlyargs,
            "notify_mentioned takes NO positional client — the seam resolves "
            "the SERVICE client itself")


# ---------------------------------------------------------------------------
# D2 — the derivation core (CALLED, not grepped)
# ---------------------------------------------------------------------------

def test_derivation_core() -> None:
    print("\n[D2] the pure derivation core")
    from services.mentions import unresolved_from

    rows = [
        {"session_id": "c1", "sequence_number": 5},
        {"session_id": "c1", "sequence_number": 8},
        {"session_id": "c2", "sequence_number": 3},
        {"session_id": "c3", "sequence_number": 7},
    ]
    live = unresolved_from(
        rows,
        floors={"c1": 0, "c2": 4, "c3": 0},
        reply_floors={"c1": 5},
        resolutions={"c3": 7},
    )
    _assert(live == [{"session_id": "c1", "sequence_number": 8}],
            "reply resolves up to it; the window hides c2; Done resolves c3")
    _assert(unresolved_from(rows, floors={}, reply_floors={}, resolutions={}) == [],
            "no cast membership → nothing derives (the read floor is the cast)")
    live2 = unresolved_from(
        [{"session_id": "c1", "sequence_number": 8}],
        floors={"c1": 0}, reply_floors={}, resolutions={},
    )
    _assert(live2 != [],
            "an unreplied, undismissed mention STAYS — it never clears by scroll-by")


def test_resolution_cursor_is_monotonic() -> None:
    print("\n[D2] the resolution cursor max-merges (server-side)")
    import services.mentions as m

    captured: dict = {}

    class _FakeQuery:
        def __init__(self, data=None):
            self._data = data or []
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            class R: data = self._data
            return R()

    class _FakeTable:
        def __init__(self, existing):
            self.existing = existing
        def select(self, *a, **k):
            return _FakeQuery([{"value": self.existing}])
        def upsert(self, row, **k):
            captured["row"] = row
            return _FakeQuery()

    class _FakeSvc:
        def __init__(self, existing):
            self.existing = existing
        def table(self, name):
            return _FakeTable(self.existing)

    real = m._svc
    try:
        m._svc = lambda: _FakeSvc({"c1": 9, "c2": 2})
        merged = m.resolve_mentions_up_to("ws", "u", "c1", 4)
    finally:
        m._svc = real
    _assert(merged["c1"] == 9,
            "resolving an OLDER mention never rewinds a newer explicit act")
    _assert(merged["c2"] == 2 and captured["row"]["value"]["c1"] == 9,
            "other conversations' cursors survive the merge, and the merge is what's stored")


# ---------------------------------------------------------------------------
# D3b — suppression + dedupe (CALLED)
# ---------------------------------------------------------------------------

def test_suppression_and_dedupe() -> None:
    print("\n[D3] email suppression derives from the transport ledger")
    import services.mentions as m
    import services.notifications as n

    class _Q:
        def __init__(self, data=None, raise_=False):
            self._data = data or []
            self._raise = raise_
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def gte(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            if self._raise:
                raise RuntimeError("ledger down")
            class R: data = self._data
            return R()

    class _Db:
        def __init__(self, data=None, raise_=False):
            self._q = _Q(data, raise_)
        def table(self, name): return self._q

    _assert(m._recent_mention_email_exists(_Db([{"id": "x"}]), "u", "c") is True,
            "a recent row suppresses")
    _assert(m._recent_mention_email_exists(_Db([]), "u", "c") is False,
            "no recent row → sendable")
    _assert(m._recent_mention_email_exists(_Db(raise_=True), "u", "c") is True,
            "an unreadable ledger SUPPRESSES (never double-emails on a hiccup)")

    sent: list = []

    async def _fake_send(db, user_id, message, **kw):
        sent.append((user_id, kw.get("kind")))
        class R: status = "sent"
        return R()

    # notify_mentioned takes NO client — it resolves the SERVICE client
    # itself (the conversation_cast._svc rule; the author's user-scoped
    # client cannot read the recipient's prefs/address/transport rows, and
    # the first prod drive proved it: "No email for user" on a real address).
    real_send, real_svc = n.send_notification, m._svc
    try:
        n.send_notification = _fake_send
        m._svc = lambda: _Db([])
        count = asyncio.get_event_loop().run_until_complete(
            m.notify_mentioned(
                workspace_id="ws", conversation_id="c",
                conversation_name="Deal room",
                mentioned=["u1", "u1", "u2"],
                author_label="Kevin",
            )
        )
    finally:
        n.send_notification, m._svc = real_send, real_svc
    _assert(count == 2 and [s[0] for s in sent] == ["u1", "u2"],
            "recipients dedupe — one turn never double-emails one person")
    _assert(all(s[1] == "mentions" for s in sent),
            "every send rides the chokepoint as kind='mentions'")


# ---------------------------------------------------------------------------
# Routes — the To-do second source exists and validates
# ---------------------------------------------------------------------------

def test_routes() -> None:
    print("\n[D2] the routes")
    src = _read("api/routes/mentions.py")
    tree = ast.parse(src)
    get_fns = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "list_my_mentions"]
    post_fns = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "resolve_mention"]
    _assert(bool(get_fns) and bool(post_fns), "GET /mentions + POST /mentions/resolve exist")
    if get_fns:
        seg = ast.get_source_segment(src, get_fns[0]) or ""
        _assert("list_mentions" in seg, "the GET calls the derivation (wired)")
    if post_fns:
        seg = ast.get_source_segment(src, post_fns[0]) or ""
        _assert("resolve_mentions_up_to" in seg, "the POST advances the cursor (wired)")
    _assert('extra = "forbid"' in src,
            "the resolve payload refuses unknown fields")
    main_src = _strip_comments_py(_read("api/main.py"))
    _assert("mentions.router" in main_src, "the router is mounted")


# ---------------------------------------------------------------------------
# FE — live targets, mounted sources, refusal chrome retired
# ---------------------------------------------------------------------------

def test_fe_wiring() -> None:
    print("\n[FE] people are live targets; the mounts read the source")
    menu = _read("web/components/chat-surface/MentionMenu.tsx")
    _assert("no alerts yet" not in menu and "aria-disabled" not in menu,
            "the refusal chrome is gone from the @ palette")
    people_block = menu.split("People", 1)[-1]
    _assert("onPick(c)" in people_block and "onMouseDown" in people_block,
            "a person row is a live pick target (wired handler, not styling)")
    _assert("...agentRows,...peopleRows" in menu.replace(" ", "").replace("\n", ""),
            "the keyboard's selectable list includes people, in render order")

    bell = _read("web/components/shell/AttentionCenter.tsx")
    _assert("api.mentions.list" in bell, "the bell fetches the mention derivation")
    _assert("unseenMentions.length" in bell and "badgeCount" in bell,
            "the badge counts unseen mentions (cursor), distinct from membership")

    queue = _read("web/components/notifications/MentionQueue.tsx")
    _assert("api.mentions.resolve" in queue, "Done advances the resolution cursor")
    page = _read("web/app/(authenticated)/notifications/page.tsx")
    _assert("<MentionQueue" in page, "the workbench To-do pane mounts the queue")

    client = _read("web/lib/api/client.ts")
    _assert("/api/mentions" in client and "mentions/resolve" in client,
            "the client speaks both endpoints")

    settings = _read("web/app/(authenticated)/settings/page.tsx")
    _assert('"mentions"' in settings,
            "the settings dial knows the wired kind (no 'urgent only' promise)")


if __name__ == "__main__":
    for fn in [
        test_kind_wired,
        test_stamp_wired_at_the_chokepoint,
        test_derivation_core,
        test_resolution_cursor_is_monotonic,
        test_suppression_and_dedupe,
        test_routes,
        test_fe_wiring,
    ]:
        fn()
    print(f"\n{'ALL PASS' if _fail == 0 else 'FAIL'} — {_pass} passed, {_fail} failed")
    sys.exit(0 if _fail == 0 else 1)
