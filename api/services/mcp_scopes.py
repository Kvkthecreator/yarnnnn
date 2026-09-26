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

from typing import Dict, FrozenSet, List

# ── The tiers ───────────────────────────────────────────────────────────────
#
# The interop verbs are not equally consequential, and until ADR-563 the
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
# on a deploy nobody watched. It is honoured, never minted: no new grant can
# carry it (ADR-563 am.1 — the operator picks a tier at consent).
SCOPE_LEGACY_FULL = "read"

# verb → the narrow scope it requires. Derived from the SAME distinction the
# tool annotations already declare (readOnlyHint / destructiveHint) — the gate
# in `test_adr563_mcp_scope_enforcement.py` asserts the two agree, so a new
# read-only verb cannot land here demanding write.
VERB_SCOPES: Dict[str, str] = {
    # ADR-584: "where am I standing?" — the WEAKEST verb by construction. A
    # token that may do anything at all may ask which workspace it is bound to
    # and which verbs it holds; it reads no file content and mutates nothing.
    "whoami": SCOPE_READ,
    # pure reads — enumeration and retrieval, write nothing
    "open": SCOPE_READ,
    "list": SCOPE_READ,
    "search": SCOPE_READ,
    "history": SCOPE_READ,
    # ADR-668 D7 — the run ledger, read. Every member already sees every run
    # (ADR-666 D6); a token that may read the files may read what the agents
    # did to make them. Nothing is written: `services/runs.py` is the one
    # writer and no verb reaches it.
    "runs": SCOPE_READ,
    # substrate mutations — each lands an attributed revision
    "save": SCOPE_WRITE,
    "edit": SCOPE_WRITE,
    "delete": SCOPE_WRITE,
    "move": SCOPE_WRITE,
    # ADR-622: minting an upload ticket IS a write — it creates a capability
    # that lands an attributed revision. It is scoped with the write verbs and
    # not below them, even though the mint itself touches no file: the ticket's
    # whole purpose is to add one, so gating the ticket more weakly than the
    # write it authorizes would be a door around `files:write`.
    "request_upload": SCOPE_WRITE,
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

# ── Who decides the grant (ADR-563 am.1) ────────────────────────────────────
#
# The tiers a connection may be GRANTED, weakest first. The legacy `read` is not
# among them: it is still honoured on the tokens that already carry it
# (`SATISFIES`), but no new grant can mint it.
GRANTABLE_TIERS = [SCOPE_READ, SCOPE_WRITE, SCOPE_SHARE]

# Registration is a CEILING, not the grant. A client that registers without
# naming a scope may later be granted any tier, and the MCP SDK refuses an
# authorize request for a scope the client did not register — so a registration
# default below the top tier is a permanent cap no consent screen can lift.
# That is what ADR-563 D1 shipped (`default_scopes=["files:read"]`): ChatGPT
# registered read-only, asked for exactly that at /authorize, and reconnecting
# re-used the same client, so "re-authorize the connector" could never grant
# write. `valid_scopes` is the same list: it is also what the authorization
# server advertises as `scopes_supported`, and the legacy grant is not offered.
REGISTRATION_SCOPES = list(GRANTABLE_TIERS)

# The OPERATOR decides the grant, on the consent screen, and the bind writes it
# onto the pending code (`POST /api/mcp/oauth-callback?scope=`). What the client
# asked for at /authorize does not decide it: ChatGPT asks for whatever it was
# registered with, Claude asks for nothing. This is the tier preselected there —
# write, because a connected assistant that cannot save is not connected to a
# shared commons; share stays an explicit opt-in because it hands the workspace
# to whoever opens a link.
DEFAULT_GRANT = SCOPE_WRITE


# ── The operator-facing half ────────────────────────────────────────────────

# One sentence per tier, in the operator's language, naming the CONSEQUENCE
# rather than the verb list. These are what the consent screen shows before the
# bind write — the whole point of ADR-563 having real tiers is that this text
# can finally be TRUE for the specific connection instead of a fixed paragraph.
_GRANT_SENTENCES = {
    SCOPE_READ: "Read your files — open, list, search, view their history — and what your agents did (runs).",
    SCOPE_WRITE: "Create, edit, move, and delete files. Every change is signed and revertible.",
    SCOPE_SHARE: "Create share links, which can give whoever opens them full member access.",
}

# The choice the consent screen offers, one label per grantable tier. The label
# names the tier; the sentences above say what it permits.
_TIER_LABELS = {
    SCOPE_READ: "Read only",
    SCOPE_WRITE: "Read and write",
    SCOPE_SHARE: "Read, write, and share",
}


def satisfied_by(required: str, held: List[str]) -> bool:
    """Whether any held scope satisfies `required` (the containment table)."""
    allowed = SATISFIES.get(required)
    if allowed is None:
        return False
    return any(s in allowed for s in held)


def describe_scopes(scopes: List[str]) -> List[str]:
    """The operator-facing sentences for a set of held scopes (ADR-563).

    Returns what this connection will be ABLE TO DO, most-consequential last so
    the riskiest capability is the final thing read before the Approve button.
    An unrecognized scope is ignored rather than guessed at — never invent a
    permission sentence for a scope this build does not understand.
    """
    out: List[str] = []
    for tier in GRANTABLE_TIERS:
        # Additive: holding files:write implies the read sentence too, and the
        # legacy grant satisfies every tier, so it reads as the full set.
        if satisfied_by(tier, scopes):
            out.append(_GRANT_SENTENCES[tier])
    return out


def consent_tiers() -> List[Dict[str, object]]:
    """The choice the consent screen offers (ADR-563 am.1).

    One entry per grantable tier, weakest first, each carrying the sentences
    `describe_scopes` gives for it, so what the operator picks is described by
    the same table `assert_scope` enforces. The bind accepts exactly these
    scopes and nothing else.
    """
    return [
        {"scope": tier, "label": _TIER_LABELS[tier], "grants": describe_scopes([tier])}
        for tier in GRANTABLE_TIERS
    ]


def allowed_verbs(scopes: List[str]) -> List[str]:
    """The verbs a set of held scopes actually authorizes (ADR-584 D1).

    Derived from `VERB_SCOPES` through the SAME `satisfied_by` the gate calls —
    so what `whoami` tells the model it may do cannot drift from what
    `assert_scope` will let it do. A hand-listed roster here would rebuild the
    pre-563 defect one layer up: a label free to disagree with the check.

    Verb order follows `VERB_SCOPES` (reads, then writes, then share) rather than
    sorting, so the most consequential capability reads last.
    """
    return [verb for verb, required in VERB_SCOPES.items() if satisfied_by(required, scopes)]


def is_legacy_full(scopes: List[str]) -> bool:
    """Whether this connection carries the LEGACY full-access grant.

    No new grant can carry it (ADR-563 am.1), but pre-563 tokens still do and
    rotate forever, so the members pane flags them: a `read`-labelled token that
    can delete and share is the exact thing ADR-563 exists to stop being
    invisible.
    """
    return SCOPE_LEGACY_FULL in scopes
