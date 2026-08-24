"""ADR-558 — chat is the engine surface; Agents are personified. The ratchet.

Run: python3 test_adr558_chat_is_engines.py   (from api/)

What this defends: **a chat conversation is created with an ENGINE and has no
birth-persona; who replies is the cast's answer.** Apps keep their residents.

The dual approach this closes (recorded verbatim at routes/lanes.py:788-793):
`lane_meta["agent"]` was a creation-time scalar ADR-495 D3 had already retired
into the cast. Two authorities for "who replies" produced a live bug — an Agent
added via CastBar never replied, because the cast said yes and lane_meta said
nobody.

The handler is EXECUTED, not grepped: a 422 that exists in source but never
fires is the failure mode this codebase keeps hitting.
"""

from __future__ import annotations

import ast
import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

FAILS: list[str] = []
N = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global N
    N += 1
    if cond:
        print(f"  ok   {label}")
    else:
        FAILS.append(label)
        print(f"  FAIL {label}" + (f"\n         {detail}" if detail else ""))


os.environ["MODEL_ROUTER_ENABLED"] = "1"

from fastapi import HTTPException  # noqa: E402

import routes.lanes as L  # noqa: E402


class _Auth:
    """Enough auth to reach the validation block; the DB is never touched
    because every case below is refused before persistence."""

    user_id = "u-probe"
    workspace_id = None
    principal_id = "u-probe"

    class client:  # noqa: N801
        @staticmethod
        def table(_name):
            class Q:
                def select(self, *a, **k): return self
                def eq(self, *a, **k): return self
                def like(self, *a, **k): return self
                def limit(self, *a, **k): return self
                def order(self, *a, **k): return self

                def execute(self):
                    class R:
                        data: list = []
                    return R()
            return Q()


def _create(**kw):
    """Run the real handler; return ('http', status, detail) or ('other', exc)."""
    try:
        asyncio.run(L.create_lane(L.CreateLaneRequest(**kw), _Auth()))
        return ("ok", None, None)
    except HTTPException as exc:
        return ("http", exc.status_code, str(exc.detail))
    except Exception as exc:  # noqa: BLE001 — got past validation into the fake DB
        return ("other", type(exc).__name__, None)


print("1. D1/D3 — a CHAT lane is created with an engine, never a persona")

# ADR-562 D3: the client names the APP, never the colleague — so the D3 rule is
# now driven through `app=`. (`agent=` is gone from the request model entirely;
# asserting on it here would pass for the WRONG reason — Pydantic refusing an
# unknown field, not this rule refusing a persona at the chat door.)
kind, status, detail = _create(app="studio")
check("a residency WITHOUT a binding is refused", kind == "http" and status == 422,
      f"got {kind}/{status}")
check("...and the refusal says why (engine, not colleague)",
      bool(detail) and "engine" in detail.lower() and "cast" in detail.lower(),
      f"detail={detail!r}")

# The removal itself, asserted as BEHAVIOUR: a client that still sends `agent`
# must not quietly get a lane. Pydantic's default would IGNORE an unknown field,
# which would let a stale client keep asserting identity and be silently obeyed
# by nothing — the failure mode ADR-562 exists to end.
check("the request model no longer carries `agent` (identity is server-derived)",
      "agent" not in L.CreateLaneRequest.model_fields,
      f"fields={sorted(L.CreateLaneRequest.model_fields)}")

kind, status, detail = _create()
check("no engine at all is refused", kind == "http" and status == 422, f"got {kind}/{status}")

kind, status, detail = _create(model="acme/not-a-model")
check("an unroutable engine is refused", kind == "http" and status == 422,
      f"got {kind}/{status}")

# A real engine must get PAST validation (it dies later in the fake DB, which is
# the proof it was accepted — this is the case that would break if the guard
# over-fired).
from services.lane_runner import LANE_MODELS, lane_model_availability  # noqa: E402

# ADR-559: pick an engine that is actually AVAILABLE in this environment.
# `next(iter(LANE_MODELS))` used to be safe when every row was offerable; now
# the create gate also refuses retired and unavailable engines, and this
# harness runs with no provider keys, so a fixed first-row pick asserts the
# availability gate rather than the ADR-558 one. Fall back to asserting the
# refusal is the AVAILABILITY refusal, never the persona refusal.
_available = [m for m in LANE_MODELS if lane_model_availability(m)[0]]
if _available:
    kind, status, _ = _create(model=_available[0])
    check("a real engine passes validation", kind == "other",
          f"got {kind}/{status} — a valid engine was refused")
