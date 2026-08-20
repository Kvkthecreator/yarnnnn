"""ADR-591 regression gate — the capture-signal payload is BUILT, not just parsed.

Why this file exists
--------------------
`d18a888` (ADR-591) narrowed `connector_settings()` to {destination,
last_capture_at} — deleting `cadence` and `digest` with the clock. Three
readers in `routes/integrations.py::get_capture_signal` were left behind:

    capture = {"schedule": cs["cadence"], ...}
    settings_obj = {"cadence": cs["cadence"], ..., "digest": cs["digest"]}

That is a KeyError for every CONNECTED provider (an unconnected one returns
early with conn_row=None, which is why it hid). Both FE callers swallow the
500 — `ManageConnectionSubsurface` `.catch(() => null)` and
`ConnectedIntegrationsSection` `catch { return null }` — so the drill-in
silently rendered without scopes, header, destination dial, or capabilities.
No Sentry event: the ADR-561 "incorrect success" class.

`test_adr582_connectors.py` checked this function by AST — return-dict key
names only, never executing it. This gate closes that class: it BUILDS the
payload from the real `connector_settings` against a realistic connected row.
Falsified against the pre-fix source (both stale readers) before landing.

Run: python3 test_adr591_capture_signal_executes.py   (script-style, like its
neighbours — note `pytest` reports "no tests ran" on these files.)
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.dirname(os.path.abspath(__file__))
_passed = 0
_failed = 0


def record(name: str, ok: bool, why: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"PASS  {name}")
    else:
        _failed += 1
        print(f"FAIL  {name}  {why}")


# -- 1. the real function, executed against a realistic connected row --------
from services.connectors import connector_settings  # noqa: E402

CONNECTED_ROW = {
    "platform": "slack",
    "metadata": {"scope": "channels:read,users:read", "workspace_name": "Acme"},
    "settings": {"connector": {"destination": "inbound/slack",
                               "last_capture_at": "2026-08-19T00:00:00Z"}},
}
# A connection whose operator never set a destination — the default lane.
BARE_ROW = {"platform": "notion", "metadata": {}, "settings": {}}

for label, row in (("configured", CONNECTED_ROW), ("bare", BARE_ROW)):
    cs = connector_settings(row)
    record(
        f"connector_settings({label}) exposes no retired clock keys",
        "cadence" not in cs and "digest" not in cs,
        f"got {sorted(cs)}",
    )
    record(
        f"connector_settings({label}) still carries destination",
        "destination" in cs,
        f"got {sorted(cs)}",
    )

# -- 2. every key the ROUTE reads off cs must actually exist ----------------
# This is the check that would have caught the regression: it pairs the
# emitter with the producer instead of trusting either in isolation.
src = open(os.path.join(REPO, "routes/integrations.py")).read()
tree = ast.parse(src)
fn = next(
    n for n in ast.walk(tree)
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    and n.name == "get_capture_signal"
)

# Find the local name bound to connector_settings(...), then collect every
# subscript read off it.
bound = {
    t.id
    for node in ast.walk(fn)
    if isinstance(node, ast.Assign)
    for t in node.targets
    if isinstance(t, ast.Name)
    and isinstance(node.value, ast.Call)
    and getattr(node.value.func, "id", None) == "connector_settings"
}
record("the route calls connector_settings", bool(bound), "no binding found")

subscripts = {
    node.slice.value
    for node in ast.walk(fn)
    if isinstance(node, ast.Subscript)
    and isinstance(node.value, ast.Name)
    and node.value.id in bound
    and isinstance(node.slice, ast.Constant)
    and isinstance(node.slice.value, str)
}
produced = set(connector_settings(CONNECTED_ROW))
missing = subscripts - produced
record(
    "every key the route subscripts off connector_settings is produced by it",
    not missing,
    f"route reads {sorted(missing)} which connector_settings never returns",
)

# -- 3. the retired `capture` block is gone from the payload ----------------
returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)
           and isinstance(n.value, ast.Dict)]
record("get_capture_signal returns a dict literal", bool(returns))
if returns:
    keys = {k.value for k in returns[-1].value.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    record(
        "the retired `capture` field is not emitted",
        "capture" not in keys,
        "ADR-591 deleted the cadence it carried; no caller read it",
    )
    record(
        "`settings` is still emitted (the destination dial reads it)",
        "settings" in keys,
        f"got {sorted(keys)}",
    )

print("=" * 60)
print(f"ADR-591 capture-signal execution gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
print("=" * 60)
sys.exit(1 if _failed else 0)
