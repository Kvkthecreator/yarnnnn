"""App exposure stage — ADR-592 (2026-08-21).

The single source of truth for **how far along an app is toward being a
product**. One field on the kernel surface row, four values, resolved here and
enforced at chokepoints — the ``services/agent_gating.py`` shape, generalized
from one flag for one subsystem to one field per app.

WHY A FIELD AND NOT A PAIR OF LISTS
Before this, "hide an app" was spelled by hand in six places: the registry's
``launcher_tier``, the registry's ``default_pinned``, the frontend's
``DEFAULT_KEPT_SURFACES``, a Dock reseed generation, the type→app association,
and (for an app with a lane) the scheduler. ADR-488 (Images) and ADR-574 (Docs)
each performed that spelling and each half-worked — Docs was declared PAUSED on
2026-08-17 and was still reachable at ``/docs``, in the Dock, and by
double-clicking any document, because a hand-kept list beside a derived truth
drifts the moment someone adds a row (the ADR-587 lesson, and the same class of
defect as the eight ungated surfaces middleware.ts:30 records).

The stage is DECLARED once and the six spellings are DERIVED. An app is hidden
because of what it is, not because six people remembered.

THE FOUR STAGES

``internal``     Not a product. Absent from the served roster, so no Dock icon,
                 no launcher tile, no flat-search hit — and absent for
                 EVERY operator, including one whose Dock was curated years ago
                 (a persisted slug that names no served surface cannot render).
                 The route is a redirect stub; the type→app association skips
                 it; a lane on a clock does not drain. Develop freely behind it.

``search-only``  Present but unpromoted: found by name in the launcher's flat
                 search, opens when a file routes to it, absent from the Dock.
                 The ADR-488 "hidden, not unplugged" posture, now spelled once.

``beta``         A tile in the launcher, still off the default Dock. The rung
                 an app climbs before it earns a permanent icon.

``primary``      Fully unveiled: launcher tile + a Dock icon by default.

WHY ``internal`` LEAVES THE ROSTER RATHER THAN CARRYING A FLAG
A ``hidden: true`` row still ships its title and summary to every client, is
still matched by flat search (Launcher.tsx searches ``summary``), and still
occupies a slug the window manager will happily foreground. Removing the row
is the only spelling that makes every consumer agree without each consumer
having to remember. The cost is stated at ``stage_route_stubs`` below: the
middleware derives its protected set from the roster, so a route whose slug
leaves the roster must become a redirect stub in the SAME change or it serves
200 to logged-out visitors — the exact defect repaired 2026-08-20.

RENDER PARITY (CLAUDE.md §5)
``APP_STAGE_*`` overrides must be set on **API + Unified Scheduler** — the
scheduler holds the drain chokepoint. Setting it on the API alone hides the
app while its lane keeps spending, which is the failure this ADR exists to end.
"""

from __future__ import annotations

import os
from typing import Literal

Stage = Literal["internal", "search-only", "beta", "primary"]

#: Declaration order = exposure order. Index comparisons are meaningful:
#: ``STAGES.index(a) >= STAGES.index("beta")`` reads "at least beta".
STAGES: tuple[Stage, ...] = ("internal", "search-only", "beta", "primary")

#: The stage an app carries when its registry row declares none. ``primary``
#: keeps every pre-ADR-592 row behaving exactly as it did — the seam ships
#: inert, the ADR-375 D4 rule (a default that changes nothing on arrival).
DEFAULT_STAGE: Stage = "primary"

_TRUE_TOKENS = {"1", "true", "yes", "on"}
_FALSE_TOKENS = {"0", "false", "no", "off"}


