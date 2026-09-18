"""ADR-654 — an agent's engine is the member's choice, per agent, any provider.

Run: python3 test_adr654_agent_engine_choice.py   (from api/)

⚠️ SCRIPT-SHAPED. Module-level checks, so `pytest` COLLECTS NOTHING and exits
green having run zero of them. Read the printed count, never the exit code of a
pytest run (CLAUDE.md gate discipline; the ADR-555/427/554 lesson).

The three failures this file exists because of:

  D1/D2. Engine choice stopped one level short. ADR-647 shipped a member
      engine preference that IS consulted for bound app lanes — but it is ONE
      engine for the whole member, so "Editor on a frontier reasoner, Blogger
      on something fast" was unsayable: choosing for one agent chose for all.
      ADR-647 D7 refused the per-agent form ("no field is added to AGENTS") and
      ADR-562 §2 D1 refused the workspace-scoped form as "the cliff arriving
      through a config file" — the latter reasoning about the RESIDENT and
      applying it to the ENGINE, which ADR-460's own ratified row shape carries
      (`{name, icon, model, posture, tools, token_profile}`).

  D3. `token_profile` has been in AGENT_ROW_KEYS since ADR-460, is set to 8192
      on all three agents, and WAS READ BY NOTHING — every chat turn ran the
      4096 constant. The `finish_reason` class (2026-09-16): a field plumbed
      from birth with zero consumers, found only when a turn spent its whole
      budget and returned an empty message.

  D4. ADR-647's preference had NO DOOR. `default_engine` was read by
      ChatSurface and written by nothing, and the agents pane rendered the raw
      routing key `anthropic/claude-sonnet-5` where `LANE_MODELS.label` exists.

⭐ The rule this file really guards: THE CHOICE NARROWS, IT NEVER GRANTS, AND IT
IS PROVIDER-BLIND. `member_state` is presentation state, deliberately
member-writable and never consulted for authorization (ADR-405 D5). A stored
engine must reach only what the door already offers — and the resolver must
contain no vendor branch, or the "optionality for all models" ruling is a
comment rather than a property.
"""

from __future__ import annotations

import ast
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

FAILS: list[str] = []
N = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global N
    N += 1
    if cond:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))
        FAILS.append(label)


# Provider keys so availability is decided by the registry, not this harness's
# environment (`no_provider_key` would otherwise mask the narrowing checks).
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
           "DEEPSEEK_API_KEY", "XAI_API_KEY"):
    os.environ.setdefault(_k, "test-key")

from services.agents_registry import AGENTS, AGENT_ROW_KEYS  # noqa: E402
from services.lane_runner import (  # noqa: E402
    LANE_MODELS,
    _LANE_MAX_TOKENS,
    agent_engine_key,
    offered_lane_models,
    resolve_agent_engine,
    resolve_max_tokens,
    resolve_member_engine,
)

ROOT = pathlib.Path(__file__).resolve().parent


class _Result:
    def __init__(self, data): self.data = data


class _Query:
    """Records the filters so a check can assert the SCOPE, not just the read.

    A fake that cannot express the real filter is not a fake of that query
    (the 2026-09-13 lesson) — `resolve_agent_engine` must read the per-agent
    key, and a fake that ignored `.eq("key", ...)` would pass whatever it was
    handed and prove nothing.
    """
    def __init__(self, data, seen): self._d, self._seen = data, seen
    def select(self, *a): return self
    def like(self, *a): return self
    def eq(self, col, val):
        self._seen[col] = val
        return self
    def limit(self, n): return self
    def execute(self): return _Result(self._d)


class _Client:
    def __init__(self, data):
        self._d = data
        self.seen: dict = {}
    def table(self, name): return _Query(self._d, self.seen)


class _Boom:
    def table(self, name): raise RuntimeError("db down")


def _override(value, slug="designer"):
    return resolve_agent_engine(_Client([{"value": value}]), "ws-1", "p-1", slug)


print("\n§1 D2 — the per-agent override resolves, and it is keyed per agent")

check("agent_engine_key spells the scoped key",
      agent_engine_key("designer") == "agent_engine:designer",
      agent_engine_key("designer"))

# DERIVED, never a hardcoded id. This fixture used to spell `openai/gpt-5`;
# when that engine retired from the door (2026-09-18 roster refresh) these
# checks went red on a gate that was testing the RESOLVER, not the roster. An
# "offered engine" fixture must come from the roster itself or it decays every
# time the roster moves.
_OFFERED = sorted(offered_lane_models())[0]

