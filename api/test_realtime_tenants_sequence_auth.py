"""Every realtime tenant sequences setAuth BEFORE subscribe.

Run script-style from api/:  python3 test_realtime_tenants_sequence_auth.py

Why this gate exists (2026-08-26, the Layer-1 G3 click-pass):

`supabase.realtime.setAuth(token)` must land BEFORE `.subscribe()`. Called
fire-and-forget beside the join, it is a race whose LOSING SIDE IS SILENT: the
socket joins with the anon apikey, `auth.uid()` resolves NULL, RLS yields no
rows, and the channel still reports SUBSCRIBED. Nothing errors; the feature is
simply dead.

It also fails ASYMMETRICALLY — warm loads resolve the session from cache and
win the race, cold loads go to the network and lose. So it works in local dev
and in any warm reload, and fails for the real user on first paint.

`use-file-revisions-realtime` learned this and sequences with `await`. The G3
bell hook (`use-attention-realtime`) shipped with the `.then()` form and was
MEASURED broken in production: the socket carried `apikey` and no
`access_token`, and a mention badged in ~10s off the poll floor rather than the
"seconds" the feature claims.

The rule is per-TENANT, so this gate walks the whole directory: a fourth tenant
added tomorrow is covered without editing this file.
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RT_DIR = os.path.join(ROOT, "web", "lib", "realtime")

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


def _tenants() -> list[tuple[str, str]]:
    """Every hook module that actually opens a realtime channel."""
    out = []
    for name in sorted(os.listdir(RT_DIR)):
        if not name.endswith(".ts"):
            continue
        with open(os.path.join(RT_DIR, name), "r", encoding="utf-8") as f:
            src = f.read()
        # Match ANY `.subscribe(` form — the bare call and the
        # `(status, err) => …` callback form are both real joins. Pinning the
        # bare spelling found 1 of 3 tenants and would have passed while two
        # went unchecked.
        if ".subscribe(" in src and "setAuth" in src:
            out.append((name, src))
    return out


def test_tenants_found() -> None:
    print("\n[roster] the realtime tenants are discovered, not hand-listed")
    tenants = _tenants()
    _assert(len(tenants) >= 2,
            f"at least two realtime tenants exist (found {len(tenants)}: "
            f"{', '.join(n for n, _ in tenants)})")


def test_setauth_is_sequenced_before_subscribe() -> None:
    print("\n[race] setAuth is AWAITED before subscribe — never fire-and-forget")
    for name, src in _tenants():
        # The defect shape: `.then(` carrying the setAuth, with the channel
        # built outside that continuation. The correct shape awaits the token
        # in the same async body that then builds + subscribes the channel.
        fire_and_forget = re.search(
            r"resolveAccessToken\([^)]*\)\s*\.then\(", src
        )
        _assert(
            fire_and_forget is None,
            f"{name}: no `resolveAccessToken(...).then(` beside the join "
            "(that is the silent race)",
        )
        _assert(
            "await resolveAccessToken(" in src,
            f"{name}: awaits resolveAccessToken before subscribing",
        )
        # Ordering — measured on CODE, not prose. Strip comments first: the
        # word "subscribing" inside an explanatory comment is not a join, and
        # matching it made this assertion fail against correct code.
        code = re.sub(r"//[^\n]*", "", src)
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
        i_auth = code.find("setAuth(")
        i_sub = code.find(".subscribe(")
        _assert(
            i_auth != -1 and i_sub != -1 and i_auth < i_sub,
            f"{name}: setAuth precedes .subscribe() in the join body (code, not comments)",
        )


def test_cleanup_guards_the_async_join() -> None:
    print("\n[teardown] an async join cannot leak a channel after unmount")
    for name, src in _tenants():
        _assert(
            "cancelled" in src,
            f"{name}: the effect guards its async join with a cancelled flag",
        )


if __name__ == "__main__":
    for fn in [
        test_tenants_found,
        test_setauth_is_sequenced_before_subscribe,
        test_cleanup_guards_the_async_join,
    ]:
        fn()
    print(f"\n{'ALL PASS' if _fail == 0 else 'FAIL'} — {_pass} passed, {_fail} failed")
    sys.exit(0 if _fail == 0 else 1)
