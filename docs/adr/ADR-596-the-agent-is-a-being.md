# ADR-596: The agent is a being — authority, clock, and judgment live on grants, declarations, and gates

**Status**: Ratified 2026-08-24 (operator-aligned discourse, 2026-08-21→24). D4 implemented in this arc; D3 is ratified *direction*, implemented phase-by-phase by later ADRs.

## Context

Two audits collided and produced one finding:

1. **The word "Agent" has drifted into four live senses**: the steward (Freddie — persona-bearing, standing intent, its own wake/prompt/model stack), the kernel colleagues (ADR-460 — Thinker/Researcher/Designer + postures), member-authored colleagues (`agents/{slug}/_agent.yaml`), and external principals ("External Agents" in Channels). GLOSSARY still defined only the first, retracted sense.

2. **Authority is currently distributed by species, which contradicts our own axiom.** ADR-405: permission is a **grant**, never a species rule. Yet clock + judgment are held by exactly one species-instance (the steward) and are *unrepresentable* for every other agent (the ADR-460 D3.a cliff). The cliff was the right scaffolding while the alternative was authority-through-unguarded-YAML; it is not the axiomatic end-state.

The steward's history explains the shape: Freddie was originally conceived as the omniscient, all-around agent. That conception is retracted, but its **bespoke vertical stack survives**: own prompt layer (`freddie_agent.py`), own model selection (`model_selection.py`), own execution path (wake sources → queue → drainer), own attribution prefix, own surface (the shell drawer) — running in parallel with the lane architecture every other agent uses. The member today faces two chat doors with two different species behind them.

## D1 — An agent is a being. There are no special agents.

**Agent = identity ⊕ character ⊕ engine.** Universally, for every species of principal. An agent row or manifest carries identity facts only — never authority, never reach, never a clock. The ADR-460 D3.a cliff survives *verbatim* at this layer (no authority-shaped field on any being, ever), but it is restated as a positive law:

> **Authority attaches to relations and declarations, never to beings. It is granted, audited, and revocable — and it is enforced by kernel gates, not by what any file says.**

Three things are *not* agents, and dissolution must not blur them:

- **Machinery** — kernel code executing unconditionally (`system:` attribution). It has no dossier, no grants, no hiring; it is trusted because it is reviewed *as code*. It may wear a character's costume for display (the strings writer resolving Keeper's model + posture while attributing `system:strings` is the canonical form).
- **The human root of the grant chain.** Every grant chains to a workspace owner, and owners are persons — not because the OS cares about species (it does not), but because liability terminates outside the OS. This is the world's constraint, named here so it is never mistaken for a species rule.
- **Gates** — chokepoint code, fail closed (the ADR-563 shape). Policy may be declared in substrate; enforcement is never substrate.

## D2 — The four-fact housing rule

Where each fact of an empowered agent lives, with the boundary drawn by *who enforces*, not *where it displays*:

