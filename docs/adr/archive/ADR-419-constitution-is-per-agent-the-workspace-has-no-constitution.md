# ADR-419: Constitution Is Per-Agent — The Workspace Has No Constitution of Its Own

**Status**: Accepted (2026-07-08, operator-ratified — "do the full build, but defer home"). Doc-first with its code in the same pass. Executes the workspace-facing half of ADR-414 D6's governance re-allocation for the constitution concept (mandate/identity/principles); the Home constitution-band recompose stays deferred per ADR-414 §9b.
**Date**: 2026-07-08
**Dimension**: Identity (Axiom 2 — whose constitution it is) + Channel (Axiom 6 — where it is surfaced) + Substrate (Axiom 1 — what a bare workspace actually holds)
**Relates to**: ADR-414 D6 (the governance re-allocation table — this ADR implements its "Mandate, persona (IDENTITY/principles) → per-agent" row on the FE), ADR-414 D2 (steward constitution → kernel constants), ADR-414 §9b (the deferred Home recompose — kept deferred here), ADR-418 (the System Agent pane purification — this is its sibling, one altitude up), ADR-382 (the Altitude-3 persona-agent layer — the per-agent constitution surface is its first FE), ADR-207/320 D4 (the MANDATE hard-gate — already retired at workspace level by ADR-414 D4; this ADR corrects the stale docs that still claim it)
**Amends**: ADR-418 (the workspace Constitution group panes become judgment-home-aware mirrors, not the primary home), ADR-207 (the "Primary Action" / autonomy-first mandate framing is scoped to a hired agent, not the workspace)

---

## 1. Context — a constitution at the wrong altitude

ADR-418 fixed the System Agent group by removing Identity/Principles/Expected
Output (Freddie has no persona post ADR-414 D2). It re-homed Identity +
Principles to the **workspace-level Constitution group** as an interim. This
ADR asks the next question the operator raised: *are Mandate / Identity /
Principles even workspace-level concepts anymore?*

The audit (2026-07-08, receipts below) says **no**:

- **Genesis seeds none of them.** `initialize_workspace` Phase 2 seeds only
  the two governance dials (`_budget.yaml`, `_autonomy.yaml`); MANDATE.md /
  IDENTITY.md / principles.md are in the deleted-from-seeding ledger. A bare
  workspace's `constitution/` and `persona/` are **empty**.
