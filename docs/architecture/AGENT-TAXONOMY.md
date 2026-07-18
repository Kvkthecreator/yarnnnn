# Agent Taxonomy — the axes YARNNN has classified agents on, and the invariant

> **Status**: Reference (hardened from the 2026-07-16 research). This is the durable companion to the two analysis docs; those record the *investigation*, this records the *conclusion* as canon.
> **Sources**: `docs/analysis/what-kind-of-agent-the-taxonomy-that-keeps-dissolving-2026-07-16.md` (the dissolution meta-story) + the concrete-catalogue research (this doc's §2). Every name below is verbatim from the ADR record with an era anchor.
> **Load-bearing for**: any future agent-type decision. Read this before proposing a new agent, a new role, or a new "kind" — the odds are the axis has been tried.

---

## 1. The one thing to take away

**YARNNN has classified agents on at least SIX different axes across its history, and the recurring failure was never picking the wrong *set* of kinds — it was picking the wrong *axis* to have kinds on.** Each axis produced a plausible roster; each was superseded when the axis itself proved to be a conflation. The invariant the codebase converged on, twice independently, is:

> **An agent is typed by ONE axis — the *reason a member reaches for it* (a verb: think / read / pressure-test / make) — and nothing else. Modality, output shape, platform, destination, and persona are all facts that live *inside* an agent or *beside* it, never axes the roster is cut on. The one boundary that is not a type at all is consequential authority, which lives on the ADR-307 gate.**

Everything below is the evidence for that sentence.

## 2. The six axes, each with the roster it produced

Every era answered a *different question* about what an agent fundamentally is. That is the real finding — not that the rosters changed, but that the **question** changed six times.

### Axis 1 — OUTPUT SHAPE ("what document comes out?") — ADR-019→082
The original 27 types (consolidated 27→8 at ADR-082). Typed by the artifact produced.
`Status Report · Research Brief · Stakeholder Update · Meeting Summary · Board Update · One-on-One Prep · Performance Self-Assessment · Newsletter Section · Changelog · Client Proposal · Inbox Summary · Reply Draft · Follow-up Tracker · Thread Summary · Weekly Status · Project Brief · Cross-Platform Digest · Activity Summary · Meeting Prep · Weekly Calendar Preview · Deep Research · Daily Strategy Reflection · Intelligence Brief` → the 8 survivors: `slack_channel_digest · gmail_inbox_brief · notion_page_summary · weekly_calendar_preview · meeting_prep · status_report · research_brief · custom`.
**Why it failed**: the type name encoded platform + temporal pattern + output at once (`slack_channel_digest` = Slack + recurring + digest). A conflation of three things wearing one name.

### Axis 2 — PLATFORM SOURCE ("where does it read from?") — ADR-035, ADR-207
`slack_channel_digest · slack_standup · gmail_inbox_brief · notion_page_summary` … and the bots: `slack_bot · notion_bot · github_bot · commerce_bot · trading_bot`.
**Why it failed**: platform is a *connection*, not an identity. Deleted as agent rows (ADR-207); became capability-gating keyed on `platform_connections`.

### Axis 3 — DELIVERY DESTINATION ("where does it send?") — ADR-028
> *"**Agent** = Commitment to deliver something to a destination on a schedule. **Destination** = First-class part of the agent definition."* (ADR-028)
**Why it failed**: destination is a *channel* (Axiom 6), not a kind. It became a task property, never an agent type. Named here because it is the most-forgotten axis — an agent-typed-by-where-it-sends was a real proposal.

### Axis 4 — COGNITIVE FUNCTION ("what work does it do?") — ADR-109→176
The longest-lived axis, and the one that resolved *first*.
- ADR-109 Role: `digest · prepare · monitor · research · synthesize · orchestrate · act`
- ADR-130 v2 roster: `briefer · monitor · researcher · drafter · analyst · writer · planner · scout · pm`
- ADR-138 archetypes: `monitor · researcher · producer · operator`
- ADR-140 business-functions: `Research Agent · Content Agent · Marketing Agent · CRM Agent`
- **ADR-176 universal roles**: `researcher · analyst · writer · tracker · designer · reporting/thinking_partner`
**Why it (mostly) held**: ADR-188 proved the *roles* were the invariant but the *roster* was not — "universal roles, contextual application." Then ADR-272 collapsed all six to `designer` alone (the Specialist Survival Test), and ADR-205 made the rest a dispatch-time palette that "does not accumulate identity." The cognitive-function *vocabulary* survives; the *roster of pre-instantiated workers* did not.

### Axis 5 — JUDGMENT PERSONA ("whose judgment does it hold?") — ADR-194→383
A different tier entirely — persona-bearing seats, not member hands.
- **Shipped/durable**: `Reviewer` (the judgment seat) · `Freddie` (the Rung-1 steward, converged occupant)
- **Named but NEVER shipped**: `Auditor · Advocate · Custodian` (future systemic judgment archetypes — placeholders across canon, none ever registered)
- **The occupant personas** a seat can embody: `Simons · Buffett · Deming` + operator-authored
- **The program hires** (Rung-2, ADR-382/383): `alpha-trader · alpha-author · alpha-commerce · alpha-defi · alpha-prediction` — each overwrites a seat's IDENTITY.md, "same seat, different occupant."
**Why it is separate**: this axis types *judgment accountability*, gated by an exogenous track-record clock (ADR-380). It is orthogonal to the member-hands axes above — a persona agent is a *different tier*, not a different role.

### Axis 6 — REASON / VERB ("why do I reach for this colleague?") — ADR-460, current
`Sonnet` (think) · `Scout` (read) · `Critic` (pressure-test) · `Designer` (make). Plus member-named instances (`Lisa` based_on a kernel reason).
**Why it holds where the others didn't**: it is Axis 4's invariant (cognitive function) re-cut into the layman's question — *"who do I want to work with?"* rather than *"what worker contributes what?"* — AND it ships with the structural ratchet the earlier eras lacked: `AGENT_ROW_KEYS` has no authority field, `test_agent_registry.py` fails if one is added (ADR-460 D3.a). The vocabulary is fixed; the roster is the vocabulary; there is nothing to re-instantiate and nothing to ladder.

## 3. The two arcs that prove the invariant

The dissolution ran on two independent tracks and landed identically — which is why the endpoint is trustworthy rather than just the latest swing:

- **The work axis** (092→093→109→138→140→176→188→205) resolved at ADR-188's bisected Hospital Principle: *"correct about roles… incorrect about roster size"* — a fixed **vocabulary**, never a fixed **roster**.
- **The judgment axis** (194→216→315→381→383→408→460) resolved at ADR-383's *"same KIND of construct, differing only in file CONTENT"* → ADR-460's *"configuration is a vector, not a rung."*

The codebase named its own oscillation in-canon, three years before the resolution — **ADR-138:29**: *"We're stuck in the middle… Every session adds project complexity; the next session proposes simplifying it. **This oscillation wastes effort.**"*

## 4. The classification rule (what to do with a new agent idea)

When someone proposes a new agent, run it through this before building:

| The idea is really about… | …which is axis | Verdict |
|---|---|---|
| a new output ("a deck agent", "a report agent") | Output shape (Axis 1) | ❌ Modality lives *inside* an agent, not as one. A deck is something **Designer makes**. |
| a new platform ("a Slack agent") | Platform source (Axis 2) | ❌ Platform is a *connection*, capability-gated. Not a kind. |
| a new place it delivers to | Destination (Axis 3) | ❌ Channel, a task property. Not a kind. |
| a new **reason a member reaches for a colleague** | Reason/verb (Axis 6) | ✅ **The only valid axis for a base agent.** And only if a member's unmet reach names it. |
| a new **judgment accountability** | Persona (Axis 5) | ⚠️ A different **tier** (systemic seat or hired persona), gated by the ADR-380 clock — not a base-agent addition. |
| the ability to take consequential external action | — | ⛔ Not a type at all. The ADR-307 gate. Unrepresentable in the registry (D3.a). |

**The single question for a base agent**: *"Is this a new VERB — a distinct reason a member addresses a colleague — or is it a modality/output/platform of an existing verb?"* If the latter, it is a capability of an existing agent, never a new one.

## 5. What this makes the base set

The base ("scaffolding") agents are the **verbs**, and every modality is a capability *within* a verb:

- **think** (Sonnet) — reasoning, judgment, hard calls
- **read** (Scout) — search the workspace + web, with sources
- **pressure-test** (Critic) — find the hole
- **make** (Designer) — produce the artifact, *in every modality*: prose, decks, docs, and — when it returns rented (ADR-417 §2a) — charts and images

**"Image maker" is not a base agent.** It is a *modality of `make`*, i.e. a capability that belongs to Designer. Typing it as its own agent would be Axis-1 thinking (output shape) — the very first axis the codebase abandoned. (Note: image generation does not currently *exist* — ADR-417 retired the render service; it returns as a rented capability under the ADR-463 §3 resolver, attached to `make`, never as a fifth character.)

The open question the vocabulary has never answered from first principles: **is the set of verbs complete at four?** ADR-176 asserted six cognitive roles; the current registry ships four reasons. Neither derived the set. The rule for closing it: a fifth agent is warranted **only** when a member's unmet reach names a fifth VERB — not a fifth engine, not a fifth persona, not a fifth output format.

## 6. One-line statement

**YARNNN typed agents on six different axes — output shape, platform, destination, cognitive function, judgment persona, and reason/verb — and the durable lesson is that only the last is a valid axis for a base agent: a base agent is a VERB (think/read/pressure-test/make), every modality (prose, decks, images) is a capability *within* a verb, persona is a different *tier*, and consequential authority is not a type at all but the ADR-307 gate — so the roster grows by depth (deeper hands for the verbs) and adds a character only when a member's unmet reach names a genuinely new verb.**
