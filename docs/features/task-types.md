# Task Types — Deliverable Catalog

> What YARNNN delivers. Task types are organized by **`output_kind`** (ADR-166):
> `accumulates_context` (knowledge tasks), `produces_deliverable` (reports), `external_action` (platform writes), `system_maintenance` (TP back office).
> Architecture: [docs/architecture/registry-matrix.md](../architecture/registry-matrix.md)
> ADRs: [ADR-145](../adr/ADR-145-task-type-registry-premeditated-orchestration.md), [ADR-166](../adr/ADR-166-registry-coherence-pass.md)

---

## How Task Types Work

1. User describes work → TP infers task type(s) from registry
2. Platform scaffolds each task with the correct agent, schedule, and domain wiring
3. **`accumulates_context`** tasks run on schedule, gather intelligence, and write to workspace context domains — no report output
4. **`produces_deliverable`** tasks read from accumulated context domains, compose prose with inline data tables and diagrams
5. **`external_action`** tasks read context, then write to a platform (Slack post, Notion comment) — the action is the output
6. **`system_maintenance`** tasks (TP-owned) run deterministic Python — no LLM, no playbooks
7. System renders visual assets (charts from tables, diagrams from mermaid blocks)
8. Compose service assembles everything into styled HTML per composition mode
9. Output delivered via email/Slack/Notion or viewed in app

**For full intelligence (e.g., competitive), pair an `accumulates_context` task with a `produces_deliverable` task.** The tracking task accumulates context in `/workspace/context/`; the report task produces deliverables from it. Without the tracking task, the report has nothing to read. Without the report, accumulated context never becomes a deliverable.

### Quality Contracts (ADR-149)

`produces_deliverable` task types scaffold a **DELIVERABLE.md** quality contract at `/tasks/{slug}/DELIVERABLE.md`. This file defines what good output looks like for this task type: structure expectations, quality bar, audience assumptions. The agent reads DELIVERABLE.md during execution and the TP uses it as a reference when evaluating output quality. `accumulates_context` tasks do not have DELIVERABLE.md — they write to domain folders, not output folders. `system_maintenance` tasks do not have DELIVERABLE.md — they emit signals only.

### Context Domains (ADR-151)

Task types declare which workspace context domains they read and write via `context_reads` and `context_writes` fields. `accumulates_context` tasks primarily WRITE to domains. `produces_deliverable` tasks primarily READ from domains. This separation enables cross-task knowledge accumulation in `/workspace/context/`.

---

## Track & Research — `output_kind: accumulates_context`

These tasks maintain your workspace knowledge. They run on schedule, update domain folders in `/workspace/context/`, and produce **no report output**. Think of them as your always-on research team keeping institutional knowledge current.

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

### Deep Research
`research-topics`

**What it does:** Deep-dive research on specified topics. Writes findings to the `content_research` context domain for later use by content synthesis tasks.

**Agent:** Research Agent
**Default schedule:** On-demand
**Domains (writes):** content_research

---

### Slack Sync
`slack-digest`

**What it does:** Reads selected Slack channels. Captures decisions, action items, and key discussions. Writes per-channel observation files to the Slack Bot's temporal context directory.

**Agent:** Slack Bot
**Default schedule:** Daily
**Domains (writes):** slack, signals
**Requires platform:** Slack
**Sources:** Auto-populated from platform connection; user-editable via ManageTask

---

### Notion Sync
`notion-digest`

**What it does:** Reads selected Notion pages. Tracks changes, new content, and stale sections. Writes per-page observation files to the Notion Bot's temporal context directory.

**Agent:** Notion Bot
**Default schedule:** Weekly
**Domains (writes):** notion, signals
**Requires platform:** Notion
**Sources:** Auto-populated from platform connection; user-editable via ManageTask

---

### GitHub Sync
`github-digest`

**What it does:** Reads selected GitHub repos — own AND external public repos. Writes 4 files per repo: `latest.md` (issues/PRs activity), `readme.md` (project summary), `releases.md` (what shipped), `metadata.md` (repo identity). Temporal + reference data.

