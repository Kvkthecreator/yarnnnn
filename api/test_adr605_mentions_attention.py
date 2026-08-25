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
    _assert(row["email_default"] == "all",
            "mentions email_default is 'all' (a direct personal ask)")
    _assert(row["email_note"] is None,
            "the 'not wired yet' refusal is retired from the registry")
    _assert(EMAIL_DIAL_DEFAULTS.get("mentions") == "all",
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

def test_stamp_wired_at_route() -> None:
    print("\n[D1] the stamp + notify are WIRED in routes/lanes.py")
    src = _read("api/routes/lanes.py")
    tree = ast.parse(src)

    mh_calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name) and n.func.id == "mentioned_humans"
    ]
    _assert(len(mh_calls) >= 2,
            "mentioned_humans is called for BOTH row kinds (member turn + agent reply)")
    args0 = {a.id for c in mh_calls for a in c.args if isinstance(a, ast.Name)}
    _assert("content" in args0 and "reply" in args0,
            "one call parses the member's text, one the agent's reply")
    _assert(all(
        any(kw.arg == "exclude" for kw in c.keywords) for c in mh_calls
    ), "every stamp excludes the acting member (ADR-405 D4 — present, not told)")

    stamp_assigns = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Assign)
        and any(
            isinstance(t, ast.Subscript)
            and isinstance(t.slice, ast.Constant) and t.slice.value == "mentions"
            for t in n.targets
        )
    ]
    _assert(len(stamp_assigns) >= 2,
            "the stamp lands on the metadata of both row kinds")

    ff_calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name) and n.func.id == "fire_and_forget"
        and any(
            isinstance(a, ast.Call) and isinstance(a.func, ast.Name)
            and a.func.id == "notify_mentioned" for a in n.args
        )
    ]
    _assert(len(ff_calls) >= 2,
            "the email consequence fires off the critical path, for both kinds")
    _assert("enrich_cast_labels" in _strip_comments_py(src),
            "the cast gains human labels before the grammar runs")


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

    real_send = n.send_notification
    try:
        n.send_notification = _fake_send
        count = asyncio.get_event_loop().run_until_complete(
            m.notify_mentioned(
                _Db([]),
                workspace_id="ws", conversation_id="c",
                conversation_name="Deal room",
                mentioned=["u1", "u1", "u2"],
                author_label="Kevin",
            )
        )
    finally:
        n.send_notification = real_send
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
        test_stamp_wired_at_route,
        test_derivation_core,
        test_resolution_cursor_is_monotonic,
        test_suppression_and_dedupe,
        test_routes,
        test_fe_wiring,
    ]:
        fn()
    print(f"\n{'ALL PASS' if _fail == 0 else 'FAIL'} — {_pass} passed, {_fail} failed")
    sys.exit(0 if _fail == 0 else 1)
