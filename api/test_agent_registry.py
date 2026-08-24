"""The agent-registry ratchet — ADR-460 D3.a's cliff, on the ADR-599 registers.

Script-style (run: cd api && python3 test_agent_registry.py).

What this gate holds, post-ADR-599 (the roster empties; agents are app
residents):

  1. The colleague registers are EMPTY — deliberately, by operator ruling.
     A row reappearing in KERNEL_AGENTS/KERNEL_POSTURES is a design decision
     that must re-open the ADR, not a drive-by addition.
  2. The member-agent machinery STAYS DELETED — the symbols do not import,
     and the /lane-agents doors are gone from the routes.
  3. THE CLIFF on the surviving register: an APP_RESIDENTS row carries
     identity + engine + character and nothing else — no authority-shaped
     key, no tools, no based_on (self-contained since ADR-599 D3). The
     whitelist itself contains no authority vocabulary.
  4. Every resident is routable and priced (the ADR-439 §4 rule), the
     keyspaces are disjoint (one resolution namespace), and the roster
     serves nobody (list_agents() == []).
  5. The /agents surface is the honest empty state, and resolution is
     kernel-only (resolve_agent takes a slug, nothing else — no member list
     to consult).
"""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

from services.agents_registry import (  # noqa: E402
    AGENT_ROW_KEYS,
    APP_RESIDENTS,
    KERNEL_AGENTS,
    KERNEL_POSTURES,
    POSTURE_ROW_KEYS,
    RESIDENT_ROW_KEYS,
    list_agents,
    model_for_agent,
    resolve_agent,
)
from services.lane_runner import LANE_MODELS, unpriced_lane_model  # noqa: E402

PASS = 0
FAIL = 0


def _check(label: str, cond: bool) -> None:
    global PASS, FAIL
    tag = "✓" if cond else "✗"
    print(f"  {tag} {label}")
    if cond:
        PASS += 1
    else:
        FAIL += 1


print("1. the colleague registers are empty (ADR-599 D1)")
_check("KERNEL_AGENTS is empty — the base roster is deleted, not hidden",
       KERNEL_AGENTS == {})
_check("KERNEL_POSTURES is empty — Critic went with the roster",
       KERNEL_POSTURES == {})
_check("the hire roster serves nobody (list_agents() == [])",
       list_agents() == [])
_check("a deleted colleague slug resolves None (honest, not aliased)",
       resolve_agent("sonnet") is None and resolve_agent("scout") is None
       and resolve_agent("critic") is None)

print("2. the member-agent machinery stays deleted (ADR-599 D2)")
for _sym in ("find_member_agents", "find_agent_skills", "parse_agent_manifest",
             "build_skills_section", "AGENT_MANIFEST_BASENAME"):
    try:
        import services.agents_registry as _reg
        _gone = not hasattr(_reg, _sym)
    except Exception:
        _gone = False
    _check(f"{_sym} does not exist", _gone)
_lanes_src = (API / "routes" / "lanes.py").read_text()
_check("the /lane-agents doors are gone from the routes",
       '"/lane-agents"' not in _lanes_src and "'/lane-agents'" not in _lanes_src)
_check("resolution is kernel-only — resolve_agent(slug) takes no member list",
       list(inspect.signature(resolve_agent).parameters) == ["slug"])

print("3. the cliff on the surviving register (ADR-460 D3.a, unweakened)")
banned = (
    "tools", "authority", "permission", "approve", "autonomy", "budget",
    "autonomous", "unattended", "standing_intent", "mandate", "wake",
    "principal", "grant", "scopes",
)
for _keys, _name in ((AGENT_ROW_KEYS, "AGENT_ROW_KEYS"),
                     (POSTURE_ROW_KEYS, "POSTURE_ROW_KEYS"),
                     (RESIDENT_ROW_KEYS, "RESIDENT_ROW_KEYS")):
    _check(f"{_name} contains no authority-shaped key",
           not any(w in " ".join(_keys).lower() for w in banned))
for r in APP_RESIDENTS.values():
    _check(f"resident '{r['slug']}' carries no key outside RESIDENT_ROW_KEYS",
           set(r.keys()) <= RESIDENT_ROW_KEYS)
    _check(f"resident '{r['slug']}' carries every required key",
           {"slug", "name", "blurb", "icon", "model", "token_profile", "posture"}
           <= set(r.keys()))
    _check(f"resident '{r['slug']}' is self-contained (no based_on — ADR-599 D3)",
           "based_on" not in r)
    keys = " ".join(r.keys()).lower()
    _check(f"resident '{r['slug']}' has no authority-shaped field",
           not any(w in keys for w in banned))

print("4. residents are routable, priced, and unambiguous")
for r in APP_RESIDENTS.values():
    _check(f"'{r['slug']}' routes a live engine with a billing rate",
           r["model"] in LANE_MODELS and not unpriced_lane_model(r["model"]))
    _check(f"model_for_agent('{r['slug']}') answers",
           model_for_agent(r["slug"]) == r["model"])
_check("the three keyspaces are disjoint (one resolution namespace)",
       not (set(KERNEL_AGENTS) & set(KERNEL_POSTURES))
       and not ((set(KERNEL_AGENTS) | set(KERNEL_POSTURES)) & set(APP_RESIDENTS)))
_check("the expected residents are exactly {designer, editor, keeper}",
       set(APP_RESIDENTS) == {"designer", "editor", "keeper"})

print("5. the surface is the honest empty state")
_surface = (API.parent / "web" / "components" / "agents" / "AgentsSurface.tsx").read_text()
_check("the /agents surface names the ruling (ADR-599) instead of a blank page",
       "ADR-599" in _surface)
_check("no hire machinery survives on the surface",
       "makeAgent" not in _surface and "AgentCard" not in _surface)
# The anti-pattern ratchet (kept from the original gate): the surface must
# never grow the ChatGPT business-agent editor's authority vocabulary.
_check("the surface carries no authority vocabulary",
       "Write action safety" not in _surface and "Never ask" not in _surface)

# The registry module itself: no function may WRITE — the kernel corpus is
# code, and a write path here would be the ADR-449 posture violated at the
# root. (AST: no attribute call named `insert`/`update`/`upsert`.)
_tree = ast.parse((API / "services" / "agents_registry.py").read_text())
_writes = [
    n for n in ast.walk(_tree)
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    and n.func.attr in ("insert", "update", "upsert", "delete")
]
_check("the registry module has no write path", not _writes)

print()
if FAIL:
    print(f"FAIL: {PASS}/{PASS + FAIL} checks")
    sys.exit(1)
print(f"PASS: {PASS}/{PASS} checks")
