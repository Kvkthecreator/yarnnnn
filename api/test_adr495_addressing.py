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


def test_human_mentions_resolve_but_never_fire_a_turn():
    """A human mention routes ATTENTION, never a TURN (ADR-605 built the
    ADR-492 D3 split; ADR-495 D6's gap is closed). Recognizing one must not
    select a responder, and must not be mistaken for an unresolved handle —
    the caller stamps `humans` onto the message row for the kernel to derive
    the To-do entry + dial-gated email from."""
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

#: Lisa WAS a member-authored Agent. ADR-599 D2/D3 deleted that machinery
#: whole (`find_member_agents`, `_agent.yaml`, `based_on`), so the roster is
#: kernel-only and a deleted colleague's cast row falls back to its slug —
#: honestly, which is the behaviour `_build_cast_section` documents and these
#: tests now assert. The old `_member_agents` monkeypatch fixture is DELETED,
#: not repaired: it patched a symbol that no longer exists, so every test
#: using it errored at setup and asserted nothing (4 of them, standing red).
#: `test_agent_registry.py` §2 independently asserts the symbol stays gone.
LISA_SLUG = "lisa"


def test_the_frame_names_the_room(monkeypatch):
    """The composed system prompt must name the other cast members. Asserted on
    the COMPOSED OUTPUT, not on the template: a section that exists but is
    never formatted in is exactly the shape that shipped."""
    import services.lane_runner as LR
    monkeypatch.setattr(LR, "_read_workspace_file", lambda c, u, p: "")

    full = LR.build_lane_conventions(
        None, "u-1", model="anthropic/claude-sonnet-5",
        member_label="kvkthecreator@gmail.com",
        agent="sonnet", cast=CAST, responder_reason="addressed",
    )
    assert "Who else is here" in full
    assert LISA_SLUG in full, "the cast-mate the Agent denied must be named"
    assert "One reply per turn" in full


def test_a_solo_conversation_is_unchanged(monkeypatch):
    """The overwhelmingly common case must be byte-identical to before —
    a cast of one gets no section at all."""
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
    from services.lane_runner import _build_cast_section
    section = _build_cast_section(None, "u-1", CAST, responder="sonnet", reason="addressed")
    assert LISA_SLUG in section
    assert "Thinker" not in section


def test_the_roster_degrades_never_raises(monkeypatch):
    """A conversation must never fail to run because the roster was unreadable.

    Patched at the LIVE seam (`resolve_agent`, the kernel lookup
    `_build_cast_section` actually calls) rather than at the deleted
    member-agent reader — a degrade test aimed at a symbol that no longer
    exists proves nothing about the path that runs.
    """
    import services.agents_registry as AR

    def boom(slug):
        raise RuntimeError("roster down")

    monkeypatch.setattr(AR, "resolve_agent", boom)
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


# ---------------------------------------------------------------------------
# 6. The surface — a turn is authored BY A PRINCIPAL
# ---------------------------------------------------------------------------

WEB = pathlib.Path(__file__).parent.parent / "web/components/chat-surface"


def test_the_transcript_has_no_species_split():
    """`foreign` required `role === 'user'`, so a HUMAN could be someone else
    but an ASSISTANT was always "the machine" — one anonymous grey column. That
    is the same species law ADR-495 D3 stripped out of the substrate, left
    standing in the renderer. Authorship must be one model for every turn."""
    panel = (WEB / "LanePanel.tsx").read_text()
    body = panel[panel.index("{messages.map("):]
    assert "const foreign =" not in body, (
        "a species-split author test cannot express two Agents in one cast"
    )
    assert "const isOwn =" in body and "const authorKey =" in body
    # Run-grouping must key on the AUTHOR, not the role — otherwise consecutive
    # replies from DIFFERENT Agents collapse into one visual run (both have
    # authorPrincipalId === undefined, and undefined !== undefined is false).
    assert "prevKey !== authorKey" in body


def test_the_message_carries_who_spoke():
    """The API has persisted `metadata.agent_slug` since addressing shipped;
    nothing read it, so a RELOADED multi-agent transcript was anonymous."""
    panel = (WEB / "LanePanel.tsx").read_text()
    assert "agentSlug?: string;" in panel, "the message model needs a speaker slot"
    assert "m.metadata?.agent_slug" in panel, "mapMessages must read what the API writes"
    # ...and the LIVE bubble, before the row is ever persisted.
    assert "onSpeaker" in panel
    client = (WEB.parent.parent / "lib/api/client.ts").read_text()
    assert "onSpeaker?" in client, "the SSE reader must dispatch the speaker frame"


def test_the_server_puts_the_speaker_on_the_wire():
    """The route always knew the responder and never sent it, so a live reply
    from Lisa rendered under the lane's engine label."""
    src = (pathlib.Path(__file__).parent / "routes/lanes.py").read_text()
    body = src[src.index("def _turn_stream_response"):]
    assert '"speaker"' in body, "WHO must precede WHAT on the wire"
    assert 'done["agent_slug"] = responder' in body, (
        "a tool-only turn yields no delta and would finalize unattributed"
    )


