"""ADR-595 D1 as amended (2026-08-28) — the desk is ONE surface.

A folder with no `_string.yaml` is served as a NORMAL view whose declaration
is empty, and rendered by the SAME tabs with the empty states they already
had. It used to 404, which forced the FE to invent a second page — a numbered
setup ladder showing the same four facts in a different shape and place, so
the declaration landing SWAPPED the page instead of filling it.

Holds:
  §1 the server serves the undeclared desk (no 404) and says so honestly
  §2 the FE has ONE body — no setup ladder, no `unconfigured` phase
  §3 the seeds live in the tab that owns each thing (nothing moves on landing)

Script-style (python3, from api/).
"""

from __future__ import annotations

import ast
import asyncio
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
WEB = API.parent / "web"
sys.path.insert(0, str(API))

PASS = 0
FAIL = 0


def check(label: str, ok, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))


# ═════════════════════════════════════════════════════════════════════════════
print("§1 the server serves an undeclared desk, honestly")
# ═════════════════════════════════════════════════════════════════════════════

import routes.strings as rs  # noqa: E402


class _EmptyClient:
    """Reads nothing: no declaration, no index row, no files. The undeclared
    folder, as the DB actually presents it."""

    def table(self, _n):
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        from types import SimpleNamespace
        return SimpleNamespace(data=[])


from types import SimpleNamespace  # noqa: E402

_auth = SimpleNamespace(client=_EmptyClient(), user_id="u-1",
                        workspace_id="ws-1", caller_identity="member:u-1")


def _get(topic, target=None):
    return asyncio.new_event_loop().run_until_complete(
        rs.get_string(topic, _auth, target)
    )


_err = None
try:
    _v = _get("marketing")
except Exception as exc:  # noqa: BLE001
    _v, _err = None, exc

check("1a an undeclared folder is SERVED, not 404'd",
      _err is None, f"raised {type(_err).__name__}: {_err}")

if _v is not None:
    check("1b it says so: declared is False",
          _v.declared is False, f"declared={_v.declared!r}")
    # ⭐ The empties must be EMPTY, not invented. A fabricated schedule or a
    # placeholder source would be the ADR-532 D1 defect — a lie of type.
    check("1c nothing is fabricated (no sources, schedule, runs, consumers)",
          _v.sources == [] and _v.schedule is None
          and _v.recent_runs == [] and _v.consumers == [],
          f"sources={_v.sources} schedule={_v.schedule!r}")
    check("1d an undeclared desk reports no PROBLEM (absence is not a fault)",
          _v.problem is None and _v.repair is None)

    # The designation-in-flight: the leaf the member picked before anything
    # was written. Only the client knows it, so it rides the request.
    _v2 = _get("marketing", "teststring.md")
    check("1e a designation-in-flight is reflected",
          _v2.target == "teststring.md" and _v2.declared is False,
          f"target={_v2.target!r}")
    # ⭐ It must not become an injection door. A bad leaf is DROPPED, not
    # refused — it is a URL param on a read.
    _v3 = _get("marketing", "../../etc/passwd")
    check("1f a malformed in-flight target is dropped, not honoured",
          _v3.target == "", f"target={_v3.target!r}")

# A DECLARED desk must be untouched by all of this.
_src = (API / "routes" / "strings.py").read_text()
_tree = ast.parse(_src)
_fn = next((n for n in ast.walk(_tree)
            if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
            and n.name == "get_string"), None)
check("1g the declared path still parses and can still 422",
      _fn is not None and "declaration unparseable" in _src)
# ⭐ The head-fact probe is ONE implementation for both paths — duplicating it
# is how the two views would drift apart again.
_calls = [getattr(n.func, "id", getattr(n.func, "attr", ""))
          for n in ast.walk(_fn) if isinstance(n, ast.Call)] if _fn else []
check("1h both paths compute head facts through ONE helper",
      _calls.count("_head_facts") == 2, f"_head_facts calls={_calls.count('_head_facts')}")

# ═════════════════════════════════════════════════════════════════════════════
print("§2 the FE has ONE body — the ladder is DELETED, not hidden")
# ═════════════════════════════════════════════════════════════════════════════

