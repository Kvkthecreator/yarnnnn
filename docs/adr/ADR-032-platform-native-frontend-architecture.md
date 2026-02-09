# ADR-032: Platform-Native Frontend Architecture

> **Status**: Draft (For Discussion)
> **Created**: 2026-02-09
> **Updated**: 2026-02-09 (Platform-first direction confirmed)
> **Related**: ADR-028 (Destination-First), ADR-031 (Platform-Native Deliverables), ADR-023 (Supervisor Desk)
> **Builds On**: All 6 phases of ADR-031 now implemented in backend

---

## Context

ADR-028 and ADR-031 established a platform-native vision for deliverables:

- **ADR-028**: "The deliverable isn't the markdown. The deliverable is the act of putting something in Slack/Notion/Email at the right time."
- **ADR-031**: "Platforms inform *what's worth saying*, not just *how to say it*."

The backend now implements all 6 phases of this vision:
- Ephemeral context storage
- Platform-semantic extraction
- Event triggers with cooldowns
- Cross-platform synthesizers
- Project-to-resource mapping
- Multi-destination delivery

**However, the frontend hasn't caught up.**

### Current Frontend State

Analysis of the existing UI reveals a **content-first mental model**:

| Aspect | Current UI | Platform-Native Vision |
|--------|-----------|----------------------|
| **Form Flow** | Title → Schedule → Sources → Recipient → Destination | Destination → Sources → Schedule → Content Shape |
| **Destination** | Optional (last step, nullable) | Required (first-class, informs everything) |
| **Sources** | Generic inputs ("URLs, documents, or integration data") | Platform-aware context ("Slack channels linked to this project") |
| **Project Resources** | Not surfaced | Central to cross-platform synthesis |
| **Synthesizers** | Flag on deliverable (`is_synthesizer`) | First-class creation path |

---

## First Principles: Platform-First is Correct

After stress-testing multiple approaches, we confirmed that **platform-first is the correct primary direction**.

### Why Platform-First

1. **Users think in platforms, not synthesis engines**
   - Users don't wake up thinking "I need a synthesizer"
   - They think: "I need to send my manager an update on Friday"
   - The platform is the *anchor*. Synthesis is the *mechanism*.

2. **Platforms are where users live**
   - Users don't live in YARNNN. They live in Slack, Gmail, Notion.
   - YARNNN is a backstage tool that makes their platform life easier.
   - UI should feel like "configuring what appears in my platforms"

3. **The output location is the commitment**
   - When someone sets up a recurring deliverable, they're committing to:
     - Not: "Run this synthesis every Friday"
     - But: "Every Friday, something should appear in #leadership-updates"

4. **Context accumulation serves platform outputs**
   - Over time, YARNNN accumulates context that makes outputs better
   - Better at what? Better at producing **platform-native outputs**
   - Context is in service of platform outputs, not an end in itself

5. **Cross-platform synthesis is a tactic, not the goal**
   - User goal isn't "synthesize my Slack + Gmail + Notion"
   - User goal is "give me a comprehensive status update"
   - We should talk about **outcomes**, not mechanisms
   - **Synthesis becomes invisible over time**

### The Activation Story

The simplest, most compelling activation:

> **"YARNNN writes your weekly updates and posts them for you."**

This is:
- Concrete (weekly updates)
- Platform-anchored (posts them)
- Outcome-focused (not mechanism-focused)

---

## Decision: Platform-First with Invisible Synthesis

**Recommendation**: Option A (Platform-First Flip) is the correct direction.

We previously hesitated due to:
1. Technical friction (attribution/ownership)
2. Migration complexity for existing users

But the first-principles analysis confirms: **users think platform-first**. The frontend should match this mental model, and we should solve the technical friction rather than compromise the vision.

### User Flow (Platform-First)

```
1. "Where do you need something to appear?"
   → Slack #leadership-updates
   → Email to manager
   → Notion /Project-Updates page

2. "What should appear there?"
   → Weekly status update
   → Project summary
   → Team digest

3. "What context should inform it?"
   → [Auto-suggested based on project resources]
   → Slack #team-general, Gmail inbox, Notion /Project-Notes

4. "When and how?"
   → Schedule: Fridays at 4pm
   → Governance: Review before sending (or auto-send)

5. Done
```

