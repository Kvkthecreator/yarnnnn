"""The settle verb — "keep this": the act that turns a conversation into record.

ADR-457 D3 (the verb, direction ratified) onto D4 (the think-home convention),
sequenced by ADR-460 §8. Three birds, one verb:

  1. The FELT MOMENT of the moat — episodic becomes cumulative, on screen.
  2. The MISSING DERIVE ORGAN — the connector→recall chain has been broken at
     *derive* since the ADR-401 audit (autonomous derive never fired). This is
     that organ, human-staged instead of autonomous.
  3. The RETRIEVAL FIX — settled products embed, so Think's grounding reads an
     indexed corpus (today Studio artifacts + lane writes are mostly NOT
     embedded).

WHY THIS IS NOT A DERIVE RECIPE (the design question, and the fact that
decides it): every DERIVE_RECIPES row declares `accepts: ["file"]` and
`build_derive_section` takes a `source_path` it normalizes to /workspace/... —
the whole registry is built on a source that is a PATH IN THE COMMONS. Settle's
source is a TRANSCRIPT (session_messages rows): no path, no revision, no
projection. That is a difference in KIND, not degree. Forcing it into the
registry would mean inventing a fake path for a session, or widening `accepts`
and forking every recipe's mechanics on source type — the dilution ADR-460
removed. So: a SIBLING of the recipe path, reusing its spine (posture overlay +
derived_from + revision_kind='derivation'), not a row in it.

WHY THIS IS NOT A PRIMITIVE: a primitive is a capability an LLM may invoke.
Settle is a MEMBER'S GESTURE — it fires only on a human act (the never-ambient
invariant), and the model that runs it is the transport, not the actor. In
CHAT_PRIMITIVES it would let a model settle its own conversation unasked.

THE DIVISION OF LABOUR: the model distills, the KERNEL places. Every mechanic
the kernel can do deterministically, the kernel does — the model's only job is
judgment about CONTENT. It never chooses the path, never writes the citation,
never decides to embed. Don't give the model a lever the kernel should hold.

Spec: docs/analysis/settle-verb-spec-2026-07-16.md
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: The think-home root (ADR-457 D4). No new namespace, no kernel noun.
_OPERATION_ROOT = "/workspace/operation"

#: Bounded — a settle is one turn, not a loop. Generous enough for a ~120-line
#: note; below the ADR-440 authoring profile (8192), which stays the ceiling.
_SETTLE_MAX_TOKENS = 4096
_SETTLE_TIMEOUT_S = 120.0

#: The settle posture — composed at turn time, never stored (the ADR-411 D6 /
#: ADR-414 D2 pattern). It carries ONLY what the model needs to distill.
#: Deliberately absent: where to write, how to cite, whether to embed. The
#: kernel holds those levers (see the module docstring).
_SETTLE_POSTURE = """You are {model_label}, settling a conversation for {member} \
in their YARNNN workspace.

THE JOB
Distill this conversation into ONE note a colleague could act on WITHOUT reading
the transcript. The conversation is the raw and stays retained; your note is the
UNDERSTANDING. This is not a summary — a summary compresses what was said; a
settle distills what was UNDERSTOOD and drops the rest.

THE SHAPE
- A `# Title` first line: the subject, not "Summary of conversation".
- What was decided or understood.
- The reasoning that matters — not the path the conversation took to reach it.
- Open questions, if any remain.

THE BAR
- Under ~120 lines. Selective beats complete: drop what a reader wouldn't act on.
- Every load-bearing claim traceable to something actually said in the
  conversation. NEVER invent specifics — no invented numbers, names, or
  decisions.
- If the conversation reached no conclusion, SAY SO plainly. A settle that
  manufactures a decision is worse than no settle.

THE OUTPUT CONTRACT
Return the note's markdown and NOTHING else — the `# Title` line, then the body.
No preamble, no "here's your note", no code fence around the whole thing.
"""


def build_settle_posture(model_label: str, member: str) -> str:
    """The settle posture overlay — pure. See ``_SETTLE_POSTURE``."""
    return _SETTLE_POSTURE.format(model_label=model_label, member=member)


def extract_title(note: str) -> str:
    """The note's title, from its leading `# Title` line. Pure.

    Falls back to the first non-empty line, then to a generic. The model is
    contracted to lead with `# Title`; this never trusts that blindly.
    """
    for line in (note or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            return s.lstrip("#").strip() or "Untitled note"
        return s[:120]
    return "Untitled note"


def slugify(title: str) -> str:
    """Kebab-case slug for the filename. Pure, deterministic."""
    s = (title or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return (s[:60].rstrip("-")) or "note"


def _leading_noun(title: str) -> str:
    """The title's first meaningful word — the topic-match probe (§5 rung 3)."""
    for w in re.split(r"[^a-zA-Z0-9]+", (title or "").lower()):
        if len(w) > 2:
            return w
    return ""


