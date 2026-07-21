"""ADR-445 §7 Phase 4 gate — the per-member cap is WORKSPACE-scoped and actually bites.

WHY THIS GATE EXISTS (the audit finding, 2026-07-21): the cap shipped keyed on
`user_id` while `write_revision` lands the sidecar workspace-scoped. A MEMBER calling
the addressed path passes their OWN `auth.user_id`, so the lookup read the member's
bucket, never found the owner-authored file, and returned UNCAPPED — Phase 4 was
inert for the exact population it was built to bound. The pre-existing ADR-445 gate
is config-only (it asserts TIER_CONFIG constants and imports none of these modules),
which is precisely how the defect survived a "37/37 green" claim.

So this gate is BEHAVIORAL: it calls the real functions against a fake client and
asserts the cap is FOUND and ENFORCED for a member. A constant-assertion cannot
catch a scope-keying bug; only exercising the lookup can.

Usage:
    cd api
    python test_adr445_member_caps_scope.py
"""

from __future__ import annotations

import sys
import types

PASSED = 0
FAILED = 0

OWNER = "11111111-1111-1111-1111-111111111111"
MEMBER = "22222222-2222-2222-2222-222222222222"
WS = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

CAPS_YAML = "caps:\n  22222222-2222-2222-2222-222222222222: 5.0\n"


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


# ── A fake Supabase client that records how the cap file was queried ──────────

