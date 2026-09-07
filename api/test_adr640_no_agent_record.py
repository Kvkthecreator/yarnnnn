"""ADR-640 — an agent has no record of its own.

Script-style (py3.9-safe, no pytest import):
    python3 test_adr640_no_agent_record.py

WHAT THIS GATE HOLDS
  D1  The agents payload carries no history-shaped key, and neither does the
      register row whitelist. Asserted as a POSITIVE whitelist over the keys
      actually served, so a NEW history key is red — the ADR-636 lesson that a
      negative check ("no longer claims X") catches a deletion and can never
      catch an addition.
  D1  No service or route composes an agent-keyed aggregate over the two
      ledgers (`execution_events`, `workspace_file_versions`).
  D2  The two PERMITTED derivations exist and are PURE — `_applies_to`
      (skills scoping) and `resolve_executor` (declaration -> app -> agent).
      A later change that makes either impure, or that gives either a setter,
      is red here rather than in production.
  D3  `resolve_executor` reads no agent slug out of the declaration (the
      ADR-603 D2 wall this ADR leans on) — re-asserted from this side.

FALSIFICATION (run against the tree before this gate existed):
  - adding `"last_active": ...` to `_agents_payload`'s dict  -> §1 red
  - adding `"history"` to AGENT_ROW_KEYS                     -> §1 red
  - a `.table("execution_events")...eq("agent",` in routes/  -> §2 red
  - making `resolve_executor` take a client argument         -> §3 red
Each was applied, observed red for the stated reason, and reverted.
"""
import ast
import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

failures = []


def check(label, cond, detail=""):
    if cond:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))
        failures.append(label)


API = os.path.dirname(os.path.abspath(__file__))

#: Words that make a key a RECORD OF DEEDS rather than an identity fact. A key
#: matching any of these on an agent row is what ADR-640 D1 refuses.
HISTORY_WORDS = (
    "run", "runs", "history", "activity", "spend", "cost", "usage",
    "last_active", "lastactive", "revisions", "receipts", "ledger",
    "output", "produced", "authored", "turns", "sessions", "record",
)

#: What `_agents_payload` may serve. Identity, character, engine, the served
#: relations, and the memory ADDRESS (ADR-624 D4). Nothing about deeds.
ALLOWED_PAYLOAD_KEYS = {
    "slug", "name", "blurb", "icon", "offered", "kernel", "apps", "model",
    "memory_path",
    # ADR-640 D2 (built 2026-09-07) — the two relations the kernel DERIVES:
    # craft (skills whose apps meet the agent's) and tending (declarations
    # whose executor resolves to it). Read-only presentations; §4 below.
    "craft", "tending",
}

print("=" * 70)
print("ADR-640 — an agent has no record of its own")
print("=" * 70)

# ---------------------------------------------------------------------------
print("\n§1 D1 — no history-shaped key on an agent, anywhere")
# ---------------------------------------------------------------------------
import services.apps  # noqa: F401,E402  (registration side-effect)
from services.agents_registry import AGENTS, AGENT_ROW_KEYS  # noqa: E402

check("AGENT_ROW_KEYS carries no history-shaped key",
      not any(w in k.lower() for k in AGENT_ROW_KEYS for w in HISTORY_WORDS),
      f"keys={sorted(AGENT_ROW_KEYS)}")

for slug, row in AGENTS.items():
    check(f"'{slug}' row carries no history-shaped key",
          not any(w in k.lower() for k in row for w in HISTORY_WORDS))

# The PAYLOAD, read from the source the route actually serves. Parsed rather
# than called so the check needs no DB, and asserted as a WHITELIST so a new
# key is red by construction (a negative check could never catch an addition).
lanes_src = open(os.path.join(API, "routes", "lanes.py")).read()
tree = ast.parse(lanes_src)
payload_fn = next(
    (n for n in ast.walk(tree)
     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
     and n.name == "_agents_payload"),
    None,
)
check("_agents_payload exists", payload_fn is not None)

served = set()
if payload_fn is not None:
    for node in ast.walk(payload_fn):
        if isinstance(node, ast.Dict):
            for k in node.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    served.add(k.value)

check("_agents_payload serves ONLY the allowed identity keys",
      served and served <= ALLOWED_PAYLOAD_KEYS,
      f"unexpected={sorted(served - ALLOWED_PAYLOAD_KEYS)}")
check("_agents_payload serves no history-shaped key",
      not any(w in k.lower() for k in served for w in HISTORY_WORDS),
      f"served={sorted(served)}")

# ---------------------------------------------------------------------------
print("\n§2 D1 — no agent-keyed aggregate over either ledger")
# ---------------------------------------------------------------------------
#: A query that filters or groups either ledger BY AGENT is the row this ADR
#: refuses, wherever it is written. The lane's own `agent` stamp on a
#: conversation is NOT this: that is the room saying who was in it.
LEDGERS = ("execution_events", "workspace_file_versions")
AGENT_FILTER = re.compile(
    r'\.(?:eq|in_|neq|like|ilike)\(\s*["\'](?:agent|agent_slug|being)["\']'
)

