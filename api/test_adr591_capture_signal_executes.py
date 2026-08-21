"""ADR-591 → ADR-594 regression gate — the capture-signal payload stays honest.

Why this file exists
--------------------
`d18a888` (ADR-591) narrowed the connector settings and left three stale
readers behind in `routes/integrations.py::get_capture_signal` — a KeyError
for every CONNECTED provider that both FE callers swallowed (`.catch(() =>
null)`), so the drill-in silently rendered empty. No Sentry event: the
ADR-561 "incorrect success" class. The original gate closed it by EXECUTING
the payload composition instead of AST-ing its return keys.

ADR-594 D1 then deleted `connector_settings` entirely (the destination dial
was its last tenant). The same failure class is still the target: the route
must not READ machinery that no longer exists, and the payload must keep the
compat shape deployed clients read. So this gate now holds:

  1. the settings machinery stays deleted (no resurrection);
  2. the route references none of it (the stale-reader class, inverted);
  3. `settings` is still EMITTED — as a literal None — until no deployed
     client reads it (the ADR-591 `connector_capture_enabled` precedent);
  4. the retired `capture` field stays gone.

Run: python3 test_adr591_capture_signal_executes.py   (script-style —
`pytest` reports "no tests ran" on these files.)
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


# -- 1. the settings machinery stays deleted (ADR-594 D1) --------------------
import services.connectors as conn  # noqa: E402

record(
    "connector_settings stays deleted",
    not hasattr(conn, "connector_settings")
    and not hasattr(conn, "update_connector_settings"),
)

# -- 2. the route reads NONE of it (the stale-reader class, inverted) --------
src = open(os.path.join(REPO, "routes/integrations.py")).read()
tree = ast.parse(src)
fn = next(
    n for n in ast.walk(tree)
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    and n.name == "get_capture_signal"
)
fn_src = ast.unparse(fn)
record(
    "get_capture_signal references no deleted settings machinery",
    "connector_settings" not in fn_src,
    "a resurrected reader is the exact KeyError class this gate exists for",
)

# -- 3. the payload keeps the compat shape ----------------------------------
returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)
           and isinstance(n.value, ast.Dict)]
record("get_capture_signal returns a dict literal", bool(returns))
if returns:
    keys = {k.value for k in returns[-1].value.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    record(
        "`settings` is still emitted (compat: served as None until no "
        "deployed client reads it)",
        "settings" in keys,
        f"got {sorted(keys)}",
    )
    record(
        "the retired `capture` field is not emitted",
        "capture" not in keys,
        "ADR-591 deleted the cadence it carried; no caller read it",
    )

    # settings_obj must be a bare None assignment — not a dict rebuilt from
    # anything (the shape that could silently resurrect a reader).
    def _targets(n):
        if isinstance(n, ast.Assign):
            return n.targets
        if isinstance(n, ast.AnnAssign):  # `settings_obj: Optional[...] = None`
            return [n.target]
        return []

    _settings_assigns = [
        n for n in ast.walk(fn)
        if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None
        and any(isinstance(t, ast.Name) and t.id == "settings_obj"
                for t in _targets(n))
    ]
    record(
        "settings_obj is assigned exactly once, to None",
        len(_settings_assigns) == 1
        and isinstance(_settings_assigns[0].value, ast.Constant)
        and _settings_assigns[0].value.value is None,
        ast.unparse(_settings_assigns[0]) if _settings_assigns else "no assignment",
    )

print("=" * 60)
print(f"ADR-591/594 capture-signal gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
print("=" * 60)
sys.exit(1 if _failed else 0)
