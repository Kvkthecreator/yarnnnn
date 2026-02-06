# ADR-028: Destination-First Deliverables & Governance Model

> **Status**: Accepted (Phases 1-3 Complete)
> **Created**: 2026-02-06
> **Updated**: 2026-02-06 (Phases 1-3 implementation complete)
> **Related**: ADR-026 (Integration Architecture), ADR-027 (Integration Reads), ADR-018 (Deliverable Pipeline)

---

## Context

YARNNN is a recurring deliverables platform where AI produces scheduled work artifacts. The current architecture treats deliverables as:

```
Deliverable = Content artifact that YARNNN produces
Integration = Optional export destination (user clicks button after approval)
```

Through building integration reads (ADR-027) and observing the MCP ecosystem (Claude Desktop, Claude Code), a more profound framing emerged.

---

## The Insight

### Current Mental Model

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Schedule    │───>│  Generate    │───>│  Review      │
│  triggers    │    │  content     │    │  (staged)    │
└──────────────┘    └──────────────┘    └──────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  Approve     │
                                        └──────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  Export      │ ← USER CLICKS BUTTON
                                        │  (manual)    │
                                        └──────────────┘
```

**Output** = Markdown content in `draft_content` / `final_content`
**Integrations** = Places to push content after approval (afterthought)

### Reframed Mental Model

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Schedule    │───>│  Generate    │───>│  Review      │
│  triggers    │    │  content     │    │  (staged)    │
└──────────────┘    └──────────────┘    └──────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  Approve     │
                                        └──────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  DELIVER     │ ← AUTOMATIC (configured)
                                        │  to dest     │
                                        └──────────────┘
```

**Deliverable** = Commitment to deliver something to a destination on a schedule
**Destination** = First-class part of the deliverable definition
**Content** = Intermediate artifact shaped by destination

---

## The Key Reframe

> **The deliverable isn't the markdown. The deliverable is the act of putting something in Slack/Notion/Email at the right time for the right person.**

This reframe has implications:

### 1. YARNNN Opted Out of Editing

YARNNN doesn't compete with Google Docs or Notion as an editor. Users don't *live* in YARNNN's content view. They live in Slack, Notion, their inbox.

The "output" isn't something YARNNN holds onto—it's something YARNNN **dispatches**.

### 2. Recurring = Destination is Constant

