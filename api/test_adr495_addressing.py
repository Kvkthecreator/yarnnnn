"""ADR-492 D3 / ADR-495 D3 — addressing selects who answers.

THE DEFECT THIS GATE EXISTS FOR (operator-observed, prod, 2026-08-13). A
conversation held {member, Thinker, Lisa}. The member typed "@lisa can you hear
me". THINKER replied: "I'm Thinker, not Lisa — there's no agent by that name
active in this session or workspace that I can see."

Three layers were missing at once, and each is asserted here:

  1. `routes/lanes.py` took `cast_agents[0]` — join order, unconditionally — so
     the first-invited Agent answered every turn and every other face in the
     cast was structurally unreachable.
  2. No mention parsing existed anywhere in the codebase, so "@lisa" was
     transported to the model as literal prose.
  3. The system frame named exactly two entities (the model and the member), so
     Thinker's denial was TRUE from inside its own prompt. It was not
     hallucinating; the injection point did not exist.

Run: python3 -m pytest test_adr495_addressing.py -q
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from services.addressing import mentions, resolve_address, select_responder  # noqa: E402

CAST = [
    {"member_kind": "agent", "agent_slug": "sonnet"},
    {"member_kind": "human", "principal_id": "u-1", "email": "kvkthecreator@gmail.com"},
    {"member_kind": "agent", "agent_slug": "lisa"},
]
ROSTER = {"sonnet": {"name": "Thinker"}, "lisa": {"name": "Lisa"}}


# ---------------------------------------------------------------------------
# 1. The observed defect
# ---------------------------------------------------------------------------

def test_the_addressed_agent_answers():
    """The exact prod transcript: "@lisa can you hear me" must reach Lisa."""
    assert select_responder("@lisa can you hear me", CAST, roster=ROSTER) == (
        "lisa", "addressed",
    )


def test_a_cast_mate_is_reachable_at_all():
    """`cast_agents[0]` made every face after the first unreachable. This is
    the standing law that replaces the tuple-pin the old gate carried."""
    assert select_responder("@lisa hi", CAST, roster=ROSTER)[0] != "sonnet"


# ---------------------------------------------------------------------------
# 2. The grammar — matched on what the MEMBER can see
# ---------------------------------------------------------------------------

def test_matching_is_by_display_name_and_slug():
    """A member reads "Thinker" and never sees `sonnet`; for kernel rows the
    two differ outright, so name-matching is the load-bearing half."""
    assert select_responder("@Thinker hi", CAST, roster=ROSTER)[0] == "sonnet"
    assert select_responder("@sonnet hi", CAST, roster=ROSTER)[0] == "sonnet"
    for spelling in ("@Lisa", "@LISA", "@lisa"):
        assert select_responder(f"{spelling} hi", CAST, roster=ROSTER)[0] == "lisa"


def test_the_grammar_does_not_over_match():
    """An email must not address `gmail`; punctuation must not be eaten."""
    assert mentions("write to kvk@gmail.com") == []
    assert mentions("a@b") == []
    assert select_responder("@lisa, are you there?", CAST, roster=ROSTER)[0] == "lisa"


def test_one_responder_per_turn():
    """ADR-495 D3 is singular ("which ONE answers"); ADR-558 D3 restates it."""
    slug, reason = select_responder("@lisa and @Thinker", CAST, roster=ROSTER)
    assert (slug, reason) == ("lisa", "addressed")


def test_an_unknown_handle_is_never_guessed_at():
    """Fuzzy-matching would make a typo silently address a colleague the member
    did not choose — worse than not routing."""
    r = resolve_address("@lisaa typo", CAST, roster=ROSTER)
    assert r["agent"] is None and r["unresolved"] == ["lisaa"]
    assert select_responder("@lisaa typo", CAST, roster=ROSTER)[1] != "addressed"


def test_human_mentions_resolve_but_route_nowhere():
    """ADR-495 D6 defers human mentions because they belong with notifications
    ("a mention routing nowhere is theatre"). Recognizing one must not fire a
    turn at it, and must not be mistaken for an unresolved handle."""
    r = resolve_address("@kvkthecreator hello", CAST, roster=ROSTER)
    assert r["agent"] is None
    assert r["humans"] == ["u-1"]


# ---------------------------------------------------------------------------
# 3. The ladder — no mention
# ---------------------------------------------------------------------------

def test_the_no_mention_ladder():
    """Each rung, including the two that preserve today's behavior exactly."""
    assert select_responder("hi", CAST[:2], roster=ROSTER) == ("sonnet", "sole_agent")
    assert select_responder("hi", CAST, roster=ROSTER, fallback="lisa") == (
        "lisa", "last_responder",
    )
    assert select_responder("hi", CAST, roster=ROSTER) == ("sonnet", "first_in_cast")
    assert select_responder("hi", [CAST[1]], fallback="designer") == (
        "designer", "lane_agent",
    )


def test_a_stale_fallback_is_ignored():
    """An Agent that left the cast must not keep answering."""
    assert select_responder("hi", CAST, roster=ROSTER, fallback="ghost") == (
        "sonnet", "first_in_cast",
    )


# ---------------------------------------------------------------------------
# 4. The frame — the layer that made the denial TRUE
# ---------------------------------------------------------------------------

#: Lisa is a MEMBER-authored Agent (an `_agent.yaml` folder), not a kernel row
#: — which is exactly what the prod cast held. Stubbed here so the frame tests
#: resolve her display name the way `find_member_agents` does live.
LISA = {"slug": "lisa", "name": "Lisa", "blurb": "Runs the deal desk.",
        "model": "anthropic/claude-sonnet-5", "kernel": False}


