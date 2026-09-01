# ADR-629: Full placement wears a beta badge

**Status**: Ratified 2026-09-01 (operator ruling: *"we make these actually
fully published with launcher and dock considered. (can just call them beta
or something, much like claude design)"*). Implemented same day.

**Amends** ADR-627 D3 (blogger's stage). **Supersedes** ADR-488's unveil hold
on IMAGES (an operator decision then; reversed by the operator now). **Builds
on** ADR-592 (stage is the one exposure declaration).

## Context

Blogger shipped at `beta` (tile, no Dock icon) and IMAGES has sat at
`search-only` since ADR-488 held its unveil for "polish parity." The operator
wants both desks **fully placed** — launcher tile AND a default Dock icon —
while still reading as early. The reference class is Claude Design: full
product placement, a small "Beta" tag beside the name.

That is two orthogonal facts, and ADR-592 already teaches the split:
**exposure** is the stage; a **tag** is presentation. Bending the stage
ladder so `beta` pins to the Dock would re-merge them — every future app
would get the Dock the moment it earned a tile.

## Decisions

### D1 — `badge`: a presentation-only field on the surface row

An optional `badge` string on a `KERNEL_SURFACES` row (`"beta"` today),
served with the roster and rendered by the shell beside the app's name
(launcher tile chip; Dock tooltip). It gates NOTHING — not exposure, not
tier, not pin, not any capability. A badge is what the member reads, never
what the kernel enforces; the moment it branches behavior it has become a
second stage field and violates ADR-592's one-declaration rule.

Removal is one deleted line when an app graduates. No gate counts badges —
the roster churns and a hand-kept count reads growth as a violation.

### D2 — blogger and images go `stage: primary`, wearing `badge: "beta"`

Full placement: tile + default Dock icon (derived, ADR-592). Both beings'
promotion (`is_promoted`) follows by derivation — Designer appears on
/agents the same edit, which is the ADR-602 D3 dividend working as designed.
`DEFAULT_KEPT_SURFACES` (the FE's asserted hand-copy of the derived pinned
set) gains both slugs; a curated Dock is untouched (the reseed fires only on
byte-equality — ADR-592's finding), so existing members meet the desks in
the launcher and pin by choice.

### D3 — ADR-488's hold is closed, not deleted

The hold ("unveil bar is polish parity") was a real decision and stays in
the record; the operator has now taken the other side of it with the badge
as the honesty mechanism — the desk says "beta" where ADR-488 said
"withhold." Blogger's ADR-627 D3 rationale updates the same way.

## Gate

Folded into `test_adr627_blogger_pairing.py` (stage/badge/pin assertions
re-anchored) + `test_adr592_app_stage.py`'s derived-pin identities, which
now cover two more primary rows by construction.
