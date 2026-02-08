# Integration-First Positioning

**Date:** 2026-02-08
**Status:** Active
**Supersedes:** GTM_POSITIONING.md (partial - learning loop still valid, context source mechanism updated)
**Builds On:** STRATEGIC_SYNTHESIS.md, ADR-030 (Context Extraction), ADR-021 (Supervision UX)

---

## Executive Summary

This document captures a fundamental reframe of yarnnn's service philosophy. The shift is not about adding integrations as a feature—it's about recognizing that **integrations are the foundation** of how yarnnn delivers value.

The insight: If users are supervisors (not writers), they shouldn't be gathering context manually. The system should pull context from where work already happens.

---

## The Purest Statement

**yarnnn is a supervision layer between your work platforms and your recurring outputs.**

You don't write. You don't gather. You don't synthesize.
You connect, configure, and approve.

---

## The Insight

Work happens in platforms:
- Slack conversations
- Email threads
- Notion docs
- Meeting notes

Deliverables live elsewhere:
- Status reports
- Investor updates
- Client briefs
- Research digests

The gap between "where work happens" and "what you owe someone" is filled with manual labor:
- Reading back through Slack
- Summarizing email threads
- Copying from docs
- Writing the same structure again

**yarnnn closes that gap automatically.**

---

## The Model

```
┌─────────────────────────────────────────────────────────────────┐
│                     WHERE WORK HAPPENS                          │
│                                                                 │
│     Slack          Gmail          Notion         (+ more)       │
│       │              │              │                           │
│       └──────────────┴──────────────┘                           │
│                      │                                          │
│                      ▼                                          │
│              ┌──────────────┐                                   │
│              │    yarnnn    │                                   │
│              │              │                                   │
│              │  • Connects  │                                   │
│              │  • Extracts  │                                   │
│              │  • Learns    │                                   │
│              │  • Produces  │                                   │
│              └──────────────┘                                   │
│                      │                                          │
│                      ▼                                          │
│              ┌──────────────┐                                   │
│              │     YOU      │                                   │
│              │  (Supervisor)│                                   │
│              │              │                                   │
│              │  • Configure │                                   │
│              │  • Review    │                                   │
│              │  • Approve   │                                   │
│              └──────────────┘                                   │
│                      │                                          │
│                      ▼                                          │
│              WHAT YOU OWE SOMEONE                               │
│                                                                 │
│     Status Report    Investor Update    Client Brief            │
└─────────────────────────────────────────────────────────────────┘
```

---

## The User's Role

You are not a writer. You are a supervisor.

**Supervisors don't do the work. They:**
- Decide what matters (configure scope)
- Check that it's right (review drafts)
- Give the go-ahead (approve)

The less you edit, the better yarnnn is working.

---

## The Learning Loop (Reframed)

**Previous framing:** "yarnnn learns from your edits."

**New framing:** "yarnnn learns what to extract, how to synthesize, and what you approve."

The goal isn't fewer edits as a metric. The goal is that **your approval becomes a rubber stamp** because yarnnn already knows:
- Which Slack channels matter
- Which email threads are signal vs noise
- What structure you want
- What tone fits the recipient

---

## Why Integrations Are First-Class

Integrations aren't a feature. They're the foundation.

| Without Integrations | With Integrations |
|---------------------|-------------------|
| yarnnn is a writing assistant | yarnnn is a supervision system |
| You feed it context, it drafts, you edit heavily | It pulls context, synthesizes, you approve |
| You do the gathering work | yarnnn does the gathering work |

**The difference is who does the work.**

---

## The Two Paths

Both paths exist, but they're not equal:

| Path | What You Do | What yarnnn Does | Your Ongoing Effort |
|------|-------------|------------------|---------------------|
| **Integrations** | Connect once, configure scope | Pulls fresh context every cycle | Approve (low) |
| **Manual** | Paste/upload each time | Works with what you gave | Gather + paste + edit (high) |

Manual is a valid starting point. But it's not the destination.

**The natural progression:**
1. Try with manual input → see yarnnn work
2. Connect integrations → see yarnnn work better
3. Approve with light touch → realize you're supervising, not writing

---

## What yarnnn Is Not

- **Not a chat assistant** — You're not prompting, you're configuring
- **Not a writing tool** — You're not drafting, you're approving
- **Not a template system** — It doesn't repeat, it synthesizes fresh context
- **Not a document editor** — The draft is the output, not the workspace

