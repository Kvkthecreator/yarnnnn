"""The door to standing work — ADR-658 D4 → ADR-667 D2: one composer, two callers.

A member makes a piece of standing work in one of two ways: the routes
(`POST`/`PATCH /api/standing`) or a conversation, where the agent calls the
lane tool `DeclareWork` (`services/primitives/declare_work.py`). Both come
through here, so there is ONE composer of `_standing.yaml`, ONE order of
refusals and ONE place the browser's member is stamped:

    declare(auth, …)   — a new declaration: CONTRACT.md + _standing.yaml
    revise(auth, …)    — pause / resume, and the composer's own fields

⭐ THE STAMP (ADR-666 D1, ADR-667 D2). Browser work runs in the ACTING member's
browser. No caller names a member: `browser_sites` present means "in mine",
and the member is `auth.user_id` — the signed-in member at the route, the
member whose turn it is in a conversation. A different member may pause it,
never re-aim it (`browser_not_yours`).

Refusals are BY NAME (`DoorRefusal.problem`), worded once in `REFUSAL_WORDS`:
the route serves `{problem, message}`, the tool hands the model the message.

Auth boundary (ADR-501): everything scopes to the ACTING WORKSPACE'S OWNER
via `acting_owner`. Authority (ADR-658 D2): nothing here takes or stores an
agent slug — the executor is derived from the target's app at read time.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import yaml as _yaml

_MAX_TOPIC_DEPTH = 6
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,62}$")

#: Every refusal the door makes, in the member's words. The problem token is
#: the parser's own where one exists (`services.standing_work`), so the door
#: says which rule refused rather than "invalid".
REFUSAL_WORDS: dict[str, str] = {
    "invalid_topic": "A folder is one to six plain names, and never under system/.",
    "missing_target": "Name the file to keep current.",
    "invalid_target": "The file to keep current must be in this folder, one plain name.",
    "unsupported_format": "Only md, csv, json and txt files can be kept current.",
    "sources_invalid": (
        "Add at least one source. A csv, json or txt file takes exactly one, "
        "and a file rather than a folder."
    ),
    "source_cycle": (
        "That would make a loop: this file would be kept from a file that is "
        "kept from it. Choose a different source."
    ),
    "source_unreadable": "You can't read that part of the workspace, so it can't be a source.",
    "app_invalid": "That app does not exist.",
    "missing_contract": "Write what the file must stay true to.",
    "already_declared": "This folder already has standing work. Open it instead.",
    "not_declared": "There is no standing work in that folder.",
    "unparseable": "The declaration in that folder cannot be read. Retire it and set it up again.",
    "browser_invalid": "Name at least one website, as a plain address like example.com.",
    "browser_member_unknown": "This work names a browser that is not a member of this workspace.",
    "browser_not_yours": "This work runs in another member's browser — they start it, and they change its sites.",
    "browser_needs_page": (
        "This work runs in your browser: open yarnnn in Chrome with the yarnnn "
        "extension on, then run it."
    ),
    "forbidden": "You can't write standing work there.",
}


class DoorRefusal(Exception):
    """A refusal by name. `status_code` is what the route answers with."""

    def __init__(self, problem: str, status_code: int = 422, reason: Optional[str] = None):
        self.problem = problem
        self.status_code = status_code
        self.message = reason or REFUSAL_WORDS.get(problem, problem)
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Paths and reads
# ---------------------------------------------------------------------------


def validate_topic(topic: str) -> str:
    """A topic is its folder path relative to /workspace/ — path hygiene (no
    traversal, no machinery segments), not a naming law. Returns normalized."""
    t = (topic or "").strip().strip("/")
    if t.startswith("workspace/"):
        t = t[len("workspace/"):]
    segments = t.split("/") if t else []
    if (
        not segments
        or len(segments) > _MAX_TOPIC_DEPTH
        or any(not _SEGMENT_RE.match(s) or s in (".", "..") for s in segments)
        # The kernel mirror is never a member's meaning-folder (the skill's
        # own anti-pattern: "declaring a file that lives under system/").
        or segments[0] == "system"
    ):
        raise DoorRefusal("invalid_topic")
    return "/".join(segments)


def decl_path(topic: str) -> str:
    from services.standing_work import DECLARATION_LEAF

    return f"/workspace/{topic}/{DECLARATION_LEAF}"


def contract_path(topic: str) -> str:
    from services.standing_work import CONTRACT_LEAF

    return f"/workspace/{topic}/{CONTRACT_LEAF}"


def acting_workspace(auth) -> Optional[str]:
    from services.workspace_context import effective_workspace_id
    return effective_workspace_id(auth.user_id, getattr(auth, "workspace_id", None))


def acting_owner(auth) -> str:
    from services.workspace_context import acting_workspace_owner
    return acting_workspace_owner(auth.client, auth.user_id, getattr(auth, "workspace_id", None))


def read_declaration(client, user_id: str, topic: str) -> Optional[str]:
    """The LIVE declaration's body, or None. Not-in-Trash by construction —
    the same predicate discovery owes (2026-09-07): a retired declaration
    must read as absent here, or Run now would fire what the roster hides."""
    from services.workspace_context import live_files_filter

    rows = (
        live_files_filter(
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", decl_path(topic))
        )
        .limit(1)
        .execute()
    ).data or []
    return rows[0].get("content") if rows else None


def parse(content: str, topic: str, user_id: str):
    """The ONE parser, over one declaration's body. None when not YAML."""
    from services.standing_work import parse_standing_yaml
    from services.workspace_context import effective_workspace_id
    return parse_standing_yaml(
        content, topic=topic, declaration_path=decl_path(topic), user_id=user_id,
        workspace_id=effective_workspace_id(user_id),
    )


