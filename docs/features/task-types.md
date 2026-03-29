# Task Types — Deliverable Catalog

> What YARNNN delivers. Each task type is a concrete output with a defined process and composition mode.
> Architecture: [docs/architecture/task-type-orchestration.md](../architecture/task-type-orchestration.md)
> ADR: [ADR-145](../adr/ADR-145-task-type-registry-premeditated-orchestration.md)

---

## How Task Types Work

1. User selects a task type (onboarding or TP conversation)
2. Platform scaffolds the task with the correct agent, schedule, and composition mode
3. Agent researches, reasons, and writes — producing prose with inline data tables and diagrams
4. System renders visual assets (charts from tables, diagrams from mermaid blocks)
5. Compose service assembles everything into styled HTML per composition mode
6. Output delivered via email/Slack/Notion or viewed in app

Most task types are **single-agent**: one agent handles the full cognitive work (research + composition) in one context window. Multi-step processes are used only where agents need genuinely different tool access (e.g., Slack Bot extracts platform data → CRM Agent synthesizes relationship intelligence).

---

## Intelligence & Research

### Competitive Intelligence Brief
`competitive-intel-brief`

**What you get:** Research-backed competitive analysis with rendered charts, positioning diagrams, and evidence-linked findings.

**Process:** Research Agent (single-step — investigates and composes the full brief)

**Default schedule:** Weekly
**Composition mode:** Document
**Export options:** PDF

**Expected output:**
- Executive summary (insight-first, not process)
- Key findings with inline source citations
- Competitive positioning diagram (mermaid → rendered)
- Market trend charts (data tables → rendered)
- Strategic implications
- Source list

---

### Market Research Report
`market-research-report`

**What you get:** Deep-dive investigation with data-backed analysis, trend visualizations, and landscape mapping.

**Process:** Research Agent (single-step — investigates and composes)

**Default schedule:** Monthly
**Composition mode:** Document
**Export options:** PDF

**Expected output:**
- Executive summary
- Market overview with growth chart
- Competitive landscape (positioning map + player table)
- Trend analysis with charts
- Opportunities & risks
- Recommendations

---

### Industry Signal Monitor
`industry-signal-monitor`

**What you get:** Surface-level industry scan with deep-dives on the signals that matter.

**Process:** Marketing Agent (single-step — scans and analyzes)

**Default schedule:** Weekly
**Composition mode:** Document

**Expected output:**
- Signal summary table (signal, source, date, significance)
- Deep dives on top 2-3 signals
- Recommended responses (watch / adapt / act now)

---

### Due Diligence Summary
`due-diligence-summary`

**What you get:** Structured investigation of a company, market, or opportunity with risk flags and evidence.

**Process:** Research Agent (single-step — investigates and composes)

**Default schedule:** On-demand
**Composition mode:** Document
**Export options:** PDF

**Expected output:**
- Executive summary (go/no-go signal first)
- Organization (org chart diagram)
- Financial summary table
- Risk assessment table (risk, severity, evidence, mitigation)
- Market position (competitive positioning diagram)
- Recommendation with conditions

---

## Business Operations

### Meeting Prep Brief
`meeting-prep-brief`

**What you get:** Relationship context from your platforms combined with fresh external research on attendees.