---

## Core Messaging

### One-liner
> yarnnn turns your work platforms into recurring deliverables.

### Tagline
> Connect. Configure. Approve.

### Elevator Pitch
> Your work happens in Slack, Gmail, and Notion. Your deliverables go to clients, investors, and teams. yarnnn connects the two—pulling context from where work happens, synthesizing it into what you owe someone, and learning from every approval. You supervise. yarnnn delivers.

### The Value Proposition (Complete)
> Set up once. yarnnn pulls context from your connected platforms, synthesizes drafts on schedule, and learns what you approve. Over time, your role shifts from editing to approving.

---

## Messaging Shifts

| Dimension | Previous | New |
|-----------|----------|-----|
| **Hero headline** | "Recurring work that gets better every single time" | "Your work platforms, turned into deliverables" |
| **Tagline** | "Set it up once. Review when ready. Watch it learn." | "Connect. Configure. Approve." |
| **How it works - Step 1** | "Set up your deliverable" | "Connect your tools" |
| **Primary context source** | User-provided (paste, describe, upload) | Platform integrations |
| **User role emphasis** | "Review and refine" | "Configure and approve" |
| **Learning emphasis** | "Learns from your edits" | "Learns what to extract and how you approve" |
| **Value demonstration** | Quality trend (edit distance) | Approval confidence (light-touch reviews) |

---

## Landing Page Structure

### 1. Hero
**Headline:** Your work platforms, turned into deliverables.
**Subhead:** Connect. Configure. Approve.
**Visual:** Platforms (Slack, Gmail, Notion) flowing into yarnnn, out to deliverables.

### 2. The Gap
**Message:** Work happens in Slack, Gmail, Notion. Deliverables go to clients and stakeholders. The space between is manual labor—reading, summarizing, reformatting. Every week.

### 3. The Solution
**Message:** yarnnn connects to where your work happens. It extracts what matters, synthesizes it into what you owe someone, and delivers drafts on schedule. You review and approve.

### 4. Your Role
**Message:** You're the supervisor. Not the writer.
- **Connect** — Link your work platforms once
- **Configure** — Tell yarnnn what to produce and when
- **Approve** — Review drafts, approve with light touch

### 5. What You Deliver
Show specific platform → deliverable flows:
- Slack #engineering → Weekly Status Report
- Gmail inbox → Client Follow-up Summary
- Notion project docs → Investor Update

### 6. The Learning
**Message:** Every approval teaches yarnnn. Which channels matter. What structure works. What tone fits. Over time, approval becomes a rubber stamp.

### 7. Two Ways to Start
**Connect your platforms (recommended):**
- Fresh context every cycle
- Less work over time
- yarnnn discovers patterns automatically

**Or describe it yourself:**
- Start immediately
- No permissions needed
- You control exactly what's seen

### 8. CTA
Start for free.

---

## How It Works Page

### Step 1: Connect Your Tools
Link the platforms where your work happens. Slack, Gmail, Notion. One-time OAuth. yarnnn can now see what you see.

### Step 2: Configure What You Deliver
Describe your recurring deliverable. Who receives it. When it's due. Which channels, threads, or docs should inform it. Set the scope.

### Step 3: Review and Approve
On schedule, yarnnn pulls fresh context, synthesizes a draft, and notifies you. Review it. Make light edits if needed. Approve when ready.

### Step 4: Watch It Learn
Every approval teaches yarnnn. What to extract. What to emphasize. What tone to use. Over time, you edit less. Approval becomes routine.

---

## Pricing Page

### What Changes
- Remove "source documents" as a tier differentiator
- Integrations are unlimited on all tiers (moat, not gate)
- Differentiate on deliverable count and execution volume

### Tier Structure

**Free ($0/month)**
- 1 active deliverable
- Unlimited integrations
- Unlimited versions
- Quality trend analytics
- Scheduled production

**Pro ($19/month)**
- Unlimited deliverables
- Unlimited integrations
- Unlimited versions
- Unlimited chat refinement
- Priority support

### Messaging
> Same price as ChatGPT Plus. But yarnnn pulls from your platforms and actually learns.

---

## About Page

### The Insight (Updated)
**Most AI forgets.** ChatGPT, Claude, Gemini—they reset every session. Your corrections evaporate.

