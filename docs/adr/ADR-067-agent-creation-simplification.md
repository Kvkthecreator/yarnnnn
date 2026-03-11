# ADR-067: Agent Creation & List Simplification — User-Driven with Platform Grouping

**Status**: Partially Implemented
**Date**: 2026-02-19
**Relates to**: ADR-028 (Destination-First), ADR-044 (Type Reconceptualization), ADR-066 (Detail Page Redesign)

### Implementation Status

**List Page** (`web/app/(authenticated)/agents/page.tsx`):
- ✅ Platform grouping (Slack, Email, Notion, Synthesis)
- ✅ Platform badges on every card
- ✅ Delivery status (delivered/failed) per ADR-066
- ✅ Schedule status (Active/Paused)
- ✅ Destination visibility with arrow indicator
- ✅ Uppercase group headers with separator lines

**Create Page** (`web/components/surfaces/AgentCreateSurface.tsx`):
- ✅ Platform-agnostic delivery options (Email/Slack DM/Channel)
- ✅ Instant run on creation
- ⏳ Simplified type selection (still has 12+ options)
- ⏳ Lazy resource loading (partial)

---

## Context

The current `/agents/new` page (AgentCreateSurface) is a 928-line wizard that attempts to handle:

1. Type selection from 12+ options across "waves"
2. Title input
3. Destination platform selection
4. Source selection (channels, labels, pages)
5. Schedule configuration (frequency, day, time)
6. Platform resource sidebar

### Current Problems

**Complexity vs. Value:**
- 12+ type options overwhelm users. Most want one of 3-4 common patterns.
- "Wave 1/2/3" internal categorization leaks into the UI.
- ADR-044's "binding-first" concept (platform-bound vs cross-platform) isn't reflected in the actual flow.

**Fragile Data Loading:**
- Page load triggers `api.integrations.list()`, `listSlackChannels()`, `listNotionPages()`
- Any backend failure causes 500 error on page load
- All platform resources load eagerly even if not needed

**ADR Drift:**
- ADR-028 proposes destination as step 2
- ADR-044 proposes binding-first selection
- ADR-035 proposes platform-first types
- Current wizard doesn't synthesize these into coherent UX

**No Logical Grouping:**
- List page shows agents in flat order
- No distinction between platform-specific monitors and cross-platform synthesis

### Separation of Concerns

YARNNN has two interaction modes:
- **Chat (TP)**: Where AI-driven work happens — conversations, proposals, generation
- **Surfaces/Routes**: Where users *see* and *manage* what exists — explicit, user-driven UI

The creation flow should be **user-driven** (explicit form), not chat-first. Any TP-driven creation happens in chat, not on `/agents/new`.

---

## Decision: User-Driven Creation with Platform Grouping

### Core Principles

1. **Surfaces are user-driven** — explicit forms, not AI inference
2. **Clear categorization** — Platform Monitors vs Synthesis Work
3. **Platform grouping** — list and create both organized by platform
4. **Lazy loading** — load resources only when needed

---

## New Create Flow

### `/agents/new` — Two Clear Paths