_c = _Client([{"value": _OFFERED}])
resolve_agent_engine(_c, "ws-1", "p-1", "designer")
check("the read is scoped to THIS agent's key",
      _c.seen.get("key") == "agent_engine:designer", str(_c.seen))
check("the read is scoped to the workspace and the principal",
      _c.seen.get("workspace_id") == "ws-1" and _c.seen.get("principal_id") == "p-1",
      str(_c.seen))

check("an offered engine resolves", _override(_OFFERED) == _OFFERED)
check("the dict shape resolves too",
      _override({"model": _OFFERED}) == _OFFERED)
check("no row resolves to None",
      resolve_agent_engine(_Client([]), "ws-1", "p-1", "designer") is None)
check("no agent slug resolves to None",
      resolve_agent_engine(_Client([{"value": _OFFERED}]), "ws-1", "p-1", "")
      is None)
check("a DB failure resolves to None (the declared engine stands)",
      resolve_agent_engine(_Boom(), "ws-1", "p-1", "designer") is None)


print("\n§2 D2 — THE OVERRIDE NARROWS, IT NEVER GRANTS")

_retired = [m for m, v in LANE_MODELS.items() if v.get("retired")]
check("a retired engine does not resolve (fixture exists)", bool(_retired))
if _retired:
    check("a retired engine resolves to None", _override(_retired[0]) is None)
check("an unknown engine resolves to None",
      _override("acme/does-not-exist") is None)
check("a non-string value resolves to None", _override(12345) is None)
check("an empty string resolves to None", _override("   ") is None)
# ⭐ THE CLEAR PATH, found by driving it on prod (2026-09-17). The member-state
# door is `value: Any = Body(...)` — REQUIRED — and FastAPI reads a bare JSON
# `null` as a MISSING body, so "back to the default" 422'd while SETTING an
# override worked. The pane now sends `{}`, which must resolve to None (the
# declared engine stands) exactly as an absent row does.
check("an empty object resolves to None (the clear path)",
      _override({}) is None)

# The narrowing is ONE definition, shared with the workspace-wide preference:
# a second copy would drift on the first engine that left the roster.
_src = (ROOT / "services" / "lane_runner.py").read_text()
check("both resolvers share one narrowing (`_narrow_engine`)",
      _src.count("def _narrow_engine(") == 1
      and _src.count("_narrow_engine(") >= 3,
      f"defs={_src.count('def _narrow_engine(')} uses={_src.count('_narrow_engine(')}")
check("both resolvers share one member_state read",
      _src.count("def _read_member_state_engine(") == 1
      and _src.count("_read_member_state_engine(") >= 3)


print("\n§3 D2 — PROVIDER-BLIND: every provider is reachable, no vendor branch")

_providers = sorted({m.split("/")[0] for m in offered_lane_models()})
check("the door offers more than one provider", len(_providers) >= 4, str(_providers))
for _p in _providers:
    _m = next(m for m in offered_lane_models() if m.startswith(f"{_p}/"))
    check(f"an override to {_p} resolves", _override(_m) == _m)

# The resolvers must not name a vendor. Parse the two functions and read their
# string constants — a grep over the file would hit the docstrings that DISCUSS
# providers, which is the false positive that makes such a check vacuous.
_tree = ast.parse(_src)
_vendor_hits: list[str] = []
for _fn in ast.walk(_tree):
    if isinstance(_fn, ast.FunctionDef) and _fn.name in (
        "_narrow_engine", "resolve_agent_engine", "resolve_member_engine",
        "_read_member_state_engine",
    ):
        for _node in ast.walk(_fn):
            if isinstance(_node, ast.Constant) and isinstance(_node.value, str):
                if _node is getattr(_fn, "_docstring_node", None):
                    continue
                low = _node.value.lower()
                for _v in ("anthropic", "openai", "gemini", "deepseek", "xai"):
                    # A docstring mentioning providers is prose; a vendor name in
                    # a COMPARISON is a branch. Only flag short operand-shaped
                    # strings, never paragraphs.
                    if _v in low and len(_node.value) < 40:
                        _vendor_hits.append(f"{_fn.name}:{_node.value!r}")
check("no resolver branches on a vendor name", not _vendor_hits, str(_vendor_hits))


print("\n§4 D1/D2 — the cliff holds: no authority key, no engine key on the row")