- **At runtime they are never workspace-level.** `freddie_envelope.py` keys on
  `resolve_judgment_home(user_id)`: when a program is hired, mandate/identity/
  principles read from `agents/{slug}/…` (*the agent's*); when bare, the
  envelope substitutes a **kernel steward constant** — never a workspace file.
- **ADR-414 D6 already ruled it.** The governance re-allocation table:
  *"Mandate, persona (IDENTITY/principles), expected-output — Was: workspace
  `constitution/` + `persona/` roots → Becomes: per-agent (`agents/{slug}/`
  homes for Altitude 3); the steward's versions → kernel constants."*

Yet the live FE still surfaced them under a workspace-root **"Constitution"**
group with autonomy-first, single-operator copy ("the single goal *this
workspace* is running toward — your **Primary Action**"). That is the
pre-ADR-414 one-judgment-seat world speaking at the workspace altitude, for a
workspace that structurally has no mandate. The move to the dry, agnostic,
multi-principal filesystem/commons (ADR-373/414) makes the mismatch acute: **a
workspace has grants, members, files, and a balance — not a constitution.**

## 2. Decisions

**D1 — The workspace has no constitution of its own.** Mandate, Identity, and
Principles are **per-agent** (a hired Altitude-3 agent's), or a **kernel
constant** (the steward's). This is the canon (ADR-414 D6) stated plainly. A
bare workspace is a *complete* product — the commons — not an "unconfigured"
or "standby" one.

**D2 — Build the per-agent constitution surface (the real home).** The agent
detail (`AgentContentView`) gains an `AgentConstitutionBlock` rendering
`agents/{slug}/MANDATE.md` + `IDENTITY.md` + `principles.md` via the universal
`WorkspaceFileView` (the pattern the `AGENT.md` revision panel already uses).
This is the first-class home for these concepts — the first slice of the
ADR-382 Altitude-3 FE. Scoped to real Altitude-3 agents (hidden for
platform-bots, which have no persona).

**D3 — The workspace Constitution panes become judgment-home-aware mirrors.**
Because the Home constitution band (deferred, §9b) still doors into the
`mandate`/`identity`/`principles` panes, they stay resolvable — but they stop
lying about altitude:
- When a program is hired, they read the agent's home
  (`agents/{slug}/…`) — resolved FE-side from `getState().active_program_slug`
  (`useConstitutionHome`), which the server derives via `resolve_judgment_home`.
- When bare, they read the steward-era root (empty) and show an
  altitude-honest empty state: *"A workspace has none of its own — hire an
  agent to give it one."*
- The autonomy-first "Primary Action / the single goal this workspace runs
  toward" copy is scoped to a hired agent's mandate (where a Primary Action is
  the real ADR-207 schema), not asserted at the workspace level.
The `MandateCard` + `PrinciplesCard` gain an optional `path` prop (defaulting
to the workspace-root path, so every other caller is unchanged).

**D4 — The MANDATE hard-gate docs are corrected.** `workspace_paths.py`'s
docstring still claimed "the workspace cannot dispatch work until MANDATE.md +
IDENTITY.md + principles.md are non-skeleton" (ADR-320 D4 / ADR-207). That
gate was **retired at the workspace level by ADR-414 D4**; the docstring is
corrected to say so. (No code gate existed — this was doc-only drift.)

## 3. The DEFAULT_STEWARD_* doc-vs-code gap (recorded, not closed here)

ADR-414 §8's deletion ledger says `DEFAULT_STEWARD_MANDATE_MD` /
`DEFAULT_STEWARD_IDENTITY_MD` / `DEFAULT_STEWARD_PRINCIPLES_MD` + the
`STEWARD_DEFAULT_MARKER` machinery are "deleted." **They are not deleted** —
they live in `orchestration.py:738-830` and are load-bearing: `freddie_envelope.py`
imports them as the steward-wake substitution (the kernel constant that rides
the envelope when a bare workspace's files are absent). The Phase gates match
this reality (`test_adr414_phase_b` *requires* them in the envelope;
`test_adr414_phase_c` only bans them in `workspace_init` seeding). So the code
is internally consistent and gate-green, but the letter of §8 ("a survivor
found later is a bug") is contradicted: the constants **survived, relocated in
role** (seed → envelope substitution) rather than module. This is a
book-keeping reconciliation, not a bug — ADR-414 D2's intent ("the steward's
constitution is a kernel constant") is *satisfied* by these constants; only
their claimed deletion was wrong. Reconciling §8 (either delete-and-inline, or
amend the ledger to "relocated to the envelope substitution") is a separate
tidy, not blocking.

## 4. What this ADR does NOT do (deferred, deliberately)

- **No Home recompose.** The Home constitution band, its cold-start CTA, and
  the `home-bundle` read re-point stay deferred (ADR-414 §9b, "Home last"). The
  band still doors into the workspace panes, which is why D3 keeps them
  resolvable rather than deleting them. **Removing the workspace Constitution
  group entirely is the Home pass's job.**
- **No setup-bundle re-point.** `get_workspace_setup_bundle` still reads
  workspace-root paths; it feeds the `/setup` Sequence, its own surface pass.
  The FE panes don't depend on it (they self-resolve via `getState`).
- **No Altitude-3 runtime.** The per-agent constitution surface is read/render
  only; agent hiring, the trust clock, and per-agent write routing stay
  ADR-382-deferred.
- **No dead-code cleanup.** `WorkspaceSection.tsx` (unmounted since the ADR-244
  program surface moved to the Program pane) still carries "activate a program
  … the workspace is in standby" pre-ADR-414 copy; it renders nowhere, so it
  is left for a deletion pass rather than re-framed here.

## 5. Receipts

Genesis: `api/services/workspace_init.py:103-138` (only dials seeded), `:20-32`
(deletion ledger). Runtime: `api/services/freddie_envelope.py:305-372`
(judgment-home branch + kernel-constant substitution). Canon:
`docs/adr/ADR-414-…md:220` (D6 table). FE before: `MandateCard.tsx:187`
(workspace-level "Primary Action" copy). Constants: `orchestration.py:738-830`
(DEFAULT_STEWARD_* alive).
