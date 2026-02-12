# ADR-054: Landing Page Restructure - Introducing TP

> **Status**: Accepted
> **Date**: 2026-02-12
> **Deciders**: Kevin (solo founder)
> **Supersedes**: INTEGRATION_FIRST_POSITIONING.md (messaging structure, not philosophy)
> **Related**: ADR-037 (Chat-First Surface), ADR-010 (Thinking Partner Architecture)

---

## Context

The current landing pages (Landing, How It Works, About) were structured around the Integration-First Positioning (Feb 8, 2026). While the positioning is correct—yarnnn as a supervision layer between platforms and deliverables—the pages have significant overlap and miss a crucial element: **introducing TP (Thinking Partner)**.

### Current State Problems

1. **Massive overlap between Landing and How It Works**
   - Both explain: Connect tools → Configure deliverables → Review → Learn
   - Same 4-step flow, same messaging, different layouts
   - User reads the same story twice

2. **How It Works too similar to About**
   - Both explain the philosophy
   - Both describe what yarnnn does
   - About has the "why", How It Works has... the same thing?

3. **Missing: TP introduction**
   - TP is the primary interface (per ADR-037 Chat-First)
   - Users land on chat when logged in
   - But marketing pages never mention the conversational interface
   - Users don't know they'll interact via chat

### The Gap

Integration-First Positioning establishes:
- "You don't write. You don't gather. You supervise."
- "Connect. Configure. Approve."

But HOW do you configure? HOW do you communicate with yarnnn?

**Through TP** — the Thinking Partner interface.

---

## Decision

### Restructure the three marketing pages with distinct purposes:

| Page | Purpose | Core Message |
|------|---------|--------------|
| **Landing** | Hook + Value Prop | "Your work platforms → deliverables" (integration animation) |
| **How It Works** | Meet TP + The Flow | "Meet your Thinking Partner" (introduce the conversational interface) |
| **About** | Philosophy + Origin | "Why we built yarnnn" (the story, the differentiation) |

### Detailed Structure

#### Landing Page (Keep Current, Minor Tweaks)

**Purpose**: First impression, value proposition, integration showcase

**Keep**:
- IntegrationHub animation (platforms flowing to outputs)
- Hero: "Your work platforms, turned into deliverables"
- Integration showcase
- Simple CTA flow

**Add**:
- Brief TP mention: "Your Thinking Partner handles the rest"

#### How It Works Page (Major Restructure → "Meet TP")

**New Purpose**: Introduce TP as the conversational interface

**New Structure**:

1. **Hero: "Meet TP, your Thinking Partner"**
   - This is who you talk to
   - TP understands your work, learns your preferences, produces your deliverables

2. **The Conversation Model**
   - You don't fill forms. You talk.
   - "Create a weekly status report" → TP asks clarifying questions
   - Show chat-style interaction example

3. **What TP Does For You**
   - Connects to your platforms (mentions integrations briefly)
   - Pulls fresh context on schedule
   - Drafts deliverables in your voice
   - Learns from your feedback

4. **The Flow (Simplified)**
   - Connect (TP guides you)
   - Describe (to TP, not forms)
   - Review (TP presents drafts)
   - Approve (or refine with TP)

5. **TP Learns**
   - Every conversation teaches TP
   - Edit patterns, preferences, tone
   - Gets better with each cycle

6. **CTA: "Start talking to TP"**

#### About Page (Tighten Focus)

**Purpose**: The story, the philosophy, the differentiation

**Keep**:
- Origin story ("We built yarnnn because...")
- The insight (platforms have context, deliverables need it)
- What makes yarnnn different (not a chatbot, not a template tool)

**Remove/Move**:
- How-it-works style explanations (moved to How It Works)
- Redundant flow descriptions

**Tighten to**:
- Why we built this (the problem)
- Our philosophy (supervision, not writing)
- What we're not (clear differentiation)
- Who it's for

---

## TP Introduction Messaging

### Core Framing

**TP = Your Thinking Partner**

