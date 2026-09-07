# ADR-644 — One reach status: the agent and the member read the same structure

**Status**: Accepted + Implemented (2026-09-07, operator ruling: *"aligned in
full … agents and display should reference the same status … the dedicated
pane to edit permissions or connections settings happen elsewhere. I think
this is no different from existing connectors handled by Claude, ChatGPT."*)
**Date**: 2026-09-07
**Disposition** (the intake-pipeline.md §5 first-paragraph rule): no reach
mechanism is added or widened. This ADR changes HOW the three dispositions
are DESCRIBED — to the agent and to the member — from four independent
faces to one derived structure with two renderers.
**Dimension** (Axiom 0): **Mechanism** (Axiom 5 — what a turn holds) stated
once; **Channel** (Axiom 6 — where reach points) described once. No
Identity or Trigger change.
**Related**: ADR-535 (see ≠ reach; `list_integrations` is the binding
inventory) · ADR-585/615 (turn reach, the engine disclosure) · ADR-635 (the
precedent: `attached_surface` is ONE structure feeding the tools, the frame
and the settings pane) · ADR-628 (the member doors) · ADR-642 (Reach, the
surface that exposed the drift) · ADR-638 (name the THING) · ADR-467 D4
(three things must agree about which tools a turn has — this ADR extends the
agreement to what the turn is TOLD about them).
**Amends**: ADR-642 D5 (the derivation moves into the structure; the
sentence renderers replace `connector_does`) · ADR-585 D5 (the engine
disclosure is now rendered from the structure, same words) · the lane
frame's reach section (lane-frame.md §"Connector-reach section": generated,
never hand-written) · agent-composition.md §3.2.1's Reach row.
**Preserves**: ADR-535 D2 (the inventory is metadata only — never a
credential, never a provider call) · ADR-577 (an agent never holds a
credential; the enumeration read is allowlisted as enumeration) · ADR-594
D1 (no per-connection settings — consent, selection and aperture stay in
Settings; this ADR only READS) · ADR-628 D5 (no publish from chat).

---

## 1. Context — four faces, no structure

The first Reach click-pass (2026-09-07) put the member's face and the
agent's face on one screen. Reach said *"an agent's Slack post goes out only
through a proposal you approve"*; the editor, asked to send the open document
to Slack, said *"I cannot post — my Slack access is read-only."* The agent
was right. The census behind that disagreement:

| Face | Where | What it is |
|---|---|---|
| What the lane HOLDS | `turn_reach_tool_names` + `lane_tool_names` | the only structurally true face — tool definitions, invisible as a description |
| What the lane is TOLD | `lane_runner.build_lane_conventions`, the reach section | three hand-written branches, one per reach state, plus a sentence appended the same afternoon |
| What the agent finds at RUNTIME | the `list_integrations` tool result | platform + status per row; no reads, no writes, no doors — less than the member sees |
| What the MEMBER sees | `connector_does` → Connectors + Reach | prose derived from three sources; patched this morning to read the first face, which made it the fourth reader of a fact with no home |

ADR-635 already solved this for attached connectors: `attached_surface`
produces one structure per server, tool by tool with its mode, and that one
structure feeds the tool list, the frame paragraph (`frame_section`) and the
settings pane. The agent and the member see the same tools with the same
modes because there is nothing else to see. First-party connections predate
ADR-635 and were never brought onto it. That is the whole gap, and it is
also the industry model: a connector is a tool list with per-tool
permissions, shown identically in settings and to the model.

## 2. Decisions

### D1 — One structure per connection, derived, never stored

`services/reach_status.py` is the ONE home. `platform_reach(platform, …)`
derives the facts for one platform from the machinery that enacts each:

| Fact | Derived from |
|---|---|
| `captures` | `CONNECTOR_CAPTURE_BINDINGS[plat]["reads"]` — the capture binding's own statement |
| `reads` | `turn_reach_tool_names((plat,))` — the tool names a lane composes for this platform |
| `agent_writes` | `PLATFORM_TOOLS_BY_CAPABILITY["write_{plat}"]` ∩ the live surface, each with its mode (`propose` when `consequential_platform_family` gates it, else `direct`) |
| `member_doors` | `PUBLISH_DOORS[plat]` — the seam's own roster of member acts: verb · door · pane · what it takes |
| `reach_on` / `in_scope` | the turn's reach state (`resolve_turn_reach`), when a turn is asking |

`reach_status(rows, …)` applies it to the member's connection rows
(`connection_rows` — metadata only, account-scoped, the ADR-535 D2
boundary), adding target and status. Attached connectors keep ADR-635's
structure; the two are siblings under one rule, not one merged shape.

**A registry row is not a live path.** `agent_writes` is empty today for
every first-party platform, because no live loop composes a write tool; the
capability registry's `write_slack` row survives the deleted task pipeline
and is not consulted on its own. The day a write tool is composed, the fact
flips without anyone editing a sentence.

### D2 — Two renderers, zero prose of their own

- `describe(facts)` → `{reads, writes, chat, agents}` — the member face,
  served on the integrations LIST and the capture-signal drill-in, rendered
  by Connectors and Reach. It carries the ADR-585 D5 engine disclosure in
  the same words the gate anchors on.
- `frame_paragraph(status, member, …)` → the reach section of the lane
  frame. It states the turn's edge for all four reach states (ADR-535 D3's
  invariant: name the inventory tool, state the true edge, never deny a
  binding it can see) and then one line per connection: what it reads, what
  it can post (by proposal or not), and where it cannot — naming the
  member's door. Three hand-written branches and the appended sentence are
  DELETED; the paragraph is generated.
- The `list_integrations` tool returns the same rows the frame was rendered
  from, so the agent's runtime answer cannot drift from its frame. Its
  description drops the retired connectors it still advertised.

### D3 — Permissions are edited elsewhere and only read here

Consent, selection and the per-tool aperture stay in Settings → Connectors
(ADR-594 D1). Which connections an agent is scoped to stays on the agent's
page (ADR-612/615). Reach, Connectors' facts block, the frame and the tool
result READ the decision; none of them carries a control. This is the
Claude/ChatGPT connector model: the permission pane is one place, the
identical description is everywhere else.

### D4 — What is deleted

`connector_does` (three sources, one prose block); the three reach-state
prose branches and the outbound sentence in `lane_runner`; `PUBLISH_VERBS`
(subsumed by `PUBLISH_DOORS`); the `commerce`/`trading` branches of the
`list_integrations` result (retired connectors, ADR-494); the direct
`platform_connections` read in the integrations LIST route and the tool
handler (one enumeration reader, `connection_rows`).

## 3. Consequences

- The member's Connectors page, Reach, the frame and the tool result now
  agree by construction. The gate asserts the agreement by DRIVING: the same
  rows through all three renderers, and a write tool patched into the live
  surface flips every face at once.
- Every first-party row now names the member's door where one exists, so an
  agent asked to send says it cannot and points to the door (the
  2026-09-07.6 behaviour, now generated).
- `docs/architecture/lane-frame.md` §"Connector-reach section",
  `connectors.md` §5's facts rows and `agent-composition.md` §3.2.1's Reach
  row point at the structure.

## 4. Gate

`api/test_adr644_one_reach_status.py` (script-style): D1 the facts derive
from the enacting machinery (a fixture per platform; the write-tool
falsifier patched into the live surface); D2 the three renderers read one
structure (the frame paragraph for all four reach states carries the row
facts and ADR-535's fragments; `describe` keeps the 585/628/582 anchors; the
tool result rows equal `reach_status`'s); D3 no renderer carries a control
(no route under this ADR mutates); D4 the deletions hold (`connector_does`
gone; no hand prose branch in the reach section; one enumeration reader; the
tool description names no retired connector); the door roster matches the
FE mounts (pane ↔ `app.slug`, door label in the mounted component).