else:
    kind, status, detail = _create(model=next(iter(LANE_MODELS)))
    check("a valid engine is never refused for the ADR-558 persona reason",
          not (kind == "http" and "cast" in (detail or "").lower()),
          f"refused as a persona error, not an availability one: {detail!r}")

print("\n2. D3 — an APP still pins its resident (ADR-467 D1 untouched)")

for binding in (
    {"artifact_path": "/workspace/operation/x/deck.html"},
    {"derive_recipe": "summary", "derive_source": "/workspace/x.md"},
):
    kind, status, detail = _create(agent="designer", **binding)
    refused_by_d3 = kind == "http" and status == 422 and "cast" in (detail or "").lower()
    check(f"bound lane keeps its resident ({', '.join(binding)})", not refused_by_d3,
          f"the D3 guard wrongly refused a bound lane: {detail!r}")

print("\n3. the cast is the SINGLE authority for who replies")

src = pathlib.Path("routes/lanes.py").read_text()
tree = ast.parse(src)
fn = next(n for n in ast.walk(tree)
          if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name == "create_lane")
body = ast.unparse(fn)

# The guard must key on the BINDING, not on a hardcoded surface name.
check("create_lane derives boundness from the binding fields",
      "is_bound" in body and "artifact_path" in body and "derive_recipe" in body)

# ⚠️ RE-ANCHORED 2026-08-24 (ADR-597 D1). The old pair pinned the STAMP
# (`lane_meta["agent"] = agent_slug`, "bound lanes need it") — retired: a
# bound lane's resident is a fact about the APP, derived at every read
# (`_lane_agent`). What ADR-558 D3 actually holds is unchanged and still
# checked here: an UNBOUND lane never acquires a resident — the 422 guard
# (section 2 above) refuses `agent` at the door, and the resident that DOES
# exist reaches the lane only through the app/recipe derivation, never a
# client assertion.
check("the resident is never stamped — it derives from the registration",
      'lane_meta["agent"] = agent_slug' not in src and "def _lane_agent(" in src)
check("...and the derivation keys on the BINDING (app/recipe), never the client",
      'lane_meta.get("app")' in src and 'lane_meta.get("derive_recipe")' in src)

print("\n4. the envelope leads with engines (the chat chooser)")

env_fn = next(n for n in ast.walk(tree)
              if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
              and n.name == "_lane_envelope")
env = ast.unparse(env_fn)
check("`models` is served (the chat chooser)", '"models"' in env or "'models'" in env)
# `agents` STAYS — the cast needs a roster of who may be invited. Removing it
# would break adding a colleague, which ADR-558 explicitly preserves.
check("`agents` is still served (the CAST's roster, not the door)",
      '"agents"' in env or "'agents'" in env)

print("\n5. FE — the door asks for an engine")

web = pathlib.Path("../web")
modal = (web / "components/chat-surface/NewChatModal.tsx").read_text()
check("modal takes engines, not agents", "engines" in modal and "agents:" not in modal)
check("modal no longer asks 'who do you want to talk to'",
      "Who do you want to talk to" not in modal)
check("modal carries the provider brand mark (D5)", "engineBrandIcon" in modal)
check("modal remembers the last engine (sticky)", "rememberEngine" in modal)

chat = (web / "components/chat-surface/ChatSurface.tsx").read_text()
check("the person-create path is DELETED (one create, not two)",
      "createConversationWithPerson" not in chat.replace(
          "`createLane(agentSlug)` and `createConversationWithPerson`", ""),
      "a second create path survived")
check("createLane sends model, never agent",
      "api.lanes.create({ model: engineId })" in chat)

brand = (web / "lib/ai-providers/brand-icons.tsx").read_text()
check("engine brand mapping lives beside the host-id one (one home)",
      "engineBrandIcon" in brand and "ENGINE_PROVIDER_MARKS" in brand)

print("\n6. DISPLAY reads the CAST, not the deleted birth-persona")