For a weekly status report:
- Recipient: constant (Sarah, my manager)
- Destination: constant (#team-updates or sarah@company.com)
- Only content changes per cycle

Destination is as stable as schedule. It should be **configured once, used every time**.

### 3. Supervision Point Shifts

```
Current:  User supervises content → then manually dispatches
Proposed: User supervises delivery commitment → system dispatches on approval
```

The user is supervising "Did my update land in the right place, at the right time, in the right tone?"—not just "Is this markdown good?"

---

## Proposed Model

### Destination as First-Class Entity

```python
# Current
Deliverable = {
    "title": "Weekly Status Report",
    "schedule": {...},
    "type": "status_report",
    "recipient_context": {"name": "Sarah", ...},  # Context for content
    ...
}

# Proposed
Deliverable = {
    "title": "Weekly Status Report",
    "schedule": {...},
    "type": "status_report",
    "destination": {                              # FIRST-CLASS
        "platform": "slack",
        "target": "#team-updates",
        "format": "message",                      # or "thread", "page"
    },
    "recipient_context": {"name": "Sarah", ...},  # Still useful for content
    ...
}
```

### Pipeline Change

```
Current:  Gather → Synthesize → Stage → [Approve] → [Manual Export]
Proposed: Gather → Synthesize → Stage → [Approve] → AUTO-DELIVER
                                                    (or one-click confirm)
```

### Governance Levels

Not all deliverables should auto-deliver. Introduce governance as first-class:

| Level | Behavior | Use Case |
|-------|----------|----------|
| **Manual** | Approve → User clicks Export | High-stakes: board updates, investor emails |
| **Semi-auto** | Approve triggers delivery | Trusted: weekly team status |
| **Full-auto** | Generate → Deliver (no review) | Self-reference: personal notes, internal logs |

```python
Deliverable = {
    ...
    "destination": {...},
    "governance": "semi_auto",  # manual | semi_auto | full_auto
    ...
}
```

### Governance Derivation

Governance level could be inferred or configured:

| Factor | Lower Risk (→ auto) | Higher Risk (→ manual) |
|--------|---------------------|------------------------|
| Audience | Self, internal team | External, executives |
| Platform | Internal Slack | Public Notion, email |
| Type | Notes, logs | Proposals, reports |
| History | High approval rate | Frequent edits |

**Default**: Semi-auto (approve triggers delivery). User can override per deliverable.

---

## Implications

### 1. Style Context Auto-Infers

If destination is Slack → use Slack style profile
If destination is Notion → use Notion style profile
If destination is Email → use formal style profile

No need for explicit `type_config.style_context`. Destination implies style.

```python
# Current (explicit)
type_config = {"style_context": "slack", ...}

# With destination-first
# style_context inferred from destination.platform
```

### 2. Wizard Flow Changes

Current wizard: Type → Config → Recipient → Sources → Schedule

Proposed wizard: Type → **Destination** → Recipient → Sources → Schedule

"Where should this be delivered?" becomes Step 2, requiring OAuth connection.

### 3. Export Preferences Collapse

Current `deliverable_export_preferences` table becomes unnecessary—destination is on the deliverable itself.

```sql
-- Current
CREATE TABLE deliverable_export_preferences (
    deliverable_id UUID,
    provider TEXT,
    destination TEXT,
    auto_export BOOLEAN
);

-- With destination-first
-- This data lives on deliverables.destination
```

### 4. Edit Distance Extends

Track not just content quality, but delivery quality:

| Metric | Description |
|--------|-------------|
| Edit distance | How much user changed content |
| **Delivery success** | Did export succeed? |
| **Engagement** | (Future) Did recipient react, open, respond? |

---

## Relationship to Supervisor Model

YARNNN's thesis: User as supervisor, AI as worker.

### Current Interpretation

User supervises content: "Is this draft good?"

### Enhanced Interpretation

User supervises delivery commitment: "Is this thing doing what I set it up to do?"

This aligns with recurring nature:
- One-time setup (configure deliverable + destination + governance)
- Ongoing supervision (spot-check versions, adjust as needed)
- Trust builds (governance level can increase over time)

---

## Schema Evolution

### Phase 1: Add Destination (Non-Breaking)

```sql
ALTER TABLE deliverables ADD COLUMN destination JSONB;
-- {"platform": "slack", "target": "#team-updates", "format": "message"}

ALTER TABLE deliverables ADD COLUMN governance TEXT DEFAULT 'manual';
-- manual | semi_auto | full_auto
```

Existing deliverables continue working (destination = NULL means manual export).

### Phase 2: Wizard Integration

Update deliverable creation wizard to:
1. Show destination step (requires OAuth connection)
2. Set governance level (with smart defaults)
3. Store destination on deliverable

### Phase 3: Auto-Delivery

Update approval flow:
1. If `governance = 'semi_auto'`, trigger export after approval
2. If `governance = 'full_auto'`, skip staging (straight to export after generation)
3. Log all deliveries to `export_log`

### Phase 4: Style Inference

Update pipeline to:
1. If `destination.platform` exists, use as style_context
2. Fall back to explicit `type_config.style_context` if set
3. Fall back to all available styles if neither

---

## Trade-offs

### Benefits

1. **Reduced friction**: No manual export step for recurring deliverables
2. **Clearer mental model**: Deliverable = commitment to destination
3. **Style coherence**: Destination implies appropriate style
4. **Supervision alignment**: User supervises outcome, not process

### Risks

1. **OAuth dependency**: Destination requires valid integration
2. **Failure handling**: What if export fails? Retry? Notify?
3. **Governance complexity**: Another setting to configure
4. **Migration**: Existing deliverables don't have destination

### Mitigations

1. **Graceful degradation**: No destination = manual export (current behavior)
2. **Retry + notify**: Export failures retry 3x, then notify user
3. **Smart defaults**: Derive governance from type + audience
4. **Optional migration**: Don't force existing users to reconfigure

---

## Interaction with ADR-027 (Integration Reads)

### Bidirectional Awareness

With destination-first:
- **Export**: Deliverable → Destination (push)
- **Import**: Destination → Context (pull)

The same channel can be both:
- Where you send status reports
- Where you import decisions and context

### Continuous Sync Reframed

ADR-027 Phase 4 (continuous sync) becomes:
- Not just "keep context fresh"
- But "stay aware of destination state"

Example: "Don't repeat what was discussed in #team-updates this week" requires reading from the destination before writing to it.

---

## Questions to Resolve

### 1. Multi-Destination

Can a deliverable have multiple destinations?
- Status report → Slack + Email
- Research brief → Notion + PDF download

Proposal: Support array of destinations, deliver to all.

### 2. Destination Versioning

What if destination changes (channel renamed, page moved)?
- Detect and warn user
- Allow destination update without creating new deliverable

### 3. Recipient vs. Destination

Are these redundant?
- Recipient: Who the content is for (tone, context)
- Destination: Where it goes (platform, channel)

Proposal: Keep both. Recipient informs content; destination informs delivery.

### 4. Ad Hoc Deliverables

For one-off deliverables, is destination required?
- No—download/copy remains valid
- Destination is optional, not required

### 5. Deliverable-Scoped Context (Future)

As deliverables accumulate history, learnings should persist per-deliverable:
- What edits the user consistently makes
- Research findings that remain relevant
- Recipient preferences inferred from approvals

**Status**: Deferred. See [Analysis: Deliverable-Scoped Context](../analysis/deliverable-scoped-context.md) for exploration. Will revisit after destination-first architecture is stable.

---

## Implementation Phases

### Phase 1: Schema & Backend (Foundation) ✅ COMPLETE

- [x] Add `destination` and `governance` columns to deliverables
- [x] Add delivery tracking columns to deliverable_versions
- [x] Add destination to create/update endpoints
- [x] Create DestinationExporter interface (`api/integrations/exporters/base.py`)
- [x] Create ExporterRegistry (`api/integrations/exporters/registry.py`)
- [x] Implement SlackExporter (`api/integrations/exporters/slack.py`)
- [x] Implement NotionExporter (`api/integrations/exporters/notion.py`)
- [x] Implement DownloadExporter (`api/integrations/exporters/download.py`)
- [x] Create DeliveryService (`api/services/delivery.py`)
- [x] Update export endpoint to use new exporter infrastructure
- [x] Implement governance-based delivery triggering (semi_auto on approval)

**Key Files:**
- `supabase/migrations/025_destination_first.sql` - Schema changes
- `api/integrations/exporters/` - Exporter infrastructure
- `api/services/delivery.py` - Governance-aware delivery
- `api/routes/deliverables.py` - Updated with destination/governance fields
- `api/routes/integrations.py` - Refactored export endpoint

### Phase 2: Wizard & UI ✅ COMPLETE

- [x] Add destination params to CREATE_DELIVERABLE_TOOL (TP asks during creation)
- [x] Add governance selector to DeliverableSettingsModal
- [x] Show destination badge on deliverable list cards
- [x] Semi-auto behavior triggers on version approval (Phase 1)

**Key Files:**
- `api/services/project_tools.py` - CREATE_DELIVERABLE_TOOL with destination_platform, destination_target, governance
- `web/types/index.ts` - Destination, GovernanceLevel, DeliveryStatus types
- `web/components/modals/DeliverableSettingsModal.tsx` - Destination & governance UI
- `web/components/surfaces/DeliverableListSurface.tsx` - Destination badge display

### Phase 3: Style Inference ✅ COMPLETE

- [x] Update pipeline to infer style_context from destination.platform
- [x] Priority: explicit type_config > destination.platform > none
- [x] Platform names match style profile names (slack, notion, etc.)

**Key Files:**
- `api/services/deliverable_pipeline.py` - Style inference in synthesize step

### Phase 4: Full-Auto & Monitoring

- [ ] Implement full-auto governance (skip staging)
- [ ] Add delivery monitoring (success rate, retry status)
- [ ] Add engagement tracking hooks (future: reactions, opens)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Deliverables with destination configured | >50% of new deliverables |
| Semi-auto adoption | >30% of deliverables with destination |
| Export step eliminated | 90% reduction in manual export clicks |
| Delivery success rate | >99% |

---

## Conclusion

This ADR proposes elevating destination from an afterthought to a first-class part of the deliverable model. This aligns with:

1. YARNNN's identity as an orchestration layer (not an editor)
2. The supervision model (user oversees delivery commitment)
3. The recurring nature of deliverables (destination is as stable as schedule)
4. Industry trajectory (MCP, agent-first architectures)

The change is evolutionary (additive columns, optional migration) but conceptually significant. It reframes what YARNNN is: not a content generator, but a **delivery automation platform**.

---

## References

- [ADR-026: Integration Architecture](./ADR-026-integration-architecture.md)
- [ADR-027: Integration Read Architecture](./ADR-027-integration-read-architecture.md)
- [ADR-018: Deliverable Pipeline](./ADR-018-deliverable-pipeline.md)
- [ESSENCE.md](../ESSENCE.md)
- [Analysis: Deliverable-Scoped Context](../analysis/deliverable-scoped-context.md)