def _strip_frontmatter(content: str) -> str:
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    return content[m.end():] if m else content


# ---------------------------------------------------------------------------
# The rules only a door can ask
# ---------------------------------------------------------------------------


def guard_sources(auth, user_id: str, decl) -> None:
    """The two source rules only the DOOR can ask (ADR-659 D4 rule 6, D5).

    `source_unreadable` — a run reads with the OWNER's reach, so a source the
    DECLARER cannot read would launder it into a file they can. Asked of the
    ONE matcher the ReadFile gate uses.

    `source_cycle` — a loop is a property of the workspace's declarations
    TOGETHER, which the one-file parse cannot see: the candidate is set among
    the live ones and the same marker discovery uses decides.
    """
    from services.primitives.workspace import _is_path_readable_for_principal
    from services.standing_work import discover_standing, mark_source_cycles

    for rel, is_folder in decl.path_sources():
        if not _is_path_readable_for_principal(auth, rel + ("/" if is_folder else "")):
            raise DoorRefusal("source_unreadable")

    if not decl.path_sources():
        return
    others = [
        d for d in discover_standing(auth.client, workspace_id=decl.workspace_id).get(user_id, [])
        if d.slug != decl.slug
    ]
    mark_source_cycles(others + [decl])
    if decl.problem is not None:
        raise DoorRefusal(decl.problem)


def write_access(auth, path: str) -> None:
    """ADR-643 D2 — a declaration schedules UNATTENDED spend (ADR-618), which
    makes it one of the sharper writes in the substrate; the door asks the
    ONE decider before composing."""
    from services.access import resolve_access

    decision = resolve_access(auth, path, "write")
    if not decision.allowed:
        raise DoorRefusal("forbidden", status_code=403, reason=decision.reason)


async def materialize(client, user_id: str) -> None:
    """Immediate index sync post-write — a switched declaration re-arms now,
    not at the next global discovery; a retired one drops its row now."""
    from services.standing_work import discover_standing, materialize_standing_index
    from services.workspace_context import effective_workspace_id
    decls = discover_standing(client, workspace_id=effective_workspace_id(user_id)).get(user_id, [])
    await materialize_standing_index(client, user_id, decls)


# ---------------------------------------------------------------------------
# The one composer
# ---------------------------------------------------------------------------


