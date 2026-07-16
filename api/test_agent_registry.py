"""The kernel Agent registry gate (ADR-460 D4 + D3.a).

Run: python3 test_agent_registry.py   (NOT pytest — check()-gates print ✗ but
pytest would PASS them; this file's exit code is the signal.)

What it protects, in priority order:
  1. ⚠️ THE D3.a CLIFF — no authority-shaped field, ever. Dissolving the A2/A3
     ladder removed the vocabulary that made the cliff visible; this ABSENCE is
     what bought that safety back. It must be enforced, not documented.
  2. Every Agent's engine is real and PRICED (the ADR-439 §4 rule).
  3. An Agent is NOT a principal — attribution stays member:{id} via {model}.
  4. A lane with no agent still runs (the no-backfill path — the W0 lesson).

Spec: docs/analysis/agent-registry-spec-2026-07-16.md
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.agents_registry import (  # noqa: E402
    AGENT_ROW_KEYS,
    KERNEL_AGENTS,
    build_agent_posture,
    get_agent,
    list_agents,
    model_for_agent,
)
from services.lane_runner import LANE_MODELS  # noqa: E402

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"  {'✓' if cond else '✗'} {label}")


def run() -> bool:
    print("\n── 1. ⚠️  THE CLIFF (ADR-460 D3.a) — authority is UNREPRESENTABLE ──")
    # The whole point of D3.a: an Agent that takes consequential action is not
    # a registry row with a flag flipped. It needs the ADR-307 gate, a mandate,
    # an autonomy dial, and a track record on a clock we do not control. If a
    # future session can express authority HERE, the ladder's safety is gone
    # and nothing catches it. This is that catch.
    banned = (
        "authority", "autonomy", "consequential", "can_act", "may_act",
        "autonomous", "unattended", "standing_intent", "mandate", "wake",
        "principal", "grant", "scopes",
    )
    for agent in KERNEL_AGENTS.values():
        keys = " ".join(agent.keys()).lower()
        for word in banned:
            _check(
                f"'{agent['slug']}' has no {word}-shaped field",
                word not in keys,
            )
        break  # the row-shape check below covers all rows exhaustively
    _check(
        "the allowed row shape itself contains no authority-shaped key",
        not any(w in " ".join(AGENT_ROW_KEYS).lower() for w in banned),
    )
    _check(
        "EVERY row carries ONLY the allowed keys (a new key is a deliberate act)",
        all(set(a.keys()) == AGENT_ROW_KEYS for a in KERNEL_AGENTS.values()),
    )

    print("\n── 2. every Agent's engine is real and PRICED (ADR-439 §4) ──")
    for slug, agent in KERNEL_AGENTS.items():
        _check(
            f"'{slug}' → {agent['model']} is a LANE_MODELS key",
            agent["model"] in LANE_MODELS,
        )
    try:
        from services.model_router import ledger_model_name
        from services.telemetry import has_billing_rate
        for slug, agent in KERNEL_AGENTS.items():
            _check(
                f"'{slug}' → {agent['model']} has a billing rate (never routes unpriced)",
                has_billing_rate(ledger_model_name(agent["model"])),
            )
    except Exception as exc:  # pragma: no cover
        _check(f"billing-rate probe ran ({exc})", False)

    print("\n── 3. the base set is a TEAM, not a spec sheet ──")
    _check("three Agents (provide enough, not the most — ADR-420 §10)", len(KERNEL_AGENTS) == 3)
    # The value of a second vendor is the DISAGREEMENT — if every Agent ran on
    # one provider, "Critic" would be the same lineage arguing with itself.
    providers = {a["model"].split("/")[0] for a in KERNEL_AGENTS.values()}
    _check(
        "spanning ≥2 providers (a cross-vendor desk is the point)",
        len(providers) >= 2,
    )
    _check(
        "each Agent has a one-line blurb (the answer to 'who do I pick?')",
        all(a.get("blurb") and len(a["blurb"]) < 120 for a in KERNEL_AGENTS.values()),
    )
    _check(
        "each Agent has a posture (a character, not just a label on an engine)",
        all(len(a.get("posture", "")) > 40 for a in KERNEL_AGENTS.values()),
    )

    print("\n── 4. the chooser asks WHO, never which engine ──")
    payload = list_agents()
    _check("list_agents serves the face", all("name" in a and "blurb" in a for a in payload))
    # The picker's whole point is that the member is never ASKED to choose an
    # engine. (The engine stays legible elsewhere — the lane reports what it
    # ran on; this is about what the CHOOSER asks, not about hiding a fact.)
    _check(
        "list_agents does NOT serve `model` (the chooser never asks an engine question)",
        all("model" not in a for a in payload),
    )
    _check(
        "…nor `posture`/`token_profile` (kernel internals, not a member's choice)",
        all("posture" not in a and "token_profile" not in a for a in payload),
    )

    print("\n── 5. resolution + the no-agent path (the W0 no-backfill lesson) ──")
    _check("a known slug resolves to its engine", model_for_agent("scout") == KERNEL_AGENTS["scout"]["model"])
    _check("an unknown slug resolves to None (a caller bug, not a lane)", model_for_agent("nope") is None)
    _check("get_agent('nope') is None", get_agent("nope") is None)
    # Every pre-registry lane and every Studio/derive lane has no agent. They
    # must run byte-identically — no backfill, no guessing.
    _check(
        "no agent → empty posture (a pre-registry lane runs byte-identically)",
        build_agent_posture("") == "" and build_agent_posture("nope") == "",
    )
    _check(
        "an agent → a posture that names WHO",
        "WHO YOU ARE" in build_agent_posture("critic"),
    )

    print("\n── 6. an Agent is NOT a principal (ADR-408 D2, on the vector) ──")
    runner = (Path(__file__).parent / "services" / "lane_runner.py").read_text()
    _check(
        "attribution is still member:{id} via {model} — unchanged by the registry",
        'f"member:{user_id} via {model}"' in runner,
    )
    reg_src = (Path(__file__).parent / "services" / "agents_registry.py").read_text()
    _check(
        "the registry never touches principal_grants",
        "principal_grants" not in reg_src.replace("`principal_grants`", ""),
    )
    _check(
        "the module states the cliff for the next reader",
        "UNREPRESENTABLE" in reg_src and "ADR-460" in reg_src,
    )

    print("\n── 7. the route wiring ──")
    routes = (Path(__file__).parent / "routes" / "lanes.py").read_text()
    # Assert the INTENT (the envelope serves the chooser), not the spelling —
    # the personified-agents widening changed the call's arguments, and a gate
    # that pins an exact string fails on its own successor.
    _check("the envelope serves `agents`", '"agents": list_agents(' in routes)
    _check(
        "`models` STAYS (every model is still routable — Studio/derive bind directly)",
        '"models": [' in routes,
    )
    _check("create accepts an agent slug", "agent_slug = (req.agent or \"\").strip()" in routes)
    _check("an unknown slug is a 422", 'detail=f"Unknown agent: {agent_slug}"' in routes)
    _check(
        "the slug lands on the lane BESIDE the model (the face + the fact)",
        'lane_meta["agent"] = agent_slug' in routes,
    )
    _check(
        "the turn passes the agent through (else the posture never composes)",
        'agent=lane_meta.get("agent")' in routes,
    )
    _check(
        "the model stays authoritative on the lane (a registry edit can't rewrite history)",
        'lane_meta: dict = {"name": name, "model": model}' in routes,
    )

    print("\n── 8. ⚠️  THE CLIFF ON THE MEMBER'S SIDE (personified agents) ──")
    from services.agents_registry import (
        AGENT_MANIFEST_KEYS,
        parse_agent_manifest,
        resolve_agent,
    )

    # The widening's whole risk: if a member's file could grow any key, then
    # "unrepresentable" (D3.a) degrades to "we didn't put it in the template",
    # and ADR-382's persona-agent seat arrives through the back door as YAML.
    _check(
        "the manifest vocabulary carries no authority-shaped key",
        not any(w in " ".join(AGENT_MANIFEST_KEYS).lower() for w in banned),
    )
    for danger in ("tools", "authority", "autonomy", "mandate", "wake", "standing_intent"):
        _check(
            f"a manifest carrying `{danger}:` is REFUSED (not silently ignored)",
            parse_agent_manifest(
                f"based_on: sonnet\nname: Lisa\n{danger}: whatever\n"
            ) is None,
        )
    _check(
        "…and a clean manifest parses",
        (parse_agent_manifest("based_on: sonnet\nname: Lisa\ntone: Warm.\n") or {}).get("name")
        == "Lisa",
    )
    _check(
        "an unknown based_on is refused (a member cannot invent a capability)",
        parse_agent_manifest("based_on: nope\nname: Lisa\n") is None,
    )
    _check(
        "a manifest with no name is refused",
        parse_agent_manifest("based_on: sonnet\n") is None,
    )
    _check(
        "no based_on → refused (identity always wears a kernel capability)",
        parse_agent_manifest("name: Lisa\n") is None,
    )
    _check(
        "junk/non-dict content never breaks discovery",
        parse_agent_manifest("just some prose") is None
        and parse_agent_manifest("") is None,
    )

    print("\n── 9. the member's Agent: identity over a kernel capability ──")
    _check(
        "an Agent with no `model` inherits its based_on's engine (never asked)",
        (parse_agent_manifest("based_on: scout\nname: Lisa\n") or {})["model"]
        == KERNEL_AGENTS["scout"]["model"],
    )
    _check(
        "…and MAY override the engine (available, never asked — spec §4)",
        (parse_agent_manifest("based_on: sonnet\nname: Lisa\nmodel: openai/gpt-5\n") or {})["model"]
        == "openai/gpt-5",
    )
    lisa = {
        "slug": "lisa", "name": "Lisa", "based_on": "critic", "kernel": False,
        "tone": "Warm and direct. Calls me Kev.", "model": "openai/gpt-5",
        "blurb": KERNEL_AGENTS["critic"]["blurb"], "icon": "swords",
    }
    posture = build_agent_posture("lisa", [lisa])
    _check(
        "a member Agent's posture carries the KERNEL character (based_on)",
        "adversary" in posture,
    )
    _check(
        "…AND the member's tone, additively (never a posture swap)",
        "Calls me Kev" in posture,
    )
    _check(
        "…AND answers to the name the member gave",
        "You are called Lisa" in posture,
    )
    _check(
        "a kernel Agent's posture has no 'you are called' line (it IS its name)",
        "You are called" not in build_agent_posture("critic"),
    )
    _check(
        "member-first resolution",
        (resolve_agent("lisa", [lisa]) or {}).get("name") == "Lisa"
        and (resolve_agent("critic", [lisa]) or {}).get("slug") == "critic",
    )
    _check(
        "the chooser lists the member's Agents FIRST, tagged kernel:false",
        [a["kernel"] for a in list_agents([lisa])][0] is False,
    )
    _check(
        "…and still lists the kernel three beneath (composes BESIDE — ADR-450)",
        len(list_agents([lisa])) == len(KERNEL_AGENTS) + 1,
    )

    print("\n── 10. the write door (the UI is a door, not a database) ──")
    # NOT /api/agents — routes/agents.py already owns that namespace (the
    # ADR-251 roster: the workspace's own entities). The build caught the
    # collision; these are a different thing (the member's lane colleagues) and
    # they say so.
    _check(
        "POST /api/lane-agents exists (own namespace — /agents is the roster's)",
        '@router.post("/lane-agents")' in routes,
    )
    _check(
        "…and does NOT squat the ADR-251 roster's namespace",
        '@router.post("/agents")' not in routes
        and '@router.patch("/agents/{slug}")' not in routes,
    )
    _check(
        "it writes the manifest through the authored path (attributed, versioned)",
        "write_revision(" in routes and "_agent.yaml" in reg_src,
    )
    _check(
        "the form carries NO tools/authority field",
        not any(
            f"    {w}:" in routes.split("class CreateAgentRequest")[1].split("@router")[0]
            for w in banned
        ),
    )
    _check(
        "a member may not shadow a kernel slug",
        "is a built-in agent's name" in routes,
    )
    _check(
        "an unpriced engine override is refused at the door too (ADR-439 §4)",
        "unpriced_lane_model(model)" in routes,
    )

    print("\n── 11. ⚠️  THE CLIFF ON THE SURFACE (the hiring card) ──")
    # The ChatGPT business-agent editor — this card's benchmark for FORM — sells
    # the ADR-307 gate as a dropdown: "Write action safety: Never ask". That is
    # consequential authority, settable by anyone in one click, with no mandate,
    # no witness, no track record. Our card must contain NO authority control in
    # ANY state: not enabled, not disabled, not "upgrade to unlock". A
    # greyed-out switch invites "how do I turn this on?" and would degrade
    # D3.a's structural guarantee into a CSS property.
    card = (
        Path(__file__).parent.parent
        / "web" / "components" / "chat-surface" / "AgentCard.tsx"
    ).read_text()
    # Strip the header comment: it NAMES the anti-pattern (deliberately, so the
    # next reader knows why the control is absent). The check is on the code.
    # Strip EVERY comment, not just the header: the file legitimately discusses
    # the anti-pattern in prose ("the chooser never ASKS an engine question"
    # matched the `never ask` needle — a substring guard over-matching innocent
    # words, the known trap). Assert on CODE.
    body = re.sub(r"/\*.*?\*/|//[^\n]*", "", card, flags=re.DOTALL).lower()
    for word in ("authority", "autonomy", "consequential", "mandate", "scopes", "never ask"):
        _check(
            f"the hiring card has no `{word}` control",
            word not in body,
        )
    _check(
        "…and states what they CAN'T do as prose (a fact, not a switch)",
        "can&apos;t send" in card and "answer when you ask" in card,
    )
    _check(
        "the card's header names the anti-pattern for the next reader",
        "Never ask" in card.split("*/", 1)[0] and "D3.a" in card,
    )
    _check(
        "the capability is FIXED on edit (to change what they ARE, hire another)",
        "disabled={!!existing}" in card,
    )
    _check(
        "the avatar rides the built upload lane (no new storage)",
        "api.documents.upload" in card,
    )
    _check(
        "a kernel Agent cannot be edited (it is the capability, not a colleague)",
        "is built in — make your own agent to change it" in routes,
    )
    _check(
        "make + edit share ONE write body (Singular Implementation)",
        "_write_member_agent(req, auth, slug=None" in routes
        and "_write_member_agent(req, auth, slug=slug" in routes,
    )

    print("\n── 12. the /agents surface (the re-surface + the chat re-align) ──")
    surfaces = (Path(__file__).parent / "services" / "kernel_surfaces.py").read_text()
    agents_block = surfaces.split('"slug": "agents",', 1)[1].split("},", 1)[0]
    _check(
        "/agents is a PRIMARY launcher surface again",
        '"launcher_tier": "primary"' in agents_block,
    )
    _check(
        "…and the re-surface records WHY (not a Rung-2 re-open)",
        "DISSOLVED that ladder" in agents_block and "does NOT re-open Rung 2" in agents_block,
    )

    web = Path(__file__).parent.parent / "web"
    surface = (web / "components" / "agents" / "AgentsSurface.tsx").read_text()
    # The same cliff, on the new surface. This is where a persona-seat pane
    # would arrive by accident.
    sbody = re.sub(r"/\*.*?\*/|//[^\n]*", "", surface, flags=re.DOTALL).lower()
    for word in ("authority", "autonomy", "consequential", "mandate", "scopes", "never ask"):
        _check(f"the /agents surface has no `{word}` control", word not in sbody)
    _check(
        "…and states the limit as prose (a fact about a colleague, not a switch)",
        "can&apos;t send email" in surface,
    )
    _check(
        "ONE surface, two modes — detail is ?agent= (window state, not a route)",
        "useSurfaceParam('agents')" in surface and "setParam({ agent:" in surface,
    )
    _check(
        "discovery IS the base set (no separate browse)",
        "Who you can hire" in surface,
    )
    # The dead roster is REPLACED, not siblinged (Singular Implementation).
    # Scan the CODE, not the docstring — the docstring NAMES what it replaced,
    # deliberately, so the next reader knows why the table isn't read here.
    page = (web / "app" / "(authenticated)" / "agents" / "page.tsx").read_text()
    page_code = page.split("*/", 1)[-1]
    legacy = (web / "app" / "(authenticated)" / "agents" / "[id]" / "page.tsx").read_text()
    legacy_code = legacy.split("*/", 1)[-1]
    _check(
        "the dead roster over the EMPTY agents table is gone",
        "useAgentsAndRecurrences" not in page_code
        and "AgentContentView" not in page_code
        # …including the legacy /agents/[id] stub, whose id→slug lookup against
        # that table could only ever miss.
        and "useAgentsAndRecurrences" not in legacy_code,
    )
    _check(
        "the legacy stub still uses navigateToSurface (no ADR-308 orphaned frame)",
        "navigateToSurface('agents'" in legacy_code,
    )
    _check(
        "…and the page mounts the new surface",
        "AgentsSurface" in page,
    )

    chat = (web / "components" / "chat-surface" / "ChatSurface.tsx").read_text()
    _check(
        "the hiring door LEFT the chat picker (it lives on /agents)",
        "AgentCard" not in chat and "Make your own" not in chat,
    )
    _check(
        "the lane facet filters by WHO, not by engine (the last spec-sheet surface)",
        "whoFilter" in chat and "modelFilter" not in chat,
    )

    print("\n── 13. the face is a PICTURE; the row says WHO, then what ──")
    face = (web / "components" / "agents" / "AgentFace.tsx").read_text()
    _check(
        "the face renders an uploaded image (not a colour swatch)",
        "blobUrl" in face and "<img" in face,
    )
    _check(
        "…falling back to an initial, never a broken image",
        "onError={() => setFailed(true)}" in face,
    )
    card = (web / "components" / "chat-surface" / "AgentCard.tsx").read_text()
    _check(
        "the hiring card has NO colour picker (a face is a picture)",
        "SWATCH" not in card and "Colour" not in card,
    )
    _check(
        "…and previews the picture the member just chose",
        "URL.createObjectURL(file)" in card,
    )
    _check(
        "the capability REPORTS its engine (a nickname must say what it IS)",
        "runs on {hired.engine}" in card,
    )
    _check(
        "the registry serves role + engine + avatar_url",
        '"role":' in reg_src and '"engine": _engine_label' in reg_src
        and '"avatar_url"' in reg_src,
    )
    _check(
        "the chat row leads with the face, then name, then role · engine",
        "<AgentFace" in chat and "laneSubLabel(lane)" in chat,
    )
    _check(
        "the create form asks WHO (the faces ARE the form — no name field)",
        "Who do you want to talk to?" in chat and "newName" not in chat,
    )
    _check(
        "BOUND lanes leave the /chat list (the seam's plank 3, ruled)",
        "if not include_bound:" in routes,
    )
    _check(
        "…and Studio still sees its own",
        "api.lanes.list(true)" in (web / "components" / "studio" / "StudioSurface.tsx").read_text(),
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