def test_the_mention_menu_only_offers_what_the_router_honours():
    """An unresolved handle is never fuzzy-matched server-side, so a menu that
    could emit an invalid handle would promise a delivery that never happens.

    Re-anchored 2026-08-25 (ADR-605): people are LIVE targets now — an @person
    routes attention (To-do + dial-gated email), so the selectable list holds
    the whole cast. What this test defends is unchanged: the menu emits only
    cast handles, and the flat keyboard order matches the render order."""
    menu = (WEB / "MentionMenu.tsx").read_text()
    assert "onItemsChange(selectable)" in menu
    assert "agentRows, ...peopleRows" in menu, "the whole cast may be picked (ADR-605)"
    # A filter matching nobody must CLOSE the menu, or a typed email address
    # strands it over the composer (the StudioSlashPalette lesson).
    assert "onClose();" in menu and "filter.length > 0" in menu


def test_out_of_band_freshness_is_not_gated_on_species():
    """A solo-human conversation with two Agents polled NEVER, so an Agent turn
    addressed from another tab never arrived until remount."""
    panel = (WEB / "LanePanel.tsx").read_text()
    chat = (WEB / "ChatSurface.tsx").read_text()
    assert "canReceiveOutOfBandTurns" in panel
    assert "hasOtherHumans={" not in chat, "the gate must not name one species"


def test_the_default_recipient_is_stated_quietly_not_announced():
    """WHO answers an unaddressed message must be VISIBLE, not INSTRUCTIONAL.

    The first attempt surfaced the continuity rung as a standing chip above the
    composer ("Thinker answers next ✕ · @ someone to redirect") with a
    server-side `release_floor` to hand it back. The operator's read was right:
    that is a permanent instructional banner plus a second gesture, for a fact
    that is only interesting in passing. A conventional chat states the
    recipient in the placeholder and marks the standing fact where the roster
    lives — the redirect gesture is already `@`, and needs no partner.

    Both homes are asserted so the fact cannot silently go missing again, and
    the banner+release machinery is asserted GONE so it cannot creep back.
    """
    panel = (WEB / "LanePanel.tsx").read_text()
    detail = (WEB / "ConversationDetail.tsx").read_text()

    # Quiet home 1 — the composer names who will actually answer.
    assert "`Message ${floorName}…`" in panel
    # Quiet home 2 — the roster marks the standing default.
    assert "defaultResponder" in detail
    assert "Replies when you don’t say who" in detail

    # The loud version is gone, both halves.
    # Asserted on RENDERED markup, not prose: both surviving mentions of the
    # phrase are comments recording why the banner was removed, and a naive
    # substring check reads its own explanation as a violation.
    assert ">answers next<" not in panel and "answers next</span>" not in panel, (
        "a standing instructional banner is not quiet"
    )
    assert "release_floor" not in (
        pathlib.Path(__file__).parent / "routes/lanes.py"
    ).read_text(), "the redirect gesture is `@`; a second one is a dead wire"

    # ONE derivation, reported up — two would be free to disagree.
    assert "onDefaultResponderChange" in panel


def test_a_human_always_has_a_readable_label():
    """Operator-observed 2026-08-14: a peer rendered as "member-2abf3f96".

    Humans were the ONLY principal class whose label could come back None —
    every other branch ends in `or principal_id` — so one transient admin-API
    hiccup produced a UUID-shaped stand-in in the transcript. The endpoint also
    re-implemented resolution instead of using the ONE resolver, which is why
    it had neither the cache nor the `user_metadata` name lookup.

    `principal_display` states the invariant it exists to hold: a degraded
    label is "NEVER a UUID or email".
    """
    src = (pathlib.Path(__file__).parent / "routes/workspace.py").read_text()
    # Anchored on the exact def — `get_workspace_memberships` is a DIFFERENT,
    # similarly-named endpoint and a prefix match silently audits the wrong one.
    body = src[src.index("def get_workspace_members("):]
    body = body[: body.index("\n@router")] if "\n@router" in body else body
    assert "resolve_member_names(" in body, "use the ONE resolver, not a second derivation"
    assert "svc.auth.admin.get_user_by_id" not in body, (
        "a second, uncached, name-blind derivation is what shipped the defect"
    )
    assert "or UNRESOLVED_MEMBER" in body, "humans need a terminal fallback like every other class"

    # ...and no surface may invent a UUID-shaped stand-in of its own.
    for name in ("ChatSurface.tsx", "LanePanel.tsx"):
        text = (WEB / name).read_text()
        assert "member-${" not in text, (
            f"{name} prints a UUID prefix as a person's name — the exact string "
            "principal_display forbids"
        )


def test_the_frontend_shows_one_speaker_not_the_room():
    """The indicator read "Thinker, Lisa is working…" for a single reply — the
    ROOM label passed to a prop documented as "the resident's name"."""
    web = pathlib.Path(__file__).parent.parent / "web/components/chat-surface/ChatSurface.tsx"
    src = web.read_text()
    assert "speakerLabel={laneSpeaker(activeLane)}" in src
    assert "speakerLabel={laneLabel(activeLane)}" not in src, (
        "laneLabel is the ROOM's name; one reply must never be attributed to two faces"
    )