def _member_agents(monkeypatch, agents=(LISA,)):
    import services.agents_registry as AR
    monkeypatch.setattr(AR, "find_member_agents", lambda c, u: list(agents))


def test_the_frame_names_the_room(monkeypatch):
    """The composed system prompt must name the other cast members. Asserted on
    the COMPOSED OUTPUT, not on the template: a section that exists but is
    never formatted in is exactly the shape that shipped."""
    _member_agents(monkeypatch)
    import services.lane_runner as LR
    monkeypatch.setattr(LR, "_read_workspace_file", lambda c, u, p: "")

    full = LR.build_lane_conventions(
        None, "u-1", model="anthropic/claude-sonnet-5",
        member_label="kvkthecreator@gmail.com",
        agent="sonnet", cast=CAST, responder_reason="addressed",
    )
    assert "Who else is here" in full
    assert "Lisa" in full, "the cast-mate the Agent denied must be named"
    assert "One reply per turn" in full


def test_a_solo_conversation_is_unchanged(monkeypatch):
    """The overwhelmingly common case must be byte-identical to before —
    a cast of one gets no section at all."""
    _member_agents(monkeypatch)
    import services.lane_runner as LR
    monkeypatch.setattr(LR, "_read_workspace_file", lambda c, u, p: "")

    solo = LR.build_lane_conventions(
        None, "u-1", model="anthropic/claude-sonnet-5", member_label="k@e.com",
        agent="sonnet", cast=[{"member_kind": "agent", "agent_slug": "sonnet"}],
    )
    none = LR.build_lane_conventions(
        None, "u-1", model="anthropic/claude-sonnet-5", member_label="k@e.com",
        agent="sonnet",
    )
    assert "Who else is here" not in solo
    assert "Who else is here" not in none
    assert solo == none, "a solo cast must compose exactly as no cast at all"


def test_the_speaker_is_never_listed_as_its_own_cast_mate(monkeypatch):
    _member_agents(monkeypatch)
    from services.lane_runner import _build_cast_section
    section = _build_cast_section(None, "u-1", CAST, responder="sonnet", reason="addressed")
    assert "Lisa" in section
    assert "Thinker" not in section


def test_the_roster_degrades_never_raises(monkeypatch):
    """A conversation must never fail to run because the roster was unreadable."""
    import services.agents_registry as AR
    def boom(c, u):
        raise RuntimeError("roster down")
    monkeypatch.setattr(AR, "find_member_agents", boom)
    from services.lane_runner import _build_cast_section
    assert _build_cast_section(None, "u-1", CAST, responder="sonnet") == ""


# ---------------------------------------------------------------------------
# 5. Attribution — the latent blocker
# ---------------------------------------------------------------------------

def test_the_route_passes_the_MESSAGE_to_the_resolver():
    """⚠️ THE WIRING, not the helper.

    Falsified 2026-08-13: replacing the route's `content` argument with `""`
    left every other check in this file GREEN — they exercise
    `select_responder` directly, so a perfectly correct resolver that the route
    never feeds the member's text would ship behind a full green board. That is
    the recorded "gate tests the derivation, not the wiring" shape.

    Asserted structurally because the route body is not callable in isolation
    (FastAPI deps, streaming, DB). The claim is narrow and real: the FIRST
    argument to `select_responder` at the call site is the member's message.
    """
    import ast

    src = (pathlib.Path(__file__).parent / "routes/lanes.py").read_text()
    tree = ast.parse(src)
    calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "select_responder"
    ]
    assert calls, "the route must resolve the responder by addressing"
    for call in calls:
        assert call.args, "select_responder needs the member's text positionally"
        first = call.args[0]
        assert isinstance(first, ast.Name) and first.id == "content", (
            "the resolver must receive the MEMBER'S MESSAGE — a literal or a "
            "stripped variable means '@lisa' never reaches the parser and the "
            "responder silently falls back to join order"
        )
        kwargs = {k.arg for k in call.keywords}
        assert "fallback" in kwargs, "the pre-cast/continuity fallback must be passed"
        assert "roster" in kwargs, "display-name matching needs the roster"


def test_the_runner_receives_the_cast():
    """The frame can only name the room if the route hands the cast over."""
    src = (pathlib.Path(__file__).parent / "routes/lanes.py").read_text()
    body = src[src.index("def _turn_stream_response"):]
    assert "cast=cast," in body, "the turn must carry its participants"
    assert "responder_reason=responder_reason," in body


def test_the_assistant_row_records_who_spoke():
    """`responder` was computed and thrown away, so a transcript could never
    say which cast member answered. With addressing live, two Agents' replies
    would otherwise render identically on reload."""
    src = (pathlib.Path(__file__).parent / "routes/lanes.py").read_text()
    body = src[src.index("def _turn_stream_response"):]
    assert 'extra["agent_slug"] = responder' in body
    assert 'extra["responder_reason"] = responder_reason' in body


def test_the_frontend_shows_one_speaker_not_the_room():
    """The indicator read "Thinker, Lisa is working…" for a single reply — the
    ROOM label passed to a prop documented as "the resident's name"."""
    web = pathlib.Path(__file__).parent.parent / "web/components/chat-surface/ChatSurface.tsx"
    src = web.read_text()
    assert "speakerLabel={laneSpeaker(activeLane)}" in src
    assert "speakerLabel={laneLabel(activeLane)}" not in src, (
        "laneLabel is the ROOM's name; one reply must never be attributed to two faces"
    )