_forbidden = {"authority", "autonomy", "mandate", "reach", "grant", "credential",
              "engine_override", "member_engine"}
check("AGENT_ROW_KEYS carries no authority-shaped key",
      not (AGENT_ROW_KEYS & _forbidden), str(AGENT_ROW_KEYS & _forbidden))
# The row shape ADR-460 §5 D4 ratified, verbatim — `model` and `token_profile`
# among them, which is the whole of D1: the cliff protects AUTHORITY, and an
# engine was never authority. Spelled out rather than derived, so a future
# session adding a key must come here and say why.
check("AGENT_ROW_KEYS is unchanged by this ADR (the override is member state)",
      AGENT_ROW_KEYS == frozenset({
          "slug", "name", "blurb", "icon", "model", "token_profile",
          "posture", "offered", "kernel"}),
      str(sorted(AGENT_ROW_KEYS)))
check("no agent row carries an override field",
      all(set(r) <= AGENT_ROW_KEYS for r in AGENTS.values()))


print("\n§5 D3 — token_profile is READ (it was declared and unread)")

_agent_with_profile = next(
    (s for s, r in AGENTS.items() if isinstance(r.get("token_profile"), int)), None)
check("an agent declares a token_profile (fixture exists)",
      _agent_with_profile is not None)
if _agent_with_profile:
    _want = AGENTS[_agent_with_profile]["token_profile"]
    check("a chat turn resolves the agent's own profile",
          resolve_max_tokens(_agent_with_profile, authoring=False) == _want,
          f"got {resolve_max_tokens(_agent_with_profile, authoring=False)}, want {_want}")
    check("the profile differs from the old constant (the check can fail)",
          _want != _LANE_MAX_TOKENS,
          "profile == _LANE_MAX_TOKENS, so §5 would pass without reading it")
check("no agent falls back to the constant",
      resolve_max_tokens(None, authoring=False) == _LANE_MAX_TOKENS)
check("an unknown agent falls back to the constant",
      resolve_max_tokens("not-an-agent", authoring=False) == _LANE_MAX_TOKENS)

from services.authoring import STUDIO_LANE_MAX_TOKENS  # noqa: E402
check("an authoring turn keeps the Studio profile (ADR-440 D3 preserved)",
      resolve_max_tokens(_agent_with_profile, authoring=True) == STUDIO_LANE_MAX_TOKENS)
check("authoring > chat still holds",
      STUDIO_LANE_MAX_TOKENS > resolve_max_tokens(_agent_with_profile, authoring=False))

# Both turn loops must resolve it — a fix applied to one is the duplication
# the `_final_text_for` note warns about.
check("both turn loops resolve the ceiling through the helper",
      _src.count("resolve_max_tokens(agent, authoring=") == 2,
      str(_src.count("resolve_max_tokens(agent, authoring=")))
check("neither loop still reads the bare constant",
      "else _LANE_MAX_TOKENS\n" not in _src)


print("\n§6 D2 — NEW conversations only: the turn path never consults the override")

_turn_src = _src.split("def run_lane_turn", 1)[-1]
check("the turn path does not call resolve_agent_engine",
      "resolve_agent_engine(" not in _turn_src)
check("the turn path does not call resolve_member_engine",
      "resolve_member_engine(" not in _turn_src)

_routes = (ROOT / "routes" / "lanes.py").read_text()
check("the creation door resolves the override",
      "resolve_agent_engine(" in _routes)
check("the override is tried BEFORE the workspace-wide preference",
      _routes.index("resolve_agent_engine(_svc") < _routes.index("resolve_member_engine(_svc"))
check("the declared engine is the last resort",
      'or agent["model"]' in _routes)


print("\n§7 D4 — the door: the key is storable, and the pane reads labels")

import re as _re  # noqa: E402
_ms = (ROOT / "routes" / "member_state.py").read_text()
_m = _re.search(r'_KEY_RE = re\.compile\(r"([^"]+)"\)', _ms)
check("the member_state key pattern is readable", _m is not None)
if _m:
    _pat = _re.compile(_m.group(1))
    check("the scoped key passes the door's own pattern",
          bool(_pat.match(agent_engine_key("designer"))))
    check("the pattern still refuses a path-shaped key",
          not _pat.match("agent_engine:designer/../admin"))
    check("the pattern still refuses an empty segment",
          not _pat.match("agent_engine:"))