```
┌─────────────────────────────────────────────────────────────┐
│ ← Back                                        Create        │
│                                                             │
│ Create Agent                                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─ Platform Monitors ───────────────────────────────────┐   │
│ │                                                       │   │
│ │  Stay on top of a single platform                     │   │
│ │                                                       │   │
│ │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │   │
│ │  │ 💬 Slack     │  │ 📧 Gmail     │  │ 📝 Notion    │ │   │
│ │  │ Digest       │  │ Brief        │  │ Changelog    │ │   │
│ │  │              │  │              │  │              │ │   │
│ │  │ Summarize    │  │ Daily inbox  │  │ Track doc    │ │   │
│ │  │ channels     │  │ triage       │  │ changes      │ │   │
│ │  └──────────────┘  └──────────────┘  └──────────────┘ │   │
│ │                                                       │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌─ Synthesis Work ──────────────────────────────────────┐   │
│ │                                                       │   │
│ │  Combine context across platforms                     │   │
│ │                                                       │   │
│ │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │   │
│ │  │ 📊 Weekly    │  │ 👥 Meeting   │  │ ✨ Custom    │ │   │
│ │  │ Status       │  │ Prep         │  │              │ │   │
│ │  │              │  │              │  │              │ │   │
│ │  │ Cross-plat   │  │ Context for  │  │ Define your  │ │   │
│ │  │ update       │  │ meetings     │  │ own          │ │   │
│ │  └──────────────┘  └──────────────┘  └──────────────┘ │   │
│ │                                                       │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### After Selection — Minimal Config

When user selects a type (e.g., "Slack Digest"):

```
┌─────────────────────────────────────────────────────────────┐
│ ← Back                                        Create        │
│                                                             │
│ 💬 Slack Digest                                             │
│ Summarize what happened in your channels                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Name                                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Engineering Digest                                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Source channels                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ☑ #engineering  ☑ #product  ☐ #general  ☐ #random     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Deliver to                                                  │
│ ┌──────────────────────┐                                    │
│ │ #engineering-digest ▼│                                    │
│ └──────────────────────┘                                    │
│                                                             │
│ Schedule                                                    │
│ ┌────────┐  ┌─────────┐  ┌───────┐                         │
│ │ Weekly │  │ Monday  │  │ 09:00 │                         │
│ └────────┘  └─────────┘  └───────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key differences from current:**
- Type already selected (no 12-option grid)
- Only relevant fields shown (Slack digest → Slack channels)
- Resources load only after type selection
- 3-4 fields max, not 5+ steps

---

## New List View

### `/agents` — Grouped by Platform with Visual Emphasis

```
┌─────────────────────────────────────────────────────────────┐
│ Agents                                    [+ New]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 💬 SLACK ──────────────────────────────────────────────     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 💬  Engineering Digest                                  │ │
│ │     Weekly Mon 9am → #engineering        ✓ Delivered    │ │
│ │     Last: Feb 19                          ⏸ Paused      │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ 💬  Product Updates                                     │ │
│ │     Daily 8am → #product                 ✓ Delivered    │ │
│ │     Last: Today 8:00 AM                   ▶ Active      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ 📧 EMAIL ──────────────────────────────────────────────     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 📧  Inbox Brief                                         │ │
│ │     Daily 8am → user@email.com           ✓ Delivered    │ │
│ │     Last: Today 8:00 AM                   ▶ Active      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ 📊 SYNTHESIS ──────────────────────────────────────────     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 📊  Weekly Status to Sarah                              │ │
│ │     Weekly Fri 4pm → sarah@company.com   ✓ Delivered    │ │
│ │     Last: Feb 14                          ▶ Active      │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ 📊  1:1 Prep with Mike                                  │ │
│ │     Before meetings → Slack DM           ✓ Delivered    │ │
│ │     Last: Feb 18                          ▶ Active      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Visual Emphasis Principles

**Platform badges on every card** — not just group headers:
- Each agent card shows its platform icon (💬/📧/📝/📊)
- Provides instant visual differentiation even when scrolling
- Maintains identity when groups are collapsed or filtered

**Delivery status (not governance status)** — aligns with ADR-066:
- `✓ Delivered` — most recent run succeeded
- `✗ Failed` — most recent run failed (show retry option)
- `⏳ Generating` — currently running

**Schedule status** (independent from delivery):
- `▶ Active` — automated runs enabled
- `⏸ Paused` — automated runs disabled

**Destination visibility**:
- Show where agents go: `→ #channel`, `→ email@domain.com`, `→ Slack DM`
- This reinforces the "scheduled automation with delivery" mental model

**Grouping logic:**
- Platform-bound agents grouped under their platform (Slack, Gmail, Notion)
- Cross-platform/synthesis agents grouped under "Synthesis"
- Use `type_classification.binding` and `type_classification.primary_platform` from ADR-044
- Group headers are uppercase with visual separator line

---

## Implementation

### Phase 1: Simplify AgentCreateSurface

Replace 928-line wizard with ~300-line two-step form:

```tsx
// Step 1: Type selection (Platform Monitor vs Synthesis)
function TypeSelection({ onSelect }: { onSelect: (type: AgentType) => void }) {
  return (
    <div className="space-y-6">
      <section>
        <h2>Platform Monitors</h2>
        <p>Stay on top of a single platform</p>
        <div className="grid grid-cols-3 gap-4">
          <TypeCard type="slack_channel_digest" icon={Slack} label="Slack Digest" />
          <TypeCard type="gmail_inbox_brief" icon={Mail} label="Gmail Brief" />
          <TypeCard type="notion_changelog" icon={FileText} label="Notion Changelog" />
        </div>
      </section>

      <section>
        <h2>Synthesis Work</h2>
        <p>Combine context across platforms</p>
        <div className="grid grid-cols-3 gap-4">
          <TypeCard type="weekly_status" icon={BarChart3} label="Weekly Status" />
          <TypeCard type="meeting_prep" icon={Users} label="Meeting Prep" />
          <TypeCard type="custom" icon={Sparkles} label="Custom" />
        </div>
      </section>
    </div>
  );
}

// Step 2: Config form (shown after type selection)
function ConfigForm({ type }: { type: AgentType }) {
  // Load resources only for selected type's platform
  const { resources, loading } = usePlatformResources(type);

  return (
    <form>
      <input name="title" placeholder={getDefaultTitle(type)} />
      <SourceSelector type={type} resources={resources} />
      <DestinationSelector type={type} />
      <ScheduleSelector type={type} />
    </form>
  );
}
```

### Phase 2: Update List with Platform Grouping and Visual Emphasis

```tsx
function AgentList({ agents }: { agents: Agent[] }) {
  // Group by platform or "synthesis"
  const grouped = groupAgents(agents);

  return (
    <div className="space-y-8">
      {grouped.slack.length > 0 && (
        <AgentGroup
          icon={<Slack />}
          label="SLACK"
          items={grouped.slack}
        />
      )}
      {grouped.email.length > 0 && (
        <AgentGroup
          icon={<Mail />}
          label="EMAIL"
          items={grouped.email}
        />
      )}
      {grouped.notion.length > 0 && (
        <AgentGroup
          icon={<FileText />}
          label="NOTION"
          items={grouped.notion}
        />
      )}
      {grouped.synthesis.length > 0 && (
        <AgentGroup
          icon={<BarChart3 />}
          label="SYNTHESIS"
          items={grouped.synthesis}
        />
      )}
    </div>
  );
}

// Individual card with platform badge
function AgentCard({ agent }: { agent: Agent }) {
  const icon = getPlatformIcon(agent);
  const latestVersion = agent.versions?.[0];

  return (
    <div className="p-4 border rounded-lg">
      <div className="flex items-start gap-3">
        {/* Platform badge on every card */}
        <span className="text-xl">{icon}</span>

        <div className="flex-1">
          <h3 className="font-medium">{agent.title}</h3>

          {/* Schedule + destination */}
          <p className="text-sm text-muted-foreground">
            {formatSchedule(agent)} → {formatDestination(agent)}
          </p>

          {/* Last delivery + schedule status */}
          <div className="flex items-center gap-4 mt-1 text-sm">
            <span>Last: {formatLastDelivery(latestVersion)}</span>
            <DeliveryStatusBadge version={latestVersion} />
            <ScheduleStatusBadge isPaused={agent.is_paused} />
          </div>
        </div>
      </div>
    </div>
  );
}

// Delivery status (from ADR-066)
function DeliveryStatusBadge({ version }) {
  if (!version) return null;
  if (version.status === 'delivered') return <span>✓ Delivered</span>;
  if (version.status === 'failed') return <span className="text-red-500">✗ Failed</span>;
  if (version.status === 'generating') return <span>⏳ Generating</span>;
  return null;
}

// Schedule status (independent)
function ScheduleStatusBadge({ isPaused }) {
  return isPaused
    ? <span className="text-amber-500">⏸ Paused</span>
    : <span className="text-green-500">▶ Active</span>;
}

function groupAgents(agents: Agent[]) {
  return {
    slack: agents.filter(d =>
      d.type_classification?.primary_platform === 'slack' &&
      d.type_classification?.binding === 'platform_bound'
    ),
    email: agents.filter(d =>
      d.destination?.platform === 'email' ||
      (d.type_classification?.primary_platform === 'gmail' &&
       d.type_classification?.binding === 'platform_bound')
    ),
    notion: agents.filter(d =>
      d.type_classification?.primary_platform === 'notion' &&
      d.type_classification?.binding === 'platform_bound'
    ),
    synthesis: agents.filter(d =>
      d.type_classification?.binding === 'cross_platform' ||
      d.type_classification?.binding === 'hybrid' ||
      d.type_classification?.binding === 'research'
    ),
  };
}
```

