# Task Types — Deliverable Catalog

> What YARNNN delivers. Task types are split into two atomic classes: **context tasks** (accumulate knowledge) and **synthesis tasks** (produce deliverables).
> Architecture: [docs/architecture/registry-matrix.md](../architecture/registry-matrix.md)
> ADR: [ADR-145](../adr/ADR-145-task-type-registry-premeditated-orchestration.md)

---

## How Task Types Work

1. User describes work → TP infers task type(s) from registry
2. Platform scaffolds each task with the correct agent, schedule, and domain wiring
3. **Context tasks** run on schedule, gather intelligence, and write to workspace context domains — no report output
4. **Synthesis tasks** read from accumulated context domains, compose prose with inline data tables and diagrams
5. System renders visual assets (charts from tables, diagrams from mermaid blocks)
6. Compose service assembles everything into styled HTML per composition mode
7. Output delivered via email/Slack/Notion or viewed in app

**For full intelligence (e.g., competitive), create BOTH a tracking task AND a synthesis task.** The tracking task accumulates context in `/workspace/context/`; the synthesis task produces reports from it. Without the tracking task, synthesis has nothing to read. Without the synthesis task, accumulated context never becomes a deliverable.

### Quality Contracts (ADR-149)

Synthesis task types scaffold a **DELIVERABLE.md** quality contract at `/tasks/{slug}/DELIVERABLE.md`. This file defines what good output looks like for this task type: structure expectations, quality bar, audience assumptions. The agent reads DELIVERABLE.md during execution and the TP uses it as a reference when evaluating output quality. Context tasks do not have DELIVERABLE.md — they write to domain folders, not output folders.

### Context Domains (ADR-151)

Task types declare which workspace context domains they read and write via `context_reads` and `context_writes` fields. Context tasks primarily WRITE to domains. Synthesis tasks primarily READ from domains. This separation enables cross-task knowledge accumulation in `/workspace/context/`.

---

## Track & Research — Context Tasks

Context tasks maintain your workspace knowledge. They run on schedule, update domain folders in `/workspace/context/`, and produce **no report output**. Think of them as your always-on research team keeping institutional knowledge current.

### Track Competitors
`track-competitors`

**What it does:** Monitors competitor activity — product launches, pricing changes, hiring, funding — and writes structured findings to the `competitors` context domain.

**Agent:** Research Agent
**Default schedule:** Weekly
**Domains (writes):** competitors, signals

---

### Track Market
`track-market`

**What it does:** Investigates market trends, sizing, growth vectors, and emerging segments. Writes market intelligence to the `market` context domain.

**Agent:** Research Agent
**Default schedule:** Monthly
**Domains (writes):** market, signals

---

### Track Relationships
`track-relationships`

**What it does:** Extracts relationship signals from connected platforms (Slack messages, meeting patterns) and maintains relationship profiles in the `relationships` context domain.

**Agent:** CRM Agent
**Default schedule:** Weekly
**Domains (writes):** relationships, signals

---

### Track Projects
`track-projects`

**What it does:** Monitors project activity from connected platforms and maintains status snapshots in the `projects` context domain.

**Agent:** Research Agent
**Default schedule:** Weekly
**Domains (writes):** projects, signals

---

### Research Topics
`research-topics`

**What it does:** Deep-dive research on specified topics. Writes findings to the `content_research` context domain for later use by content synthesis tasks.

**Agent:** Research Agent
**Default schedule:** On-demand
**Domains (writes):** content_research

---

### Slack Digest
`slack-digest`

**What it does:** Reads selected Slack channels. Captures decisions, action items, and key discussions. Writes per-channel observation files to the Slack Bot's temporal context directory.

**Agent:** Slack Bot
**Default schedule:** Daily
**Domains (writes):** slack, signals
**Requires platform:** Slack

---

### Notion Digest
`notion-digest`

**What it does:** Reads selected Notion pages. Tracks changes, new content, and stale sections. Writes per-page observation files to the Notion Bot's temporal context directory.

**Agent:** Notion Bot
**Default schedule:** Weekly
**Domains (writes):** notion, signals
**Requires platform:** Notion

---

## Reports & Outputs — Synthesis Tasks

Synthesis tasks read from accumulated context domains and produce deliverables. They are where workspace knowledge becomes polished, delivered output. Each synthesis task declares which domains it reads from — the richer those domains (maintained by context tasks), the better the output.

