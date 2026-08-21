"""ADR-593 gate — apps declare semantics, the kernel derives emission.

Script-style (python3 test_adr593_notifications_management.py from api/).
Locks:
  D1  the kind registry: one owner per kind, wired kinds carry a dial default,
      unwired kinds carry a printed refusal (never a dead dial).
  D2  the pref shape is schema-checked at the one writer (422 at the door).
  D3  one chokepoint: the jobs.email import roster; the gate FAILS CLOSED.
  D4  the daily P&L opt-in lives in the one store (no _preferences.yaml read).
  D5  the Notifications pane exists on the account door, with its doors.
  D6  the residue is gone (dead functions, dead module, dead tables' writers).
"""

from __future__ import annotations

import ast
import os
import sys
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


def test_d1_kind_registry() -> None:
    print("\n[D1] the kind registry — declared semantics, one owner per kind")
    from services.notifications import EMAIL_DIAL_DEFAULTS, NOTIFICATION_KINDS

    keys = [k["key"] for k in NOTIFICATION_KINDS]
    _assert(len(keys) == len(set(keys)), "kind keys are unique (one owner per kind)")
    _assert(all(k.get("owner") and k.get("label") and k.get("description") for k in NOTIFICATION_KINDS),
            "every kind declares owner + label + description")
    _assert({"decisions", "reports", "mentions", "runs"} <= set(keys),
            "the ratified kinds are declared")
    by_key = {k["key"]: k for k in NOTIFICATION_KINDS}
    _assert(by_key["decisions"]["email_default"] == "high",
            "decisions dial defaults 'high' (the ADR-489 D4 witness dial, renamed)")
    _assert(by_key["reports"]["email_default"] == "none",
            "reports dial defaults 'none' (the opt-in posture, D4)")
    for k in NOTIFICATION_KINDS:
        if k["email_default"] is None:
            _assert(bool(k.get("email_note")),
                    f"unwired kind '{k['key']}' prints a refusal, not a dead dial")
    _assert(set(EMAIL_DIAL_DEFAULTS) == {k["key"] for k in NOTIFICATION_KINDS if k["email_default"]},
            "EMAIL_DIAL_DEFAULTS is derived from the registry (wired kinds only)")


def test_d2_validated_writer() -> None:
    print("\n[D2] the pref shape is schema-checked at the one writer")
    from services.notifications import validate_notification_prefs as v

    _assert(v({"email": {"decisions": "all", "reports": "none"}}) == [],
            "a valid v2 shape passes")
    _assert(v({"email": {"decisions": "ALL"}}) != [],
            "a typo'd dial is refused (the silent-silence defect)")
    _assert(v({"email": {"mentions": "all"}}) != [],
            "an UNWIRED kind is refused (a stored pref nothing honors)")
    _assert(v({"witness_email": "all"}) != [],
            "the legacy 3-key shape is refused, not dual-read")
    _assert(v("high") != [], "a non-object value is refused")

    # The PUT route actually calls the validator (wired, not just importable).
    tree = ast.parse(_read("api/routes/member_state.py"))
    put_fns = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "put_member_state"]
    _assert(bool(put_fns), "put_member_state exists")
    if put_fns:
        src = ast.get_source_segment(_read("api/routes/member_state.py"), put_fns[0]) or ""
        _assert("validate_notification_prefs" in src and "422" in src,
                "the PUT route 422s notification_prefs on a bad shape")

    ms = _read("api/routes/member_state.py")
    _assert("/notification-kinds" in ms and "NOTIFICATION_KINDS" in ms,
            "the kind registry is SERVED (backend-driven pane vocabulary)")


def test_d3_chokepoint() -> None:
    print("\n[D3] one chokepoint — the jobs.email import roster + fail-closed gate")
    from services.notifications import _pref_allows

    _assert(_pref_allows(None, "decisions", "high") is False,
            "an unreadable prefs store FAILS CLOSED")
    _assert(_pref_allows(None, "direct", "normal") is True,
            "'direct' is ungated by policy (explicitly instructed acts)")

    # The import roster: only these modules may reach the raw Resend wire.
    # Named exemptions (ADR-593 D3): the invite (recipient is a raw email
    # address — no principal exists yet) and the account test email (an
    # explicitly requested diagnostic to self).
    allowed = {
        "services/notifications.py",
        "services/workspace_invites.py",
        "routes/account.py",
    }
    offenders: list[str] = []
    for sub in ("services", "routes", "jobs", "integrations", "agents"):
        for py in (API / sub).rglob("*.py"):
            rel = py.relative_to(API).as_posix()
            if rel == "jobs/email.py" or rel in allowed:
                continue
            text = py.read_text(encoding="utf-8", errors="ignore")
            if "from jobs.email import" in text or "import jobs.email" in text:
                offenders.append(rel)
    _assert(not offenders, f"no sender bypasses the chokepoint (offenders: {offenders})")

    _assert('kind="direct"' in _read("api/services/platform_tools.py"),
            "the operator email tool routes through the chokepoint (recorded)")
    _assert('kind="decisions"' in _read("api/services/witness.py"),
            "the witness loop names its kind")