def _env_override(slug: str) -> Stage | None:
    """Read ``APP_STAGE_{SLUG}`` — the per-deploy escape hatch.

    Lets a stage be flipped without a deploy (the ``COMPOSIO_DRIVER_ENABLED``
    idiom), which is what makes an internal app testable on a real deployment
    without shipping it to everyone. Slug hyphens become underscores:
    ``workspace-settings`` → ``APP_STAGE_WORKSPACE_SETTINGS``.

    An unrecognized value is IGNORED rather than guessed. A typo'd stage name
    silently un-hiding an app is precisely the incorrect-success this file
    exists to prevent, so the declared stage wins and the override is dropped.
    """
    raw = os.getenv(f"APP_STAGE_{slug.replace('-', '_').upper()}")
    if raw is None:
        return None
    token = raw.strip().lower()
    if token in STAGES:
        return token  # type: ignore[return-value]
    # Booleans are accepted as a convenience at the two ends of the ladder —
    # `false` reads as "not a product", `true` as "fully unveiled".
    if token in _FALSE_TOKENS:
        return "internal"
    if token in _TRUE_TOKENS:
        return "primary"
    return None


def _implied_stage(entry: dict) -> Stage:
    """The stage a row that declares none is ALREADY at, read from its fields.

    The default cannot be a constant. A flat ``primary`` default would promote
    every ``search-only`` row (the config panes, the constitution mirrors,
    Images) into the launcher's Workspace group and pin ~27 surfaces to the
    Dock — inventing exposure while claiming to ship inert. So an undeclared
    row's stage is INFERRED from the pair it already carries, which makes the
    derivation an identity for every pre-ADR-592 row:

        pinned + primary tier  → ``primary``     (a fully unveiled app)
        primary tier, unpinned → ``beta``        (a tile, no Dock icon)
        anything else          → ``search-only`` (present, unpromoted)

    Only an APP needs to state a stage; the rest keep behaving exactly as they
    did, which is the ADR-375 D4 rule (a seam that changes nothing on arrival).
    """
    tier = entry.get("launcher_tier")
    if tier == "primary":
        return "primary" if entry.get("default_pinned") else "beta"
    return "search-only"


def resolve_stage(entry: dict) -> Stage:
    """The stage this surface row is at, env override applied.

    Args:
        entry: a ``KERNEL_SURFACES`` row. A row with no ``stage`` key resolves
            to the stage its existing fields already imply (:func:`_implied_stage`),
            so rows that predate ADR-592 are unchanged.
    """
    declared = entry.get("stage")
    if declared not in STAGES:
        declared = _implied_stage(entry)
    return _env_override(entry.get("slug", "")) or declared  # type: ignore[return-value]


def is_exposed(entry: dict) -> bool:
    """Whether this surface reaches the served roster at all.

    False only for ``internal``. Every other stage is served — the difference
    between them is PROMOTION (tile, Dock icon), not existence.
    """
    return resolve_stage(entry) != "internal"


def launcher_tier_for(entry: dict) -> str | None:
    """The launcher tier DERIVED from the stage.

    Returns ``None`` for an internal app (it is not served, so it has no tier).
    A row may still pin its own ``launcher_tier`` — the config surfaces do
    (``workspace-config`` / ``system-config`` are placements, not stages) — and
    an explicit tier always wins. The stage only supplies a tier for rows that
    do not state one, which is every APP.
    """
    stage = resolve_stage(entry)
    if stage == "internal":
        return None
    explicit = entry.get("launcher_tier")
    if explicit and explicit not in ("primary", "search-only"):
        return explicit  # a placement, not a promotion rung — untouched
    return "primary" if stage in ("beta", "primary") else "search-only"


def is_default_pinned(entry: dict) -> bool:
    """Whether this app ships in the Dock — TRUE only at ``primary``.

    Derived rather than declared, which is what keeps
    ``test_adr297_phase1.py``'s coherence gate (``default_pinned`` == the
    primary tier, as a set) satisfied by construction instead of by hand. That
    gate stays: it now guards the derivation rather than a pair of hand-kept
    fields.

    Gated on the DERIVED tier, not the stage alone: a chrome or dormant row
    carries no tier, so it can never be pinned however its stage resolves —
    the ``chrome surfaces are not pinnable`` invariant (test_adr297_phase1.py)
    holds by construction rather than by remembering.
    """
    return resolve_stage(entry) == "primary" and launcher_tier_for(entry) == "primary"


__all__ = [
    "STAGES",
    "DEFAULT_STAGE",
    "Stage",
    "resolve_stage",
    "is_exposed",
    "launcher_tier_for",
    "is_default_pinned",
]
