"""The one access decider (ADR-643 D2).

⭐⭐⭐ AN ACCESS DECISION IS A SINGLE FUNCTION OF (principal, path, verb), AND NO
DOOR COMPOSES ITS OWN.

This module adds NO permission concept. Every predicate it composes already
existed and keeps its home and its gates:

    operator_can_organize(path)          workspace_paths — path SHAPE
    is_prose_document(path)              workspace_paths — FORMAT class
    CALLER_WRITE_POLICY[class]           workspace_paths — the class ceiling
    _is_path_locked_for_principal(auth)  primitives.workspace — the GRANT

The only new thing is that they are asked TOGETHER, ONCE. That is the whole
point, and it is what makes the property structural rather than diligent.

## Why this exists

ADR-501 wrote the lesson down — *"a permission fix must enumerate the doors,
not the deciders"* — enumerated the TWO doors it knew about, and shipped. Nine
existed. Enumeration is not a structure; it is a to-do list that expires
silently, and a ratchet that names its doors by hand cannot go red for a door
nobody added to it.

So eight doors hand-assembled different subsets of the four predicates and
diverged. Seven asked only the path-shape question and then acted through the
SERVICE client, so RLS was no backstop either. Measured: a principal resolving
to the `agent` class got WRITE=403 and TRASH=200 on `constitution/`,
`persona/`, `governance/` and `contract/`. **A principal who may not write a
file could destroy it.**

## ⭐⭐ A CARVE LAW IS NOT AN AUTHORIZATION CHECK

The confusion that made the divergence look reasonable at every single call
site. `operator_can_organize` LOOKS like permission: it takes a path, returns a
bool, and callers raise 403 on it.

It is a **filesystem-INTEGRITY rule about path SHAPE** — "don't rename a file
another program finds by path" — and it returns the SAME answer for every
principal. It carves `system/`, raw `inbound/` and `_*.yaml` leaves, and
NOTHING else. `constitution/` `persona/` `governance/` `contract/` all PASS it,
deliberately, because ADR-320 says those are the operator's own to reorganize.

**A door that asks only that question has asked nothing about the caller.**
Hence `Decision` carries both answers separately and never collapses them.

## The verbs

The substrate's own, not HTTP's. `read` is served for PRESENTATION (so a
surface can render a document it may not edit) and is NOT an authorization
gate — the read path is bounded by `substrate_scope_filter` + RLS, which this
module does not duplicate.

⚠️ A new verb must be added HERE, where the gate can see it. That is deliberate
friction: a door cannot invent a verb the decider has never heard of.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

#: Every act a door can ask about. `create` is distinct from `write` because a
#: door may legitimately allow one and not the other (ADR-424 D2: naming a
#: folder for your work is not editing a kernel file).
VERBS = frozenset({
    "read", "write", "create", "move", "rename", "trash", "restore", "destroy",
})

#: The verbs that MUTATE. Every one owes the grant consult; `read` does not.
MUTATING_VERBS = frozenset(VERBS - {"read"})

#: The verbs that RE-PLACE a file — the carve law's own question ("may anyone
#: hand-organize a file in this position"). `write` is NOT here: editing a
#: file's content in place moves nothing, so a machine-config leaf is
#: un-renameable but its content is still writable by a principal with reach.
ORGANIZE_VERBS = frozenset({"move", "rename", "trash", "restore", "destroy", "create"})


@dataclass(frozen=True)
class Decision:
    """One answer, with the reason a surface can show a person.

    `reason` is NOT decoration. It is what the client is served (ADR-643 D3) so
    a refusal explains itself in the operator's words instead of arriving as a
    bare 403 — the difference between Files' "It's a settings file the system
    needs in this exact place" and a raw error string.
    """

    allowed: bool
    #: Machine-readable cause, for gates and clients. None when allowed.
    code: Optional[str] = None
    #: One sentence, object-focused, macOS-plain. No mechanism jargon.
    reason: Optional[str] = None

    def __bool__(self) -> bool:  # `if not resolve_access(...)` reads naturally
        return self.allowed


ALLOWED = Decision(True)


def _rel(path: str) -> str:
    rel = (path or "").strip().lstrip("/")
    if rel.startswith("workspace/"):
        rel = rel[len("workspace/"):]
    return rel


def _carve_reason(path: str) -> Decision:
    """The carve law's refusal, in the words the Files surface already uses.

    Mirrors `web/lib/workspace/ownership.ts::organizeBlockedReason` — which
    ADR-643 D3 deletes once this is served, so the strings live here alone.
    """
    from services.workspace_paths import INBOUND_UPLOADS_ROOT, SYSTEM_ROOT

    rel = _rel(path)
    leaf = rel.rsplit("/", 1)[-1] or "This item"
    if rel.startswith(SYSTEM_ROOT):
        return Decision(
            False, "system_managed",
            f"“{leaf}” is used by the system to keep your workspace running. "
            "Moving, renaming, or deleting it isn’t allowed.",
        )
    if rel.startswith("inbound/") and not rel.startswith(INBOUND_UPLOADS_ROOT):
        return Decision(
            False, "raw_intake",
            f"“{leaf}” is a record of something that came into your workspace, "
            "kept exactly as it arrived. Records like this don’t change.",
        )
    return Decision(
        False, "machine_config",
        f"“{leaf}” is a settings file the system needs in this exact place. "
        "Moving, renaming, or deleting it isn’t allowed.",
    )


def resolve_access(auth: Any, path: str, verb: str) -> Decision:
    """THE decider. May this principal perform `verb` on `path`?

    Order is fixed and each step is a different question:

      1. Is the verb one we know?          (a door cannot invent one)
      2. Is the path SHAPE organizable?    (carve law — same for everyone)
      3. May THIS principal touch it?      (the grant — ADR-373/ADR-501)

    ⚠️ Step 2 runs only for `ORGANIZE_VERBS`. A `write` to a carved path is not
    a placement question: `system/awareness.md` is un-renameable AND
    un-writable, but the second fact comes from step 3, not step 2. Conflating
    them is what produced `edit_workspace_file`'s `editable_prefixes` — a
    prefix list OR'd against the carve law, re-admitting `system/` one line
    after the carve law rejected it (ADR-643 D5).

    Never raises. A door composes the HTTP status; this returns a fact.
    """
    if verb not in VERBS:
        raise ValueError(
            f"unknown access verb {verb!r} — add it to services.access.VERBS, "
            "where the gate can see it (ADR-643 D2)"
        )

    from services.workspace_paths import operator_can_organize

    if verb in ORGANIZE_VERBS and not operator_can_organize(path):
        return _carve_reason(path)

    if verb in MUTATING_VERBS:
        from services.primitives.workspace import _is_path_locked_for_principal

        if _is_path_locked_for_principal(auth, path):
            return Decision(
                False, "grant",
                f"Your grant in this workspace does not permit changing {path}. "
                "The workspace owner can widen it from the Access pane.",
            )

    return ALLOWED


def may_edit_as_prose(auth: Any, path: str) -> Decision:
    """The Text app's question (ADR-570 D4 + ADR-643 D4): may this principal
    edit this path AS PROSE, in a markdown canvas?

    Two conditions, and the FORMAT one comes first because its refusal is a
    different fact: `governance/_autonomy.yaml` is not refused because of who
    is asking — it is machine-parsed YAML, and rendering it as markdown is a
    category error whoever opens it. The operator's report was sharpest here:
    it opened in a canvas whose inspector asserted *"it stays a .md file."*

    ⭐ This is the predicate `resolveSurfaceApplication` claims to mirror and
    does not (it implements two of the carve law's three carves). Serving this
    is what lets ADR-643 D3 delete that re-derivation.
    """
    from services.workspace_paths import is_prose_document, operator_can_organize

    if not is_prose_document(path):
        leaf = _rel(path).rsplit("/", 1)[-1] or "This file"
        return Decision(
            False, "not_prose",
            f"“{leaf}” isn’t a text document, so it doesn’t open in the editor.",
        )

    # ⚠️ THE CARVE LAW APPLIES HERE, though `write` alone would skip it.
    # Caught by driving the decider rather than reading it: a `.md` file under
    # raw `inbound/` passes `is_prose_document` AND the owner's write ceiling,
    # so without this it reported editable — contradicting ADR-422 D2 (an
    # arrival is retained exactly as it came, never rewritten). The FE's
    # `isArrival` check was RIGHT about this one; it is the `system/` carve it
    # omits, not this one.
    #
    # This is not the `write`-vs-organize conflation warned about in
    # `resolve_access`: opening a canvas is an invitation to REPLACE the file's
    # content, which for an immutable record is the same category error as
    # renaming it. `write` stays carve-free for the doors that legitimately
    # rewrite in place (a machine leaf's own writer).
    if not operator_can_organize(path):
        return _carve_reason(path)

    return resolve_access(auth, path, "write")


def access_summary(auth: Any, path: str) -> dict:
    """What the client is TOLD (ADR-643 D3), so it never re-derives the rule.

    Rides the file/tree payloads. A served decision cannot drift from the
    decider, because it IS the decider's output — which is the whole reason
    the hand-kept TypeScript mirror goes away rather than being kept in sync.

    Kept deliberately SMALL: three booleans and one sentence. A client that
    needs a fourth fact should ask for a verb, not reconstruct a rule.
    """
    write = resolve_access(auth, path, "write")
    organize = resolve_access(auth, path, "trash")
    prose = may_edit_as_prose(auth, path)
    return {
        "may_write": write.allowed,
        "may_organize": organize.allowed,
        "may_edit_as_prose": prose.allowed,
        # The first refusal that applies, in the order a person meets them.
        "reason": organize.reason or write.reason or prose.reason,
        "code": organize.code or write.code or prose.code,
    }
