# ADR-421: The Workspace Has No Constitution Surface — Remove Mandate/Identity/Principles

**Status**: Accepted (2026-07-08, operator-ratified — "remove all three from the workspace"; sequenced "surfaces now, Home stays"). Doc-first with its code in the same pass. Completes the surface removal ADR-419 held back: the workspace-level Constitution panes are removed; the Home-band constitution recompose stays deferred (ADR-414 §9b).
**Date**: 2026-07-08
**Dimension**: Channel (Axiom 6 — the surfaces removed) + Identity (Axiom 2 — whose constitution it is)
**Relates to**: ADR-419 (made the panes judgment-home-aware as an interim + built the per-agent surface — this ADR removes the workspace surface it kept), ADR-418 (the sibling System Agent purification), ADR-414 D6 (the governance re-allocation — this is its endpoint for the constitution), ADR-414 §9b (the deferred Home recompose — kept deferred), ADR-382 (the Altitude-3 per-agent surface — its constitution slice)
**Amends/Supersedes**: ADR-419 (the workspace Constitution panes stop being home-aware mirrors and are removed), ADR-418 (the Constitution group it created is deleted), ADR-341/312 D5 (the Home constitution band's mandate/identity/principles link trio is removed; the mandate hero read survives until §9b), ADR-207 (the workspace-level "Primary Action" mandate framing is retired — a Primary Action is a hired agent's)

---

## 1. Context — the operator saw a steward mandate at the workspace altitude

ADR-419 established (with receipts) that mandate/identity/principles are
per-agent, not workspace-level — but it kept the workspace panes resolvable
(home-aware mirrors) because the Home constitution band doored into them, and
removing them touched the deferred Home recompose.

The operator then observed the exact confusion the interim left: on a
pre-genesis workspace, the **Mandate pane rendered the STEWARD's kernel-default
mandate** ("Steward this workspace's substrate…") under the heading "What this
workspace is running toward" — conflating three distinct things (the steward's
kernel purpose, an optional workspace charter, and a hired agent's operation
mandate) into one workspace-root pane. The interim mirror was still lying about
altitude.

A first-principles re-examination of the **file directory + intent** resolved
the question the interim deferred:

| File | Workspace-level? | Why |
|---|---|---|
| `persona/IDENTITY.md` | **No** | Persona belongs to the steward (kernel constant, ADR-414 D2) or a hired agent (`agents/{slug}/`). A workspace has no persona of its own. |
| `persona/principles.md` | **No** | A judgment framework belongs to whoever holds the seat. Same. |
| `constitution/MANDATE.md` | **No** (operator ruling) | ADR-414 D6 preserved an "optional operator-authored charter," and `lane_runner` reads a workspace mandate as orientation — but the operator ruled even that is not a workspace-level *constitutional pane*; a mandate is a hired agent's declared intent. |

**Ruling: a workspace has no constitution of its own.** It holds files,
members, connections, and a balance. Mandate/Identity/Principles are removed
from every workspace-level surface.

## 2. Decisions

**D1 — Remove the workspace Constitution surface.** The `mandate` / `identity`
/ `principles` kernel surfaces go **dormant** (drop `route` + `pane_of` +
`pane_group` + `launcher_tier`; registry row survives for flat-search
knowledge, non-navigable). They leave the FE allowlist + type union (`desk.ts`).
The **Constitution pane group is deleted** from Workspace Settings; its three
`renderPane` cases + the `useConstitutionHome` resolver (ADR-419) are removed.

**D2 — Remove the Home-band constitution trio.** `HomeHeader`'s
`ConstitutionLinks` (the mandate/principles/identity mirror-link row) is
deleted. **The Home mandate HERO read survives** (the header still reads
`MANDATE.md` content via the home-bundle) — its re-derivation is the deferred
ADR-414 §9b Home recompose ("Home last"), out of scope here. But it now treats
a **steward-default mandate as empty** (the `yarnnn:steward-default` marker →
the honest empty state), so a pre-genesis workspace stops rendering the
steward's kernel text as its operation headline. The empty state is re-cut to
the commons ("This workspace is a commons… hire an agent"), off the
autonomy-first "Primary Action" framing.

**D3 — The per-agent constitution is the only home.** The mandate/persona/
principles for a hired agent render on the agent detail
(`AgentConstitutionBlock`, ADR-419, reading `agents/{slug}/`). The workspace
has none.

**D4 — Bookmark safety.** `/mandate`, `/identity`, `/principles` redirect stubs
survive but point to the **bare Settings door** (no dead `?pane=` param).

## 3. What survives untouched (deliberately)

- **Backend read paths + the `constitution/` + `persona/` directories.** The
  `MANDATE.md` / `IDENTITY.md` / `principles.md` substrate paths, their region
  locks, and every backend reader (`freddie_envelope`, `substrate_reapply`,
  `lane_runner`'s workspace-mandate orientation, `system.py`'s timezone parse)
  are unchanged — they tolerate absence and read whatever is (or isn't) on
  disk. This is a surface removal, not a substrate deletion; retiring the
  directories is a separate substrate decision.
- **The Home mandate hero.** Still reads `MANDATE.md` (marker-guarded). Its
  full re-derivation toward the commons is the deferred §9b Home pass.
- **The System Agent group** (Autonomy/Budget dials + Capabilities/Activity) —
  ADR-418, unchanged.
- **The `DEFAULT_STEWARD_*` constants** — the ADR-419-recorded doc/code gap is
  unchanged (they remain the envelope substitution).

## 4. Why remove rather than keep-and-fix-empty-state

The interim (ADR-419) kept the panes and made them home-aware; the operator's
observation showed that a *mirror at the wrong altitude still miscommunicates*
even when its content is correct — the frame ("What this workspace is running
toward") asserts a workspace-level constitution that does not exist. The clean
expression of the dry, multi-principal commons (ADR-373/414) is that the
workspace surface simply does not have these panes. The concepts have a
first-class home (the agent detail); duplicating them at the workspace root —
even honestly — reintroduces the altitude confusion this whole arc removes.

## 5. Gate updates

The pane-set / group / band / stub / allowlist assertions in
`test_adr338_surface_registry_parity`, `test_adr340_p2_settings_fold`,
`test_adr340_p3_launcher`, `test_adr341_two_settings_doors`, and
`test_adr412_chat_surface` are updated: the three slugs are dormant (no
pane_of, no route, off the allowlist); the Constitution group + the
`ConstitutionLinks` band trio are asserted GONE; the stubs redirect to the bare
Settings door; the per-agent `AgentConstitutionBlock` is asserted present. The
three-way parity invariant holds with all three out of navigable + allowlist +
pane set.