### Phase 3: Lazy Resource Loading

Load platform resources only after type selection:

```tsx
function usePlatformResources(type: AgentType) {
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const platform = getPrimaryPlatform(type);
    if (!platform) return;

    setLoading(true);
    loadResourcesForPlatform(platform)
      .then(setResources)
      .finally(() => setLoading(false));
  }, [type]);

  return { resources, loading };
}
```

### Phase 4: Reduce Type Count

Visible types in create flow (6 total, not 12+):

| Category | Types |
|----------|-------|
| Platform Monitors | Slack Digest, Gmail Brief, Notion Changelog |
| Synthesis Work | Weekly Status, Meeting Prep, Custom |

Other types from ADR-044 remain in schema but aren't shown in primary UI — they're created via TP chat or "Custom".

---

## Routes

### Keep
- `/agents` — List page (with platform grouping)
- `/agents/[id]` — Detail page (ADR-066 redesign)
- `/agents/new` — Simplified create page
- `/agents/new?type=slack_channel_digest` — Direct to config step

### Remove
- None (same routes, simpler implementation)

---

## What This Removes

| Removed | Reason |
|---------|--------|
| 12+ type grid | Replaced with 6 clear options (3 platform + 3 synthesis) |
| Wave 1/2/3 categorization | Internal complexity, not user-facing |
| Eager platform resource loading | Load only after type selection |
| Platform context sidebar | Remove (detail page shows sources) |
| Flat agent list | Grouped by platform with visual emphasis |
| "Pending Review" status in list | Replaced with delivery status (ADR-066) |
| Governance-related status badges | Agents deliver immediately, no approval |

---

## What This Enables

- **Clear mental model**: Platform Monitors vs Synthesis Work
- **Faster creation**: 2 steps (type → config) not 5
- **Resilient loading**: No 500 on page load
- **Consistent philosophy**: Simple create + grouped list + delivery-first detail
- **Platform-first organization**: List reflects how users think about agents
- **Visual differentiation**: Platform badges on every card, not just group headers
- **True automation clarity**: Delivery + schedule status, not governance status

---

## Separation of Concerns

| Surface | Driven By | Purpose |
|---------|-----------|---------|
| Chat | TP (AI) | Conversation, proposals, generation |
| `/agents` | User | See and manage agents (grouped by platform) |
| `/agents/new` | User | Explicit creation form |
| `/agents/[id]` | User | View delivery history, manage automation |

TP can still create agents via chat — that's the AI-driven path. The `/agents/new` route is the user-driven path.

Note: Governance/approval workflow has been removed per ADR-066. Agents run on schedule and deliver immediately.

---

## Migration

1. Replace `AgentCreateSurface.tsx` with simplified version
2. Update list page to group by platform
3. No database changes (uses existing `type_classification` from ADR-044)
4. No API changes
5. Old URLs continue working

---

## Open Questions

### Resolved
- **What about power users?** "Custom" type allows full configuration
- **How to determine platform grouping?** Use `type_classification.primary_platform` + `binding`
- **What if no agents in a group?** Don't show the group header

### Deferred
- **Edit agent config inline?** Keep in settings modal for now
- **Reorder agents within groups?** Future feature

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to create first agent | < 45 seconds (from > 2 minutes) |
| Page load errors | 0 (no eager API calls) |
| Lines of code (create) | < 350 (from 928) |
| Type selection clarity | User testing feedback |

---

## Related

- [ADR-028](ADR-028-destination-first-agents.md) — Destination-first model
- [ADR-044](ADR-044-agent-type-reconceptualization.md) — Type classification (provides grouping data)
- [ADR-066](ADR-066-agent-detail-redesign.md) — Detail page simplification
- `web/components/surfaces/AgentCreateSurface.tsx` — Current implementation
- `web/app/(authenticated)/agents/page.tsx` — List page