### Key Principles

| Principle | Implication |
|-----------|-------------|
| **Destination is step 1** | UI starts with "where does this go?" |
| **Synthesis is invisible** | Users see outcomes, not mechanisms |
| **Context is auto-suggested** | Project resources pre-populate sources |
| **Ownership is preserved** | User sends as themselves (see Technical Friction section) |

---

## Technical Friction: User Ownership

### The Core Tension

Users want: **"Do the work for me, but I take credit for it."**

This is especially true for:
- Status updates to leadership (don't want to look like "my bot wrote this")
- Client-facing emails (must come from me, not a bot)
- Meeting summaries (should look like I wrote them)

### Platform Reality

| Platform | Can YARNNN Post As User? | Attribution |
|----------|-------------------------|-------------|
| **Gmail** | Yes (OAuth sends as user) | User's email address |
| **Slack** | No (bot token) | "YARNNN Bot" |
| **Notion** | No (integration token) | "YARNNN Integration" |

### First-Principles Analysis: User Ownership Psychology

Ownership of work output has multiple dimensions:

| Dimension | Definition | Example |
|-----------|------------|---------|
| **Authorship** | "Who created this content?" | "I wrote this" vs. "AI wrote this" |
| **Attribution** | "Who does it appear to come from?" | Message from "Kevin" vs. "YARNNN Bot" |
| **Responsibility** | "Who is accountable for the content?" | "I stand behind this" |
| **Credit** | "Who gets recognized for the work?" | "Kevin is on top of things" |

### The Hierarchy of Stakes

Not all outputs have equal ownership stakes:

| Context | Ownership Stake | Why |
|---------|-----------------|-----|
| **Client/external email** | Very High | Professional reputation, relationship trust |
| **Update to leadership** | High | Career perception, competence signal |
| **Team channel post** | Medium | Peer perception, but internal |
| **Internal tool/log** | Low | No audience judgment |
| **Personal notes** | None | Only self sees it |

### When Bot Attribution is Acceptable

Bot attribution ("YARNNN Bot posted this") is acceptable when:

1. **The audience knows it's a workflow**
   - "Our team uses YARNNN for weekly digests"
   - The automation is disclosed and normalized
   - Example: #team-updates where everyone knows it's automated

2. **The output is utilitarian, not personal**
   - Meeting notes, calendar summaries, data reports
   - No personal voice or judgment expected
   - Example: "Here are the action items from today's standup"

3. **Speed/consistency matters more than personal touch**
   - Real-time alerts, status boards, automated reports
   - Timeliness > personal authorship

4. **The user explicitly opts for convenience**
   - "I don't care, just post it"
   - User has decided the tradeoff is worth it

### When User Attribution is Required

User attribution ("This came from Kevin") is required when:

1. **Professional reputation is at stake**
   - Updates to managers, executives, clients
   - The content reflects on the user's judgment

2. **The output has personal voice**
   - Opinions, recommendations, decisions
   - Reader expects a human perspective

3. **Trust/relationship is the medium**
   - Client communications, partner updates
   - The relationship is with the person, not the tool

4. **Credit/recognition matters**
   - The user wants to be seen as having done the work
   - Even if AI helped, they want attribution

### The Stakes Spectrum

```
LOW STAKES                                           HIGH STAKES
(Bot OK)                                            (Must be me)
    │                                                    │
    ▼                                                    ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Internal│ │Team    │ │Cross-  │ │Manager │ │Client  │ │External│
│logs    │ │channel │ │team    │ │update  │ │email   │ │publish │
│        │ │digest  │ │update  │ │        │ │        │ │        │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
     │          │          │          │          │          │
   AUTO       AUTO      EITHER     REVIEW     REVIEW      MUST
  (bot ok)  (bot ok)  (depends)  (user sends) (user sends) SEND
```

### Key Insight: The Disclosure Flip

There's a psychological flip point:

**Before disclosure**: "I don't want people to know AI wrote this"
**After disclosure**: "Now that everyone knows we use AI tools, I care less"

This suggests: **Normalization reduces ownership friction.**

If the team/org knows YARNNN is in use:
- Bot attribution becomes "Kevin's YARNNN posted this" (still Kevin's)
- The tool becomes an extension of the user, not a replacement

---

## Per-Platform Delivery Strategy

### Phase 1: Blanket "Draft Mode" (Launch)

**Core insight**: Early users have low trust. They *want* to review everything. Start with draft mode everywhere, let automation become an upgrade as trust builds.

**The blanket approach**:

| Platform | Phase 1 Mode | User Experience |
|----------|--------------|-----------------|
| **Gmail** | Draft → User sends | YARNNN prepares email, user clicks send in Gmail |
| **Slack** | Draft → User posts | YARNNN prepares message, user copies to Slack |
| **Notion** | Draft → User creates | YARNNN prepares content, user creates page in Notion |

**Why this works**:
1. Matches low-trust reality of new users
2. One consistent mental model: "YARNNN prepares, I send"
3. No per-channel, per-audience decisions
4. Trust builds naturally through quality

---

### Gmail: The Cleanest Path

Gmail has the simplest path because OAuth allows sending as the user.

**User Flow**:
```
1. YARNNN generates email draft
2. User reviews in YARNNN UI
3. User clicks "Send" (or "Open in Gmail")
4. Email sends FROM user's address
5. Recipient sees: "From: kevin@company.com"
```

**Technical Path**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ YARNNN      │────>│ Gmail API   │────>│ Recipient   │
│ generates   │     │ (OAuth)     │     │ inbox       │
│ draft       │     │ sends as    │     │             │
│             │     │ user        │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                    Attribution:
                    kevin@company.com
```

**Implementation Options**:

| Option | Description | UX |
|--------|-------------|-----|
| **A: Send from YARNNN** | User clicks "Send" in YARNNN, API sends | Seamless, one interface |
| **B: Open in Gmail** | YARNNN creates draft in Gmail, user opens and sends | User sees Gmail UI before send |
| **C: Copy to Gmail** | User copies content, pastes into Gmail compose | Most manual, full control |

**Recommendation**: Option A (Send from YARNNN) with Option B as fallback.
- Primary: "Send" button in YARNNN review UI
- Secondary: "Open in Gmail" for users who want to edit further

---

### Slack: Copy-to-Post Flow

Slack requires bot token, so true "post as user" isn't possible. Draft mode = user copies and posts.

**User Flow**:
```
1. YARNNN generates Slack-formatted message
2. User reviews in YARNNN UI (shows Slack preview)
3. User clicks "Copy for Slack"
4. User opens Slack, pastes in destination channel
5. Message appears from user, not bot
```

**Technical Path**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ YARNNN      │────>│ User's      │────>│ Slack       │
│ generates   │     │ clipboard   │     │ channel     │
│ Slack       │     │             │     │             │
│ blocks      │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                    User pastes
                    manually
                          │
                    Attribution:
                    Kevin Kim (user)
```

**Copy Format Considerations**:

Slack uses mrkdwn (not markdown). When user copies:
- Bold: `*text*` (not `**text**`)
- Links: `<url|text>`
- Mentions: `<@U123>` (but these won't resolve when pasted)

**Implementation**:

| Component | Behavior |
|-----------|----------|
| **Preview** | Show Slack-styled preview in YARNNN |
| **Copy button** | "Copy for Slack" - copies mrkdwn format |
| **Formatting** | Convert markdown → mrkdwn on copy |
| **Mentions** | Show as plain text (@name) since IDs won't resolve |

**UX Enhancement**:
- Show destination channel name: "Ready for #team-updates"
- One-click copy with success toast
- Optional: "Open Slack" button (deep link to channel)

---

### Notion: Copy-to-Create Flow

Notion integration creates as "YARNNN Integration". Draft mode = user copies blocks.

**User Flow**:
```
1. YARNNN generates Notion-formatted content
2. User reviews in YARNNN UI (shows Notion preview)
3. User clicks "Copy for Notion"
4. User opens Notion, creates new page, pastes
5. Page shows user as creator/editor
```

**Technical Path**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ YARNNN      │────>│ User's      │────>│ Notion      │
│ generates   │     │ clipboard   │     │ page        │
│ Notion      │     │             │     │             │
│ blocks      │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                    User pastes
                    manually
                          │
                    Attribution:
                    Kevin Kim (user)
```

**Copy Format Considerations**:

Notion accepts:
- Markdown (converts on paste)
- Rich text (preserves formatting)
- Notion blocks (if using Notion API clipboard format)

**Implementation**:

| Component | Behavior |
|-----------|----------|
| **Preview** | Show Notion-styled preview in YARNNN |
| **Copy button** | "Copy for Notion" - copies markdown (Notion converts) |
| **Formatting** | Standard markdown works well |
| **Structure** | Headers, bullets, toggles all paste correctly |

**UX Enhancement**:
- Show target page/database name if known
- "Copy as Markdown" (standard) vs "Copy as Rich Text" (experimental)
- Optional: "Open Notion" button (deep link to workspace)

---

### Phase 1 Summary: Draft Mode Everywhere

| Platform | Copy Format | Attribution | User Action |
|----------|-------------|-------------|-------------|
| **Gmail** | Email (HTML) | User's email | Click "Send" or "Open in Gmail" |
| **Slack** | mrkdwn | User posts manually | Copy → Paste in Slack |
| **Notion** | Markdown | User creates manually | Copy → Paste in Notion |

**Unified UX Pattern**:
```
┌────────────────────────────────────────────────────────┐
│ Review: Weekly Status Update                           │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ [Preview of content in platform style]             │ │
│ │                                                    │ │
│ │ Here's what happened this week...                  │ │
│ │ • Completed feature X                              │ │
│ │ • Started work on Y                                │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│ Destination: #team-updates (Slack)                     │
│                                                        │
│ ┌──────────────────┐  ┌──────────────────┐            │
│ │ Copy for Slack   │  │ Open Slack       │            │
│ └──────────────────┘  └──────────────────┘            │
│                                                        │
│ Or for Gmail:                                          │
│ ┌──────────────────┐  ┌──────────────────┐            │
│ │ Send Email       │  │ Open in Gmail    │            │
│ └──────────────────┘  └──────────────────┘            │
└────────────────────────────────────────────────────────┘
```

---

### Phase 2: Trust-Based Automation Upgrade (Future)

After users have experienced quality drafts, offer automation:

**Trigger**: User has approved 5+ deliverables for same destination without edits.

**Prompt**:
```
"Your weekly updates to #team-updates have been sent without changes
the last 5 times. Want YARNNN to post directly next time?"

[Keep reviewing]  [Enable auto-post]
```

**Per-Platform Automation (Phase 2)**:

| Platform | Auto Mode | Attribution |
|----------|-----------|-------------|
| **Gmail** | YARNNN sends via API | User's email (OAuth) |
| **Slack** | YARNNN bot posts | "YARNNN Bot" (disclosed) |
| **Notion** | YARNNN integration creates | "YARNNN Integration" |

**Governance Mapping (Phase 2)**:

| Setting | Gmail | Slack | Notion |
|---------|-------|-------|--------|
| **Manual** | Draft → User sends | Draft → User copies | Draft → User copies |
| **Semi-auto** | Send after approve | Bot posts after approve | Integration creates after approve |
| **Full-auto** | Send immediately | Bot posts immediately | Integration creates immediately |

---

### Tiered Audience Strategy (Phase 3, Future)

*Documented for completeness, not Phase 1 scope.*

For power users who want different governance per audience:

| Audience Type | Suggested Default |
|---------------|-------------------|
| Internal team channel | Semi-auto OK |
| Cross-team channel | Semi-auto OK |
| DM to manager | Manual (draft) |
| External/client | Manual (draft) |

This complexity is deferred. Phase 1 = blanket draft mode.

---

## Implementation Phases

### Phase 1: Platform-First Foundation + Draft Mode

**Goal**: Restructure UI to platform-first, implement draft-mode delivery.

**UI Changes**:
- Restructure DeliverableSettingsModal: Destination → Type → Sources → Schedule
- Make destination required
- Remove governance complexity (default all to "manual"/draft mode)
- Show platform-appropriate preview

**Per-Platform Delivery**:

| Platform | Implementation |
|----------|----------------|
| **Gmail** | "Send" button uses Gmail API (OAuth); "Open in Gmail" creates draft |
| **Slack** | "Copy for Slack" copies mrkdwn to clipboard; "Open Slack" deep links |
| **Notion** | "Copy for Notion" copies markdown; "Open Notion" deep links |

**Components to Build**:
- `PlatformPreview` - Shows content in platform-native styling
- `CopyForPlatformButton` - Platform-aware copy with format conversion
- `SendEmailButton` - Gmail OAuth send integration
- Update `DeliverableVersionDetail` with new action buttons

### Phase 2: Project Resources UI

**Goal**: Surface project resources to enable cross-platform context.

**Components**:
- Add Resources tab/section to `ProjectDetailSurface`
- `ProjectResourcesList` - Shows linked Slack channels, Gmail labels, Notion pages
- `AddProjectResourceModal` - Link new resources to project
- `ContextSummaryCard` - Shows "142 messages, 23 emails in last 7 days"

**Hooks** (already built):
- `useProjectResources` - CRUD for project resources
- `useResourceSuggestions` - Auto-suggest resources
- `useContextSummary` - Context availability stats

### Phase 3: TP Platform-First Flow

**Goal**: Teach TP to guide platform-first deliverable creation.

**TP Capabilities**:
- "Set up a weekly update to #leadership" → destination-first flow
- Auto-suggest sources from project resources
- "What should appear in your weekly update?" → outcome-focused prompts

### Phase 4: Trust-Based Automation (Future)

**Goal**: Offer auto-posting after trust is established.

**Trigger**: 5+ approved deliverables without edits for same destination.

**Implementation**:
- Track edit distance per deliverable/destination
- Prompt user to enable semi-auto or full-auto
- Per-platform automation (Gmail sends, Slack bot posts, Notion integration creates)

### Phase 5: Tiered Audience Governance (Future)

**Goal**: Power users can configure different governance per audience type.

- DM to manager → Manual
- Team channel → Semi-auto
- External → Manual

*Deferred until user demand is demonstrated.*

---

## Terminology Decision

**Avoid "synthesizer" in user-facing language.**

Instead, use outcome-focused terms:
- "Weekly Update" (not "Weekly Status Synthesizer")
- "Project Summary" (not "Cross-Platform Synthesizer")
- "Team Digest" (not "Slack Digest Synthesizer")

The synthesis is **invisible**. Users see the outcome.

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Deliverables with destination configured | >80% of new deliverables |
| Time to first deliverable | <3 minutes |
| Draft-to-send completion rate | >90% (users actually send after copying) |
| Platform coverage (Slack + Gmail + Notion) | >60% of users connect 2+ |
| Upgrade to auto-post (Phase 4) | 30%+ of high-frequency deliverables |

---

## Open Questions (Resolved)

1. ~~**User ownership psychology**~~: Resolved. Users want ownership. Default to draft mode.

2. ~~**Slack user tokens**~~: Not needed for Phase 1. Bot posting is Phase 2+ (opt-in).

3. ~~**Draft location strategy**~~: Resolved. Drafts live in YARNNN UI. User copies/sends from there.

4. **Migration**: How do we transition existing deliverables?
   - Answer: Existing deliverables continue working. New UI is for new deliverables.

5. **Gmail draft vs. send**: Should "Send" be primary or "Open in Gmail"?
   - Recommendation: "Send" primary, "Open in Gmail" secondary for power users.

---

## Conclusion

**Platform-first is the correct direction.** Users think in platforms, not synthesis engines. The frontend should match this mental model.

**Phase 1 approach**: Draft mode everywhere.
- Gmail: YARNNN sends via OAuth (user attribution preserved)
- Slack: User copies and posts (user attribution preserved)
- Notion: User copies and creates (user attribution preserved)

Key shifts:
- Destination becomes step 1 (not optional, not last)
- Synthesis becomes invisible (users see outcomes)
- Ownership is preserved (draft mode by default)
- Automation is an upgrade, not a default (trust builds over time)

---

## References

- [ADR-028: Destination-First Deliverables](./ADR-028-destination-first-deliverables.md)
- [ADR-031: Platform-Native Deliverables](./ADR-031-platform-native-deliverables.md)
- [ADR-023: Supervisor Desk Architecture](./ADR-023-supervisor-desk-architecture.md)
- [useProjectResources Hook](../../web/hooks/useProjectResources.ts)
