"""Workspace genesis — the single seam through which an OWNED workspace is born.

ADR-465 D2 moved owner-genesis out of the DB (migration 106's `on_auth_user_created`
trigger, dropped by migration 233) and up into the app, where it can be CONDITIONAL.
That gave us one mint site — `supabase.ensure_owner_workspace`, the cold-user door —
which is structurally a FIRST-workspace function: it returns early when any owner row
exists, so it cannot mint a second and must not be taught to. This module is the
other half: the DELIBERATE act, where the caller names the workspace they want.

## Why this is its own module

Genesis is about to grow. Today the act is "a name"; the intended end state is a
multi-step flow (a directory/organisation shape, a starting structure, possibly
signup-shaped steps). Every one of those is a step INSIDE `create_workspace`, not a
new call site — so callers bind to this seam now and keep working when the flow
lands. The staging is explicit at `_GENESIS_STEPS` below.

## The two mint paths, and why they stay distinct

| | `ensure_owner_workspace` (supabase.py) | `create_workspace` (here) |
|---|---|---|
| Trigger | implicit — the cold-user door | explicit — the operator asked |
| Names it | no (`DEFAULT_WORKSPACE_NAME`) | yes (the caller's name) |
| Signup grant | **yes** — $3, the per-person incentive | **no** — see below |
| Idempotent | yes (returns any existing owner row) | no — each call is a new commons |

Collapsing them would be wrong in both directions: the cold door must stay idempotent
(it fires on every `/workspace/state` of a principal with no binding), and the
deliberate act must NOT be (asking twice means wanting two).

## The billing carve (ADR-416 + ADR-429)

The workspace is the billing unit (ADR-416 §2) — "the same human in two workspaces is
two separately-billed seats" (:96) — and ADR-429:374 rules that new workspaces bill
from creation. The `workspaces` row carries `balance_usd DEFAULT 3.0` +
`free_balance_granted DEFAULT true` (migration 144), which is the ADR-172 SIGNUP grant:
a per-PERSON incentive to try the product, recorded once in `balance_transactions`.

A workspace minted here therefore starts at **zero balance**, explicitly overriding the
column default. Letting the default ride would make this endpoint print $3 of real
spend per click — a per-person incentive silently re-scoped to per-workspace. The
first workspace keeps its grant (the cold door is untouched); the owner funds each
additional commons like any other.

`free_balance_granted=True` is stamped deliberately: it means "the signup grant has
been settled for this row", so no later top-up/refill path re-grants it. The flag
tracks whether the grant is OUTSTANDING, not whether money arrived.

## What genesis does NOT do (ADR-414 D4 — pure genesis)

No skeleton seeding, no template, no program fork, no MANDATE. A workspace is born
with the constitutional facts and nothing else; substrate grows from work, not from
signup scaffolding (FOUNDATIONS Axiom 1 corollary). `initialize_workspace` is a
SEPARATE, idempotent act that the cold-user door runs on first `/workspace/state` —
we deliberately do not call it here, so the two stay independently triggered exactly
as ADR-414 D4 left them.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from services.supabase import get_service_client, _resolve_owner_workspace_id_cached

logger = logging.getLogger(__name__)

# The name bound at 80 chars to match PATCH /api/workspace (routes/workspace.py)
# and the `maxLength` on the General pane. One rule, three places that must agree.
WORKSPACE_NAME_MAX = 80


class WorkspaceGenesisError(ValueError):
    """A named workspace could not be born. Carries an operator-safe message."""


# ── The staged flow ──────────────────────────────────────────────────────────
# Genesis is ONE act with N steps. Today only `identity` is real; the rest are
# named so a future session extends this list rather than adding a second entry
# point (which is how `ensure_owner_workspace` and this function came to differ
# in the first place). A step is added HERE and executed inside `create_workspace`
# — never by a caller, which knows only "create me a workspace called X".
_GENESIS_STEPS = (
    "identity",      # LIVE — the name (and later: icon, slug, directory shape)
    # "structure",   # FUTURE — starting folders / directory handling
    # "principals",  # FUTURE — seed grants beyond the owner
    # "program",     # FUTURE — an at-birth hire (ADR-414 D5 says post-genesis;
    #                #          would need its own ratification to move here)
)


def normalize_workspace_name(raw: Optional[str]) -> str:
    """Validate + normalize an operator-supplied workspace name.

    Collapses internal whitespace so a name cannot be padded into looking like
    two different workspaces in the switcher ("Acme" vs "Acme "), and rejects
    empty/oversize. Raises `WorkspaceGenesisError` with operator-safe copy.
    """
    name = re.sub(r"\s+", " ", (raw or "").strip())
    if not name:
        raise WorkspaceGenesisError("Workspace name cannot be empty")
    if len(name) > WORKSPACE_NAME_MAX:
        raise WorkspaceGenesisError(
            f"Workspace name is too long ({WORKSPACE_NAME_MAX} max)"
        )
    return name


def create_workspace(user_id: str, name: str) -> dict:
    """Mint a NEW owned workspace for `user_id`, named by them.

    The deliberate counterpart to `ensure_owner_workspace`. Returns the created
    row (`id`, `name`, `icon`). Raises `WorkspaceGenesisError` on a bad name.

    NOT idempotent by design — two calls mean two commons (see module docstring).

    The insert runs under the SERVICE client, not the caller's. The RLS INSERT
    policy (`with_check owner_id = auth.uid()`, migration 001) would permit the
    caller's own client here, but the service client is what every other mint
    site uses (`ensure_owner_workspace`, the L4 re-mint) and it keeps the
    owner-stamp under our control rather than the JWT's. `owner_id` is taken
    from the authenticated `user_id` and is never caller-supplied.
    """
    clean = normalize_workspace_name(name)
    client = get_service_client()

    # ── Step: identity ───────────────────────────────────────────────────────
    # balance_usd=0 + free_balance_granted=True OVERRIDE the migration-144
    # defaults on purpose — see the billing carve in the module docstring. Do
    # not "simplify" by dropping these two keys; the column defaults would mint
    # $3 per call.
    inserted = (
        client.table("workspaces")
        .insert(
            {
                "name": clean,
                "owner_id": user_id,
                "balance_usd": 0,
                "free_balance_granted": True,
            }
        )
        .execute()
    ).data or []
    if not inserted:
        raise RuntimeError(f"workspace genesis failed for {user_id}")
    row = inserted[0]

    # The owner→workspace resolver is lru_cached and may hold this principal's
    # PREVIOUS answer (or a None from before they owned anything). Genesis is
    # exactly the event that invalidates it. Note the resolver is oldest-first,
    # so an existing owner's "home" does NOT move to the new workspace — the
    # caller binds explicitly via X-Workspace-Id instead.
    _resolve_owner_workspace_id_cached.cache_clear()

    logger.info(
        "[ADR-465] minted owned workspace %s for %s (steps=%s)",
        row.get("id"),
        user_id,
        ",".join(_GENESIS_STEPS),
    )
    return {"id": row.get("id"), "name": row.get("name") or clean, "icon": row.get("icon")}
