"""Addressing — WHO in the cast this turn is spoken to (ADR-492 D3, ADR-495 D3).

THE FACT THIS MODULE OWNS

A Conversation may hold N Agents (ADR-495 D3). Something has to decide which
one answers a given turn, and ADR-492 D3 already named it: *"rung (a) 'pick who
answers' IS who you address."* Until now nothing implemented that sentence —
`routes/lanes.py` took `cast_agents[0]`, so the first-invited Agent answered
every turn forever and every other face in the cast was structurally
unreachable. A member typing "@lisa can you hear me" got Thinker replying that
no such agent exists.

WHY A MENTION AND NOT A PICKER. ADR-492 D3 is explicit that no per-turn engine
picker exists or arrives: addressing is *authored content*, inside the
conversation grammar, species-blind by construction — "you address a person or
a named hand with the same gesture." The `@name` stays in the message the
member sent; this module only READS it. Nothing is stripped, nothing is
rewritten, and the transcript keeps exactly what was typed.

WHAT THIS DELIBERATELY DOES NOT DO

- **No human TURN routing.** A human mention never fires anything and never
  selects a responder — a person answers when they answer. What it does reach,
  since ADR-605 closed the ADR-495 D6 gap: the ATTENTION consequence. The
  caller (`routes/lanes.py`) stamps `resolve_address`'s `humans` onto the
  message row (`metadata.mentions`) and the kernel derives the To-do entry +
  dial-gated email from there (`services/mentions.py`). Same gesture, two
  consequence machineries: @agent = a turn now (the mention IS the human act
  that fires it); @human = attention routed (ADR-492 D3's split, built).
- **No change to never-ambient.** This selects WHICH agent answers a human act;
  it never causes a turn. A message with no mention still fires exactly one
  reply, from the same agent as before.
- **No multi-responder.** ADR-495 D3 is singular ("addressing selects which one
  answers") and ADR-558 D3 restates it ("one authority for the responder"). Two
  mentions resolve to the FIRST, and `resolve_address` returns one slug.
"""

from __future__ import annotations

import re
from typing import Any, Optional

#: An `@handle` in authored text. Handles are matched case-insensitively
#: against BOTH an agent's slug (`sonnet`) and its display name (`Thinker`),
#: because the member reads the name and never sees the slug.
#:
#: `[\w-]+` (not `\S+`) so trailing punctuation is not eaten: "@lisa, hello"
#: addresses `lisa`. The leading boundary keeps an email address from parsing
#: as a mention — `kvk@gmail.com` must not address `gmail`.
_MENTION = re.compile(r"(?:(?<=\s)|(?<=^))@([\w-]+)", re.UNICODE)


def _handles(participant: dict, roster: dict[str, dict]) -> set[str]:
    """Every spelling that addresses this participant, lowercased.

    Both the slug and the display name: a member types the name they can see.
    A name with spaces ("Deal Desk") contributes its squashed form, since the
    mention grammar is one token.
    """
    slug = (participant.get("agent_slug") or "").strip()
    out = {slug.lower()} if slug else set()
    character = roster.get(slug) or {}
    name = (character.get("name") or "").strip()
    if name:
        out.add(name.lower())
        if " " in name:
            out.add(name.replace(" ", "").lower())
    return {h for h in out if h}


def mentions(text: str) -> list[str]:
    """Every `@handle` in authored text, lowercased, in order, deduped."""
    seen: list[str] = []
    for raw in _MENTION.findall(text or ""):
        h = raw.lower()
        if h not in seen:
            seen.append(h)
    return seen


