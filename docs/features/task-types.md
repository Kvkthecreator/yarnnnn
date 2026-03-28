# Task Types — Deliverable Catalog

> What YARNNN delivers. Each task type is a concrete output produced by a pre-meditated multi-agent process.
> Architecture: [docs/architecture/task-type-orchestration.md](../architecture/task-type-orchestration.md)
> ADR: [ADR-145](../adr/ADR-145-task-type-registry-premeditated-orchestration.md)

---

## How Task Types Work

1. User selects a task type (onboarding or TP conversation)
2. Platform scaffolds the task with the correct agents, schedule, and output spec
3. Agents execute in sequence — each contributing its specialty
4. Final output is delivered as branded HTML, with optional PDF/PPTX export

Task types are **deliverable-centric**: defined by what you receive, not by which agents produce it.

---

## Intelligence & Research

### Competitive Intelligence Brief
`competitive-intel-brief`

**What you get:** Research-backed competitive analysis with charts, diagrams, and evidence-linked findings.

**Process:** Research Agent (investigate web + platforms) → Content Agent (format with charts, brand styling)

**Default schedule:** Weekly
**Output format:** Branded HTML, exportable as PDF
**Context sources:** Web search, connected platforms, workspace

**Example sections:**
- Executive summary with lead insight
- Key findings with evidence sources
- Market trend charts (bar/line)
- Competitor positioning diagram (mermaid)
- Strategic implications
- Linked sources

---

### Market Research Report
`market-research-report`

**What you get:** Deep-dive investigation on a specific topic with data-backed analysis, trend visualizations, and landscape mapping.

**Process:** Research Agent (deep web investigation) → Content Agent (polish with visualizations, professional layout)

**Default schedule:** Monthly
**Output format:** Branded HTML, exportable as PDF
**Context sources:** Web search, connected platforms, workspace

**Example sections:**
- Research objective and methodology
- Landscape overview with market map (mermaid)
- Data analysis with trend charts
- Key players and positioning
- Opportunities and risks
- Recommendations

---

### Industry Signal Monitor
`industry-signal-monitor`

**What you get:** Surface-level industry scan with deep-dives on signals that matter. Catches signals others miss, then validates the important ones.

**Process:** Marketing Agent (scan web + platforms for signals) → Research Agent (investigate flagged signals)

**Default schedule:** Weekly
**Output format:** Branded HTML
**Context sources:** Web search, connected platforms, workspace

**Example sections:**
- Top signals worth attention (with links)
- Signal analysis: what it means for your business
- Competitive moves tracker
- Emerging trends
- Recommended actions

---

### Due Diligence Summary
`due-diligence-summary`

**What you get:** Structured investigation of a company, market, or opportunity with risk flags and evidence.

**Process:** Research Agent (investigate across web + platforms) → Content Agent (format with org charts, relationship diagrams)

**Default schedule:** On-demand
**Output format:** Branded HTML, exportable as PDF
**Context sources:** Web search, workspace

**Example sections:**
- Subject overview
- Organizational structure (mermaid org chart)
- Financial indicators
- Risk flags with evidence
- Market positioning
- Recommendation

---

## Business Operations

### Meeting Prep Brief
`meeting-prep-brief`

**What you get:** Relationship context from your platforms combined with fresh external research on the attendee's company and recent news.