def compose_standing_yaml(
    *,
    target: str,
    schedule: Any,
    paused: bool,
    sources: list[dict],
    app: Optional[str] = None,
    shape: Optional[dict] = None,
    fire_on_activation: bool = False,
    browser: Optional[dict] = None,
) -> str:
    """Compose the ``_standing.yaml`` body — PURE machine config (ADR-569 D2:
    judgment prose lives in CONTRACT.md, which no machine writer touches).
    Deterministic, machine-class (ADR-254): comment header + safe_dump.

    THE ONE COMPOSER (ADR-658 D4, ADR-667 D2). The routes and `DeclareWork`
    both emit through here; a second formatter is the drift `DECLARATION_KEYS`
    was created to end."""
    payload: dict[str, Any] = {"target": target}
    if app:
        payload["app"] = app
    payload["schedule"] = schedule
    if browser:
        payload["browser"] = {"member": browser.get("member"),
                              "sites": list(browser.get("sites") or [])}
    if fire_on_activation:
        payload["fire_on_activation"] = True
    payload["paused"] = paused
    payload["sources"] = sources
    if shape:
        payload["shape"] = shape
    header = (
        "# _standing.yaml — standing declaration (ADR-666: browser work)\n"
        "# Run in the member's own browser, on these sites only. When it comes\n"
        "# due it waits for that member to run it. Machine config only — what\n"
        "# must be true when it finishes belongs in CONTRACT.md, not here.\n"
    ) if browser else (
        "# _standing.yaml — standing declaration (ADR-639: the kept file)\n"
        "# On its schedule the sources are fetched and the designated target\n"
        "# is revised under CONTRACT.md. Machine config only — what the file\n"
        "# must stay true to belongs in CONTRACT.md, not here.\n"
    )
    return header + _yaml.safe_dump(payload, sort_keys=False, allow_unicode=True,
                                    default_flow_style=False)


def _identity(auth, authored_by: str) -> Optional[str]:
    """The human a revision is stamped with (ADR-410): the member themself,
    whether they clicked or their agent wrote in their turn."""
    return auth.user_id if (authored_by == "operator" or authored_by.startswith("member:")) else None


# ---------------------------------------------------------------------------
# declare · revise
# ---------------------------------------------------------------------------


async def declare(
    auth,
    *,
    folder: str,
    target: str,
    schedule: Any,
    contract: str,
    app: Optional[str] = None,
    sources: Optional[list[dict]] = None,
    shape: Optional[dict] = None,
    browser_sites: Optional[list[str]] = None,
    authored_by: str = "operator",
):
    """A new declaration. Order: the folder is validated; a blank contract is
    refused (the contract is the load-bearing half — without it no run can be
    judged); a folder that already holds a LIVE declaration is refused (one
    per folder, ADR-569 D2); the composed YAML is parsed and any problem
    refuses the write; the source rules and access are asked; then
    CONTRACT.md and _standing.yaml land as `lifecycle='active'` revisions (a
    retired declaration at this path is REVIVED, never left in Trash —
    ADR-658 A1.6); the index is synced so the roster shows it now.

    Returns the parsed declaration."""
    actor = acting_owner(auth)
    topic = validate_topic(folder)
    contract = (contract or "").strip()
    if not contract:
        raise DoorRefusal("missing_contract")
    if read_declaration(auth.client, actor, topic) is not None:
        raise DoorRefusal("already_declared", status_code=409)

    browser = (
        {"member": auth.user_id, "sites": list(browser_sites)}
        if browser_sites is not None else None
    )
    content = compose_standing_yaml(
        target=(target or "").strip(),
        app=(str(app).strip() if app else None) or None,
        schedule=schedule,
        paused=False,
        sources=[s for s in (sources or []) if isinstance(s, dict)],
        shape=shape if isinstance(shape, dict) and shape else None,
        # The first run fires on the next tick, not at the first cron boundary
        # (ADR-658 D7): the member sees the file change within minutes. Browser
        # work is never fired by a tick — its member runs it (ADR-666 D4).
        fire_on_activation=browser is None,
        browser=browser,
    )
    decl = parse(content, topic, actor)
    if decl is None:  # cannot happen for content we just composed — fail loud
        raise RuntimeError("composed declaration unparseable")
    if decl.problem is not None:
        raise DoorRefusal(decl.problem)
    guard_sources(auth, actor, decl)
    write_access(auth, decl_path(topic))

    from services.authored_substrate import write_revision
    ws = getattr(auth, "workspace_id", None)
    identity = _identity(auth, authored_by)
    write_revision(
        auth.client, user_id=actor, path=contract_path(topic), content=contract + "\n",
        authored_by=authored_by, author_identity_uuid=identity,
        message=f"declare standing work in '{topic}': the instructions",
        workspace_id=ws, lifecycle="active",
    )
    write_revision(
        auth.client, user_id=actor, path=decl_path(topic), content=content,
        authored_by=authored_by, author_identity_uuid=identity,
        message=(f"declare browser work in '{topic}': keep '{decl.target}' true"
                 if browser else
                 f"declare standing work in '{topic}': keep '{decl.target}' current"),
        workspace_id=ws, lifecycle="active",
    )
    await materialize(auth.client, actor)
    return decl


