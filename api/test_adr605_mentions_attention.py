"""ADR-605 gate — a mention reaches its person.

Run script-style from api/:  python3 test_adr605_mentions_attention.py

What it defends, per decision:
  D1  the stamp is WIRED at the turn route (both row kinds, author excluded)
  D2  the derivation core keys on ONE read cursor (ADR-637), respects the
      window, and the cursor is monotonic
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
    print("\n[D2] the pure derivation core (ADR-637: one cursor)")
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
        read_cursors={"c1": 5, "c3": 7},
    )
    _assert(live == [{"session_id": "c1", "sequence_number": 8}],
            "the cursor clears what it covers; the window hides c2; c3 is read")
    _assert(unresolved_from(rows, floors={}, read_cursors={}) == [],
            "no cast membership → nothing derives (the read floor is the cast)")
    live2 = unresolved_from(
        [{"session_id": "c1", "sequence_number": 8}],
        floors={"c1": 0}, read_cursors={},
    )
    _assert(live2 != [],
            "an unread mention STAYS until something advances the cursor")

    # ADR-637's collapse, asserted as a FACT and not as a spelling: there is
    # exactly ONE floor parameter besides the visibility window. A revived
    # reply-floor (or any third rival cursor) fails here.
    import inspect
    params = set(inspect.signature(unresolved_from).parameters) - {"rows"}
    _assert(params == {"floors", "read_cursors"},
            f"one cursor decides membership, not two or three (got {sorted(params)})")


def test_visiting_is_reading() -> None:
    """ADR-637 D1 — the lane read advances the cursor.

    AST-anchored on the wired call, because the defect this closes was a
    discharge path that existed only in a surface nobody visited. The seam
    must be reachable from the READ, not from an FE ping.
    """
    print("\n[D2] visiting a conversation discharges its mentions")
    src = _read("api/routes/lanes.py")
    tree = ast.parse(src)
    fn = next(
        (n for n in ast.walk(tree)
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
         and n.name == "lane_messages"),
        None,
    )
    _assert(fn is not None, "the lane read endpoint exists")
    called = {
        n.func.id for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    _assert("_mark_visited" in called,
            "the lane read calls the visit seam (not an FE-initiated ping)")

    helper = next(
        (n for n in ast.walk(tree)
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
         and n.name == "_mark_visited"),
        None,
    )
    _assert(helper is not None, "the visit seam is defined")
    attrs = {
        n.func.attr for n in ast.walk(helper)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    names = {
        n.id for n in ast.walk(helper) if isinstance(n, ast.Name)
    }
    _assert("mark_read_up_to" in names,
            "the visit seam advances the ONE cursor (the same act Dismiss uses)")

    # The cursor can only be right if the read actually SELECTS the column the
    # seam reads off the rows. The first cut of this change did not — the
    # helper was wired, the column absent, and every advance a silent no-op.
    # Assert the select() argument itself, not the surrounding slice: the
    # nearby .gte("sequence_number", floor) makes a substring check pass
    # vacuously (falsified — it did).
    selects = [
        n.args[0].value
        for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "select" and n.args
        and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)
    ]
    _assert(any("sequence_number" in sel for sel in selects),
            f"the lane read SELECTS sequence_number — the cursor reads it (got {selects})")


def test_read_cursor_is_monotonic() -> None:
    print("\n[D2] the read cursor max-merges (server-side)")
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
        merged = m.mark_read_up_to("ws", "u", "c1", 4)
    finally:
        m._svc = real
    _assert(merged["c1"] == 9,
            "marking an OLDER point read never rewinds a newer act "
            "(the fire-and-forget visit write races the dismiss safely)")
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
    post_fns = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "mark_mentions_read"]
    _assert(bool(get_fns) and bool(post_fns), "GET /mentions + POST /mentions/read exist")
    if get_fns:
        seg = ast.get_source_segment(src, get_fns[0]) or ""
        _assert("list_mentions" in seg, "the GET calls the derivation (wired)")
    if post_fns:
        seg = ast.get_source_segment(src, post_fns[0]) or ""
        _assert("mark_read_up_to" in seg,
                "the POST advances the SAME cursor the visit does (one act, two doors)")
    _assert('extra = "forbid"' in src,
            "the mark-read payload refuses unknown fields")
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
            "the badge counts unseen mentions (recency), distinct from membership")
    # ADR-637 — the bell row's click IS the visit, so the row must not
    # survive it locally until the next 60s derive.
    _assert("setMentions((prev) =>" in bell,
            "clicking a bell mention drops the row (the visit discharges it)")

    queue = _read("web/components/notifications/MentionQueue.tsx")
    _assert("api.mentions.markRead" in queue,
            "Dismiss advances the read cursor (clear without opening)")
    _assert("api.mentions.resolve" not in queue,
            "the retired resolve door is gone from the queue")
    page = _read("web/app/(authenticated)/notifications/page.tsx")
    _assert("<MentionQueue" in page, "the workbench To-do pane mounts the queue")

    client = _read("web/lib/api/client.ts")
    _assert("/api/mentions" in client and "mentions/read" in client,
            "the client speaks both endpoints")
    _assert("mentions/resolve" not in client,
            "the retired resolve endpoint has no client caller left")

    settings = _read("web/app/(authenticated)/settings/page.tsx")
    _assert('"mentions"' in settings,
            "the settings dial knows the wired kind (no 'urgent only' promise)")


def test_g4_polish() -> None:
    print("\n[G4] polish — viewer's own chip, outsider door, DM label")
    menu = _read("web/components/chat-surface/MentionMenu.tsx")
    out_block = menu.split("Not in this conversation", 1)[-1]
    _assert("onPickOutsider(c)" in out_block and "onMouseDown" in out_block,
            "a not-in-cast row is a wired DOOR (opens Add people), never a mention target")
    _assert("c.inCast === false" in menu,
            "outsiders are partitioned from live targets in the menu")

    lane = _read("web/components/chat-surface/LanePanel.tsx")
    _assert("extraKnownHandles" in lane and "c.inCast === false" in lane,
            "the viewer's own handles mark in the transcript; outsider handles never chip")

    chat = _read("web/components/chat-surface/ChatSurface.tsx")
    _assert("inCast: false" in chat and "extraKnownHandles=" in chat,
            "the surface supplies both: outsiders as add-doors, viewer handles for chips")
    _assert("setParam({ detail: 'add' })" in chat.replace('"', "'"),
            "picking an outsider opens the add-participant drill-in (the existing door)")

    # DM label, behavioral: a two-human zero-agent cast emails/derives as
    # "a direct chat", never the stored name (which is usually the
    # RECIPIENT's own email — observed wrong in the first live send).
    import services.mentions as m
    import services.conversation_cast as cc

    class _Q:
        def __init__(self, data=None): self._data = data or []
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def in_(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def order(self, *a, **k): return self
        def execute(self):
            d = self._data
            class R: data = d
            return R()

    class _Svc:
        def table(self, name):
            if name == "chat_sessions":
                return _Q([{"workspace_id": "ws", "context_metadata": {"lane": {"name": "kvk@x.com"}}}])
            return _Q()

    captured: dict = {}
    def _fake_notify(**kw):
        captured.update(kw)
        return None

    real = (cc.list_participants, m._svc, m.enrich_cast_labels,
            m.notify_mentioned, m.fire_and_forget)
    try:
        cc.list_participants = lambda sid: [
            {"member_kind": "human", "principal_id": "u1", "display_name": "Kevin Kim"},
            {"member_kind": "human", "principal_id": "u2", "display_name": "Seul Kim"},
        ]
        m._svc = lambda: _Svc()
        m.enrich_cast_labels = lambda c: c
        m.notify_mentioned = _fake_notify
        m.fire_and_forget = lambda coro: None
        got = m.stamp_and_route_mentions(
            "s1", "@KevinKim look", {"author_principal_id": "u2"})
        _assert(got == ["u1"] and captured.get("conversation_name") == "a direct chat",
                "a DM's mention names the relationship, not the stored string")
    finally:
        (cc.list_participants, m._svc, m.enrich_cast_labels,
         m.notify_mentioned, m.fire_and_forget) = real


if __name__ == "__main__":
    for fn in [
        test_kind_wired,
        test_stamp_wired_at_the_chokepoint,
        test_derivation_core,
        test_visiting_is_reading,
        test_read_cursor_is_monotonic,
        test_suppression_and_dedupe,
        test_routes,
        test_fe_wiring,
        test_g4_polish,
    ]:
        fn()
    print(f"\n{'ALL PASS' if _fail == 0 else 'FAIL'} — {_pass} passed, {_fail} failed")
    sys.exit(0 if _fail == 0 else 1)