**Process:** CRM Agent (relationship history from Slack/Notion/email) → Research Agent (investigate attendee's company, recent news)

**Default schedule:** On-demand (before meetings)
**Output format:** Branded HTML
**Context sources:** Connected platforms, web search, workspace

**Example sections:**
- Meeting context (who, relationship history, current status)
- Last interaction summary and open items
- Attendee's recent company news (web research)
- Suggested talking points
- Open items tracker table

---

### Stakeholder / Board Update
`stakeholder-update`

**What you get:** Executive-quality update with KPI dashboards, metric cards, and narrative context — ready for board or leadership consumption.

**Process:** Research Agent (gather metrics, data, context) → Content Agent (compose dashboard-layout deliverable with charts and KPI cards)

**Default schedule:** Monthly or quarterly
**Output format:** Branded HTML (dashboard layout), exportable as PDF/PPTX
**Context sources:** Connected platforms, workspace

**Example sections:**
- KPI dashboard (metric cards with trend indicators)
- Revenue/growth charts
- Key achievements with evidence
- Challenges and mitigations
- Next period priorities

---

### Relationship Health Digest
`relationship-health-digest`

**What you get:** Interaction patterns from Slack synthesized into actionable relationship intelligence — who needs attention, what follow-ups are due.

**Process:** Slack Bot (extract interaction patterns, thread signals) → CRM Agent (synthesize into relationship status and follow-up recommendations)

**Default schedule:** Weekly
**Output format:** Branded HTML
**Context sources:** Slack (requires connection)
**Requires platform:** Slack

**Example sections:**
- Relationship health summary (active, cooling, at-risk)
- Interaction frequency trends
- Follow-ups due this week
- Unanswered threads requiring response
- Relationship notes and context

---

### Project Status Report
`project-status-report`

**What you get:** Cross-platform status synthesis — team activity from Slack, stakeholder expectations from CRM context, composed into a polished report.

**Process:** Slack Bot (team activity signals) → CRM Agent (stakeholder expectations, commitments) → Content Agent (compose formatted status report)

**Default schedule:** Weekly
**Output format:** Branded HTML, exportable as PDF
**Context sources:** Slack, workspace
**Requires platform:** Slack

**Example sections:**
- Status overview (on track / at risk / blocked)
- Team activity highlights (from Slack)
- Stakeholder commitments and expectations
- Blockers and escalations
- Next week priorities

---

## Platform Digests

### Slack Recap
`slack-recap`

**What you get:** Decisions, action items, key discussions, and FYIs extracted from your Slack channels.

**Process:** Slack Bot (single-agent)

**Default schedule:** Daily or weekly
**Output format:** Markdown or branded HTML
**Context sources:** Slack (requires connection)
**Requires platform:** Slack

**Example sections:**
- Decisions made (with attribution)
- Action items (owner, deadline, status)
- Key discussions (summarized with thread links)
- FYIs (important announcements, shared documents)

---

### Notion Sync Report
`notion-sync-report`

**What you get:** What changed in your Notion workspace — new pages, updates, staleness flags, and structure suggestions.

**Process:** Notion Bot (single-agent)

**Default schedule:** Weekly
**Output format:** Markdown or branded HTML
**Context sources:** Notion (requires connection)
**Requires platform:** Notion

**Example sections:**
- Pages created this period
- Pages updated (meaningful edits highlighted)
- Staleness flags (pages not updated in >30 days)
- Structure suggestions (how new content fits hierarchy)

---

## Content & Communications

### Content Brief / Blog Draft
`content-brief`

**What you get:** Research-backed content with competitive landscape context, formatted with visual assets and brand styling.

**Process:** Research Agent (investigate topic + competitive landscape) → Content Agent (write and format with images, charts)

**Default schedule:** On-demand
**Output format:** Branded HTML, exportable as PDF
**Context sources:** Web search, connected platforms, workspace

**Example sections:**
- Topic overview with market context
- Key arguments with evidence
- Competitive positioning chart
- Draft content with embedded visuals
- SEO/distribution recommendations

---

### Launch / Announcement Material
`launch-material`

**What you get:** GTM intelligence transformed into polished launch material — positioning context becomes branded presentation or announcement.

**Process:** Marketing Agent (positioning, competitive context, market signals) → Content Agent (format as presentation, branded HTML, or video)

**Default schedule:** On-demand
**Output format:** Branded HTML (presentation layout), exportable as PDF/PPTX
**Context sources:** Web search, connected platforms, workspace

**Example sections:**
- Market context and timing rationale
- Positioning statement
- Competitive differentiation
- Key messages by audience
- Visual assets (charts, diagrams)

---

## Data & Tracking

### GTM Tracker
`gtm-tracker`

**What you get:** Competitive moves, market signals, and feature matrices — intelligence layer with visual tracking.

**Process:** Marketing Agent (intelligence gathering, web scan, platform signals) → Content Agent (format as dashboard with feature matrices, trend charts)

**Default schedule:** Weekly
**Output format:** Branded HTML (dashboard layout)
**Context sources:** Web search, connected platforms, workspace

**Example sections:**
- Market signals worth attention (with links)
- Competitive moves table (who, what, impact, action)
- Feature matrix (your product vs. competitors)
- Channel performance signals
- Opportunity windows

---

## Task Type Categories

| Category | Task Types | Primary Value |
|----------|-----------|---------------|
| **Intelligence** | Competitive Intel, Market Research, Signal Monitor, Due Diligence | Know what's happening and what it means |
| **Operations** | Meeting Prep, Stakeholder Update, Relationship Health, Project Status | Keep work organized and stakeholders informed |
| **Platform** | Slack Recap, Notion Sync | Never miss what happened on your platforms |
| **Content** | Content Brief, Launch Material | Produce polished, research-backed content |
| **Tracking** | GTM Tracker | Track competitive landscape continuously |

---

## Schedules

| Schedule | Meaning | Example Types |
|----------|---------|---------------|
| `daily` | Every day | Slack Recap |
| `weekly` | Every week | Competitive Intel, GTM Tracker, Relationship Health |
| `biweekly` | Every 2 weeks | Industry Signal Monitor |
| `monthly` | Every month | Market Research, Stakeholder Update |
| `on-demand` | User or TP triggers manually | Meeting Prep, Due Diligence, Content Brief |

---

## Platform Requirements

Some task types require a connected platform:

| Task Type | Required Platform |
|-----------|------------------|
| Slack Recap | Slack |
| Relationship Health Digest | Slack |
| Project Status Report | Slack |
| Notion Sync Report | Notion |

All other task types work without platform connections (using web search + workspace context), but produce richer output when platforms are connected.
