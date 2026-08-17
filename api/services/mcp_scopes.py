"""MCP interop scopes — the shared vocabulary (ADR-563).

**Why this module exists, and why it is not in `mcp_server/auth.py`.**

ADR-563 made the scope tiers load-bearing: `assert_scope(verb)` refuses a verb
the token does not authorize. But the tiers are also the thing the OPERATOR is
asked to approve at the consent screen — and the consent screen is served by the
**API service**, which *cannot import* `mcp_server.auth` (it uses `str | None`
in a default-argument annotation, evaluated at import, and the API venv is
py3.9; the `mcp` SDK it reaches for is py3.11-only besides). The same constraint
already forced `delete_tokens_for_client` out of `mcp_server/` and into
`services/principal_grants.py`.

So the vocabulary lives HERE, where both services can reach it, and
`mcp_server/auth.py` imports it. One definition, two readers — rather than a
copy in the consent route that drifts from the copy the gate enforces. A scope
label that disagrees with the scope check is exactly the pre-563 defect
(a token *labelled* read could delete and share) re-introduced at the surface.

`describe_scopes()` is the operator-facing half: it turns held scopes into the
sentences shown before approval. It is deliberately in the same file as the
enforcement table, so a new tier cannot be enforced without someone seeing that
it also needs consent copy.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional

# ── The tiers ───────────────────────────────────────────────────────────────
#
# The nine interop verbs are not equally consequential, and until ADR-563 the
# surface said they were: `valid_scopes=["read"]` was the ONLY scope, so a token
# LABELLED read could delete a file and mint a member-grant share link. The
# label was decorative.
#
# The tiers are ADDITIVE and ordered — each contains the ones before it. This
# is the whole reason the transition is non-breaking: `read` is retained as the
# LEGACY FULL-ACCESS grant it has always effectively been, so every already-
# connected assistant keeps working, while any token that carries a narrow
# scope is enforced for real. A new client asking for `files:read` gets exactly
# the four read verbs.
SCOPE_READ = "files:read"
SCOPE_WRITE = "files:write"
SCOPE_SHARE = "files:share"

# The legacy scope. Every token issued before ADR-563 carries exactly this
# (schema default `ARRAY['read']`, and both the OAuth and static-bearer paths
# hardcoded it). It authorizes everything — NOT because that is a good grant,
# but because narrowing it retroactively would silently break live connectors
# on a deploy nobody watched. New registrations should request the narrow set.
SCOPE_LEGACY_FULL = "read"

# verb → the narrow scope it requires. Derived from the SAME distinction the
# tool annotations already declare (readOnlyHint / destructiveHint) — the gate
# in `test_adr563_mcp_scope_enforcement.py` asserts the two agree, so a new
# read-only verb cannot land here demanding write.
VERB_SCOPES: Dict[str, str] = {
    # pure reads — enumeration and retrieval, write nothing
    "open": SCOPE_READ,
    "list": SCOPE_READ,
    "search": SCOPE_READ,
    "history": SCOPE_READ,
    # substrate mutations — each lands an attributed revision
    "save": SCOPE_WRITE,
    "edit": SCOPE_WRITE,
    "delete": SCOPE_WRITE,
    "move": SCOPE_WRITE,
    # widens who can reach the workspace at all: 'member' grants full access to
    # whoever opens the link. Its own tier because granting reach is a
    # different act from changing content — a token that may write need not be
    # a token that may hand the workspace to a stranger.
    "share": SCOPE_SHARE,
}

# Which held scopes satisfy a requirement. Ordered containment, plus the legacy
# grant satisfying everything.
SATISFIES: Dict[str, FrozenSet[str]] = {
    SCOPE_READ: frozenset({SCOPE_READ, SCOPE_WRITE, SCOPE_SHARE, SCOPE_LEGACY_FULL}),
    SCOPE_WRITE: frozenset({SCOPE_WRITE, SCOPE_SHARE, SCOPE_LEGACY_FULL}),
    SCOPE_SHARE: frozenset({SCOPE_SHARE, SCOPE_LEGACY_FULL}),
}

# What a newly registering client may ask for. `read` stays valid so existing
# clients can still refresh, but it is no longer the DEFAULT — a fresh
# registration that names nothing gets the read-only tier, which is the safe
# floor rather than the full grant.
VALID_SCOPES = [SCOPE_READ, SCOPE_WRITE, SCOPE_SHARE, SCOPE_LEGACY_FULL]
DEFAULT_SCOPES = [SCOPE_READ]


# ── The operator-facing half ────────────────────────────────────────────────

# One sentence per tier, in the operator's language, naming the CONSEQUENCE
# rather than the verb list. These are what the consent screen shows before the
# bind write — the whole point of ADR-563 having real tiers is that this text
# can finally be TRUE for the specific connection instead of a fixed paragraph.
_GRANT_SENTENCES = {
    SCOPE_READ: "Read your files — open, list, search, and view their history.",
    SCOPE_WRITE: "Create, edit, move, and delete files. Every change is signed and revertible.",
    SCOPE_SHARE: "Create share links, which can give whoever opens them full member access.",
}

# The legacy grant is described honestly and its risk is named. A token carrying
# `read` can delete and share; the pre-563 consent screen said it could
# "read and write your memory", which understated it in both directions
# (wrong noun, and silent about deletion and about handing out member access).
_LEGACY_SENTENCES = [
    "Read your files — open, list, search, and view their history.",
    "Create, edit, move, and delete files. Every change is signed and revertible.",
    "Create share links, which can give whoever opens them full member access.",
]


def satisfied_by(required: str, held: List[str]) -> bool:
    """Whether any held scope satisfies `required` (the containment table)."""
    allowed = SATISFIES.get(required)
    if allowed is None:
        return False
    return any(s in allowed for s in held)


def normalize_scopes(raw: Optional[str]) -> List[str]:
    """Parse a stored space-delimited scope string into a list.

    The `mcp_oauth_codes.scope` column is a single TEXT field written as
    `" ".join(scopes)` by the authorize leg. Empty/absent means the legacy
    grant, matching the column default (`'read'`) — NOT the safe floor, because
    what we display must describe what the token will actually carry.
    """
    if not raw or not raw.strip():
        return [SCOPE_LEGACY_FULL]
    return [s for s in raw.split() if s]


def describe_scopes(scopes: List[str]) -> List[str]:
    """The operator-facing sentences for a set of held scopes (ADR-563).

    Returns what this connection will be ABLE TO DO, most-consequential last so
    the riskiest capability is the final thing read before the Approve button.
    An unrecognized scope is ignored rather than guessed at — never invent a
    permission sentence for a scope this build does not understand.
    """
    if SCOPE_LEGACY_FULL in scopes:
        return list(_LEGACY_SENTENCES)

    out: List[str] = []
    for tier in (SCOPE_READ, SCOPE_WRITE, SCOPE_SHARE):
        # Additive: holding files:write implies the read sentence too.
        if satisfied_by(tier, scopes):
            out.append(_GRANT_SENTENCES[tier])
    return out


def is_legacy_full(scopes: List[str]) -> bool:
    """Whether this connection carries the LEGACY full-access grant.

    The consent screen flags this: a `read`-labelled token that can delete and
    share is the exact thing ADR-563 exists to stop being invisible.
    """
    return SCOPE_LEGACY_FULL in scopes