_FE = (WEB / "components" / "strings" / "StringsSurface.tsx").read_text()
# Strip comments so the gate does not grep its own prose describing what was
# removed (the mistake that made an earlier gate pass for the wrong reason).
import re  # noqa: E402

_code = re.sub(r"/\*.*?\*/", "", _FE, flags=re.DOTALL)
_code = re.sub(r"^\s*//.*$", "", _code, flags=re.MULTILINE)
_code = re.sub(r"^\s*\*.*$", "", _code, flags=re.MULTILINE)

check("2a SetupPanel is gone", "function SetupPanel" not in _code)
check("2b SetupSlot is gone", "function SetupSlot" not in _code)
# ⭐ The PHASE must go too. Keeping it beside the served fact would leave two
# authorities on "is this set up?" — the ADR-532 §3a failure: the honest state
# bolted onto the page built for the model it replaces.
check("2c the `unconfigured` phase is gone from the state union",
      "'unconfigured'" not in _code, "a phase still spells unconfigured")
check("2d the 404 branch is gone from the loader",
      "status === 404" not in _code)
# The repair phase SURVIVES — it is a different failure (the declaration
# exists and cannot be parsed, so there is no view to render).
check("2e `repair` survives as a phase (a real unrenderable state)",
      "'repair'" in _code)

# ═════════════════════════════════════════════════════════════════════════════
print("§3 each ask lives in the tab that owns it")
# ═════════════════════════════════════════════════════════════════════════════

# ⭐ This is the whole point of the amendment: nothing MOVES when the
# declaration lands. If a seed lived outside its tab it would relocate, which
# is the disorientation the ladder caused.
def _between(hay: str, start: str, end: str) -> str:
    i = hay.find(start)
    j = hay.find(end, i + 1) if i >= 0 else -1
    return hay[i:j] if i >= 0 and j > i else ""


_sources_panel = _between(_code, "function SourcesPanel", "function SectionHeading")
check("3a the aperture chips live in the Sources tab",
      "slices" in _sources_panel and "seedChat(" in _sources_panel,
      "the connector roster is not in SourcesPanel")
# ⭐ And the roster must load for an UNDECLARED desk — it used to be fetched
# only in the deleted phase, which is why a DECLARED desk could never see
# "what else could I pull from".
check("3b the aperture loads off the served fact, not a phase",
      "if (declared || apertureSlices !== null) return;" in _code)

check("3c the cadence presets live at the cadence row",
      "CADENCE_PRESETS.map" in _code and "CADENCE_PRESETS" in _code)
check("3d the contract ask lives in the Contract tab",
      "This file must stay true to: " in _code)
# The one DIRECT gesture (ADR-595 D4) must survive the ladder's deletion.
check("3e the file pick survives on the undesignated desk",
      "onPickFile" in _code and "Pick the file to keep current" in _code)

# The header states the desk, never hides its controls: a control that appears
# from nowhere when a declaration lands reads as a different page.
check("3f Run now is disabled-with-a-reason, not absent, when undeclared",
      "!declared || view.problem != null" in _code
      and "Nothing to run yet" in _FE)

# ⚠️ THE AMENDMENT'S OWN FOOTGUN. Before it, an unconfigured desk had NO
# `view`, so `view?.target` was `undefined` and `??` fell through to the
# in-flight param. Now the desk is SERVED, so an undesignated target is the
# empty STRING — which `??` does NOT fall through on. Every such fallback had
# to become `||`, or the title, the focus label and the lane name render
# blank on exactly the desk this amendment added.
_bad = re.findall(r"\.target \?\? ", _code)
check("3g an empty target falls through (|| not ??), on every fallback",
      not _bad, f"{len(_bad)} nullish fallback(s) left on .target")

# And the load must re-run when the designation arrives: `targetParam` lands
# on the same navigation as `topic` but not always in the same commit.
_load = _between(_code, "if (topic) void loadDesk(topic, targetParam);", "// The aperture chips")
check("3h the desk reloads when the in-flight target arrives",
      "[topic, targetParam, loadDesk]" in _code,
      "targetParam is not a dependency of the load effect")

print()
print(f"{PASS}/{PASS + FAIL} ADR-595-amendment assertions pass")
sys.exit(1 if FAIL else 0)