def resolve_address(
    text: str,
    participants: list[dict],
    *,
    roster: Optional[dict[str, dict]] = None,
) -> dict[str, Any]:
    """Who this turn is addressed to.

    Returns::

        {"agent": <slug|None>,     # the addressed Agent, if one was named
         "humans": [<principal_id>],  # humans named (recognized, NOT notified)
         "unresolved": [<handle>]}    # handles matching nobody in the cast

    PURE — no DB, no client. The caller supplies the cast (from
    `conversation_cast.list_participants`) and, optionally, a slug→character
    roster for display-name matching.

    An unrecognized handle is REPORTED, never guessed at. Fuzzy-matching a
    mention to the nearest agent would make a typo silently address a colleague
    the member did not choose — the one failure mode worse than not routing.
    """
    roster = roster or {}
    found = mentions(text)
    if not found:
        return {"agent": None, "humans": [], "unresolved": []}

    agent_by_handle: dict[str, str] = {}
    human_by_handle: dict[str, str] = {}
    for p in participants or []:
        if p.get("member_kind") == "agent" and p.get("agent_slug"):
            for h in _handles(p, roster):
                agent_by_handle.setdefault(h, p["agent_slug"])
        elif p.get("member_kind") == "human" and p.get("principal_id"):
            # Every spelling that addresses this person — the mirror of
            # `_handles` for agents: the resolved label (a full name or an
            # email local-part, per `principal_display.resolve_member_names`),
            # its space-squashed form (the mention grammar is one token), and
            # the raw email local-part. The FE menu emits the squashed form;
            # accepting all three keeps a hand-typed handle honest too.
            label = (p.get("display_name") or p.get("email") or "").strip()
            if label:
                local = label.split("@")[0]
                for h in {local.lower(), local.replace(" ", "").lower()}:
                    if h:
                        human_by_handle.setdefault(h, p["principal_id"])

    agent: Optional[str] = None
    humans: list[str] = []
    unresolved: list[str] = []
    for h in found:
        if h in agent_by_handle:
            # FIRST mention wins — one responder per turn (ADR-495 D3).
            if agent is None:
                agent = agent_by_handle[h]
        elif h in human_by_handle:
            if human_by_handle[h] not in humans:
                humans.append(human_by_handle[h])
        else:
            unresolved.append(h)
    return {"agent": agent, "humans": humans, "unresolved": unresolved}


def select_responder(
    text: str,
    participants: list[dict],
    *,
    roster: Optional[dict[str, dict]] = None,
    fallback: Optional[str] = None,
) -> tuple[Optional[str], str]:
    """The Agent that answers this turn, and WHY — `(slug, reason)`.

    The reason is returned rather than logged so the caller can put it on the
    turn's metadata: "why did Lisa answer?" must be answerable from the record,
    not re-derived from the text months later.

    Precedence, and the reasoning for each rung:

    1. ``addressed`` — a mention naming an Agent in the cast. The member said
       who; nothing outranks that.
    2. ``sole_agent`` — no mention, exactly one Agent present. The degenerate
       case ADR-492 D3 names: "a cast of one, where every turn is implicitly
       addressed to the lane's Agent."
    3. ``last_responder`` — no mention, several Agents, and one of them spoke
       last. A conversation continues with whoever you were talking to; making
       the member re-address every turn would be the picker ADR-492 D3 refused.
    4. ``first_in_cast`` — no mention, several Agents, none has spoken. Join
       order, the pre-addressing behavior, kept as the floor so a cast that has
       never been addressed behaves exactly as it does today.
    5. ``lane_agent`` — no Agents in the cast at all: the lane's creation-time
       scalar (pre-cast Studio/derive lanes).
    """
    resolved = resolve_address(text, participants, roster=roster)
    if resolved["agent"]:
        return resolved["agent"], "addressed"

    from services.conversation_cast import agent_slugs

    cast_agents = agent_slugs(participants or [])
    if not cast_agents:
        return fallback, "lane_agent"
    if len(cast_agents) == 1:
        return cast_agents[0], "sole_agent"
    if fallback and fallback in cast_agents:
        return fallback, "last_responder"
    return cast_agents[0], "first_in_cast"


__all__ = ["mentions", "resolve_address", "select_responder"]
