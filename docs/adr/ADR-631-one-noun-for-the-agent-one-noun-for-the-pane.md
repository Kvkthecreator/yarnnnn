# ADR-631 — One noun for the agent, one noun for the pane

> **Status**: **Accepted + Implemented** (2026-09-02). Operator ruling in the skills discourse: *"being should now be upgraded to agents… desk should now be upgraded to something app-specific… ok that seat is now gone."* The third clause is answered by ADR-632's audit, not here.
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — what the noun for a hand is) with a **Channel** consequence (the lanes envelope serves one roster). No Purpose change, no Mechanism change: the same register, the same residency, the same doors.
> **Amends**: ADR-596 (the transitional noun *being* is retired; every decision stands verbatim under *agent*) · ADR-601 D4 (`homes` → `apps`, one served relation) · ADR-624 D4 (`desks` folded into `apps`) · ADR-614 D1 / ADR-625 (the chat doors read the one roster) · ADR-385 (the "External Agents" wording → *connected principals*).
> **Preserves**: ADR-460 D3.a (the cliff — no authority-shaped field on an agent), ADR-600 (one register; `offered` is a field), ADR-467 D1 (an app pins one resident), ADR-522/606 (the pane frame at one kernel site).

## 1. Context — three words for the surface, two for the hand, one roster served twice

**The hand.** ADR-596 introduced *being* to break four drifted senses of "agent" while the taxonomy settled. The taxonomy is now gated (identity ⊕ character ⊕ engine; authority on grants, declarations and gates; one register). The code never adopted the word: the register is `agents_registry.AGENTS`, the home is `agents/{slug}/`, the pane is `/agents`, the caller class is `agent`, the attribution prefix is `agent:`. *Being* lived in canon and in five identifiers (`beings` on the lanes envelope, `_beings_payload`, `BeingIcon`, one FE type, one gate name). Every code/canon boundary paid a translation.

Three candidate reasons to keep the second word were tested and failed:

- *"agent" implies autonomy and authority in the industry.* The definition carries the refusal; the word need not. ADR-464 §3 already proved prose is not permission.
- *collision with external principals.* ADR-385's Channels pane called MCP / foreign-LLM principals "External Agents". Real, but the smaller residue: Channels was deleted by ADR-415, and what remained was two docstrings and a GLOSSARY entry. They now say **connected principal**. *Principal* stays the species-agnostic noun; *agent* is a principal yarnnn runs a character and engine for; a human is a principal with no engine.
- *humans.* Principal over human, agent, and connected principal needs no fourth word.

**The surface.** Three words named where a member uses an app. Counted in non-test kernel code before this ADR: `pane` 563 hits, `desk` 309, `homes` 56. The posture builders were `studio_pane_posture`, `text_pane_posture`, `_strings_pane_posture` — and, alone, `build_strings_desk_posture`. The lanes envelope served the agent↔app relation **three times on one row** (`homes` slugs, `home_titles` titles, `desks` rich rows) and served the roster **twice** (`agents` = the `offered` subset, empty since ADR-599 D1; `beings` = everyone). Every FE consumer read `beings` and held `agents` as an always-empty fallback.

A compound ("app-desk", "app-resident") was refused: a compound noun is the symptom that the base noun was ambiguous, and the fix is the base.

## 2. Decisions

### D1 — The hand is an *agent*

*Being* is retired. ADR-596 D1's definition stands verbatim under *agent*: **identity ⊕ character ⊕ engine, and nothing else**. GLOSSARY marks *Being* historical. Ratified ADRs keep the word as a record of their time; live canon, code, and surfaces say *agent*. The one collision is resolved on the other side: MCP / foreign-LLM principals are **connected principals**.

### D2 — The surface is a *pane*; the row is an *app*; the relation is served once as `apps`

- **app** — the kernel row (`register_app`), the thing a declaration names (ADR-603 D2) and an agent serves (ADR-601 D1).
- **pane** — where a member uses an app: the bound lane, the artifact or maintained file, the rail, the housing. Already the canon word since ADR-522/606 and the majority word in kernel code.
- **resident** — unchanged: the agent met in an app's pane.

*Desk* is retired. `apps_for_agent(slug)` replaces `homes_for_agent` + `home_titles_for_agent` + `desks_for_agent`; the envelope serves `apps` (slug · title · icon_key · route) and nothing else for the relation. *Desk* survives only as ESSENCE's product metaphor ("the desk is the product"), which names the felt surface and is not a kernel noun.

### D3 — One roster

The lanes envelope's `beings` key becomes `agents`, and the `offered`-only `agents` roster beside it is **deleted** with `list_agents()`. `offered` is a FIELD on every row (ADR-600 D2); a door that lists candidates filters it (ADR-625 already does). Two keys for one roster was a second key with no reader.

## 3. What shipped

- **API**: `agents_registry.apps_for_agent` (one relation) · `list_agents` deleted · `routes/lanes.py::_agents_payload` + envelope `agents` (one roster) · `strings.build_strings_pane_posture` + `_STANDING_PANE_FRAME` · docstrings and comments swept for the canon nouns in the modules that name the concept.
- **Web**: `components/pane/{PaneHousing,PaneActivityRail}.tsx` (was `desk/Desk*`) · `types/surface.ts` (was `types/desk.ts`; `DeskSurface` → `NarrativeSurface`) · `agents/AgentIcon.tsx` · the four roster consumers read `agents` and hold no second roster · `AgentsSurface` renders `apps` chips from the one relation.
- **Canon**: GLOSSARY (Agent recut; Being historical; Pane added; Resident/Colleague/Supervisor/Standing declaration re-worded), lane-frame.md, LAYER-MAPPING, connectors, intake-pipeline, primitives-matrix, CLAUDE.md. ADR-LEDGER keeps historical vocabulary in the entries of earlier ADRs, by design.
- **Gate**: `api/test_adr631_vocabulary.py` — the envelope carries `agents` with `apps` and no `beings` / `homes` / `desks`; no `list_agents`; no `*_desk_*` posture; no `Desk*` component or `BeingIcon` in web; the GLOSSARY defines Pane and marks Being historical. Pins the DEFINITION where it can, the absence of the retired spelling where it must.

## 4. Not done here

- The **seat** (Reviewer / steward) vocabulary retires with its machinery under ADR-632, whose audit found the stack dormant but still wired.
- Operator probes under `api/scripts/` and the `tp/` transcript components keep their wording; they leave with the seat.
