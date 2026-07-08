# ADR-418: System-Agent Pane Purification — Freddie Owns Only Its Dials

**Status**: Accepted (2026-07-08, operator-ratified — "full dormant change, can write adr if warranted"). Doc-first with its code in the same pass; a single FE + registry + gate change pushed to main. The un-run tail of ADR-414 Phase F (the System-Agent settings surface caught up to ADR-414 D2's purification; the Home constitution-band recompose stays deferred per ADR-414 §9b).
**Date**: 2026-07-08
**Dimension**: Channel (Axiom 6 — where each agent's config lives in the shell) + Identity (Axiom 2 — the System Agent shown for what it structurally is)
**Relates to**: ADR-414 D2 (the steward's persona → kernel constants — this ADR is the FE consequence the ADR named but deferred), ADR-412 D5 (the System Agent group placement this amends), ADR-387 §6.4 (the roster-pane placement ADR-412 already reversed), ADR-312 D5 (the constitution band as slot #1 — identity/principles stay first-class), ADR-340 D5 (the constitution mirrors leave the launcher top level, doored from Home), ADR-348 (Expected Output the surface — made dormant here)
**Amends**: ADR-412 D5 (the System Agent group shrinks from 7 panes to 4; identity/principles/expected-output leave it), ADR-341/347 (the one-Settings-door pane placement — identity/principles re-home to the Constitution group, expected-output goes dormant), ADR-338 (the surface-registry parity pane set drops expected-output)

---

## 1. Context — a group that outlived its own purification

ADR-412 D5 (2026-07-06) re-homed five registry panes from the `/agents`
roster into a Workspace Settings **System Agent** group: Identity ·
Principles · Autonomy · Budget · Expected Output (+ the local Capabilities ·
Activity reads). That was correct *the day it shipped* — the panes were
"the agent's settings," and Freddie's inspection surface belongs on the
system layer, not the staff roster.

**ADR-414 (2026-07-07) purified Freddie one day later and the group never
caught up.** ADR-414 D2 ruled that the steward's identity, mandate, and
principles are **kernel constants** — deleted as seeded files; "`persona/`
ceases to be Freddie's home." What remains operator-tunable for the system
agent is **exactly two dials**: the witness dial (`_autonomy.yaml`) and the
budget allocation (`_budget.yaml`). Identity, Principles, and Expected
Output are the **hired Altitude-3 agent's** concerns (ADR-408 D2 / ADR-382 §3),
not the system agent's.

So the live surface asserted something ADR-414 had just made false: it
invited the operator to "author Freddie's persona" (the Identity pane's
copy) for an entity that structurally has no operator-authored persona. The
`useFreddiePersona` hook still read `persona/IDENTITY.md` as "Freddie's
persona" against the same retired path. This is not cosmetic — it
mis-teaches the altitude model the whole ADR-408/412/414 band exists to make
legible.

**The label itself was never the problem.** "System Agent" is the deliberate
group name (GLOSSARY v3.1, ADR-412 D5): the entity is *named* "Freddie" (its
chrome home, the rail, carries the proper noun — ADR-381 D1), the settings
door carries the *role*. Renaming the group "Freddie System Agent" would
break that convention and read redundantly. The defect was the group's
**membership**, not its name.

## 2. The three panes are not homogeneous

The audit surfaced that the three panes to remove from the System Agent
group have different natures — which is why they get different fates:

| Pane | Register | Doored from | Nature |
|---|---|---|---|
| **Identity** | `intent` | the **Home constitution band** (`ConstitutionLinks`) | a constitution mirror (ADR-312 D5), NOT Freddie's persona |
| **Principles** | `intent` | the **Home constitution band** | a constitution mirror |
| **Expected Output** | `os-config` | nothing (no band door) | a hired-agent contract pane (ADR-345/348) |

Identity and Principles are **constitution mirrors** — first-class kernel
surfaces the Home constitution band opens via `foregroundSurface` (ADR-340
D5). Making them fully dormant would break the band, and re-deriving that
band is *exactly* what ADR-414 §9b defers and sequences LAST ("the
constitution band's referent is gone… deferred"). Expected Output has no
other consumer.

## 3. Decisions

**D1 — The System Agent group shrinks to Freddie's actual surface.** The
group becomes **Autonomy · Budget · Capabilities · Activity** — the two
operator-tunable dials (ADR-414 D2) plus the two read-only legibility panes.
Identity, Principles, and Expected Output leave it.

**D2 — Identity + Principles re-home to the Constitution group** (they stay
`pane_of: workspace-settings`, `pane_group` changes System Agent →
Constitution, joining Mandate; register stays `intent`). The Home
constitution band is untouched — `foregroundSurface('identity' | 'principles')`
still resolves to the same door. This is faithful to ADR-312 D5 (the
constitution is first-class) and stops filing the constitution under a
persona the system agent doesn't have. Their pane bodies move from
`SystemAgentPanes` to the workspace-settings `renderPane` switch, beside
Mandate (Singular Implementation — one home per pane).

**D3 — Expected Output goes dormant.** It is the one pane with no other
consumer and a pure hired-agent identity. Its kernel registry row drops
`route` + `pane_of` + `pane_group` (becoming a routeless, non-navigable
dormant row), it leaves the FE allowlist (`KERNEL_SURFACE_SLUGS` + the
`KernelSurfaceSlug` union), and its `/expected-output` redirect stub is
neutralized. The surface returns when a hired agent's per-agent contract
pane is built (ADR-414 §9b / ADR-382 — the deferred Altitude-3 FE).

**D4 — The stale persona copy is corrected.** The Identity pane's
"Freddie's persona — who occupies the seat" copy and the `useFreddiePersona`
path-drift comments are corrected: post-ADR-414 the persona (when one
exists) is a hired agent's, read from `agents/{slug}/`; `persona/IDENTITY.md`
is the seat path a hire installs into, not "Freddie's."

**D5 — The Phase-F Reviewer-string leftover is fixed in the same pass**
(`WorkspaceContextOverlay.tsx`'s `'Reviewer not configured'` → agent
wording, matching its sibling branches). Same ADR-414 Phase-F debt class,
one commit.

## 4. What this does NOT do

- **No Home recompose.** The constitution band, its cold-start CTA, and the
  StandingBand/JudgmentTrail per-agent re-derivation stay deferred (ADR-414
  §9b) — identity/principles remain doored from Home exactly as before.
- **No per-agent surface build.** The Altitude-3 hired-agent config surfaces
  (where Identity/Principles/Expected Output live *for a hire*) stay
  ADR-382-deferred. Expected Output goes dormant, not relocated.
- **No label rename.** "System Agent" stays the group name (ADR-412 D5 /
  GLOSSARY canon). "Freddie" stays the entity name on the rail.
- **No backend behavior change.** The `_autonomy.yaml` / `_budget.yaml` /
  `_expected_output.yaml` substrate + the envelope reads are untouched; this
  is Channel-dimension placement only.

## 5. Gate updates

The pane-set + placement assertions in `test_adr338_surface_registry_parity`,
`test_adr340_p2_settings_fold`, `test_adr340_p3_launcher`,
`test_adr341_two_settings_doors`, `test_adr347_one_settings_door`, and
`test_adr412_chat_surface` are updated to the new state: the System Agent
group is the 4-pane set; identity/principles carry `pane_group: Constitution`;
expected-output is dropped from the pane set + the FE allowlist. The
three-way parity invariant (`navigable == allowlist`, `registry ==
allowlist − panes`) holds with expected-output removed from all three.