| Fact | Constrains | Home | Rule |
|---|---|---|---|
| **Identity** (name, character, engine, skills) | nobody | `agents/{slug}/` in workspace substrate | Fully member-authored; discovery, never registration (ADR-449). |
| **Reach** (what it may touch) | the agent itself | `principal_grants`, kernel-held | Never a file the constrained principal can author. A legible mirror in substrate is display, not enforcement. |
| **Clock** (when it fires unattended) | the wallet | Declarations in substrate (`_recurrences.yaml`, `_string.yaml`, hooks); kernel materializes the index | File-first is proven safe because spend is gated independently (budget machinery, balance hard-stop). |
| **Judgment** (how far decisions bind) | the agent + the commons | Policy files (ceilings, dials) with a **gated write path**; verdicts + track record are machinery-written substrate (the agent's dossier) | The ADR-293 lock-set is the precedent; the dossier is what grants widen against. |

The one-line test for any future fact: **whoever a fact constrains must not be its unguarded author of record.**

## D3 — The steward dissolves (ratified direction; phased)

"Freddie" is three fused things with three different fates:

1. **Kernel machinery** (budget enforcement, wake plumbing, genesis, balance audit) → reclassified as machinery, `system:` attributed. Not an agent; needs no persona.
2. **The review function** → a **policy declaration + a grant**: "consequential acts above ceiling X require a verdict from a principal holding the review grant," enforced by a code gate. The verdict-giver is *any principal* — a kernel character, a member's named colleague, or the operator themself. The seat≠occupant construction (ADR-315) is honored as the scaffolding that kept the reviewer canon coherent while there was exactly one judgment-holder; in a multi-principal commons it reduces to grant + policy + gate + dossier, and no seat-noun survives.
3. **The persona and voice** → dissolve. The shell drawer becomes an ordinary lane with a cast (one chat door, not two); pure genesis (ADR-414 D4) means Freddie does not survive even as a seeded default colleague — the kernel character floor is the default population. The `freddie:` attribution prefix becomes data-compat, display-resolved (the reviewer→freddie rename precedent, run one final hop).

**Phase order** (each phase its own ADR, gate-by-gate, falsifier-first): (a) machinery reclassification; (b) one chat door; (c) declarations name their executor character; (d) review = grant + policy declaration; (e) the prompt-layer/runner merge **last** — every protection currently living in the steward's prose frame moves into a code gate *before* the stack it rides in is deleted. Prose is not permission, and prose is not protection.

## D4 — The clock gets a home timezone (IMPLEMENTED by this ADR)

The first shipped clause, because it is a standalone defect: the scheduling path resolved "the user's timezone" by **regex-parsing the prose file** `persona/IDENTITY.md` (`schedule_utils.get_user_timezone`), silently defaulting to UTC — a machine fact read from a never-machine-parsed doc, violating ADR-254's own format discipline.

Now:

- **The workspace declares a home timezone** — `workspaces.timezone` (IANA name, nullable; NULL = not yet declared, scheduling uses UTC). Migration 247. Set at Workspace Settings → General, owner-gated by the same RLS UPDATE policy as name/icon. The fossil `digest_*` columns and `get_workspaces_due_for_digest` (migration 003, zero readers) are dropped in the same migration.
- **Shared clocks resolve against the workspace's home timezone**, because "the Monday digest" is a fact about the commons, not about whoever authored the YAML. `get_user_timezone` is renamed **`get_workspace_timezone`** — the old name asserted a semantic the function no longer has — and reads the column through `effective_workspace_id`. The prose path is deleted, not shimmed.
- Store IANA names, never offsets; compute in-tz then UTC (unchanged downstream math); DST edge policy stays decided once in kernel scheduling code.
- A `timezone:` line in a member's IDENTITY.md becomes what it always looked like: prose about a person. Nothing machine-reads it.

**Deferred, deliberately** (named so they are not re-discovered): per-principal timezone (display + personal-scope declarations); per-declaration explicit `tz:` on recurrence entries (rides D3 phase c, the executor-naming widening of the one flat list — ADR-261's consolidation is not reopened); genesis asking the timezone question (the FE seeds the selector from the browser instead).

## Also deferred from this arc

- **Bound-lane resident derived at turn time** (the fix for stale `lane_meta["agent"]` showing engine labels in Studio / the wrong colleague in Strings): correct by this ADR's own logic — the resident is a fact about the app — but deferred to avoid colliding with the active Strings arc (ADR-595). Owed to D3 phase (b) or its own commit.
- `FreddieAboutPanel` / `FreddieActivityPanel` had zero consumers and are deleted in this arc (cleanup, not dissolution).

## Consequences

- GLOSSARY's "Agent" entry is rewritten to this taxonomy (being · machinery · grant · declaration · gate · dossier); the persona-bearing-judgment-entity definition is marked historical.
- Future "should agent X be able to Y?" questions decompose mechanically: identity → its folder; reach → a grant; unattended → a declaration; consequential → the gate + its policy. A proposal that answers with a new species, a new seat, or a new authority field on a being is wrong by construction.
- Gate: `api/test_adr596_workspace_timezone.py` (D4). D3 phases carry their own gates as they land.
