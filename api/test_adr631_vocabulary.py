"""ADR-631 — one noun for the agent, one noun for the pane. Script-style gate.

Pins the DEFINITION where it can (the envelope shape, the one relation) and
the ABSENCE of the retired spellings where it must (a retired word surviving
as an identifier is how the next session re-inherits the ambiguity).

Run: cd api && python3 test_adr631_vocabulary.py
"""
from __future__ import annotations

import os
import re
import sys

API = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(API)
WEB = os.path.join(ROOT, "web")
sys.path.insert(0, API)

_passed = 0
_failed = 0


def _check(label: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}{(' — ' + detail) if detail else ''}")


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def _walk(root: str, exts: tuple[str, ...]):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".next", ".venv", ".venv-mcp", "__pycache__")]
        for fn in filenames:
            if fn.endswith(exts):
                yield os.path.join(dirpath, fn)


print("§1 the register serves ONE relation")
import services.apps  # noqa: F401,E402  (registration side-effect)
from services import agents_registry as ar  # noqa: E402

_check("apps_for_agent exists", hasattr(ar, "apps_for_agent"))
for gone in ("homes_for_agent", "home_titles_for_agent", "desks_for_agent", "list_agents"):
    _check(f"{gone} is deleted", not hasattr(ar, gone))
rows = ar.apps_for_agent("editor")
_check("editor serves slides + text, as rich rows",
       {r["slug"] for r in rows} == {"slides", "text"} and all({"slug", "title", "icon_key", "route"} <= set(r) for r in rows),
       str(rows))
_check("blogger serves blogger", [r["slug"] for r in ar.apps_for_agent("blogger")] == ["blogger"])
_check("an unknown slug serves nothing (no fallback)", ar.apps_for_agent("nobody") == [])

print("§2 the lanes envelope serves ONE roster, keyed `agents`, with `apps`")
lanes_src = _read("api/routes/lanes.py")
_check("`_agents_payload` is the producer", "def _agents_payload()" in lanes_src)
_check("no `_beings_payload`", "_beings_payload" not in lanes_src)
_check("envelope key `agents` is the payload", '"agents": _agents_payload(),' in lanes_src)
_check("no `beings` envelope key", '"beings"' not in lanes_src)
_check("no second offered-only roster on the envelope", "list_agents" not in lanes_src)
for k in ('"homes"', '"home_titles"', '"desks"'):
    _check(f"no {k} key on the payload", k not in lanes_src)
_check('`"apps": apps_for_agent(` is the relation', '"apps": apps_for_agent(r["slug"]),' in lanes_src)

print("§3 no desk noun survives — and the standing lane carries no pane posture at all (ADR-639)")
from services import standing_work  # noqa: E402

for gone in ("build_strings_pane_posture", "build_strings_desk_posture", "_STANDING_PANE_FRAME",
             "_STANDING_RUN_POSTURE", "build_standing_run_posture"):
    _check(f"{gone} is gone (craft is a skill, ADR-639 D2)", not hasattr(standing_work, gone))
apps_init = _read("api/services/apps/__init__.py")
_check("no strings registration and no desk posture in the apps package",
       "desk_posture" not in apps_init and 'register_app(\n    "strings"' not in apps_init
       and '"strings",' not in apps_init.split("ADR-639")[-1])

print("§4 no retired identifier survives in web")
RETIRED_WEB = re.compile(r"\b(BeingIcon|DeskHousing|DeskActivityRail|DeskSurface|deskRoot|refreshDesk|ChatBeingChoice|setBeings|_beings_payload)\b")
hits = []
for path in _walk(WEB, (".ts", ".tsx")):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    for m in RETIRED_WEB.finditer(src):
        hits.append(f"{os.path.relpath(path, ROOT)}: {m.group(0)}")
_check("no retired FE identifier", not hits, "; ".join(hits[:6]))
_check("components/pane/PaneHousing.tsx exists", os.path.exists(os.path.join(WEB, "components/pane/PaneHousing.tsx")))
_check("components/desk/ is gone", not os.path.exists(os.path.join(WEB, "components/desk")))
_check("types/surface.ts exists, types/desk.ts gone",
       os.path.exists(os.path.join(WEB, "types/surface.ts")) and not os.path.exists(os.path.join(WEB, "types/desk.ts")))
client = _read("web/lib/api/client.ts")
_check("client LanesEnv has no `beings`", "beings" not in client)
_check("client LanesEnv `agents` rows carry `apps`", re.search(r"agents: Array<\{[^}]*offered: boolean;[^}]*apps: Array<", client, re.S) is not None)
for k in ("homes:", "home_titles", "desks?:"):
    _check(f"client LanesEnv has no `{k}`", k not in client)

print("§5 the GLOSSARY names the nouns")
gl = _read("docs/architecture/GLOSSARY.md")
_check("Pane is defined", "**Pane** *(canonical" in gl)
_check("Being is historical", "**Being** *(historical" in gl)
_check("Agent is the one noun", "the one noun since ADR-631" in gl)
_check("connected principals named", "connected principal" in gl)

print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
