"""ADR-650 gate — account email, the always-on class.

Script-style (python3 -B test_adr650_account_email.py from api/). Reports a
count; a check that crashes is a FAIL, not silence.

Locks:
  D1  the `account` kind is declared, kernel-owned and FIXED: absent from the
      dial map, refused by the prefs validator, never fail-closed.
  D2  the four hook sites exist where the ACT is, in the right order:
      welcome on the mint's inserted branch (after the owner grant),
      welcome_joined on accept (first membership only), removed on eviction
      (human `member` only), farewell resolved-before / sent-after the delete.
  D3  the composer never touches the wire (the ADR-593 roster is unchanged),
      and every event renders through the one shell.
  D4  driven: a fixed-kind send writes one transport row and reaches the wire
      even when the prefs store is unreadable; the farewell composes.
  D5  dispatch is non-blocking on both paths (a running loop; no loop).
  D6  the pane renders a fixed kind as a fact, not a select.
  D7  cleanup: the plain-message template and the test email wear the shell;
      the manage link has ONE home (deep_links).
  D8  Supabase Auth's six templates are rendered from the shell into
      supabase/templates/auth/, in sync with the renderer, placeholders intact.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

API = Path(__file__).resolve().parent
REPO = API.parent

_passed = 0
_failed = 0


def _assert(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {msg}")
    else:
        _failed += 1
        print(f"  FAIL  {msg}")


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def _strip_comments(src: str) -> str:
    return "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))


# -----------------------------------------------------------------------------
# A chainable fake Supabase client: records inserts, answers reads per table.
# -----------------------------------------------------------------------------
class _Q:
    def __init__(self, store, table):
        self.store, self.table_name, self.op, self.payload = store, table, None, None

    def select(self, *a, **k): self.op = self.op or "select"; return self
    def insert(self, row): self.op, self.payload = "insert", row; return self
    def update(self, row): self.op, self.payload = "update", row; return self
    def eq(self, *a): return self
    def in_(self, *a): return self
    def limit(self, *a): return self
    def order(self, *a, **k): return self

    def execute(self):
        if self.table_name == "member_state" and self.store.get("break_prefs"):
            raise RuntimeError("prefs store down")
        if self.op == "insert":
            self.store.setdefault("inserts", []).append((self.table_name, self.payload))
            return type("R", (), {"data": [{"id": "n-1"}]})()
        if self.op == "update":
            self.store.setdefault("updates", []).append((self.table_name, self.payload))
            return type("R", (), {"data": [{}]})()
        return type("R", (), {"data": self.store.get("reads", {}).get(self.table_name, [])})()


class _Fake:
    def __init__(self, store):
        self.store = store
        user = type("U", (), {"email": "new@example.com"})()
        self.auth = type("A", (), {"admin": type("Ad", (), {
            "get_user_by_id": staticmethod(lambda uid: type("Res", (), {"user": user})())
        })()})()

    def table(self, name):
        return _Q(self.store, name)


def test_d1_fixed_kind() -> None:
    print("\n[D1] the account kind is declared, kernel-owned, FIXED")
    from services.notifications import (
        EMAIL_DIAL_DEFAULTS, FIXED_KINDS, NOTIFICATION_KINDS, _pref_allows,
        validate_notification_prefs,
    )
    row = next((k for k in NOTIFICATION_KINDS if k["key"] == "account"), None)
    _assert(row is not None, "the account kind is in the registry")
    if row:
        _assert(row["owner"] == "kernel", "the kernel owns it")
        _assert(row.get("fixed") is True, "it is FIXED")
        _assert(row["email_default"] == "all" and not row.get("email_note"),
                "it is WIRED (not a declared-unwired refusal)")
    _assert("account" in FIXED_KINDS, "FIXED_KINDS is derived from the registry")
    _assert("account" not in EMAIL_DIAL_DEFAULTS, "a fixed kind has no dial default")
    _assert(validate_notification_prefs({"email": {"account": "none"}}) != [],
            "the validator REFUSES a stored pref for a fixed kind (no silence can be stored)")
    _assert(_pref_allows(None, "account", "low") is True,
            "an unreadable store cannot silence a fixed kind")
    _assert(_pref_allows({"email": {"account": "none"}}, "account", "low") is True,
            "even a smuggled 'none' cannot silence it")
    kinds_src = _read("api/services/notifications.py")
    _assert('"account"' in kinds_src.split("NotificationKind = Literal")[1].split("\n")[0],
            "the kind literal names it")


def test_d2_hook_sites() -> None:
    print("\n[D2] four hook sites, where the act is, in the right order")
    import services.supabase as sb
    src = _strip_comments(inspect.getsource(sb.ensure_owner_workspace))
    i_grant, i_mail = src.find("ensure_principal_grant("), src.find("send_welcome(")
    _assert(i_mail > i_grant > 0, "welcome rides the mint AFTER the owner grant (inserted branch only)")
    _assert("dispatch(" in src, "the welcome is dispatched, never awaited by genesis")
    i_ret = src.rfind("return workspace_id")
    _assert(i_mail < i_ret, "the dispatch precedes the final return")
    # the early returns (existing / fresh) come BEFORE the mint — no mail on a re-resolve
    first_return = src.find("return existing")
    _assert(0 < first_return < i_mail, "a re-resolved owner (early return) never gets a second welcome")

    import services.workspace_invites as wi
    src = _strip_comments(inspect.getsource(wi.accept_invite))
    i_acc, i_first, i_mail = src.find('"status": "accepted"'), src.find("is_first_membership("), src.find("send_welcome_joined(")
    _assert(0 < i_acc < i_first < i_mail, "welcome_joined follows the accept and is gated on FIRST membership")

    import services.principal_grants as pg
    src = _strip_comments(inspect.getsource(pg.evict_principal))
    i_rev, i_gate, i_mail = src.find('"status": "revoked"'), src.find('== "member"'), src.find("send_removed(")
    _assert(0 < i_rev < i_gate < i_mail, "removed follows the revoke and is gated on a HUMAN member role")

    src = _strip_comments(_read("api/routes/account.py"))
    fn = src[src.find("async def deactivate_account"):src.find("# Email Wire Smoke Test")]
    i_addr, i_del, i_mail = fn.find("recipient"), fn.find("delete_user("), fn.find("compose_account_deleted(")
    _assert(0 < i_addr < i_del < i_mail, "farewell: address resolved BEFORE the auth delete, sent AFTER it")
    _assert("auth.email" in fn and "get_user_email(" in fn, "the address comes from the JWT, else auth.admin")


def test_d3_roster_and_shell() -> None:
    print("\n[D3] the composer never touches the wire; every event wears the shell")
    comp = _read("api/services/account_email.py")
    _assert("from jobs.email import" not in comp and "import jobs.email" not in comp,
            "the composer does not import the wire (ADR-593 roster unchanged)")
    _assert('kind=KIND' in comp and 'KIND = "account"' in comp, "the composer names the kind once")
    _assert(comp.count("render_email(") >= 4, "welcome, joined, removed, farewell all render through email_shell")
    _assert("_html.escape(" in comp, "user-supplied strings are escaped")
    _assert("notification_settings_url" in comp, "the footer's manage link comes from deep_links")
    # Nothing outside the composer names the kind.
    offenders = []
    for py in (API / "services").rglob("*.py"):
        if py.name == "account_email.py":
            continue
        if 'kind="account"' in py.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(py.name)
    _assert(not offenders, f"only the composer sends kind=account (offenders: {offenders})")


def test_d4_driven() -> None:
    print("\n[D4] driven: a fixed send records and reaches the wire with the store DOWN")
    import jobs.email as wire
    import services.account_email as ae
    import services.notifications as notif

    store = {"break_prefs": True, "reads": {"workspaces": [{"name": "Acme Deals"}]}}
    fake = _Fake(store)
    sent = []

    async def _fake_send(to, subject, html, text=None, from_email=None, reply_to=None, attachments=None):
        sent.append({"to": to, "subject": subject, "html": html, "text": text})
        return wire.EmailResult(success=True, message_id="msg-1")

    orig_send, orig_svc = wire.send_email, ae._svc
    wire.send_email, ae._svc = _fake_send, (lambda: fake)
    try:
        r = asyncio.run(ae.send_welcome("user-1", "ws-1"))
        _assert(r.status == "sent", f"welcome sent with prefs store down (status={r.status})")
        rows = [p for (t, p) in store.get("inserts", []) if t == "notifications"]
        _assert(len(rows) == 1 and rows[0]["source_type"] == "account" and rows[0]["workspace_id"] == "ws-1",
                "one transport row, source_type=account, workspace-stamped")
        _assert(sent and sent[-1]["subject"] == "Welcome to yarnnn" and sent[-1]["to"] == "new@example.com",
                "the wire got the welcome, addressed by auth.admin")
        _assert("settings.pane=notification-settings" in sent[-1]["html"], "the footer carries the manage link")

        r = asyncio.run(ae.send_welcome_joined("user-1", "ws-1", "<Acme & Co>"))
        _assert(r.status == "sent" and "&lt;Acme &amp; Co&gt;" in sent[-1]["html"],
                "joined: the workspace name is escaped in the body")

        r = asyncio.run(ae.send_removed("user-1", "ws-1"))
        _assert(r.status == "sent" and "Acme Deals" in sent[-1]["subject"],
                "removed: the name is read from the workspace row when not supplied")

        subject, html, text = ae.compose_account_deleted("gone@example.com")
        _assert("deleted" in subject and "gone@example.com" in html and "gone@example.com" in text,
                "the farewell composes to (subject, html, text) for the route to send")
        _assert(not [p for (t, p) in store.get("inserts", []) if t != "notifications"],
                "composing the farewell writes no row (no principal remains to key one)")

        # A dialled kind with the store down still FAILS CLOSED — D1 changed nothing there.
        r = asyncio.run(notif.send_notification(
            fake, "user-1", "hello", kind="decisions", urgency="high", workspace_id="ws-1"))
        _assert(r.status == "skipped", "a dialled kind with the store down still fails closed")
    finally:
        wire.send_email, ae._svc = orig_send, orig_svc


def test_d5_dispatch() -> None:
    print("\n[D5] dispatch is non-blocking on both paths")
    from services.account_email import dispatch

    ran = threading.Event()

    async def _job():
        ran.set()

    # No running loop (the sync auth dependency in a threadpool): a thread.
    dispatch(_job())
    _assert(ran.wait(2.0), "no loop → the coroutine ran on its own thread")

    ran2 = threading.Event()

    async def _job2():
        ran2.set()

    async def _main():
        dispatch(_job2())
        _assert(not ran2.is_set(), "running loop → scheduled, not run inline (the caller does not wait)")
        await asyncio.sleep(0.05)
        _assert(ran2.is_set(), "running loop → the task ran on the loop")

    asyncio.run(_main())


def test_d6_pane() -> None:
    print("\n[D6] the pane renders a fixed kind as a fact")
    page = _read("web/app/(authenticated)/settings/page.tsx")
    _assert("k.fixed" in page and "Always sent" in page, "the pane branches on `fixed` and states it")
    _assert(page.find("k.fixed ?") < page.find("k.email_default ?"), "the fixed branch precedes the dial branch")
    client = _read("web/lib/api/client.ts")
    _assert("fixed?: boolean" in client, "the client type carries `fixed`")


def test_d7_cleanup() -> None:
    print("\n[D7] the shell is singular; the manage link has one home")
    import jobs.email as wire
    import services.notifications as notif

    src = _strip_comments(inspect.getsource(notif._send_notification_email))
    _assert("render_email(" in src and "<html>" not in src, "the plain-message template renders through the shell")
    _assert("_html.escape(" in src, "the plain message is escaped (it carries user-controlled strings)")
    _assert("settings.pane=notification-settings" not in src and "notification_settings_url()" in src,
            "the manage link is deep_links.notification_settings_url, not hand-built")
    tsrc = inspect.getsource(wire.send_test_email)
    _assert("render_email(" in tsrc and "<h1>" not in tsrc, "the test email wears the shell")

    sent = []

    async def _fake_send(to, subject, html, text=None, from_email=None, reply_to=None, attachments=None):
        sent.append({"subject": subject, "html": html})
        return wire.EmailResult(success=True, message_id="m")

    orig = wire.send_email
    wire.send_email = _fake_send
    try:
        asyncio.run(notif._send_notification_email(
            "a@b.c", "<b>Bold</b> mentioned you\nsecond line", "high", {"url": "https://x.test/y"}))
        _assert(sent[-1]["subject"].startswith("[Action Required] "), "urgency prefix preserved")
        _assert("&lt;b&gt;Bold&lt;/b&gt;" in sent[-1]["html"] and "<b>Bold</b>" not in sent[-1]["html"],
                "driven: caller text is escaped, not rendered as markup")
        _assert('href="https://x.test/y"' in sent[-1]["html"], "driven: the caller's deep link is the CTA")
    finally:
        wire.send_email = orig

    from services.deep_links import notification_settings_url
    _assert(notification_settings_url().endswith("/settings?settings.pane=notification-settings"),
            "one manage URL, built by deep_links")
    hand_built = [
        p.relative_to(REPO).as_posix()
        for p in (API / "services").rglob("*.py")
        if "settings.pane=notification-settings" in _strip_comments(p.read_text(encoding="utf-8", errors="ignore"))
        and p.name != "deep_links.py"
    ]
    _assert(not hand_built, f"no service hand-builds the manage link (offenders: {hand_built})")


def test_d8_supabase_auth_templates() -> None:
    print("\n[D8] Supabase Auth mail wears the shell — rendered, in sync, placeholders intact")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "render_auth_templates", API / "scripts/render_supabase_auth_templates.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rendered = mod.render_all()
    out = REPO / "supabase/templates/auth"
    _assert(set(rendered) == {"confirm-signup", "invite", "magic-link", "change-email",
                              "reset-password", "reauthentication"},
            "the six Supabase templates are declared")
    stale = [k for k, v in rendered.items()
             if not (out / f"{k}.html").exists()
             or (out / f"{k}.html").read_text(encoding="utf-8") != v]
    _assert(not stale, f"the files on disk match the renderer (stale: {stale}) — edit the renderer, re-run it")
    for k, v in rendered.items():
        need = "{{ .Token }}" if k == "reauthentication" else "{{ .ConfirmationURL }}"
        _assert(need in v, f"{k} keeps its Go placeholder {need}")
        _assert('class="y-mark"' in v and "<script" not in v, f"{k} wears the shell, carries no script")
    _assert("{{ .NewEmail }}" in rendered["change-email"], "change-email names the new address")
    readme = (out / "README.md").read_text(encoding="utf-8")
    _assert(all(f"`{k}.html`" in readme for k in rendered) and "Subject" in readme,
            "the README maps every file to its dashboard template and subject")
    access = _read("docs/database/ACCESS.md")
    _assert("smtp.resend.com" in access and "supabase/templates/auth" in access,
            "ACCESS.md records the SMTP state and the templates' home")


if __name__ == "__main__":
    for t in (test_d1_fixed_kind, test_d2_hook_sites, test_d3_roster_and_shell,
              test_d4_driven, test_d5_dispatch, test_d6_pane, test_d7_cleanup,
              test_d8_supabase_auth_templates):
        try:
            t()
        except Exception as e:  # a crashed section is a FAIL, never silence
            _failed += 1
            print(f"  FAIL  {t.__name__} CRASHED: {type(e).__name__}: {e}")
    print("\n" + "=" * 60)
    print(f"ADR-650 gate: {_passed} passed, {_failed} failed")
    print("=" * 60)
    sys.exit(1 if _failed else 0)
