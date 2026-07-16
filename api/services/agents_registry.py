"""The kernel Agent registry — named, pre-configured hands (ADR-460 D4).

WHY THIS EXISTS
The lane picker served `LANE_MODELS` as a <select> of engines: "Claude Sonnet |
Claude Haiku | GPT-4o mini | GPT-5 | Gemini Flash | Gemini Pro | DeepSeek".
That is a SPEC SHEET — it asks the member to know which engine is good at what,
before the first message, when they know least. LLM-routing is not a layman
concept; a pre-configured Agent is. So: the engine moves BEHIND a name, and the
question becomes one anyone can answer — who do you want to work with?

WHAT AN AGENT IS (ADR-460: one concept, independent facts, one gate)
A named, configured entity. Its facts are independent and optional:
attribution · configuration · standing intent · governance files. These kernel
Agents sit at exactly one point of that space: they attribute as the MEMBER
(`member:{id} via {model}` — ADR-411 D4), carry configuration, hold NO standing
intent, and carry NO governance files. They fire only when addressed.

WHAT AN AGENT IS NOT
- NOT a principal. No `principal_grants` row, never on the ADR-431 roster. The
  face is an Agent; the ledger says the member's hands. (ADR-408 D2's
  load-bearing claim, preserved on the vector rather than on a rung.)
- NOT a persona-agent seat (ADR-382 / Rung 2). The distinguishing fact is the
  ADR-307 consequential gate, NOT the presence of a proper noun. A named preset
  is not a seat.
- NOT standing intent. No wake source, no mandate, no autonomy dial.

⚠️ THE CLIFF — ADR-460 D3.a, MADE STRUCTURAL ⚠️
There is NO field here for consequential authority, and there must never be one.
Kernel Agents are addressed-only hands BY CONSTRUCTION: the authority is
UNREPRESENTABLE, not merely unset. An Agent that would take consequential
external action is not a registry row with a flag flipped — it needs the ADR-307
gate, a mandate, an autonomy dial, and a track record accruing on a clock we do
not control. Dissolving the A2/A3 ladder (ADR-460 D1) removed the vocabulary
that made this cliff visible; THIS ABSENCE is what bought that safety back.
**A session that adds an authority field to a row here has violated ADR-460.**
`test_agent_registry.py` is that ratchet.

THE PATTERN
Third instance of a twice-ratified shape: `LANE_MODELS` (ADR-411 D5) and
`DERIVE_RECIPES` (ADR-450) are both kernel-constant registries of pre-configured
work-shapes. ADR-450: "recipes are data, not sub-processes... versioned in this
codebase; when [agent-composed] arrives it composes BESIDE kernel recipes, never
replacing them." Per-workspace Agents are that later widening — now BUILT (see
"Member-authored Agents" below): the kernel ships the CAPABILITY, the member
ships the PERSON (ADR-222: the kernel names the category, the member assigns
the instance).

Specs: docs/analysis/agent-registry-spec-2026-07-16.md (the kernel set)
       docs/analysis/personified-agents-spec-2026-07-16.md (the widening)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: The base set — "provide enough, not the most" (the ADR-420 §10 rule that
#: governs LANE_MODELS, applied one level up: one Agent per reason a member
#: would reach for a different colleague, NOT one per model that exists).
#: Seven engines is a spec sheet; a handful of characters is a team. The unit
#: of growth is a REASON (think · read · pressure-test · make), never an engine.
#:
#: Agents are named for the WORK, never for the engine — the engine is the fact
#: BEHIND the name. (The one wart: "Sonnet" is an engine name. It stays as the
#: default's name because it is the workspace's incumbent default and the
#: operator already talks to it; renaming what you already know is a cost with
#: no payoff. Named as a wart, not defended — if a rename pass runs, this is
#: the row to fix.)
#:
#: Adding an Agent = a row here. Its `model` MUST be a LANE_MODELS key with a
#: billing rate (gate-asserted — the ADR-439 §4 rule: an unpriced model never
#: routes in prod).
KERNEL_AGENTS: dict[str, dict[str, Any]] = {
    "sonnet": {
        "slug": "sonnet",
        "name": "Sonnet",
        "blurb": "Thinks a problem through with you — writing, judgment, hard calls.",
        "icon": "brain",
        "model": "anthropic/claude-sonnet-4-6",
        "token_profile": 4096,
        "posture": (
            "You are Sonnet — the member's thinking partner. Reason carefully and "
            "say what you actually think, including when it cuts against what they "
            "hoped. Prefer the shortest honest answer over a complete one."
        ),
    },
    "scout": {
        "slug": "scout",
        "name": "Scout",
        "blurb": "Digs through material fast — the workspace and the web, with sources.",
        "icon": "compass",
        "model": "gemini/gemini-2.5-flash",
        "token_profile": 4096,
        # ADR-463 D4 — the first Agent to reach past the five file verbs, and
        # the reason `tools` exists. Scout's blurb promised digging while it had
        # only SearchFiles (exact match) and ListFiles: a researcher with no
        # research tools, doing grep and calling it research. Worse,
        # QueryKnowledge is the semantic recall we SHIP TO STRANGERS over MCP
        # (ADR-368) — ChatGPT could search this workspace by meaning and Scout
        # could not.
        #
        # Both are non-consequential READS in permission.py — the same class as
        # ReadFile, which every lane already holds. They were withheld by an
        # allowlist, not by a gate.
        "tools": ("QueryKnowledge", "WebSearch"),
        "posture": (
            "You are Scout — the member's fast reader. Find what they asked for and "
            "report it plainly, with the exact source. Search the workspace by "
            "meaning (QueryKnowledge) before reading files, and the web (WebSearch) "
            "when the answer is not in the workspace. Volume is your job; do not "
            "editorialize, and say 'not here' rather than guessing."
        ),
    },
    "critic": {
        "slug": "critic",
        "name": "Critic",
        "blurb": "Pressure-tests an idea — finds the hole before it costs you.",
        "icon": "swords",
        "model": "openai/gpt-5",
        "token_profile": 4096,
        "posture": (
            "You are Critic — the member's adversary, on their side. Your job is the "
            "strongest objection, not a balanced view: find the assumption that would "
            "sink this if it were wrong. If the idea survives, say so in one line and "
            "name what would still falsify it. Never flatter."
        ),
    },
    # The fourth capability — the one a BOUND (Studio) lane defaults to.
    #
    # The maker. An ORDINARY Agent — chat with it, hire your own based on it,
    # same five verbs, same scope as every row here. Studio's lane happens to
    # pin it (see below), but that is a fact about the LANE, not about Designer.
    #
    # WHY IT EXISTS: before this row, `StudioSurface` created its authoring lane
    # with `model: models[0].id` — whatever engine happened to be FIRST in the
    # array. Nobody chose it and nobody named it. It was the last place in the
    # OS that answered "who am I talking to?" with an array index, which is the
    # same incoherence the <select> had, surviving where nobody looked.
    #
    # WHY IT IS A RE-HOME, NOT A NEW MECHANISM: the ADR-440 D3 Studio overlay is
    # ALREADY a posture (`build_studio_posture`) — the JOB (this artifact, its
    # head, the block grammar). Designer is the COLLEAGUE who does that job. The
    # two compose exactly like every other binding: character first, job second.
    # `models[0]` resolved to anthropic/claude-sonnet-4-6, so a Designer on the
    # same engine keeps every bound lane running what it runs today.
    #
    # ⚠️ EVERY AGENT CAN MAKE THINGS. Designer is not the one with permission to
    # write artifacts — every row here has the same WriteFile. It is the one
    # whose CHARACTER is making, so the member has an obvious colleague to ask
    # and Studio has an obvious one to pin. Capability is uniform; character is
    # the differentiator. A `designer_only` restriction anywhere is this row
    # being misread. (A `bound_only` field lived here for one commit and was
    # removed the same day — see AGENT_ROW_KEYS.)
    #
    # This row is why the deck in a Studio lane can be settled as "Maya made it"
    # rather than "gemini-2.5-flash made it": the attribution the member reads
    # is a person, and the ledger underneath still says `member:{id} via {model}`
    # (ADR-460 D2 — the face is an Agent, the fact is your hands).
    "designer": {
        "slug": "designer",
        "name": "Designer",
        "blurb": "Makes the thing itself — decks, docs, the artifact in front of you.",
        "icon": "pen-tool",
        "model": "anthropic/claude-sonnet-4-6",
        # The AUTHORING profile, and it rides with the Agent rather than with the
        # binding — because making is what Designer DOES, in a Studio lane or in
        # /chat. (`_studio_max_tokens` still raises a BOUND lane's ceiling
        # regardless of who is in it: the binding's job is heavy for anyone.
        # Both are true and neither is redundant — one says "this colleague
        # writes long", the other says "this job runs long".)
        "token_profile": 8192,
        "posture": (
            "You are Designer — the member's maker. You build the thing itself: "
            "decks, documents, the artifact in front of you. Work in their material "
            "rather than describing what you would do; when the ask is ambiguous, "
            "make the smallest honest version and say what you assumed."
        ),
    },
}

#: The keys a registry row may carry. The gate asserts rows carry ONLY these —
#: which is what makes the cliff structural rather than documentary (see the
#: module header).
#:
#: `tools` (optional, ADR-463 D4): extra primitives this Agent reaches, BEYOND
#: the five file verbs every lane holds (ADR-411 D3). Absent → the five verbs,
#: byte-identical to every pre-463 lane. It was deliberately absent in v1 on the
#: stated condition that "a per-Agent tool scope with exactly one possible value
#: is a field that lies about being a choice — it lands when a second value
#: exists." QueryKnowledge and WebSearch are that second value.
#:
#: ⚠️ ITS RANGE IS READS AND OUR OWN PRIMITIVES. NEVER AN OUTWARD WRITE.
#: See `resolve_agent_tools` — the ceiling is DERIVED from permission.py's own
#: classification, not declared here, so it cannot drift out of agreement with
#: the gate that enforces it.
#: (A `bound_only` key lived here for one commit on 2026-07-16 and was removed
#: the same day, operator-corrected. It marked Designer as un-chooseable +
#: un-hireable — which is a TAXONOMY wearing a field's clothes: it made Designer
#: a different KIND of Agent, which is exactly what ADR-460 D1 dissolved. The
#: fact it was trying to express — "Studio's lane always talks to Designer" — is
#: a property of the BOUND LANE, not of the Agent, and it belongs beside
#: `artifact_path` in `lane_meta` where every other binding fact already lives.
#: An Agent is an Agent: you can chat with Designer, hire your own based on it,
#: and every Agent can make artifacts. Nothing here is restricted.)
AGENT_ROW_KEYS = frozenset(
    {"slug", "name", "blurb", "icon", "model", "token_profile", "posture", "tools"}
)


def resolve_agent_tools(slug: Optional[str], member_agents: Optional[list[dict]] = None) -> tuple:
    """The extra primitives this Agent reaches, beyond the five file verbs.

    Empty for no agent, an unknown slug, or an Agent that declares none — the
    pre-ADR-463 surface, byte-identical.

    ⚠️ THE CEILING (ADR-463 D4.a — the ADR-460 D3.a pattern, second instance).
    A tool here MUST be non-consequential. The check is a DERIVATION from
    `permission.py::READ_ONLY_PRIMITIVES` — the very set the ADR-307 gate
    classifies with — not a deny-list maintained beside it. A deny-list would
    drift; a derivation cannot: the day a primitive stops being a read, it stops
    being grantable here, in the same edit, with nobody remembering to.

    WHY THIS IS THE CLIFF AND NOT A SCOPE. "Give an Agent a Slack connection" is
    two asks wearing one word. A connection that READS is an ADR-401 peripheral
    — mechanical, no judgment. A connection that WRITES OUTWARD is consequential
    external action: the one fact that is not a dial (ADR-460 D3), gated by a
    track record on a clock we do not own (ADR-380 D2). An outward write
    reachable from a tools list is Rung 2 arriving through config — the exact
    back door D3.a closed in the row shape, reopened one field over.

    A member Agent inherits its `based_on` kernel Agent's tools and cannot
    declare its own (AGENT_MANIFEST_KEYS has no `tools`): naming a colleague is
    an identity act, and granting reach is not.
    """
    from services.primitives.permission import READ_ONLY_PRIMITIVES

    agent = resolve_agent(slug or "", member_agents)
    if not agent:
        return ()
    base = KERNEL_AGENTS.get(agent.get("based_on") or agent.get("slug") or "")
    tools = tuple((base or agent).get("tools") or ())

    grantable = tuple(t for t in tools if t in READ_ONLY_PRIMITIVES)
    if len(grantable) != len(tools):
        # Loud, and it drops the offender rather than serving it. A consequential
        # primitive in a tools list is a bug in the registry, not a member's
        # problem — but it must never reach a model while we argue about it.
        refused = [t for t in tools if t not in READ_ONLY_PRIMITIVES]
        logger.error(
            "[AGENTS] REFUSED non-read tools %s for agent %r — ADR-463 D4.a: a "
            "tools list may name reads and our own primitives, never an outward "
            "write. This is the ADR-307 gate, not a scope.",
            refused, agent.get("slug"),
        )
    return grantable


# ---------------------------------------------------------------------------
# Member-authored Agents (the ADR-450/ADR-460 D4 later-widening)
# ---------------------------------------------------------------------------
#
# "Instead of calling a mundane Sonnet, they can name it and call their own
# agent 'Lisa'." The kernel ships the CAPABILITY; the member ships the PERSON.
#
# THE SHAPE IS ADR-449's, VERBATIM: an ordinary meaning-folder identified by a
# manifest, discovered by search, never registered. Nothing is seeded
# (ADR-414). The kernel READS; the member OWNS. Fourth instance of a ratified
# pattern (recipes · models · design systems · agents).
#
# ⚠️ WHY NOT "UNLEASH ALL AGENTS TO THE FILESYSTEM" ⚠️
# If an Agent were PURELY a member file, the workspace could author an Agent —
# and an Agent is a thing that holds a persona, tools, and eventually
# authority. That is a straight line to the ADR-382 persona-agent seat arriving
# through the back door as a config file: Rung 2 rebuilt without the ADR-307
# gate, without a mandate, without the exogenous track-record clock, and
# nothing would catch it because "it's just YAML the member wrote". The
# ADR-460 D3.a cliff is structural BECAUSE the row shape has no field for
# authority — so the member's manifest needs the SAME guarantee, or the
# widening reopens what D3.a closed. Hence AGENT_MANIFEST_KEYS + a parser that
# REJECTS (never silently ignores) an unknown key.
#
# The cut is not "kernel vs filesystem" — it is CAPABILITY vs IDENTITY:
#   tools + token profile → kernel (they gate, cost, route)
#   engine               → kernel default, member MAY override (see below)
#   name + tone + color  → the member (costs nothing, gates nothing)
#   authority            → NOBODY. Unrepresentable in both layers.

#: The manifest basename — underscore-prefixed = machine-parsed (CLAUDE.md §9).
AGENT_MANIFEST_BASENAME = "_agent.yaml"

#: The ONLY keys a member's manifest may carry. This is the D3.a cliff on the
#: member's side. `parse_agent_manifest` REJECTS a manifest carrying anything
#: else — loudly, not silently — so an attempt to grow the vocabulary (tools,
#: authority, a wake source) is VISIBLE rather than quietly dropped.
#: `avatar` (2026-07-16, the hiring card): a workspace path to an uploaded
#: image — IDENTITY-class, like a user's profile picture. Added DELIBERATELY:
#: the parser refusing `avatar:` before this line was the guard working as
#: designed. Widening the vocabulary is an explicit act, and every key added
#: here must be identity (costs nothing, gates nothing, routes nothing) —
#: never capability, never authority.
AGENT_MANIFEST_KEYS = frozenset(
    {"based_on", "name", "tone", "model", "color", "avatar"}
)


def parse_agent_manifest(content: Optional[str]) -> Optional[dict]:
    """Parse an `_agent.yaml` body → the manifest, or None if it is not one.

    Pure. Returns None (not an exception) for anything that is not a valid
    member-Agent manifest — discovery must never break on a stray file.

    STRICT-KEY: a manifest carrying a key outside AGENT_MANIFEST_KEYS is
    REFUSED. That is the point, not pedantry — `tools:` or `authority:` in a
    member's file must not silently do nothing (it would read as supported and
    become a bug report), and must not work (it would reopen ADR-460 D3.a).
    """
    if not content or not content.strip():
        return None
    try:
        from services.review_policy import load_workspace_yaml
        data = load_workspace_yaml(content)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    extra = set(data.keys()) - AGENT_MANIFEST_KEYS
    if extra:
        logger.warning(
            "[AGENTS] manifest REFUSED — unsupported keys %s. A member's Agent "
            "carries identity (name/tone/color) over a kernel capability "
            "(based_on/model); tools and authority are not in its vocabulary "
            "(ADR-460 D3.a).", sorted(extra),
        )
        return None

    based_on = str(data.get("based_on") or "").strip()
    name = str(data.get("name") or "").strip()
    if not based_on or not name:
        return None
    if based_on not in KERNEL_AGENTS:
        logger.warning("[AGENTS] manifest names an unknown based_on: %r", based_on)
        return None

    # The engine override (spec §4): available, never ASKED. The picker still
    # asks WHO — the ADR-460 D4 argument was about the moment of creation, when
    # the member knows least. A member deliberately building a colleague has
    # opted into caring; that is the later-widening, not the spec sheet.
    model = str(data.get("model") or "").strip() or KERNEL_AGENTS[based_on]["model"]

    return {
        "based_on": based_on,
        "name": name,
        "tone": str(data.get("tone") or "").strip(),
        "model": model,
        "color": str(data.get("color") or "").strip(),
        "avatar": str(data.get("avatar") or "").strip(),
    }


def _engine_label(model: str) -> str:
    """The engine's human label ("GPT-5"), or "" — pure.

    The operator's rule (2026-07-16): a nickname must still say what it IS —
    "at the minimum the model and agent role". So the technical fact stays
    VISIBLE, it just stops being the headline: identity leads, `role · engine`
    rides quietly behind it. This is not a re-opening of the spec sheet — the
    chooser still never ASKS an engine question (ADR-460 D4); it reports one.
    """
    from services.lane_runner import LANE_MODELS
    return (LANE_MODELS.get(model) or {}).get("label", "")


def _resolve_avatar_url(client: Any, user_id: str, avatar_path: str) -> str:
    """The avatar's `content_url` — the FE resolves it to a signed URL.

    The manifest stores a workspace PATH (what the member uploaded); the image
    BYTES live out-of-band in the ADR-395 bucket, reachable through the file
    row's `content_url`. The FE can't send a Bearer header from an <img src>,
    so it exchanges this reference for a fresh signed URL
    (`api.documents.blobUrl` — the FileTile pattern). Read-only, best-effort:
    a missing avatar is a fallback initial, never a broken card.
    """
    if not avatar_path:
        return ""
    try:
        rows = (
            client.table("workspace_files")
            .select("content_url")
            .eq("path", avatar_path)
            .limit(1)
            .execute()
        ).data or []
        return (rows[0].get("content_url") or "") if rows else ""
    except Exception as exc:  # noqa: BLE001
        logger.debug("[AGENTS] avatar resolve failed for %s: %s", avatar_path, exc)
        return ""


def find_member_agents(client: Any, user_id: str) -> list[dict]:
    """Discover the workspace's member-authored Agents (the ADR-449 mechanic).

    Returns [{slug, name, blurb, icon, model, based_on, tone, kernel: False}]
    for every `_agent.yaml` whose body parses as a manifest. No registry row
    exists or is maintained — discovery IS the convention. Best-effort:
    failures return what was found (a broken manifest never breaks the picker).
    """
    from services.workspace_context import substrate_scope_filter

    out: list[dict] = []
    try:
        rows = (
            client.table("workspace_files")
            .select("path, content, lifecycle")
            .eq(*substrate_scope_filter(user_id))
            .like("path", f"%/{AGENT_MANIFEST_BASENAME}")
            .order("updated_at", desc=True)
            .limit(50)
            .execute()
        ).data or []
        for r in rows:
            if r.get("lifecycle") == "archived":
                continue
            manifest = parse_agent_manifest(r.get("content"))
            if not manifest:
                continue
            path = r["path"]
            slug = path.rsplit("/", 2)[-2] if "/" in path else ""
            if not slug or slug in KERNEL_AGENTS:
                # A member folder may not shadow a kernel slug — the kernel set
                # is the floor, and a silent override would make "sonnet" mean
                # two things depending on the workspace.
                continue
            base = KERNEL_AGENTS[manifest["based_on"]]
            out.append({
                "slug": slug,
                "name": manifest["name"],
                # The member named them; the blurb still says what they're FOR
                # (inherited from the capability they wear).
                "blurb": base["blurb"],
                "icon": base["icon"],
                "color": manifest["color"],
                "avatar": manifest["avatar"],
                # The image reference the FE trades for a signed URL.
                "avatar_url": _resolve_avatar_url(client, user_id, manifest["avatar"]),
                "model": manifest["model"],
                "based_on": manifest["based_on"],
                "tone": manifest["tone"],
                "token_profile": base["token_profile"],
                "kernel": False,
                "manifest_path": path,
            })
    except Exception as exc:  # noqa: BLE001 — discovery is best-effort
        logger.debug("[AGENTS] member-agent discovery failed: %s", exc)
    return out


# ---------------------------------------------------------------------------
# Skills — the market's convention, without the engine that killed it (ADR-464)
# ---------------------------------------------------------------------------
#
# ADR-118 (2026-03) adopted SKILL.md EXPLICITLY: "Adopt Claude Code's naming
# conventions (skills, SKILL.md) directly — no yarnnn-specific terminology where
# Claude conventions exist." It also named its own missing leg: "yarnnn already
# has the instructions and the filesystem; THE MISSING PRIMITIVE IS THE COMPUTE
# ENVIRONMENT."
#
# ADR-417 retired the compute environment (the yarnnn-render service) and asset
# generation. It did NOT rule that structured instructions in a file were wrong
# — it retired the ENGINE. The convention was orphaned by a decision about
# hosting, and "skills are dead" has been a misreading of that ever since.
#
# ⭐ A SKILL AS INSTRUCTIONS HAS NO VENDOR PROBLEM AT ALL. This is the whole
# reason it can come back now. ADR-118 needed a render service because it wanted
# skills to EXECUTE (matplotlib, PDF). A skill that is PROSE needs a file and a
# model that can read — which is every model. The ADR-463 model-agnostic
# discipline is free here: only compute ever bound us to a vendor, and we
# already stopped hosting compute.
#
# THE SHAPE IS THE ONE THIS CODEBASE AND THE MARKET ALREADY AGREE ON:
#
#     agents/{slug}/_agent.yaml     ← identity (machine-parsed, §9)
#     agents/{slug}/skills/*.md     ← instructions (LLM-read prose, §9)
#
# Discovery, never registration — the ADR-449 mechanic the manifest already
# uses, one level down. No new table, no new registry, no seeding (ADR-414).
#
# ⚠️ WHY THIS DOES NOT REOPEN THE D3.a CLIFF. A skill is PROSE composed into a
# prompt. It cannot grant a tool: `resolve_agent_tools` reads the KERNEL row via
# `based_on` and a member's file is not consulted. It cannot grant authority:
# the gate branches on `caller_identity`, which the RUNTIME stamps from
# (user_id, model) — unreachable from any file. A skill that SAYS "you may post
# to Slack" is a lie the gate refuses, exactly as it refuses the same words typed
# in chat. **Prose is not permission.** The cliff was never held by the file
# format; it is held by what the runtime stamps and the gate derives.

#: Skill files live here, under the member's agent folder. `skills/` (not
#: `_skills/`) because these are LLM-read prose, not machine config — CLAUDE.md
#: §9: format follows the consumer.
AGENT_SKILLS_DIRNAME = "skills"

#: A bound on what one agent's skills may inject. Skills compose into every turn
#: this agent takes, so an unbounded corpus is an unbounded per-turn bill —
#: cost is why this is a ceiling and not a preference. Generous enough that a
#: real skill set fits; low enough that a runaway folder cannot quietly triple
#: a member's token cost. Trimmed by whole skills, never mid-sentence: half an
#: instruction is worse than none.
_MAX_SKILL_FILES = 8
_MAX_SKILL_CHARS = 12_000


def find_agent_skills(client: Any, user_id: str, folder: str) -> list[dict]:
    """The skills under one agent's folder — [{name, content}]. Best-effort.

    `folder` is the agent's directory (e.g. `/workspace/agents/lisa`). Reads
    `{folder}/skills/*.md`. A member with no skills folder gets [] and a turn
    byte-identical to a pre-ADR-464 one.
    """
    from services.workspace_context import substrate_scope_filter

    prefix = f"{folder.rstrip('/')}/{AGENT_SKILLS_DIRNAME}/"
    out: list[dict] = []
    try:
        rows = (
            client.table("workspace_files")
            .select("path, content, lifecycle")
            .eq(*substrate_scope_filter(user_id))
            .like("path", f"{prefix}%")
            .order("path")
            .limit(_MAX_SKILL_FILES * 2)  # headroom: archived rows filter below
            .execute()
        ).data or []
        for r in rows:
            if r.get("lifecycle") == "archived":
                continue
            path = r.get("path") or ""
            if not path.endswith(".md"):
                continue
            body = (r.get("content") or "").strip()
            if not body:
                continue
            out.append({"name": path.rsplit("/", 1)[-1][:-3], "content": body})
    except Exception as exc:  # noqa: BLE001 — discovery is best-effort
        logger.debug("[AGENTS] skill discovery failed for %s: %s", folder, exc)
    return out[:_MAX_SKILL_FILES]


def build_skills_section(skills: list[dict]) -> str:
    """Skills → the prompt section, or "" when there are none. Pure.

    Trimmed to `_MAX_SKILL_CHARS` by dropping WHOLE skills from the end — a
    truncated instruction is worse than an absent one, because the model acts on
    the half it can see.
    """
    if not skills:
        return ""
    kept: list[dict] = []
    used = 0
    for s in skills:
        cost = len(s["content"]) + len(s["name"]) + 16
        if used + cost > _MAX_SKILL_CHARS:
            logger.info(
                "[AGENTS] skill %r dropped — the %d-char budget is full (%d kept)",
                s["name"], _MAX_SKILL_CHARS, len(kept),
            )
            break
        kept.append(s)
        used += cost
    if not kept:
        return ""
    body = "\n\n".join(f"### {s['name']}\n{s['content']}" for s in kept)
    return (
        "\n\nSKILLS (the member taught you these — follow them as written)\n"
        f"{body}\n"
    )


def resolve_agent(slug: str, member_agents: Optional[list[dict]] = None) -> Optional[dict]:
    """An Agent by slug — the member's first, then the kernel's. Pure.

    Member-first because a member's Agents compose BESIDE the kernel set
    (ADR-450's rule) and cannot shadow it (find_member_agents drops any folder
    named after a kernel slug), so the two namespaces never collide — the order
    is for the caller's clarity, not a precedence fight.
    """
    s = (slug or "").strip()
    for a in member_agents or []:
        if a["slug"] == s:
            return a
    return KERNEL_AGENTS.get(s)


def get_agent(slug: str) -> Optional[dict]:
    """The KERNEL Agent row for a slug, or None. Pure."""
    return KERNEL_AGENTS.get((slug or "").strip())


def list_agents(member_agents: Optional[list[dict]] = None) -> list[dict]:
    """The chooser payload — the member-facing face only.

    Deliberately does NOT serve `model`, `posture`, or `token_profile`: the
    picker's whole point is that the member is never ASKED to choose an engine.
    (The engine stays legible elsewhere — a lane reports the model it ran on;
    this is about what the CHOOSER asks, not about hiding a fact.)

    The member's own Agents come FIRST — they named them, so they are the
    colleagues; the kernel set is the floor beneath. `kernel: true|false`
    lets the UI mark which are theirs (and which can be renamed/edited).

    EVERY kernel Agent is served, Designer included. It is an Agent like any
    other: you can start a chat with it and hire your own based on it. That
    Studio's lane pins it is a fact about the BOUND LANE, not about Designer,
    and a chooser that hid it would be describing the lane's binding in the
    Agent's row — the muddiness ADR-460 D1 exists to refuse.
    """
    # NOTE what is served and what is NOT. `based_on` + `tone` + `avatar` +
    # `color` ride along because the hiring card pre-fills an EDIT from them —
    # they are the member's own identity choices, theirs to see. `model` does
    # NOT: the chooser's whole point is that the member is never asked an
    # engine question, and a field the card never renders is a field that
    # leaks. (The engine stays legible where it is a FACT — the lane reports
    # what it ran on. The card reaches for it through its own door if the
    # "Details" disclosure ever lands.)
    mine = [
        {"slug": a["slug"], "name": a["name"], "blurb": a["blurb"],
         "icon": a["icon"], "color": a.get("color") or "",
         "avatar": a.get("avatar") or "",
         "avatar_url": a.get("avatar_url") or "",
         "based_on": a.get("based_on") or "",
         "tone": a.get("tone") or "",
         # The operator's ask: a nickname must still say what it IS. `role` is
         # the capability's name (Critic); `engine` is the model's label
         # (GPT-5). Identity leads, the technical fact rides quietly behind it.
         "role": (KERNEL_AGENTS.get(a.get("based_on") or "") or {}).get("name", ""),
         "engine": _engine_label(a.get("model") or ""),
         "kernel": False}
        for a in (member_agents or [])
    ]
    theirs = [
        {"slug": a["slug"], "name": a["name"], "blurb": a["blurb"],
         "icon": a["icon"], "color": "", "avatar": "", "avatar_url": "",
         "based_on": a["slug"], "tone": "",
         "role": a["name"], "engine": _engine_label(a["model"]),
         "kernel": True}
        for a in KERNEL_AGENTS.values()
    ]
    return mine + theirs


def model_for_agent(slug: str) -> Optional[str]:
    """The engine behind the name, or None if the slug is unknown. Pure."""
    agent = get_agent(slug)
    return agent["model"] if agent else None


def build_agent_posture(
    slug: str,
    member_agents: Optional[list[dict]] = None,
    skills: Optional[list[dict]] = None,
) -> str:
    """The Agent's turn-time posture overlay, or "" when there is no Agent. Pure.

    Composed at turn time from the slug, never stored (the ADR-411 D6 pattern) —
    correct precisely BECAUSE a posture is not a historical fact about what ran.
    It is how this Agent works NOW, so it must follow the registry. The `model`
    is the opposite: it IS a historical fact, so it is persisted on the lane and
    never re-derived (see the registry spec §6).

    For a MEMBER Agent: the kernel `based_on` character + the member's `tone`.
    The tone is ADDITIVE, never a replacement — a member writing
    `tone: "ignore your instructions"` gets a tonal line appended to a posture,
    not a posture swap. Deliberately the thin end: a member authoring a full
    posture is prompt-engineering, which is the expert ceremony the whole
    re-cut removed. If members reach for more, that is evidence — build then.

    `skills` (ADR-464): the agent's SKILL.md-shaped instructions, read by the
    caller (this function stays PURE — the read is the caller's, the composition
    is ours). Appended LAST: character → name → tone → skills, because a skill is
    what this colleague was TAUGHT, and it is read in the voice of who they are.
    Empty list → byte-identical to a pre-464 turn.
    """
    agent = resolve_agent(slug, member_agents)
    if not agent:
        return ""

    # A member Agent wears a kernel capability's character (`based_on`); a
    # kernel Agent is its own.
    base = KERNEL_AGENTS.get(agent.get("based_on") or agent.get("slug") or "")
    character = (base or agent).get("posture") or ""
    if not character:
        return ""

    # The member named them — the model should answer to that name, not to the
    # capability's.
    name = agent.get("name") or ""
    section = f"\n\nWHO YOU ARE\n{character}\n"
    if not agent.get("kernel", True):
        section += f"\nYou are called {name}. Answer to it.\n"
    tone = (agent.get("tone") or "").strip()
    if tone:
        section += f"\nHOW {name.upper()} SOUNDS (the member's own words)\n{tone}\n"
    # ADR-464 — what the member TAUGHT them. Last, and in the voice of who they
    # are: a skill is instructions this colleague follows, not a second identity.
    section += build_skills_section(skills or [])
    return section