_agents_dir = ROOT.parent / "web" / "components" / "agents"
# BOTH files: the trigger lives on the pane, the roster and the commit step in
# the chooser. Reading only the pane would have gone quietly vacuous the moment
# the picker moved (it did — 2026-09-17, select -> modal).
_pane = ((_agents_dir / "AgentsSurface.tsx").read_text()
         + "\n" + (_agents_dir / "EngineChooserModal.tsx").read_text())
check("the pane no longer renders the raw routing key",
      "{agent.model}</dd>" not in _pane)
check("the pane renders engine LABELS",
      "m.label" in _pane or "labelFor(" in _pane)
# Strip comments: these two are about what RENDERS, and the files necessarily
# DISCUSS both `<select>` (why it was replaced) and providers (the grouping).
_pane_nc = _re.sub(r"\{/\*.*?\*/\}", "", _pane, flags=_re.S)
_pane_nc = _re.sub(r"/\*.*?\*/", "", _pane_nc, flags=_re.S)
_pane_nc = _re.sub(r"^\s*//.*$", "", _pane_nc, flags=_re.M)
check("the pane offers every served engine (no client-side vendor filter)",
      "g.rows.map(" in _pane_nc and "startsWith('anthropic" not in _pane_nc)
check("an unavailable engine is greyed, not filtered",
      "available === false" in _pane)
check("the pane says the choice applies to NEW conversations",
      "new conversations" in _pane.lower())

# ⭐ THE ACT IS DELIBERATE (operator, 2026-09-17: a dropdown "makes switching
# almost too easy"). A native <select> COMMITS ON CHANGE — a stray scroll or
# arrow key re-points an agent with no confirm and no undo. The chooser holds a
# PENDING selection and writes only on confirm.
check("no native select commits the engine",
      "<select" not in _pane_nc)
check("the choice is held pending until confirmed",
      "setPicked(" in _pane and "const dirty =" in _pane)
# ⚠️ This check was "onConfirm(picked) in _pane" and PASSED against a falsifier
# that ALSO wrote on every pick — the confirm call still existed, so the check
# could not see the second write. Assert the ROW only sets pending state: the
# absence is the property, so the absence is what gets asserted.
check("confirm is the only thing that writes",
      "onConfirm(picked)" in _pane_nc
      and "onClick={() => setPicked(id)}" in _pane_nc
      and "setPicked(id); void onConfirm" not in _pane_nc)
check("confirm is disabled until something actually changed",
      "disabled={!dirty || busy}" in _pane)
check("the engines are grouped by provider, DERIVED from the id",
      "function providerOf(" in _pane and "id.split('/')[0]" in _pane)

# The ROSTER shows the engine too (2026-09-17 operator ask). Before this the
# engine lived only on the detail page, so "which of these is on Opus" was a
# three-click question on a three-row list.
check("the roster row renders the engine",
      "EngineTag" in _pane and "function EngineTag(" in _pane)
check("the roster row resolves the LABEL, not the routing key",
      "models.find((m) => m.id === agent.model)?.label" in _pane)
check("the roster reads the same models roster the picker does",
      _pane.count("models={models}") >= 2)
# A discriminator label with nothing to discriminate against: "In an app" named
# what every row's own app chip already showed, and its only sibling section
# renders when `offered.length > 0` — nobody is offered (ADR-599 D1).
# Strip comments first: the rule is about what RENDERS, and the comment
# explaining the removal necessarily quotes the label it removed. A raw
# substring check would red on its own rationale.
_pane_code = _re.sub(r"\{/\*.*?\*/\}", "", _pane, flags=_re.S)
_pane_code = _re.sub(r"/\*.*?\*/", "", _pane_code, flags=_re.S)
check("the single-group section carries no discriminator header",
      "In an app" not in _pane_code)
check("the sibling header survives for when an agent IS offered",
      "To work with" in _pane)
# The clear must send a shape the door ACCEPTS. `Body(...)` is required and a
# bare JSON `null` reads as a missing body — the live 422 this check pins.
check("the pane clears with {} and never a bare null",
      "model ? { model } : {}" in _pane_code
      and "model ? { model } : null" not in _pane_code)

_payload = _routes
check("the envelope serves the declared default",
      '"model_default"' in _payload)
check("the envelope serves the member's override as a FIELD",
      '"model_override"' in _payload)


print(f"\n{N - len(FAILS)}/{N} checks passed")
if FAILS:
    print("\nFAILED:")
    for f in FAILS:
        print(f"  - {f}")
    sys.exit(1)