def resolve_topic_folder(
    title: str,
    *,
    artifact_path: Optional[str] = None,
    derive_source: Optional[str] = None,
    existing_folders: Optional[list[str]] = None,
) -> Optional[str]:
    """The placement ladder (spec §5) — pure, deterministic, NO LLM.

    Returns the topic folder under operation/ (e.g. "pricing"), or None to mean
    the Documents root (D4's stated fallback).

    Rungs:
      1. A BOUND lane (artifact_path)  → the artifact's own folder. The thinking
         about a thing lands beside the thing.
      2. A DERIVE lane (derive_source) → the source's folder. Same logic.
      3. An EXISTING peer folder matching the title's leading noun — EXACT,
         case-insensitive, against existing operation/* folders only. No fuzzy
         match, no LLM guess: a near-match that files thinking under the wrong
         topic is worse than the fallback, because the fallback is VISIBLY
         un-filed and a mis-file is INVISIBLY wrong.
      4. None → the Documents root.
    """
    for bound in (artifact_path, derive_source):
        if bound:
            folder = _folder_of(bound)
            if folder:
                return folder

    noun = _leading_noun(title)
    if noun and existing_folders:
        for f in existing_folders:
            if (f or "").strip().lower() == noun:
                return f
    return None


def _folder_of(path: str) -> Optional[str]:
    """The operation/ topic folder a bound path sits in, if any. Pure."""
    p = (path or "").strip()
    if not p:
        return None
    if not p.startswith("/workspace/"):
        p = "/workspace/" + p.lstrip("/")
    prefix = _OPERATION_ROOT + "/"
    if not p.startswith(prefix):
        return None
    rest = p[len(prefix):]
    parts = [s for s in rest.split("/") if s]
    # operation/{topic}/file.md → topic ; operation/file.md → no topic folder
    return parts[0] if len(parts) >= 2 else None


def compose_settle_path(
    title: str, topic: Optional[str], *, today: Optional[str] = None
) -> str:
    """`operation/{topic}/{yyyy-mm-dd}-{slug}.md` (ADR-457 D4). Pure."""
    date = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    leaf = f"{date}-{slugify(title)}.md"
    if topic:
        return f"{_OPERATION_ROOT}/{topic}/{leaf}"
    return f"{_OPERATION_ROOT}/{leaf}"


def _existing_topic_folders(client: Any, user_id: str, workspace_id: Optional[str]) -> list[str]:
    """Topic folder names directly under operation/. Read-only, best-effort."""
    try:
        q = client.table("workspace_files").select("path").like(
            "path", f"{_OPERATION_ROOT}/%"
        )
        if workspace_id:
            q = q.eq("workspace_id", workspace_id)
        else:
            q = q.eq("user_id", user_id)
        rows = q.limit(1000).execute().data or []
    except Exception as exc:  # a placement hint is never worth failing the settle
        logger.warning("[SETTLE] topic-folder scan failed: %s", exc)
        return []
    folders = set()
    for r in rows:
        f = _folder_of(r.get("path") or "")
        if f:
            folders.add(f)
    return sorted(folders)


def _unique_path(client: Any, user_id: str, workspace_id: Optional[str], path: str) -> str:
    """Collision → -2, -3. NEVER overwrite: two settles from one conversation
    are two acts, and the ledger's job is to keep both."""
    base, ext = (path[:-3], ".md") if path.endswith(".md") else (path, "")
    candidate, n = path, 1
    while True:
        try:
            q = client.table("workspace_files").select("path").eq("path", candidate)
            if workspace_id:
                q = q.eq("workspace_id", workspace_id)
            else:
                q = q.eq("user_id", user_id)
            if not (q.limit(1).execute().data or []):
                return candidate
        except Exception:
            return candidate  # fail-open: a collision check is not worth the act
        n += 1
        candidate = f"{base}-{n}{ext}"


