# ADR-642 — The boundary has a door: Reach

**Status**: Accepted + Implemented (2026-09-07, operator ruling: *"proceed with
2–3 … reach and outbound can drastically 'feel different to the user, even our
first real customer' from day one"*).
**Date**: 2026-09-07
**Disposition** (the intake-pipeline.md §5 first-paragraph rule): this ADR adds
**no reach mechanism**. It PRESENTS the three that exist — intake, turn reach,
outbound — on one kernel surface, and it consolidates the proposal queue into
that surface. The one mechanism change it rides beside is ADR-628's third
amendment (Slack, the second outbound tenant), recorded there, not here.
**Dimension** (Axiom 0): **Channel** (Axiom 6 — every act has a Where). No
Identity change (ADR-640 holds: an agent appears only as the character on a
receipt). No Trigger change (no clock lives on the surface; it reads
declarations). No Substrate change (nothing new is stored; DP29).
**Related**: ADR-346 (one body, N mounts) · ADR-592 (stage; the stub +
middleware obligation) · ADR-616 (count callers before deleting a surface) ·
ADR-628 (outbound) · ADR-635 (attached connectors; the proposal queue's first
producer) · ADR-639 (standing work is a kernel lane — the precedent this
surface copies: a concern that owns no file type is a kernel surface, not an
app) · ADR-640 (no agent record) · ADR-641 (accent = identity).
**Amends**: the `queue` surface (ADR-297/346/349) — DELETED as a surface, its
body absorbed here and in Notifications → To do. `docs/design/WORKSPACE.md`'s
Queue contract → the Reach contract.
**Preserves**: ADR-594 D1 (no per-connection settings — consent, selection
and aperture stay Settings acts; Reach lists and doors) · ADR-628 D5 (no
publish from chat; no act on this surface publishes) · Axiom 9 (one
narrative — the Crossed pane is a LENS on the workspace timeline, never a
second log) · Axiom 8 (a receipt shows what the reader gets).

---

## 1. Context — the moat lives on the one dimension with no surface

Put the live surface roster against Axiom 0's six dimensions:

| Dimension | Surfaces |
|---|---|
| What (substrate) | Files · Slides · Text · Images · Blogger — five |
| Who (identity) | Agents — one, and ADR-640 rules it presents a character, never a record |
| When (trigger) | Notifications (mentions, standing work) |
| How (mechanism) | Chat |
| **Where (channel)** | **none at the front door.** Connectors and Sources under Settings. The proposal queue as its own back-room surface (`search-only`, one navigation caller). The reach receipts of Part T on the standing-work ledger. Five pieces, no door. |

ESSENCE's moat sentence — *the system of record where human and AI work
settles* — is a claim about the boundary: things come in attributed, things go
out receipted. That is a Channel claim. The dimension the moat argument lives
on was the one dimension a member could not see as a whole.

The strategic read that produced this ADR (the 2026-09-07 discourse): the
frontier labs' agents are becoming the hands on existing software — a Where
story. yarnnn cannot out-shell a lab's shell; what no lab can offer neutrally
is the kernel — the attributed, multi-principal record of what crossed. The
summer's build went into five What-surfaces. This ADR builds the Where one.

The layman legibility argument points the same way. A member looking at a
slide pane already has a mental slot for it, and the slot is "a slide editor
with AI", which they compare to tools that beat it. A member looking at a
signed loop across their tools has no existing slot: *this came in from Slack
on Monday, the agent kept this file current, this went out to a channel, here
is the receipt, here is who signed each step.*

## 2. What already existed, counted (ADR-616)

| Piece | Where it lived | Acts, with caller counts |
|---|---|---|
| Connections (platform + attached) | Settings → Connectors (`ConnectedIntegrationsSection`) | connect · disconnect · select · aperture — all Settings acts, untouched |
| What a connection does | `GET /integrations/{provider}` only (`connector_does`) | read; the LIST carried no `does`, so a roster could not say what each row reads or writes |
| The proposal queue | `/queue` (search-only) + Notifications → To do | list (2 mounts) · approve (1 caller) · reject (1 caller) · navigate-to-queue (**1 caller**, the To-do escape hatch) |
| Outbound receipts | `_publish.yaml` sidecars, `revision_kind='derivation'` | read as files; **no ledger row of their own** (an outbound publish writes no `execution_events` / `activity_log` row) — and `classify_weight` files an underscore YAML as housekeeping, so Activity HID every publish receipt by default |
| Intake arrivals | `revision_kind='observation'` (capture + standing retention) | routine weight; visible in Activity only among every other revision |
| Reach receipts (Part T) | `StandingSummary.sources[].reads` + the run's `reach` | the Standing work pane |

Two facts in that table are defects on their own: the Connectors roster could
not say what a row does, and the Activity ledger hid every outbound receipt.

## 3. Decisions

### D1 — Reach is a kernel surface on the Channel dimension, not an app

`reach` joins `KERNEL_SURFACES`: `stage: primary`, `register: application`,
`archetype: dashboard`, `icon_key: arrow-left-right`, route `/reach`, pinned by
derivation (ADR-592). It owns no file type, declares no posture and no object
model, and therefore has **no `AppDescriptor` row** (ADR-636 governs apps;
ADR-639 D4 is the precedent — a concern that owns no type is a kernel surface).
Its accent is cyan — the connectors hue (ADR-641 keys accent on the SLUG, and
the boundary and its consent page are one identity).

### D2 — Three panes, three questions, everything derived

One `SettingsPaneShell` (the Notifications shape), three panes:

- **Connected** — every connection the member holds (platform OAuth + attached
  `mcp:{slug}`), each with WHERE it points, what it **reads** and **writes**
  (`connector_does`, now served on the LIST), its freshness (the capture
  signal), and **which standing declarations read it** (derived from
  `GET /standing`'s `sources[].connector`). Every consent act is a door to
  Settings → Connectors; nothing here connects, selects or sets an aperture.
- **Leaving** — the proposal queue, filtered to the families that cross the
  boundary: `external-write` and `capital`. `QueueBody` gains a `families`
  prop; Notifications → To do mounts it unfiltered (everything awaiting me),
  Reach mounts it filtered (what is about to leave). One body, three mounts
  (ADR-346). The two acts it carries — approve, reject — are the two the
  queue already had; no third act is added.
- **Crossed** — the workspace timeline under a **boundary lens**
  (`GET /workspace/timeline?lens=boundary`): revisions with
  `revision_kind='observation'` (arrived — capture and standing retention
  alike, one predicate) or whose basename is `_publish.yaml` (left, on a
  click), and proposals of the two boundary families (left, or refused, by
  decision). No invocation or membership rows. Publish-sidecar rows carry a
  `receipt` (platform · url · status · `publicly_readable` · `read_back`),
  parsed from the sidecar at read time, and are weighted **material** under
  this lens — a receipt is never housekeeping at the boundary.

Nothing on the surface is stored. Connections are rows because credentials
must be; declarations are files; proposals are ledger rows; the rest is the
timeline. The compositor reads, never authors.

### D3 — The guards

- **No agent record** (ADR-640 D1). No pane presents work, output, cost or
  history as an agent's own. An agent appears exactly where the ledger already
  puts it: as the character on a receipt's attribution line.
- **No clock**. The surface reads what stands; Run now and Pause stay in
  Notifications → Standing work, the one home ADR-639 gave them.
- **No authoring, no publishing**. The only writes reachable from Reach are
  the two proposal decisions. The outbound act stays on the artifact's own
  pane (ADR-628 D2: the member stands on the file), and the open chat never
  carries it (D5).
- **One narrative** (Axiom 9). Crossed is a lens over the same three ledgers
  Activity reads, with the same row grammar (`timeline-rows`). A second
  outbound log — the ADR-415 emissions union over two legacy tables — is not
  extended; it stays where it is.
- **Receipts, not claims** (Axiom 8). A boundary row shows what the platform
  said AND what a reader gets (D7) AND, where the tenant mechanizes it, what
  was read back (D8). A stage with neither a receipt nor a refusal is served
  as unresolved, never as fine.

### D4 — The queue surface is absorbed

`queue` leaves `KERNEL_SURFACES`, the FE slug union, the allowlist and the
component registry. `/queue` becomes an ADR-308 `redirect()` stub →
`/reach?reach.pane=leaving`, hand-listed in middleware (the ADR-592
obligation), and `queue` joins `DOCK_RETIRED_SLUGS` so a persisted open/
foregrounded entry renders no ghost. The To-do escape hatch — the one
navigation caller — re-points to Reach. The `components/queue/` folder is NOT
renamed: it is the proposal queue's body (ADR-307's `QUEUE` decision, the
chat's `ProposalCard`), not the surface, and the concept outlives the door.

### D5 — What a connection does is derived from the publish seam AND the LIVE tool surface

`connector_does` said *"nothing — yarnnn never writes to Slack"*, derived
from the publish seam alone. The first cut of this ADR "fixed" it by also
reading the capability registry (`PLATFORM_TOOLS_BY_CAPABILITY`'s
`write_{platform}`) and produced *"an agent's Slack post goes out only
through a proposal you approve"* — and the first click-pass falsified that
within the hour: asked to send a document to Slack, the editor truthfully
answered *"I cannot post — my Slack access is read-only."* The registry
still carries `write_slack` for the task pipeline ADR-231 deleted; the
lane — the only live tool surface — composes read rosters only
(`turn_reach_tool_names`), and the standing lane is toolless.

**A registry row is not a live path.** The `writes` fact derives from two
homes, both live: the member-clicked publish target (`PUBLISH_TARGETS`, with
the door's own verb from `PUBLISH_VERBS`) and whether a write tool for the
platform is composed into a live tool loop. Today none is, so every
first-party row says the agent cannot send and names the member's door; the
day a write tool is composed, the sentence names the proposal path on its
own. The `agents` fact says the same from the agent's side. The gate drives
both branches by patching the live surface.

**The mirror fix rides the lane frame** (CHANGELOG `[2026.09.07.6]`): the
reach section now names the member's outbound doors, derived from the same
roster, so an agent asked to send says it cannot and points to the door
instead of to Settings.

> **Superseded the same day by [ADR-644](ADR-644-one-reach-status.md)**: the
> derivation moved into ONE structure (`services/reach_status.py`) with two
> renderers — `describe` for the member, `frame_paragraph` for the agent —
> and `connector_does` was deleted. D5's rule (a registry row is not a live
> path) stands; its home moved.

### D6 — The Dock gains a pin, by generation

Reach is `primary`, so `DEFAULT_KEPT_SURFACES` gains it (the gate asserts the
hand-kept copy equals the derivation) and a reseed generation lets an
un-curated Dock converge in one read. A curated Dock is left alone, as ever.
The on-screen order becomes `Chat │ Text Slides Blogger Images │ Files Agents
Reach` — the record, its residents, its boundary.

## 4. Consequences

- The strategic re-cut this ADR enacts: the authoring apps are frozen at
  reference depth (the agent-native format for unattended work + a viewer;
  never a human's daily editor against Figma or PowerPoint); the interop face
  leads; outbound widens one tenant at a time, demand-named; the remote
  binding (a file that knows its remote) waits for a second outbound tenant
  to exist — it now does (ADR-628 amendment 3), and stays owed.
- `sources` (the ADR-335 bundle-watch view, hidden since ADR-425 D2) is NOT
  re-homed here: its model rides the retired recurrence machinery. Its
  successor is the standing declaration's connector source, which Connected
  already shows. Deleting the row is a separate ruling.
- ADR-635's owed distribution (registry publish, plugin-directory submission,
  the attach click-pass) is deliberately sequenced AFTER this ADR by operator
  ruling; it remains the kernel-led posture's distribution channel and is
  still owed.
- `docs/design/WORKSPACE.md` Queue → Reach contract; `connectors.md` §5 names
  the surface; GLOSSARY's "Platform reach" row gains the door.

## 5. Gate

`api/test_adr642_reach.py` (script-style): D1 the row + the four-file
lockstep + accent + pin + generation; D2 the boundary lens DRIVEN with fakes
(an observation and a publish sidecar pass, a plain revision and an invocation
do not; the receipt rides; family filter holds); D3 the surface component
calls no run/pause, no publish, no agents API, and the lens selects no cost
column; D4 `queue` is gone from the four files, `/queue` is a `redirect()`
stub into Reach's Leaving pane, `"/queue"` is hand-listed in middleware,
`queue` is retired from the Dock, the To-do escape hatch targets `reach`,
`QueueBody` takes `families`; D5 `connector_does("slack")["writes"]` names
BOTH paths and `("wordpress")` names one; `does` rides the integrations LIST.