offenders = []
for root, _dirs, files in os.walk(API):
    if any(p in root for p in ("/venv", "/.venv", "/node_modules", "/__pycache__")):
        continue
    for f in files:
        if not f.endswith(".py") or f.startswith("test_"):
            continue
        path = os.path.join(root, f)
        try:
            src = open(path, encoding="utf-8").read()
        except Exception:  # noqa: BLE001
            continue
        if not any(t in src for t in LEDGERS):
            continue
        # Look only at statements that mention a ledger table AND an agent filter
        for chunk in re.split(r"\n(?=\S)", src):
            if any(t in chunk for t in LEDGERS) and AGENT_FILTER.search(chunk):
                offenders.append(os.path.relpath(path, API))
                break

check("no module filters a ledger by agent", not offenders, f"{offenders}")

# ---------------------------------------------------------------------------
print("\n§3 D2 — the two PERMITTED derivations exist, and are pure")
# ---------------------------------------------------------------------------
from services.skills import _applies_to, _load_kernel  # noqa: E402
from services.standing_work import resolve_executor  # noqa: E402
from services.agents_registry import apps_for_agent  # noqa: E402

# (a) the CRAFT relation — skills whose scope intersects an agent's apps.
kernel = _load_kernel()
craft = {}
for slug in AGENTS:
    apps = [a["slug"] for a in apps_for_agent(slug)]
    craft[slug] = sorted(
        name for name, meta in kernel.items()
        if any(_applies_to(meta, app, set()) for app in apps)
    )
check("the craft relation derives for every agent",
      all(craft[s] for s in AGENTS), f"{ {k: len(v) for k, v in craft.items()} }")
check("_applies_to is pure (no client/auth parameter)",
      not ({"client", "auth", "user_id"} & set(inspect.signature(_applies_to).parameters)),
      str(inspect.signature(_applies_to)))

# (b) the TENDING relation — a declaration's executor.
sig = inspect.signature(resolve_executor)
check("resolve_executor is pure (declaration in, agent out)",
      list(sig.parameters) == ["decl"], str(sig))

# Neither may have acquired a SETTER: a door that ASSIGNS a skill or a file to
# an agent is authority on an agent (ADR-596 D1), which is the whole cliff.
import services.skills as _sk  # noqa: E402
import services.standing_work as _sw  # noqa: E402
for mod, name in ((_sk, "services.skills"), (_sw, "services.standing_work")):
    bad = [n for n in dir(mod)
           if re.match(r"^(set|assign|grant)_.*(agent|being|skill_for)", n)]
    check(f"{name} exposes no agent-assignment verb", not bad, f"{bad}")

# ---------------------------------------------------------------------------
print("\n§4 D3 — the declaration still names an app, never an agent")
# ---------------------------------------------------------------------------
src = inspect.getsource(resolve_executor)
check("resolve_executor reads the APP, not an agent key",
      "standing_executor_for_app" in src
      and not re.search(r"decl\.(agent|being|executor_slug)\b", src))

from services.standing_work import DECLARATION_KEYS  # noqa: E402
check("no DECLARATION_KEYS member is an agent slug",
      not (set(DECLARATION_KEYS) & set(AGENTS)),
      f"{sorted(set(DECLARATION_KEYS) & set(AGENTS))}")

# ---------------------------------------------------------------------------
print("\n§5 D2 (built) — the two derived rows are DERIVED, and settable from nowhere")
# ---------------------------------------------------------------------------
from services.skills import craft_for_agent  # noqa: E402
from services.agents_registry import apps_for_agent  # noqa: E402

_craft = {a: [c["slug"] for c in craft_for_agent([x["slug"] for x in apps_for_agent(a)])]
          for a in ("designer", "editor", "blogger")}
check("craft is a presentation of _applies_to: Designer's carries the images skill "
      "and not the text-only spec skill; Editor's carries the spec skill",
      "composing-an-image" in _craft["designer"] and "writing-a-spec" not in _craft["designer"]
      and "writing-a-spec" in _craft["editor"],
      str(_craft))
check("craft is app-scoped, so the three rosters differ (many-to-one is free)",
      len({tuple(v) for v in _craft.values()}) == 3, str({k: len(v) for k, v in _craft.items()}))
_tending_src = lanes_src[lanes_src.index("def _tending_by_agent"):]
_tending_src = _tending_src[:_tending_src.index("\ndef ") if "\ndef " in _tending_src else None]
check("tending is derived through discover_standing + the PURE resolve_executor — "
      "the same discovery the drain runs and the same resolver the run calls",
      "discover_standing(" in _tending_src and "resolve_executor(decl)" in _tending_src,
      "")
check("tending reads no ledger — no execution_events / workspace_file_versions query",
      not any(t in _tending_src for t in LEDGERS), "")
# Settable from nowhere: no request model anywhere in routes/ accepts either key.
_route_bodies = ""
for f in os.listdir(os.path.join(API, "routes")):
    if f.endswith(".py"):
        _route_bodies += open(os.path.join(API, "routes", f), encoding="utf-8").read()
_settable = re.findall(r"^\s+(craft|tending)\s*:\s*(?:Optional\[)?(?:list|dict|str)", _route_bodies, re.M)
check("neither `craft` nor `tending` is a field on any request model (a door that "
      "ASSIGNS a skill or a file to an agent is authority on an agent — ADR-596 D1)",
      not _settable, str(_settable))

# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
if failures:
    print(f"RED — ADR-640: {len(failures)} check(s) failed")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("GREEN — ADR-640 holds.")