**Process:** CRM Agent (relationship history from platforms) → Research Agent (investigate attendee's company + compose brief)

**Default schedule:** On-demand
**Composition mode:** Document

**Expected output:**
- Relationship timeline and last interaction
- Open items and commitments
- Attendee's recent company news
- Suggested agenda and talking points
- Things to avoid

---

### Stakeholder / Board Update
`stakeholder-update`

**What you get:** Executive-quality update with KPI cards, metric charts, and narrative context.

**Process:** Content Agent (single-step — gathers context and composes)

**Default schedule:** Monthly
**Composition mode:** Dashboard
**Export options:** PDF, PPTX

**Expected output:**
- Key metrics table (rendered as KPI cards)
- Achievement highlights
- Challenges with owners and mitigations
- Forward look and decisions needed

---

### Relationship Health Digest
`relationship-health-digest`

**What you get:** Interaction patterns from Slack synthesized into actionable relationship intelligence.

**Process:** Slack Bot (extract interaction patterns) → CRM Agent (synthesize into health report)

**Default schedule:** Weekly
**Composition mode:** Document
**Requires platform:** Slack

**Expected output:**
- Relationship health by contact (active / cooling / at-risk)
- Interaction frequency data
- Follow-up recommendations with specific talking points
- Top 3 follow-ups this week

---

### Project Status Report
`project-status-report`

**What you get:** Team activity from Slack composed into a polished status report.

**Process:** Slack Bot (extract team activity) → Content Agent (compose formatted report)

**Default schedule:** Weekly
**Composition mode:** Document
**Export options:** PDF
**Requires platform:** Slack

**Expected output:**
- Overall status (On Track / At Risk / Blocked)
- Progress highlights with attribution
- Blockers & risks with owners
- Action items table
- Next week priorities

---

## Platform Digests

### Slack Recap
`slack-recap`

**What you get:** Decisions, action items, key discussions, and FYIs from your Slack channels.

**Process:** Slack Bot (single-step)

**Default schedule:** Daily
**Composition mode:** Document
**Requires platform:** Slack

**Expected output:**
- Decisions made (with attribution)
- Action items (owner, deadline)
- Key discussions (thread summaries)
- FYIs (announcements, shared documents)

---

### Notion Sync Report
`notion-sync-report`

**What you get:** What changed in your Notion workspace — updates, staleness flags, and structure suggestions.

**Process:** Notion Bot (single-step)

**Default schedule:** Weekly
**Composition mode:** Document
**Requires platform:** Notion

**Expected output:**
- Pages created or meaningfully updated
- Staleness flags (pages not updated >30 days)
- Health notes and structure suggestions

---

## Content & Communications

### Content Brief / Blog Draft
`content-brief`

**What you get:** Research-backed content draft with competitive landscape context and visual assets.

**Process:** Research Agent (single-step — researches and writes)

**Default schedule:** On-demand
**Composition mode:** Document
**Export options:** PDF

**Expected output:**
- Compelling hook and thesis
- 3-5 evidence-backed sections
- Embedded charts for data
- Competitive positioning diagram
- Actionable conclusion

---

### Launch / Announcement Material
`launch-material`

**What you get:** GTM intelligence transformed into polished presentation-ready launch material.

**Process:** Marketing Agent (single-step — positioning and composition)

**Default schedule:** On-demand
**Composition mode:** Presentation
**Export options:** PDF, PPTX

**Expected output:**
- Title + tagline slide
- Problem → Solution → How It Works slides
- Competitive differentiation diagram + feature matrix
- Key messages by audience
- Social/PR quotes
- Next steps

---

## Data & Tracking

### GTM Tracker
`gtm-tracker`

**What you get:** Competitive moves, market signals, and feature matrices — intelligence dashboard.

**Process:** Marketing Agent (single-step — gathers and composes)

**Default schedule:** Weekly
**Composition mode:** Dashboard

**Expected output:**
- Signal count cards (features, pricing, funding, hires)
- Competitive feature matrix table
- Signal log (most recent first)
- Opportunity windows ranked by urgency

---

## Summary

| Category | Types | Process Model |
|----------|-------|---------------|
| **Intelligence** | 4 types | Single-agent (research or marketing) |
| **Operations** | 4 types | Mixed — 1 single-agent, 3 multi-step |
| **Platform** | 2 types | Single-agent (platform bot) |
| **Content** | 2 types | Single-agent (research or marketing) |
| **Tracking** | 1 type | Single-agent (marketing) |

**Total:** 13 task types, 16 process steps. 10 single-agent, 3 multi-step.

Multi-step is used only where agents need different tool access:
- **meeting-prep-brief**: CRM (platform data) → Research (web search)
- **relationship-health-digest**: Slack Bot (platform read) → CRM (relationship domain)
- **project-status-report**: Slack Bot (platform read) → Content (formatting)
