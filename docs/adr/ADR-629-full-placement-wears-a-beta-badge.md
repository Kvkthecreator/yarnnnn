# ADR-629: Full placement wears a beta badge

**Status**: Ratified 2026-09-01 (operator ruling: *"we make these actually
fully published with launcher and dock considered. (can just call them beta
or something, much like claude design)"*). Implemented same day.
**Amended 2026-09-12 — D4**: the product wears one too, from one declaration.

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

### D4 — The product wears one too, from one declaration (2026-09-12)

**Prompted by** the operator's sister, shown the site before a friends-and-
family round: *"we should have a badge showing it's explicitly a beta."* The
audit found no product-level marker on any surface a friend walks — landing,
sign-in, invite, the shared-link page, the top bar, the account menu — while
the only "beta" on the public site described Freddie, a seat ADR-632 deleted,
behind a `/freddie` link with no route. D1 had given the fact a home at APP
grain; the product had none.

**The stage is one field, `BRAND.stage` in `web/lib/metadata.ts`**, beside
the name and tagline — optional on the type, so graduation is deleting the
line and it compiles. Presentation only under D1's rule: nothing routes,
gates or prices on it. Not an env var (a second axis that drifts across
Vercel environments); not a server field (nothing on the server reads it,
and the landing page is static). `STAGE_NOTICE` derives the one sentence.

**Two grains, two shapes.** The D1 chip is a *discriminator*: in the
launcher it says "these two are behind the other six," and that reading
depends on the other rows being bare. The product stage is a *constant*: on
every page, every visit, until graduation. The same chip at both grains
cancels — a parent wearing BETA makes Blogger's chip read as "beta inside a
beta" — and the reference class agrees (Claude Design tags the product, not
its features; GitHub tags features, not the product; nobody runs both at one
volume). So the product annotation is *quiet*: lowercase, the body sans, at
half the mark's ink, beside the mark. Emphasis is spent once, where
expectations form — one sentence under "Create your account" — not on every
page.

**One renderer.** The Pacifico mark was hand-spelled in fourteen files, the
ADR-592 failure class (a hand-kept set beside a derived truth). `Wordmark`
(`web/components/shared/Wordmark.tsx`) is now the only place `font-brand`
renders; the landing hero passes `bare`, the one exemption, because the
canon lock (CANON-LOCK-2026-07-30 §1) fixes that sequence verbatim and the
header above it already carries the stage. `SurfaceIdentityHeader.brandTitle`
— a second Pacifico path with zero callers — is deleted.

**The door.** A stage annotation without a door is a label. The account menu
gains *Send feedback*, a plain link to the SAME Tally form the landing footer
opens (`FEEDBACK_FORM` in `web/lib/cta.ts`, the id spelled once), so a
visitor's and a member's report land together; the menu header also carries
the annotation, because the top bar hides the mark below `sm` and a phone is
where a family member looks. The door is permanent — the stage graduates,
not the door.

**Stale copy removed, not softened (ADR-561 D4).** The FAQ's "second set of
eyes (in beta)" entry and llms.txt's Freddie section + key-page line are
gone; the FAQ gains "Is yarnnn in beta?", derived from the stage. llms.txt's
"three verbs" bullet — `remember`/`recall`/`trace`, retired by ADR-543 — is
replaced by a sentence that points at the server's own `tools/list` rather
than copying the roster (the ADR-635 D9 rule, already applied to the
discovery card).

## Gate

D1–D3: folded into `test_adr627_blogger_pairing.py` (stage/badge/pin
assertions re-anchored) + `test_adr592_app_stage.py`'s derived-pin
identities, which now cover two more primary rows by construction.

D4: `test_adr629_the_product_wears_beta.py` — one home · one renderer · two
shapes (asserted both ways) · one form id · said once at the door · no
non-presentation reader.