**Your work already contains the signal.** The Slack threads, email chains, and docs you accumulate every week—that's the raw material for your deliverables. You just have to extract it. Again. And again.

**yarnnn extracts it for you.** Connect your platforms. Configure your deliverables. Approve the drafts. That's supervision, not writing.

### What Makes yarnnn Different (Updated)
1. **Platforms, not prompts** — yarnnn connects to where work happens, not where you type instructions
2. **Synthesis, not templates** — Every draft is fresh, built from current context
3. **Approval, not editing** — The goal is light-touch review, not heavy rewriting
4. **Learning that compounds** — Every approval teaches yarnnn what matters

---

## Onboarding (Conceptual)

### The Choice Screen

```
How should yarnnn get context for your deliverables?

┌─────────────────────────────────────┐  ┌─────────────────────────────────────┐
│  Connect your tools                 │  │  Describe it yourself               │
│  (Recommended)                      │  │                                     │
│                                     │  │                                     │
│  ✓ Always fresh context             │  │  ✓ Start immediately                │
│  ✓ Less work over time              │  │  ✓ No permissions needed            │
│  ✓ Discovers patterns automatically │  │  ✓ You control exactly what's seen  │
│                                     │  │                                     │
│  Requires one-time sign-in          │  │  You'll update context manually     │
│                                     │  │  as things change                   │
│                                     │  │                                     │
│  [Connect Slack, Gmail, or Notion]  │  │  [Start with an example]            │
└─────────────────────────────────────┘  └─────────────────────────────────────┘
```

### Post-Connection Flow
1. yarnnn shows what it can see (channels, folders, inbox)
2. User selects scope for first deliverable
3. yarnnn creates deliverable with integration sources pre-configured
4. First draft generated from live context
5. User reviews → lands in supervision mode from day one

### Manual Path Flow
1. User describes or pastes example
2. yarnnn creates deliverable
3. First draft generated from provided context
4. Prompt to connect integrations appears after first approval
5. Natural upgrade path to full supervision mode

---

## Implications for Product

### Onboarding
- Lead with integration connection, not deliverable description
- Show the value of fresh context immediately
- Manual path exists but is positioned as "quick start" not "default"

### Deliverable Setup
- Integration source selection is primary configuration
- Scope parameters (time range, channels, etc.) are prominent
- Manual upload is secondary option

### Execution
- Delta extraction for recurring deliverables (only fetch new context)
- Coverage visibility (what yarnnn is pulling from)
- Source attribution in drafts (where context came from)

### Dashboard
- Show connected integrations prominently
- Coverage indicators per deliverable
- "Last synced" timestamps

---

## What This Is Not

This is not:
- A pivot away from recurring deliverables (core stays same)
- A deprecation of manual input (still valid path)
- A change to the learning mechanism (still learns from approvals/edits)
- A technical refactor mandate (architecture already supports this)

This is:
- A reframe of where context comes from (platforms first)
- A clarification of user role (supervisor, not writer)
- An alignment of messaging with existing architecture
- A positioning update for marketing and onboarding

---

## Relationship to Existing Docs

| Document | Status |
|----------|--------|
| ESSENCE.md | Still valid. Supervision model + recurring deliverables unchanged. |
| GTM_POSITIONING.md | Partially superseded. Learning loop messaging still valid. Context source messaging updated here. |
| STRATEGIC_SYNTHESIS.md | Still valid. "Witnessed existence" framing compatible. This doc addresses the *mechanism*. |
| ADR-030 | Validated. This positioning relies on that architecture. |
| ADR-021 | Validated. Review-first supervision UX aligns with this framing. |
| CONVERSATION_FIRST_ONBOARDING.md | Needs update. Should offer integration path first, conversation path second. |

---

## Summary

**The shift:** From "describe your deliverable and paste examples" to "connect your platforms and configure scope."

**The reason:** If users are supervisors, they shouldn't gather context manually. That's worker-level labor.

**The outcome:** Users who connect integrations experience yarnnn as a supervision system. Users who use manual input experience it as a writing assistant. Both work, but one is the destination.

**The bet:** Positioning integrations as foundational (not optional) will result in deeper engagement, higher retention, and stronger moat.

---

*This document is the source of truth for integration-first positioning. All marketing pages and onboarding flows should reference this framing.*