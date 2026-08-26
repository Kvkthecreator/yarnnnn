"""Standing declarations — the kernel concept behind standing work (ADR-603).

A **standing declaration** is a SUBJECT + a CONTRACT (what "true" means for it)
+ SOURCES + a SCHEDULE + the APP whose resident does the work — producing an
attributed revision, or an honest no-op.

WHY THIS MODULE IS THIN, AND MUST STAY THIN
It holds the RULE, not a second mechanism. Strings (ADR-569) is the first
instance and its machinery is unchanged: `_string.yaml` beside its subject,
`STRING_KIND`, its own parser and drain. Building a general engine before a
SECOND instance exists would abstract from one example, which is how the wrong
axis gets picked. What generalises today is D2 — the resolution rule — and
that is what lives here.

THE RULE (ADR-603 D2): A DECLARATION NAMES THE APP; THE AGENT IS DERIVED.
Deliberately inverting ADR-596 D3's phrasing ("declarations name their
executor"). ADR-601 made `editor` serve two desks, so a declaration naming the
AGENT is ambiguous about which craft it wants, while one naming `slides` or
`text` never is. Naming the app also means a re-pairing (ADR-602's
`slides → editor`) re-points every declaration with NO data move.

⚠️ A DECLARATION IS AUTHORITY OVER WORK, NEVER OVER A BEING (ADR-603 D3).
Supervisor authors declarations; it never commands colleagues. A declaration
carries an `app`, and the resident arrives because the app derives it — there
is no field here naming an agent, and there must never be one. That is
ADR-596 D2 ("authority attaches to relations and declarations, never to
beings") and the ADR-460 D3.a cliff, one layer out from the registry.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

#: The keys a standing declaration may carry, whatever its kind. `app` is the
#: executor field — an APP slug, never an agent slug (the D2 rule, as a
#: whitelist rather than as prose). No key here names a being, ever.
DECLARATION_KEYS = frozenset(
    {"subject", "contract", "sources", "schedule", "app", "paused", "options"}
)


def resident_for_declaration(app: Optional[str]) -> Optional[str]:
    """The being that will do this declaration's WORK, or None. Pure-ish.

    ADR-603 D2 — resolved through the app's own registration at READ time
    (the ADR-597 D1 precedence, reused rather than reinvented), so a
    re-pairing follows every declaration with no data move.

    ADR-604 D2 deepened the derivation by one field: a desk has a VOICE
    (`resident`) and its standing work has an EXECUTOR (`standing_executor`,
    else the resident). "The being that will do this declaration's work" is
    the EXECUTOR. ADR-610 dissolved the one being that made these differ, so
    a declaration on `strings` derives Supervisor — the same being the desk's
    conversation runs through. The rule itself is unchanged: a declaration
    names the APP, never a being.

    Returns None for an unregistered app rather than a plausible default: the
    ADR-548 lesson, that a fallback degrading to a plausible value hides the
    bug it should surface. The caller decides what an unnamed executor means.
    """
    if not app:
        return None
    import services.apps  # noqa: F401  (registration side-effect — ADR-562)
    from services.authoring import standing_executor_for_app

    return standing_executor_for_app(app)


__all__ = ["DECLARATION_KEYS", "resident_for_declaration"]