def test_d4_one_store() -> None:
    print("\n[D4] the daily P&L opt-in lives in the ONE store")
    import services.daily_pnl_email as pnl

    _assert(not hasattr(pnl, "is_opted_in") and not hasattr(pnl, "PREFERENCES_PATH"),
            "the _preferences.yaml pref store is deleted from the dispatcher")
    src = _read("api/services/daily_pnl_email.py")
    _assert('kind="reports"' in src and "send_notification" in src,
            "the send routes through the chokepoint under the reports dial")


def test_d5_the_pane() -> None:
    print("\n[D5] the Notifications pane — on the account door, with its doors")
    from services.kernel_surfaces import KERNEL_SURFACES

    row = next((e for e in KERNEL_SURFACES if e["slug"] == "notification-settings"), None)
    _assert(row is not None, "the notification-settings registry row exists")
    if row:
        _assert(row.get("pane_of") == "settings", "pane-grade on the account door")
        _assert(row.get("route") == "/notification-settings", "bookmarkable route declared")

    stub = REPO / "web/app/(authenticated)/notification-settings/page.tsx"
    _assert(stub.exists() and "redirect(" in stub.read_text()
            and "settings.pane=notification-settings" in stub.read_text(),
            "the route is an ADR-308 server redirect stub into the pane")

    desk = _read("web/types/desk.ts")
    _assert("'notification-settings'" in desk,
            "the slug joins the FE union (auth gate derives from it)")

    page = _read("web/app/(authenticated)/settings/page.tsx")
    _assert('pane === "notification-settings"' in page and "notificationKinds" in page,
            "the pane renders, vocabulary from the served registry")
    _assert("Email Notifications</h" not in page.replace("\n", ""),
            "the buried Account-pane email section is deleted")
    _assert("useFeedback" in page and "toast(" in page,
            "a failed save says so (ADR-400), not console-only")

    bell = _read("web/components/shell/AttentionCenter.tsx")
    _assert("notification-settings" in bell, "the bell popover doors to the pane")
    win = _read("web/app/(authenticated)/notifications/page.tsx")
    _assert("notification-settings" in win, "the Notifications window doors to the pane")


def test_d6_residue() -> None:
    print("\n[D6] the residue is gone")
    notif = _read("api/services/notifications.py")
    _assert("notify_agent_delivered" not in notif and "notify_agent_failed" not in notif,
            "the zero-caller convenience senders are deleted")
    _assert(not (API / "services/daily_update_email.py").exists(),
            "daily_update_email.py (zero callers) is deleted")
    _assert(not (API / "test_delivery_email_rendering.py").exists(),
            "the test importing a deleted module is deleted")
    hooks = _read("api/routes/webhooks.py")
    _assert("email_delivery_log\").insert" not in hooks,
            "the webhook stops writing the dropped sink")
    mig = _read("supabase/migrations/245_adr593_notifications_residue_sweep.sql")
    _assert("DROP TABLE IF EXISTS email_delivery_log" in mig
            and "DROP TABLE IF EXISTS scheduled_messages" in mig
            and "digest_enabled" in mig,
            "migration 245 sweeps the dead schema")
    _assert("BEGIN;" not in mig and "COMMIT;" not in mig,
            "245 lets the runner own the transaction (dry-run stays a dry run)")
    manifest = _read("api/services/scope_manifest.yaml")
    _assert("email_delivery_log" not in manifest, "scope manifest row removed")


if __name__ == "__main__":
    test_d1_kind_registry()
    test_d2_validated_writer()
    test_d3_chokepoint()
    test_d4_one_store()
    test_d5_the_pane()
    test_d6_residue()
    print("\n" + "=" * 60)
    print(f"ADR-593 gate: {_passed} passed, {_failed} failed")
    print("=" * 60)
    sys.exit(1 if _failed else 0)