# The defect this section exists for (operator screenshot, 2026-08-12): the
# creation path was correct, but the LIST still rendered from `lane.agent` —
# the field ADR-558 removes from chat. So a colleague who JOINED a conversation
# had their name resolved from the cast while their AVATAR and card-link were
# resolved from a field that is now always null. Writing the new rule without
# migrating its readers is the recorded `feedback_migrate_every_reader_of_a_grain_together`
# failure; these checks are what make it visible.


def _fn_body(source: str, name: str) -> str:
    """The text of a `const <name> = useCallback(...)` block, up to the next
    top-level `const` — enough to assert what a helper reads from."""
    i = source.find(f"const {name} = ")
    if i < 0:
        return ""
    j = source.find("\n  const ", i + 10)
    return source[i: j if j > 0 else len(source)]


for helper, needs_cast in (("laneSubLabel", True), ("laneAvatarUrl", True)):
    body = _fn_body(chat, helper)
    check(f"{helper} exists", bool(body))
    # `participants` is the cast; a display helper must consult it.
    check(f"{helper} resolves the counterpart from the cast",
          "participants" in body and "member_kind" in body,
          "it reads lane.agent only, which is null on every chat lane")

# The header's card-link must not key on the bound-lane resident alone.
check("the header agent-link reads the cast first",
      "p.member_kind === 'agent'" in chat and "activeAgent?.slug ?? null" in chat,
      "a joined colleague's face would link nowhere")

# `laneAgent` SURVIVES on purpose — bound lanes have no participant rows, so
# deleting it would render a Studio lane as an engine instead of Designer.
check("laneAgent is retained for BOUND lanes (not deleted wholesale)",
      "const laneAgent = useCallback" in chat)


# ---------------------------------------------------------------------------
# The /agents door — D3 held from the OTHER side (fixed 2026-08-13)
# ---------------------------------------------------------------------------
# `/agents` "Start a chat" sent `create({ agent: slug })` — an UNBOUND lane
# naming a colleague — and 422'd on every click from `af5339f` until the
# ADR-566 arc. It was invisible because THIS gate only ever checked the server's
# refusal, never that any door still made the refused call. A green gate over a
# dead call is the failure mode; these checks close it.
import re as _re  # noqa: E402

agents_surface = (web / "components/agents/AgentsSurface.tsx").read_text()
# Strip comments before asserting ABSENCE — this file documents the very call
# it must not make, so a text scan would match the explanation and read a
# correct file as a violation.
_as_code = _re.sub(r"//.*$", "", agents_surface, flags=_re.M)
_as_code = _re.sub(r"/\*.*?\*/", "", _as_code, flags=_re.S)

check("the /agents door creates with an ENGINE, never a colleague",
      "lanes.create({ model:" in _as_code and "lanes.create({ agent" not in _as_code,
      "an unbound lane naming a colleague is the 422 this ADR defines")
check("...and joins the colleague through the CAST (ADR-495)",
      "addParticipant" in _as_code and "agent_slug" in _as_code,
      "who replies must come from the cast, not a birth-persona")
check("...and invents no engine when the member has none (ADR-467 D2)",
      "readLastEngine" in _as_code,
      "a default engine here would be the resident ADR-467 D2 refuses")


# ---------------------------------------------------------------------------
# D5 — ONE engine resolution, and the brand mark rides with it
# ---------------------------------------------------------------------------
# THE DEFECT (operator screenshot, 2026-08-13): the header read
# `Lisa · Critic · GPT-5` while the empty state read `New chat · Gemini Flash`.
# Both were honest about their own source — the header from the CAST agent's
# registry row, the body from `lane_meta.model` — and BOTH WERE TRUE. Two
# truths, one screen, and no way to tell which engine answers. The cause was a
# DUPLICATE derivation, so the fix is a single resolver every reader uses.
chat_src = (web / "components/chat-surface/ChatSurface.tsx").read_text()

check("there is ONE engine resolver for display (laneEngineLabel)",
      "const laneEngineLabel = useCallback" in chat_src)
check("...and the sub-label reads it rather than re-deriving",
      "laneEngineLabel(lane)" in chat_src
      and "a.engine || modelLabel(lane.model)" not in chat_src,
      "re-deriving the engine beside the resolver is how the two disagreed")