**Agent:** GitHub Bot
**Default schedule:** Daily
**Domains (writes):** github, signals
**Requires platform:** GitHub
**Sources:** Auto-populated from platform connection; user-editable via ManageTask. Accepts any `owner/repo` — own repos + external public repos (competitors, ecosystem).

---

## Reports & Outputs — `output_kind: produces_deliverable`

These tasks read from accumulated context domains and produce deliverables. They are where workspace knowledge becomes polished, delivered output. Each one declares which domains it reads from — the richer those domains (maintained by `accumulates_context` tasks), the better the output.

### Competitive Intel Report
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

**What you get:** Single market intelligence brief covering market sizing, competitive moves, GTM signals, and opportunity identification. Composed from accumulated market, competitive, and signal context. **Absorbs former `gtm-report`** (ADR-166) — same audience, same context domains, one report instead of two.

**Agent:** Content Agent
**Default schedule:** Monthly
**Reads from:** market, competitors, signals
**Output category:** reports
**Composition mode:** Document
**Export options:** PDF

**Expected output:**
- Executive summary
- Market overview with growth chart
- Competitive moves (signal cards, positioning shifts)
- Key players profiled (≥5)
- GTM signals & opportunity windows
- Trend analysis with charts
- Opportunities & risks
- Recommendations

---

### Meeting Prep
`meeting-prep`

**What you get:** Relationship context combined with competitive intelligence — everything you need before a meeting with a key contact.

**Agent:** Content Agent
**Default mode:** goal (the meeting is the completion event — ADR-166)
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

### Stakeholder Report
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

### Project Status
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

### Content Draft
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

## Platform Writes — `output_kind: external_action`

These tasks read workspace context, compose a message, then write it to a third-party platform via API. The action is the output — there is no workspace artifact.

### Slack Post
`slack-respond`

**What it does:** Composes a message from workspace context and posts it to a Slack channel or DM.

**Agent:** Slack Bot
**Default mode:** reactive
**Default schedule:** On-demand
**Reads from:** slack, signals
**Requires platform:** Slack

---

### Notion Update
`notion-update`

**What it does:** Composes an update from workspace context and posts it as a comment on a Notion page.

**Agent:** Notion Bot
**Default mode:** reactive
**Default schedule:** On-demand
**Reads from:** notion, signals
**Requires platform:** Notion

---

## Back Office — `output_kind: system_maintenance`

TP-owned. Run through the same task pipeline as user-facing tasks, but execute deterministic Python instead of an LLM. Visible at `/work` (essential, cannot be archived). See [ADR-164](../adr/ADR-164-back-office-tasks-tp-as-agent.md).

### Agent Hygiene
`back-office-agent-hygiene`

**What it does:** Reviews active agents daily. Pauses agents whose approval rate has decayed below threshold. Migrated from the old `_pause_underperformers` scheduler hack.

**Agent:** Thinking Partner (TP)
**Default mode:** recurring
**Default schedule:** Daily
**Effect:** Agent status updates + activity_log entry

---

### Workspace Cleanup
`back-office-workspace-cleanup`

**What it does:** Sweeps ephemeral files past their TTL, prunes orphaned outputs, keeps the workspace tidy. Migrated from the old scheduler cleanup branch.

**Agent:** Thinking Partner (TP)
**Default mode:** recurring
**Default schedule:** Daily
**Effect:** File deletions + activity_log entry

---

## Summary

| `output_kind` | Types | Owners | Purpose |
|---|---|---|---|
| `accumulates_context` | 8 types | Domain stewards + platform bots | Accumulate workspace knowledge (no user-visible artifact) |
| `produces_deliverable` | 8 types | Domain stewards + Reporting | Produce deliverables from accumulated context |
| `external_action` | 2 types | Platform bots | Write to a third-party platform; no workspace artifact |
| `system_maintenance` | 2 types | Thinking Partner | TP-owned hygiene; deterministic Python, no LLM |

**Total:** 15 task types. Context tasks write to domains. Synthesis tasks read from domains. All synthesis tasks use the Content Agent — composition is a single concern. Context gathering uses specialized agents (Research, CRM, platform bots) matched to the domain.