- Not a chatbot (you don't prompt it endlessly)
- Not an assistant (it doesn't wait for commands)
- It's a partner that understands your work and produces on your behalf

### Key Messages

1. **"You talk to TP like a colleague"**
   - Natural conversation, not rigid commands
   - Context-aware (knows your platforms, your history)
   - Proactive (surfaces attention items, suggests improvements)

2. **"TP handles the gathering"**
   - Pulls from your connected platforms
   - Synthesizes context you'd otherwise read manually
   - Stays fresh every cycle

3. **"TP learns from you"**
   - Not just corrections—preferences, tone, structure
   - Gets better at anticipating what you need
   - Your approval IS the training signal

### Example Conversation (for How It Works)

```
You: I need to send a weekly update to Sarah

TP: Got it. I see you have #engineering and #product connected.
    Should I pull from both for your updates?

You: Just engineering for now

TP: Perfect. When does Sarah need this?

You: Monday mornings

TP: I'll have your first draft ready Sunday evening.
    Based on this week's #engineering activity, here's what I'd include:
    [Draft preview]

    Want me to adjust anything?
```

---

## Content Deduplication

### Move from How It Works → About
- "The idea" section (context already exists, patterns are learnable)
- "What it's not" section
- Philosophy-heavy content

### Move from About → How It Works
- Any step-by-step flow content
- Technical notes about how extraction works

### Remove (Redundant)
- Duplicate "learning from edits" explanations (keep best version)
- Duplicate integration explanations (keep in Landing, reference elsewhere)
- Duplicate CTAs with identical messaging

---

## Page-Level Changes Summary

### Landing (`/`)
- **Keep**: IntegrationHub animation, value prop, integration showcase
- **Add**: "Your Thinking Partner handles the rest" mention
- **Maintain**: Clean, hook-focused, minimal text

### How It Works (`/how-it-works`)
- **Rewrite**: Becomes "Meet TP" page
- **New hero**: "Meet TP, your Thinking Partner"
- **New structure**: Conversational model, what TP does, the flow, learning
- **Add**: Chat-style example interaction
- **Remove**: Philosophy content (goes to About)

### About (`/about`)
- **Keep**: Origin story, philosophy, differentiation
- **Remove**: Flow/how-it-works content
- **Tighten**: More focused on "why" and "what we believe"

---

## Implementation

### Phase 1: How It Works Rewrite
1. New hero section with TP introduction
2. Chat example interaction
3. Simplified flow (TP-centric)
4. Remove philosophy content

### Phase 2: About Page Tightening
1. Absorb relevant philosophy from How It Works
2. Remove flow explanations
3. Strengthen differentiation section

### Phase 3: Landing Page Polish
1. Add TP mention in appropriate place
2. Ensure no overlap with How It Works

---

## Consequences

### Positive
- **Distinct pages**: Each page has clear purpose, no redundancy
- **TP introduced**: Users know what to expect (conversational interface)
- **Better story flow**: Landing (hook) → How It Works (meet TP) → About (philosophy)
- **Reduced confusion**: Clear mental model before signup

### Negative
- **Significant rewrite**: How It Works needs substantial changes
- **Content migration**: Some content moves between pages

### Neutral
- **Integration-First still valid**: TP is how you access the integration-powered system
- **Positioning unchanged**: Still supervision, not writing

---

## Relationship to Prior Docs

| Document | Status |
|----------|--------|
| INTEGRATION_FIRST_POSITIONING.md | Still valid for philosophy. This ADR updates page structure. |
| ADR-037 (Chat-First Surface) | Validated. Marketing now introduces what users will experience. |
| ADR-010 (Thinking Partner) | Validated. TP gets public introduction. |

---

## Summary

**The gap**: Marketing pages explain WHAT yarnnn does but not HOW users interact with it.

**The fix**: How It Works becomes "Meet TP" — introducing the conversational interface users will actually use.

**The result**: Clear page differentiation, TP properly introduced, better user preparation for the product experience.

---

*This ADR restructures marketing pages to introduce TP while maintaining Integration-First positioning.*