# RE-DERIVED 2026-08-13. This pinned `speakerLabel={laneLabel(activeLane)}`.
# The prop must be PASSED (the original claim, intact) — but `laneLabel` is the
# ROOM's name, so a 3-member cast rendered "Thinker, Lisa is working…" for one
# reply, implying both Agents were answering when ADR-495 D3 permits exactly
# one. The standing law is that the panel is told who SPEAKS; the room's label
# is a different question with a different answer.
check("the panel is told WHO is speaking (ADR-562 D5's prop, finally passed)",
      "speakerLabel={laneSpeaker(activeLane)}" in chat_src,
      "the prop existed and was never passed, so a chat with Lisa named an engine")
check("...and the SPEAKER is never the room's roster",
      "speakerLabel={laneLabel(activeLane)}" not in chat_src,
      "one reply must never be attributed to two faces (ADR-495 D3 is singular)")
check("...and the panel's engine label is the one that ANSWERS",
      "modelLabel={laneEngineLabel(activeLane)}" in chat_src,
      "the lane's birth engine is a ledger fact, not the present tense")

# ADR-558 D5 — "an engine-first surface should say whose engine it is."
check("the chat list rows carry the provider brand mark",
      "engineBrandIcon(laneEngineModel(lane))" in chat_src)
check("the header carries it too, keyed on the SAME resolution",
      "engineModel={" in chat_src and "laneEngineModel(activeLane)" in chat_src)
header_src = (web / "components/chat-surface/ConversationHeader.tsx").read_text()
check("...and the header renders it from a model id, not a label",
      "engineBrandIcon(engineModel)" in header_src)
check("the agents surface carries the mark as well",
      "engineBrandIcon(engines[" in agents_surface)

# D5 — ONE mark per vendor, drawn ONCE.
#
# THE DEFECT (operator-observed, 2026-08-13): `brand-icons.tsx` and
# `PlatformIcons.tsx` EACH drew their own Claude glyph and they were DIFFERENT
# artwork — the Anthropic corporate "A" in the chat surface, the Claude sunburst
# in the notification panel. One vendor, two brands, depending which surface you
# looked at. (The ChatGPT paths had also drifted apart by transcription noise.)
# The mapping module now IMPORTS the marks instead of re-drawing them.
brand_icons = (web / "lib/ai-providers/brand-icons.tsx").read_text()
platform_icons = (web / "components/ui/PlatformIcons.tsx").read_text()

check("the engine-mark module imports its artwork rather than re-drawing it",
      "from '@/components/ui/PlatformIcons'" in brand_icons)
check("...and draws no vendor <path> of its own",
      "<path" not in brand_icons,
      "a second copy of a vendor mark is how the Claude glyphs diverged")
check("Claude is the PRODUCT's mark, not the Anthropic corporate 'A'",
      "ClaudeIcon" in brand_icons and "M17.304 3.541" not in brand_icons,
      "the corporate 'A' path must not come back")
# Every vendor with a mark must render branded on EVERY surface — the principal
# badge degraded Gemini to a generic glyph while chat rendered it branded.
check("the MCP principal badge serves Gemini's mark too",
      'case "gemini":' in platform_icons)
for glyph in ("ClaudeIcon", "ChatGPTIcon", "GeminiIcon"):
    check(f"{glyph} is declared exactly once (in PlatformIcons)",
          platform_icons.count(f"export const {glyph}") == 1
          and f"const {glyph} =" not in brand_icons)

# The agent pane must not restate a name where it promises a description.
# Comments stripped: the fix's own comment NAMES the retired heading to record
# why it went, and a raw scan matches that prose (the repo's canonical trap —
# third time this session).
check("the agent pane shows no 'What they do' tautology for kernel agents",
      "What they do" not in _as_code,
      "it rendered 'What they do -> Thinker', the name under a description heading")

# The NUL byte that made a 47KB chat component invisible to `grep`.
lane_panel_bytes = (web / "components/chat-surface/LanePanel.tsx").read_bytes()
check("LanePanel.tsx holds no NUL byte (it read as BINARY to grep)",
      b"\x00" not in lane_panel_bytes,
      "a literal \\0 join delimiter hid the whole file from shell tooling")

print(f"\n{N - len(FAILS)}/{N} checks passed")
if FAILS:
    print("\nFAILURES:")
    for f in FAILS:
        print(f"  - {f}")
    sys.exit(1)
print("ADR-558 gate GREEN")