def transcript_for_settle(messages: list[dict]) -> str:
    """The conversation, rendered for the distilling turn. Pure."""
    lines = []
    for m in messages or []:
        role = "Member" if m.get("role") == "user" else "Assistant"
        content = (m.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


def strip_fence(note: str) -> str:
    """Drop a whole-note ``` fence if the model wrapped it despite the contract.

    Pure. Only strips when the note OPENS with a fence and CLOSES with one —
    a fenced code block *inside* the note is content and stays.
    """
    s = (note or "").strip()
    if not s.startswith("```"):
        return s
    lines = s.splitlines()
    if len(lines) < 2 or not lines[-1].strip().startswith("```"):
        return s
    return "\n".join(lines[1:-1]).strip()


async def settle_lane(
    auth: Any,
    *,
    lane_id: str,
    lane_meta: dict,
    messages: list[dict],
    member_label: Optional[str] = None,
) -> dict:
    """Settle one lane: distill → place → write → cite → embed → meter.

    The kernel's half of the division of labour. The model returns CONTENT
    (one bounded turn, no tool loop — giving it WriteFile here would let it
    choose the path, and D4's convention is the kernel's to enforce, not the
    model's to interpret). Everything else below is deterministic.

    Returns {path, title, revision_id, model}.
    Raises ValueError on an empty conversation or an empty distillation.
    """
    from services.authored_substrate import write_revision
    from services.lane_runner import LANE_MODELS, _resolve_byok_key, lane_caller_identity
    from services.model_router import route_completion

    model = (lane_meta or {}).get("model") or ""
    if model not in LANE_MODELS:
        raise ValueError(f"lane model not routable: {model!r}")

    transcript = transcript_for_settle(messages)
    if not transcript.strip():
        raise ValueError("nothing to settle: the conversation is empty")

    member = member_label or "the member"
    label = LANE_MODELS.get(model, {}).get("label", model)

    # ── 1. distill (one bounded turn, no tools) ──────────────────────────
    routed = await route_completion(
        model,
        [{"role": "user", "content":
          f"Here is the conversation to settle:\n\n{transcript}"}],
        system=build_settle_posture(label, member),
        max_tokens=_SETTLE_MAX_TOKENS,
        timeout=_SETTLE_TIMEOUT_S,
        api_key=_resolve_byok_key(auth, model),
    )
    note = strip_fence(routed.text or "")
    if not note.strip():
        raise ValueError("the model returned an empty note")

    title = extract_title(note)

    # ── 2. place (kernel-deterministic, ADR-457 D4) ──────────────────────
    workspace_id = getattr(auth, "workspace_id", None)
    topic = resolve_topic_folder(
        title,
        artifact_path=(lane_meta or {}).get("artifact_path"),
        derive_source=(lane_meta or {}).get("derive_source"),
        existing_folders=_existing_topic_folders(auth.client, auth.user_id, workspace_id),
    )
    path = _unique_path(
        auth.client, auth.user_id, workspace_id, compose_settle_path(title, topic)
    )

    # ── 3. write + cite (ADR-448 edge, ADR-423 kind, ADR-411 D4 attribution) ──
    # derived_from carries the lane's BINDINGS (real paths, real edges that
    # `trace` and `list_dependents` already understand). The CONVERSATION
    # itself rides in metadata: `derived_from` is a list of workspace PATHS
    # (ADR-448) and a lane is not a file. Named honest gap, not a fudge — it
    # upgrades in ONE place when the conversation-as-substrate question
    # (capture ruling (c)) rules. See spec §6.
    edges = [
        p for p in (
            (lane_meta or {}).get("artifact_path"),
            (lane_meta or {}).get("derive_source"),
        ) if p
    ]
    lane_name = (lane_meta or {}).get("name") or "untitled"
    # The lane id rides the revision MESSAGE, not `metadata=`. Probed
    # 2026-07-16 and corrected: write_revision's `metadata` writes to
    # workspace_files.metadata — the FILE row, which the NEXT revision
    # overwrites. The provenance of THIS settle would be silently lost the
    # first time the note was edited. `workspace_file_versions` has no
    # metadata column; its `message` is the permanent per-revision record, so
    # the citation lives there — greppable, immutable, and visible in `trace`.
    revision_id = write_revision(
        auth.client,
        user_id=auth.user_id,
        path=path,
        content=note,
        authored_by=lane_caller_identity(auth.user_id, model),
        message=f"settled from the lane '{lane_name}' (session {lane_id})",
        workspace_id=workspace_id,
        revision_kind="derivation",
        derived_from=edges or None,
    )

    # ── 4. embed (THE retrieval fix — bird 3 dies if this is skipped) ────
    try:
        from services.primitives.workspace import _embed_workspace_file
        await _embed_workspace_file(auth.client, auth.user_id, path, note)
    except Exception as exc:
        # The note is written and attributed; an embed failure costs
        # retrieval, not the act. Never lose a settled note to it.
        logger.warning("[SETTLE] embed failed for %s: %s", path, exc)

    # ── 5. meter (falsifier 2's instrument — W0 built this) ──────────────
    try:
        from services.supabase import get_service_client
        from services.telemetry import record_execution_event
        record_execution_event(
            get_service_client(),
            user_id=auth.user_id,
            slug="settle",          # ← falsifier 2 keys on this slug
            mode="judgment",
            trigger_type="addressed",
            status="success",
            model=routed.ledger_model,
            principal_id=getattr(auth, "principal_id", None) or auth.user_id,
            workspace_id=workspace_id,
            session_id=lane_id,     # ← W0's join key
            **routed.usage,
        )
    except Exception as exc:
        logger.warning("[SETTLE] cost ledger record failed: %s", exc)

    return {"path": path, "title": title, "revision_id": revision_id, "model": model}