async def revise(
    auth,
    topic: str,
    *,
    paused: Optional[bool] = None,
    schedule: Any = None,
    sources: Optional[list[dict]] = None,
    shape: Optional[dict] = None,
    target: Optional[str] = None,
    browser_sites: Optional[list[str]] = None,
    contract: Optional[str] = None,
    authored_by: str = "operator",
):
    """Pause / Resume, the composer's own fields (ADR-658 D6), and — from a
    conversation — the instructions (`contract` rewrites CONTRACT.md). A change
    that would leave the declaration unable to run is refused BY NAME and
    writes nothing; the pause switch alone is never refused. Returns the
    parsed declaration."""
    actor = acting_owner(auth)
    topic = validate_topic(topic)
    content = read_declaration(auth.client, actor, topic)
    if content is None:
        raise DoorRefusal("not_declared", status_code=404)
    try:
        parsed = _yaml.safe_load(_strip_frontmatter(content)) or {}
    except _yaml.YAMLError:
        raise DoorRefusal("unparseable")
    if not isinstance(parsed, dict):
        raise DoorRefusal("unparseable")

    if paused is not None:
        parsed["paused"] = paused
    edited = False
    if schedule is not None:
        parsed["schedule"] = schedule
        edited = True
    if sources is not None:
        parsed["sources"] = [s for s in sources if isinstance(s, dict)]
        edited = True
    if shape is not None:
        parsed["shape"] = shape if shape else None
        edited = True
    if target is not None:
        parsed["target"] = str(target).strip()
        edited = True
    if browser_sites is not None:
        if not isinstance(parsed.get("browser"), dict):
            raise DoorRefusal("browser_invalid")
        # Its member re-aims it; nobody else points another's browser anywhere.
        if str(parsed["browser"].get("member") or "").lower() != str(auth.user_id).lower():
            raise DoorRefusal("browser_not_yours", status_code=403)
        parsed["browser"] = {**parsed["browser"], "sites": list(browser_sites)}
        edited = True

    # fire_on_activation is consume-on-first-update (the radar lesson: a
    # re-emitted create-time flag kept a never-run declaration permanently
    # armed through every pause/resume).
    new_content = compose_standing_yaml(
        target=str(parsed.get("target") or ""),
        app=(str(parsed.get("app")).strip() if parsed.get("app") else None),
        schedule=parsed.get("schedule"),
        paused=bool(parsed.get("paused", False)),
        sources=[s for s in (parsed.get("sources") or []) if isinstance(s, dict)],
        shape=parsed.get("shape") if isinstance(parsed.get("shape"), dict) else None,
        browser=parsed.get("browser") if isinstance(parsed.get("browser"), dict) else None,
    )
    decl = parse(new_content, topic, actor)
    if decl is None:  # cannot happen for content we just composed — fail loud
        raise RuntimeError("recomposed declaration unparseable")
    if edited and decl.problem is not None:
        raise DoorRefusal(decl.problem)
    if edited:
        guard_sources(auth, actor, decl)
    write_access(auth, decl_path(topic))

    from services.authored_substrate import write_revision
    if edited:
        message = f"edit standing work in '{topic}'"
    else:
        message = f"{'pause' if parsed.get('paused') else 'resume'} standing work in '{topic}'"
    ws = getattr(auth, "workspace_id", None)
    identity = _identity(auth, authored_by)
    if contract is not None and contract.strip():
        write_access(auth, contract_path(topic))
        write_revision(
            auth.client, user_id=actor, path=contract_path(topic), content=contract.strip() + "\n",
            authored_by=authored_by, author_identity_uuid=identity,
            message=f"revise the instructions of standing work in '{topic}'", workspace_id=ws,
        )
    write_revision(
        auth.client, user_id=actor, path=decl_path(topic), content=new_content,
        authored_by=authored_by, author_identity_uuid=identity,
        message=message, workspace_id=ws,
    )
    await materialize(auth.client, actor)
    return decl