class _Query:
    def __init__(self, table: str, log: dict):
        self.table = table
        self.log = log
        self.filters: dict = {}

    def select(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filters[col] = val
        return self

    def execute(self):
        if self.table == "workspace_files":
            # Record the scope key the caller used — the whole point of the gate.
            self.log["file_filters"] = dict(self.filters)
            # The sidecar exists ONLY workspace-scoped (as write_revision lands it).
            if self.filters.get("workspace_id") == WS:
                return types.SimpleNamespace(data=[{"content": CAPS_YAML}])
            return types.SimpleNamespace(data=[])
        if self.table == "workspaces":
            return types.SimpleNamespace(data=[{"owner_id": OWNER}])
        return types.SimpleNamespace(data=[])


class FakeClient:
    def __init__(self):
        self.log: dict = {}

    def table(self, name):
        return _Query(name, self.log)


def _install_ws_context(ws_for_user: dict):
    """Stub services.workspace_context.effective_workspace_id deterministically."""
    mod = types.ModuleType("services.workspace_context")
    mod.effective_workspace_id = lambda user_id, explicit=None: (
        explicit or ws_for_user.get(user_id)
    )
    sys.modules["services.workspace_context"] = mod


def test_load_is_workspace_scoped() -> None:
    print("\n[scope] the cap map is read by workspace_id, not user_id (ADR-373/416)")
    from services.member_caps import load_member_caps
    c = FakeClient()
    caps = load_member_caps(c, OWNER, WS)
    check("explicit workspace_id is used as the query key",
          c.log.get("file_filters", {}).get("workspace_id") == WS,
          f"filters={c.log.get('file_filters')}")
    check("user_id is NOT the query key when a workspace resolves",
          "user_id" not in c.log.get("file_filters", {}),
          f"filters={c.log.get('file_filters')}")
    check("the owner-authored cap map is found", caps.get(MEMBER) == 5.0, f"caps={caps}")


def test_member_lookup_finds_owner_authored_cap() -> None:
    print("\n[the bug] a MEMBER's lookup finds the OWNER's cap file")
    _install_ws_context({OWNER: WS, MEMBER: WS})
    from services.member_caps import load_member_caps
    c = FakeClient()
    # The member passes their OWN user_id — this is what feed.py does.
    caps = load_member_caps(c, MEMBER)
    check("member resolves the shared workspace and finds the cap",
          caps.get(MEMBER) == 5.0,
          f"caps={caps} filters={c.log.get('file_filters')} "
          "(user_id-keyed read would return {} here — the shipped defect)")


def test_member_over_cap_is_blocked() -> None:
    print("\n[gate] a member over their cap is BLOCKED; under it, allowed")
    _install_ws_context({OWNER: WS, MEMBER: WS})
    import services.platform_limits as pl
    from services.member_caps import check_member_cap

    real = getattr(pl, "spend_by_principal", None)
    try:
        pl.spend_by_principal = lambda *a, **k: [
            {"principal_id": MEMBER, "spend_usd": 7.5}
        ]
        allowed, cap, spent = check_member_cap(FakeClient(), MEMBER, MEMBER, workspace_id=WS)
        check("member at $7.50 against a $5 cap is BLOCKED",
              allowed is False and cap == 5.0 and spent == 7.5,
              f"allowed={allowed} cap={cap} spent={spent}")

        pl.spend_by_principal = lambda *a, **k: [
            {"principal_id": MEMBER, "spend_usd": 1.25}
        ]
        allowed, cap, spent = check_member_cap(FakeClient(), MEMBER, MEMBER, workspace_id=WS)
        check("member at $1.25 against a $5 cap is ALLOWED",
              allowed is True and cap == 5.0, f"allowed={allowed} cap={cap}")
    finally:
        if real is not None:
            pl.spend_by_principal = real


def test_owner_is_never_capped() -> None:
    print("\n[carve] the owner is never capped (no self-lockout, ADR-386 D4 parity)")
    _install_ws_context({OWNER: WS})
    from services.member_caps import check_member_cap
    allowed, cap, spent = check_member_cap(FakeClient(), OWNER, OWNER, workspace_id=WS)
    check("owner passes uncapped regardless of spend", allowed is True and cap is None,
          f"allowed={allowed} cap={cap}")


def test_carve_is_owner_only_not_self() -> None:
    """The second defect this gate caught: the carve read
    `acting_principal_id in {owner_id, user_id}`. Since the addressed path passes
    the caller's own id as BOTH args, every member exempted themselves and the cap
    could never bind — even once the scope key was fixed."""
    print("\n[carve] a member acting as themselves does NOT self-exempt")
    _install_ws_context({OWNER: WS, MEMBER: WS})
    import services.platform_limits as pl
    from services.member_caps import check_member_cap
    real = getattr(pl, "spend_by_principal", None)
    try:
        pl.spend_by_principal = lambda *a, **k: [{"principal_id": MEMBER, "spend_usd": 9.0}]
        # user_id == acting_principal_id == MEMBER, exactly as feed.py calls it.
        allowed, cap, _ = check_member_cap(FakeClient(), MEMBER, MEMBER, workspace_id=WS)
        check("member calling as themselves is still capped", allowed is False and cap == 5.0,
              f"allowed={allowed} cap={cap} (self-exempt bug would give True/None)")
    finally:
        if real is not None:
            pl.spend_by_principal = real


def test_uncapped_default() -> None:
    print("\n[default] absent cap = UNCAPPED (fail-safe)")
    _install_ws_context({OWNER: WS})
    from services.member_caps import check_member_cap
    other = "33333333-3333-3333-3333-333333333333"
    allowed, cap, _ = check_member_cap(FakeClient(), MEMBER, other, workspace_id=WS)
    check("a principal with no cap entry is allowed", allowed is True and cap is None,
          f"allowed={allowed} cap={cap}")


def test_write_pins_the_workspace() -> None:
    print("\n[write] set_member_cap pins workspace_id on the revision (read==write key)")
    import inspect
    from services import member_caps
    src = inspect.getsource(member_caps.set_member_cap)
    check("write_revision is called with workspace_id=", "workspace_id=ws" in src,
          "the write must land under the key load_member_caps reads")
    sig = inspect.signature(member_caps.set_member_cap)
    check("set_member_cap accepts an explicit workspace_id",
          "workspace_id" in sig.parameters)


def test_callers_pass_workspace() -> None:
    print("\n[callers] every call site threads the workspace (no user_id-only reads)")
    import re
    from pathlib import Path
    for rel, fn in (
        ("routes/feed.py", "check_member_cap"),
        ("routes/workspace.py", "load_member_caps"),
        ("routes/workspace.py", "set_member_cap"),
    ):
        src = Path(rel).read_text()
        # Find the call and walk to its closing paren.
        m = re.search(rf"{fn}\(", src)
        found = False
        if m:
            i, depth = m.end(), 1
            while i < len(src) and depth:
                depth += (src[i] == "(") - (src[i] == ")")
                i += 1
            found = "workspace_id" in src[m.start():i]
        check(f"{rel} :: {fn}() passes a workspace", found)


def main() -> int:
    print("=" * 74)
    print("ADR-445 §7 Phase 4 — per-member caps are workspace-scoped and enforced")
    print("=" * 74)
    test_load_is_workspace_scoped()
    test_member_lookup_finds_owner_authored_cap()
    test_member_over_cap_is_blocked()
    test_owner_is_never_capped()
    test_carve_is_owner_only_not_self()
    test_uncapped_default()
    test_write_pins_the_workspace()
    test_callers_pass_workspace()
    print("\n" + "=" * 74)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 74)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