### Competitive Brief
`competitive-brief`

**What you get:** Competitive analysis with positioning diagrams, trend charts, and evidence-linked findings — composed from accumulated competitive intelligence.

**Agent:** Content Agent
**Default schedule:** Weekly
**Reads from:** competitors, signals
**Output category:** briefs
**Composition mode:** Document
**Export options:** PDF

**Expected output:**
- Executive summary (insight-first, not process)
- Key findings with inline source citations
- Competitive positioning diagram (mermaid rendered)
- Market trend charts (data tables rendered)
- Strategic implications

---

### Market Report
`market-report`

**What you get:** Data-backed market analysis with trend visualizations and landscape mapping — composed from accumulated market and competitive intelligence.

**Agent:** Content Agent
**Default schedule:** Monthly
**Reads from:** market, competitors, signals
**Output category:** reports
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

### Meeting Prep
`meeting-prep`

**What you get:** Relationship context combined with competitive intelligence — everything you need before a meeting with a key contact.

**Agent:** Content Agent
**Default schedule:** On-demand
**Reads from:** relationships, competitors, signals
**Output category:** briefs
**Composition mode:** Document

**Expected output:**
- Relationship timeline and last interaction
- Open items and commitments
- Attendee's recent company news
- Suggested agenda and talking points
- Things to avoid

---

### Stakeholder Update
`stakeholder-update`

**What you get:** Executive-quality update with KPI cards, metric charts, and narrative context — draws from ALL workspace domains.

**Agent:** Content Agent
**Default schedule:** Monthly
**Reads from:** ALL domains
**Output category:** reports
**Composition mode:** Dashboard
**Export options:** PDF, PPTX

**Expected output:**
- Key metrics table (rendered as KPI cards)
- Achievement highlights
- Challenges with owners and mitigations
- Forward look and decisions needed

---

### Project Status Report
`project-status`

**What you get:** Project activity composed into a polished status report from accumulated project tracking data.

**Agent:** Content Agent
**Default schedule:** Weekly
**Reads from:** projects, signals
**Output category:** reports
**Composition mode:** Document
**Export options:** PDF

**Expected output:**
- Overall status (On Track / At Risk / Blocked)
- Progress highlights with attribution
- Blockers & risks with owners
- Action items table
- Next week priorities

---

### Content Brief
`content-brief`

**What you get:** Research-backed content draft with competitive context and visual assets — composed from accumulated topic research.

**Agent:** Content Agent
**Default schedule:** On-demand
**Reads from:** content_research, competitors, signals
**Output category:** content_output
**Composition mode:** Document
**Export options:** PDF

**Expected output:**
- Compelling hook and thesis
- 3-5 evidence-backed sections
- Embedded charts for data
- Competitive positioning diagram
- Actionable conclusion

---

### Launch Material
`launch-material`

**What you get:** GTM intelligence transformed into polished launch material — draws from research, competitive, and market context.

**Agent:** Content Agent
**Default schedule:** On-demand
**Reads from:** content_research, competitors, market, signals
**Output category:** content_output
**Composition mode:** Presentation
**Export options:** PDF, PPTX

**Expected output:**
- Title + tagline slide
- Problem, Solution, How It Works slides
- Competitive differentiation diagram + feature matrix
- Key messages by audience
- Social/PR quotes
- Next steps

---

### GTM Report
`gtm-report`

**What you get:** Competitive moves, market signals, and feature matrices — intelligence dashboard composed from accumulated competitive and market context.

**Agent:** Content Agent
**Default schedule:** Weekly
**Reads from:** competitors, market, signals
**Output category:** reports
**Composition mode:** Dashboard

**Expected output:**
- Signal count cards (features, pricing, funding, hires)
- Competitive feature matrix table
- Signal log (most recent first)
- Opportunity windows ranked by urgency

---

## Summary

| Class | Types | Agent | Purpose |
|-------|-------|-------|---------|
| **Context — Track & Research** | 7 types | research, crm, slack_bot, notion_bot | Accumulate workspace knowledge (no output) |
| **Synthesis — Reports & Outputs** | 8 types | content | Produce deliverables from accumulated context |

**Total:** 15 task types. Context tasks write to domains. Synthesis tasks read from domains. All synthesis tasks use the Content Agent — composition is a single concern. Context gathering uses specialized agents (Research, CRM, platform bots) matched to the domain.
