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
    _check("the envelope serves `agents`", '"agents": list_agents()' in routes)
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

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
