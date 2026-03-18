# ADR-032: Platform-Native Frontend Architecture

> **Status**: Accepted (Phase 3 Complete)
> **Created**: 2026-02-09
> **Updated**: 2026-02-09 (Phase 3 Platform Resources UI complete)
> **Related**: ADR-028 (Destination-First), ADR-031 (Platform-Native Agents), ADR-023 (Supervisor Desk)
> **Builds On**: All 6 phases of ADR-031 now implemented in backend

---

## Context

ADR-028 and ADR-031 established a platform-native vision for agents:

- **ADR-028**: "The agent isn't the markdown. The agent is the act of putting something in Slack/Notion/Email at the right time."
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
| **Synthesizers** | Flag on agent (`is_synthesizer`) | First-class creation path |

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
   - When someone sets up a recurring agent, they're committing to:
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

### Key Insight: Platform-Centric Drafts

**Core principle**: Meet users where they are. Drafts should be **pushed to platforms**, not sit in YARNNN's UI waiting.

This fundamentally changes the model:

```
Old Model:  YARNNN generates → User reviews in YARNNN → User copies to platform
New Model:  YARNNN generates → Draft pushed to platform → User reviews/sends there
```

**Why this is better**:
1. Users live in Gmail/Slack/Notion—not YARNNN
2. Reduces friction (one less step, no context switching)
3. Draft is already in the right place when user wants to send
4. Natural notification: "You have a draft waiting"

---

### Phase 1: Platform-Centric Draft Mode (Launch)

**The blanket approach**:

| Platform | Draft Mode | Where Draft Lives |
|----------|------------|-------------------|
| **Gmail** | Draft in Gmail Drafts folder | Gmail app/web |
| **Slack** | DM from YARNNN Bot to user | Slack DMs |
| **Notion** | Draft page in staging location | Notion workspace |

**Why this works**:
1. Matches low-trust reality: user still reviews/sends
2. Meets users where they already work
3. No YARNNN UI required for review
4. Natural "inbox" pattern for each platform

---

### Gmail: Draft in Drafts Folder ✅

**API Capability**: Gmail API has native draft support via `drafts.create`.

**Current Implementation** ([gmail.py:845-915](api/integrations/core/client.py#L845-L915)):
- Creates MIME message with `To:`, `Subject:`, `CC:` headers
- Supports HTML body via platform variants
- Returns `draft_id` for reference

**User Flow**:
```
1. YARNNN generates email content
2. YARNNN calls Gmail API drafts.create()
3. Draft appears in user's Gmail Drafts folder
4. User opens Gmail, sees draft with:
   - To: prefilled (recipient from agent)
   - Subject: prefilled
   - Body: full content ready
5. User reviews, edits if needed, clicks Send
```

**Technical Path**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ YARNNN      │────>│ Gmail API   │────>│ Gmail       │
│ generates   │     │ drafts.     │     │ Drafts      │
│ email       │     │ create()    │     │ folder      │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                    Draft contains:
                    - To: recipient@company.com
                    - Subject: Weekly Status Update
                    - Body: Full HTML content
```

**Draft Metadata (Destination Context)**:

The draft should be fully self-contained. User opens it and knows exactly what it's for:

```
To: sarah@company.com
Subject: Weekly Status Update - Week of Feb 10
CC: (optional)

[Full email content here]
```

**No attribution footer**: The user is the author. YARNNN helps them write, but they take credit for the work. No "Prepared by YARNNN" or similar footers that users might forget to remove before sending.

**Notification Path**:
- YARNNN can optionally send push notification: "Draft ready: Weekly Status Update"
- Or rely on Gmail's natural "1 draft" indicator

**Implementation Checklist**:
- [x] `drafts.create()` API call works
- [x] Subject line prefilled
- [x] To: recipient prefilled
- [x] HTML body support (ADR-031 Phase 5)
- [x] Clean content (no attribution footer - user is the author)
- [ ] Thread context for replies (`thread_id`)
- [ ] YARNNN notification when draft created

---

### Slack: DM from YARNNN Bot 🔄

**API Capability**: Slack API supports DMs via `conversations.open` + `chat.postMessage`.

**Current Limitation**: SlackExporter only posts to channels, not user DMs.

**Proposed Flow**:
```
1. YARNNN generates Slack message content
2. YARNNN sends DM to user (via bot)
3. User receives DM with:
   - Clear destination context: "Draft for #team-updates"
   - Full message preview in Block Kit format
   - Copy button or forward instructions
4. User reviews, copies content, posts to destination channel
```

**Technical Path**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ YARNNN      │────>│ Slack API   │────>│ User's      │
│ generates   │     │ DM to user  │     │ Slack DMs   │
│ message     │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                    DM contains:
                    - Destination context
                    - Full draft content
                    - Copy/forward actions
```

**DM Format (Destination Context)**:

The DM must clearly indicate what the draft is for:

```
┌─────────────────────────────────────────────────────┐
│ 📝 Draft ready for #team-updates                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Here's what happened this week:                     │
│ • Completed feature X                               │
│ • Started work on Y                                 │
│ • Next week: Focus on Z                             │
│                                                     │
├─────────────────────────────────────────────────────┤
│ ℹ️ This is a draft. Copy the content above and      │
│    paste it in #team-updates when ready.            │
│                                                     │
│ [📋 Copy Message]  [🔗 Open #team-updates]          │
└─────────────────────────────────────────────────────┘
```

**Block Kit Structure**:
```python
{
    "blocks": [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📝 Draft ready for #team-updates"}
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Here's what happened this week:\n• Completed feature X\n• Started work on Y"}
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "ℹ️ This is a draft. Copy the content above and paste it in <#C123456|team-updates> when ready."}
            ]
        },
        {
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "📋 Copy Message"}, "action_id": "copy_draft"},
                {"type": "button", "text": {"type": "plain_text", "text": "🔗 Open #team-updates"}, "url": "slack://channel?team=T123&id=C456"}
            ]
        }
    ]
}
```

**Implementation Checklist**:
- [x] Add DM support to SlackExporter (`conversations.open`)
- [x] Resolve user Slack ID from email (`users.lookupByEmail`)
- [x] Format draft with destination context header (Block Kit)
- [x] Add "Open Channel" deep link
- [ ] Add "Copy Message" button (may need Slack app interactivity)
- [ ] Add Slack user ID caching (schema ready)

**Open Question**: Slack "Copy Message" interactivity:
- Slack buttons can trigger webhooks but can't directly copy to clipboard
- Options: (a) "Copy" shows modal with text to select, (b) Just format for easy manual copy

---

### Notion: Draft Page in Staging Location 🔄

**API Capability**: Notion API creates pages immediately—no native "draft" state.

**Workaround Options**:

| Option | How It Works | Pros | Cons |
|--------|--------------|------|------|
| **A: "YARNNN Drafts" database** | Create page in dedicated drafts database | Clear staging area, status property | User must move/copy to final location |
| **B: Draft page in target parent** | Create page with "[DRAFT]" prefix | Already in right place | Visible to others before review |
| **C: Private section in workspace** | Create in user's private area | Hidden until ready | User must move to final location |

**Recommendation**: Option A (YARNNN Drafts database)

**Proposed Flow**:
```
1. YARNNN generates Notion page content
2. YARNNN creates page in "YARNNN Drafts" database (one per user)
3. Page has properties:
   - Status: "Draft"
   - Target Location: "/Product Spec" (link to destination)
   - Created: timestamp
4. User opens Notion, sees draft page
5. User reviews, then either:
   - Moves page to target location, OR
   - Copies blocks to existing target page
```

**Technical Path**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ YARNNN      │────>│ Notion API  │────>│ YARNNN      │
│ generates   │     │ create page │     │ Drafts DB   │
│ content     │     │ in drafts   │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                    Page contains:
                    - Status: Draft
                    - Target: /Product Spec
                    - Full content
```

**Page Format (Destination Context)**:

The draft page must clearly indicate where it's meant to go:

```
┌─────────────────────────────────────────────────────┐
│ 📄 Weekly Project Update                            │
├─────────────────────────────────────────────────────┤
│ 📍 Target: /Projects/ProductX/Updates               │
│ 📅 Created: Feb 9, 2026                             │
│ 📊 Status: 🟡 Draft                                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ## This Week                                        │
│ - Completed feature X                               │
│ - Started work on Y                                 │
│                                                     │
│ ## Next Week                                        │
│ - Focus on Z integration                            │
│                                                     │
├─────────────────────────────────────────────────────┤
│ ℹ️ This is a draft. Move this page to the target   │
│    location or copy the content when ready.         │
│                                                     │
│ [🔗 Open Target Location]                           │
└─────────────────────────────────────────────────────┘
```

**Database Schema**:
```
YARNNN Drafts (Database)
├── Title (title)
├── Status (select): Draft | Sent | Archived
├── Target Location (url): Link to destination page
├── Target Name (rich_text): "/Product Spec"
├── Agent (relation): Link to YARNNN agent
├── Created (created_time)
└── Content (page body)
```

**Implementation Checklist**:
- [x] Add page creation to NotionExporter with "draft" format
- [x] Include target location property (link + name)
- [x] Add status property for tracking ("Draft")
- [x] Include destination context callout in page body
- [ ] Create "YARNNN Drafts" database on first Notion integration (user setup)

---

### Phase 1 Summary: Platform-Centric Drafts

| Platform | Draft Location | Destination Context | User Action |
|----------|---------------|---------------------|-------------|
| **Gmail** | Drafts folder | To:/Subject: prefilled | Open Gmail, click Send |
| **Slack** | DM from bot | "Draft for #channel-name" header | Copy content, paste in channel |
| **Notion** | YARNNN Drafts DB | "Target: /Page" property + link | Move page or copy blocks |

**Key Difference from Previous Approach**:

| Aspect | Old (YARNNN UI) | New (Platform-Centric) |
|--------|-----------------|------------------------|
| Review happens in | YARNNN web app | Native platform |
| Draft location | YARNNN database | Platform (Gmail/Slack/Notion) |
| User context switch | YARNNN → Platform | Stay in platform |
| Notification | Check YARNNN | Platform's native (email badge, Slack DM, Notion notification) |

---

### Draft Content Format Requirements

All drafts must be **clean and ready to send** - no attribution that users might forget to remove.

**Core Principle**: The user is the author. YARNNN helps them write, but they take credit for the work.

**Gmail**:
```
To: recipient@company.com  ← Prefilled
Subject: Weekly Status Update - Week of Feb 10  ← Prefilled

[Body content - clean, ready to send]
```

**Slack DM** (wrapper context for user, content is clean):
```
📝 Draft ready for #team-updates  ← Destination in header
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Draft content - clean, ready to copy]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️ Copy and paste in #team-updates when ready
```
The header/footer are for the user's benefit (in the DM). The content section they copy is clean.

**Notion Page**:
```
📍 Target: /Projects/ProductX/Updates  ← Database property (not in page body)
📊 Status: 🟡 Draft  ← Database property (not in page body)

[Page content - clean, ready to move/copy]
```
Target and status live in database properties, not in the page content itself.

---

### Phase 2: Trust-Based Automation Upgrade (Future)

After users have experienced quality drafts, offer automation:

**Trigger**: User has sent 5+ drafts for same destination without edits.

**Prompt** (in-platform or via YARNNN):
```
"Your weekly updates to #team-updates have been sent unchanged
the last 5 times. Want YARNNN to post directly next time?"

[Keep drafts]  [Enable auto-post]
```

**Per-Platform Automation (Phase 2)**:

| Platform | Auto Mode | Attribution |
|----------|-----------|-------------|
| **Gmail** | YARNNN sends directly | User's email (OAuth) |
| **Slack** | YARNNN bot posts to channel | "YARNNN Bot" (disclosed) |
| **Notion** | YARNNN creates page directly | "YARNNN Integration" |

**Governance Mapping (Phase 2)**:

| Setting | Gmail | Slack | Notion |
|---------|-------|-------|--------|
| **Manual** | Draft in Drafts folder | DM draft to user | Page in Drafts DB |
| **Semi-auto** | Send after user confirms | Bot posts after user confirms | Create in target after user confirms |
| **Full-auto** | Send immediately | Bot posts immediately | Create in target immediately |

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

This complexity is deferred. Phase 1 = blanket platform-centric draft mode.

---

## Implementation Phases

### Phase 1: Platform-Centric Draft Infrastructure

**Goal**: Push drafts to platforms, not YARNNN UI.

**Backend Changes**:

| Platform | Changes Needed |
|----------|----------------|
| **Gmail** | ✅ Already works (`drafts.create`) - Add destination context footer |
| **Slack** | 🔄 Add DM support to SlackExporter, format with destination header |
| **Notion** | 🔄 Create "YARNNN Drafts" database, add target location property |

**Backend Tasks**:
1. **Gmail**: Update draft body to include destination context footer
2. **Slack**: Extend SlackExporter to send DMs (not just channel posts)
3. **Slack**: Create Block Kit format with destination context header
4. **Notion**: Implement "YARNNN Drafts" database creation on integration setup
5. **Notion**: Update NotionExporter to create database items with target property
6. **All**: Add `delivery_mode: "draft"` to version tracking

**UI Changes** (minimal for Phase 1):
- Show draft delivery status in version history: "Draft sent to Gmail" / "Draft DM sent"
- Platform-specific notification copy

### Phase 2: Platform-First UI Restructure ✅

**Goal**: Restructure agent creation to destination-first.

**Previous State** (before Phase 2):
```
Old flow:
1. Title
2. Schedule (frequency, day, time)
3. Data Sources
4. Recipient (name, role, notes)
5. Delivery (destination + governance) ← last, optional
```

**Implemented Flow**:
```
New flow:
1. Destination (where does this go?) ← first, required
2. Title
3. Schedule (when?)
4. Sources (what informs it?)
5. Recipient (collapsed, optional)
```

**Completed UI Changes**:
- ✅ Restructured AgentSettingsModal: Destination → Title → Schedule → Sources → Recipient
- ✅ Made destination required (validation prevents save without destination)
- ✅ Defaulted governance to "manual" (platform-centric draft mode)
- ✅ Simplified governance (hidden, fixed to manual)
- ✅ Show platform icon/badge prominently in header

**Components Built**:
- ✅ `DestinationSelector` - First step, shows connected platforms with targets
  - Gmail: Draft/Send modes, recipient email input
  - Slack: DM draft/Post modes, channel selector
  - Notion: Draft/Page modes, target page input
  - Download: Always available fallback
- ✅ `DraftStatusIndicator` - Shows where draft was pushed with deep links
  - States: pending, delivering, delivered, failed
  - Platform-specific styling and icons
  - Deep links to platform (Gmail Drafts, Slack DM, Notion page)
- ✅ `DraftStatusBadge` - Compact version for list views

**Components Modified**:
- ✅ `AgentSettingsModal.tsx` - Destination-first flow, required validation
- ✅ `AgentReviewSurface.tsx` - Shows DraftStatusIndicator after approval
- ✅ `AgentDetailSurface.tsx` - Shows destination in header, DraftStatusIndicator for approved versions
- ✅ `types/index.ts` - Added `delivery_mode`, `delivery_error` to AgentVersion

### Phase 3: Platform Resources UI ✅

**Goal**: Surface linked platform resources to enable cross-platform context auto-suggestion.

**Completed Components**:
- ✅ `PlatformResourcesList` - Shows linked Slack channels, Gmail labels, Notion pages
  - Grouped by platform with platform-specific icons
  - Remove resource functionality
  - Empty state with add button
- ✅ `AddPlatformResourceModal` - Link new platform resources
  - Platform selection step
  - Auto-suggestions based on project name
  - Resource type, ID, and name input
- ✅ `ContextSummaryCard` - Shows cross-platform context stats
  - Total items count with platform breakdown
  - Latest item timestamps
  - Compact badge variant for inline use
- ✅ `ProjectDetailSurface` - Updated with Platform Resources section

**Hooks** (already built):
- `useProjectResources` - CRUD for platform resources
- `useResourceSuggestions` - Auto-suggest resources
- `useContextSummary` - Context availability stats

**Benefit**: When creating a agent, sources can be auto-suggested from linked platform resources instead of manual entry.

### Phase 4: TP Platform-First Flow (Future)

**Goal**: Teach TP to guide platform-first agent creation.

**TP Capabilities**:
- "Set up a weekly update to #leadership" → destination-first flow
- Auto-suggest sources from linked platform resources
- "What should appear in your weekly update?" → outcome-focused prompts
- "Your draft is ready in Gmail" → platform-aware confirmation

---

### Deferred: Automation Features (Post-Launch)

The following phases are **deferred until post-launch** when we have real user data. These are nice-to-have features that add complexity without proven demand. Core feature reliability and user trust are the priority.

#### ~~Phase 5: Trust-Based Automation~~

*Deferred. Auto-posting based on "N unchanged drafts" is premature optimization. Will revisit after observing actual user behavior post-launch.*

~~**Goal**: Offer auto-posting after trust is established.~~

~~**Trigger**: 5+ drafts sent unchanged for same destination.~~

#### ~~Phase 6: Tiered Audience Governance~~

*Deferred. Different governance per audience type adds complexity without proven need. Manual/draft mode is sufficient for launch.*

~~**Goal**: Power users can configure different governance per audience type.~~

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
| Agents with destination configured | >80% of new agents |
| Time to first agent | <3 minutes |
| Draft-to-send completion rate | >90% (users actually send after copying) |
| Platform coverage (Slack + Gmail + Notion) | >60% of users connect 2+ |

---

## Open Questions

### Resolved

1. ~~**User ownership psychology**~~: Resolved. Users want ownership. Default to draft mode.

2. ~~**Slack user tokens**~~: Not needed for Phase 1. Bot DM is the draft mechanism.

3. ~~**Draft location strategy**~~: Resolved. Drafts pushed to platforms (Gmail Drafts, Slack DM, Notion DB).

4. ~~**Migration**~~: Existing agents continue working. Platform-centric drafts for new agents.

### Open

5. **Slack "Copy Message" interactivity**:
   - Slack buttons trigger webhooks, can't directly copy to clipboard
   - Options: (a) Button shows modal with selectable text, (b) Just format for easy manual copy
   - **Recommendation**: Start with (b), iterate based on feedback

6. **Notion Drafts database setup**:
   - When to create? On first Notion integration, or first Notion-targeted agent?
   - **Recommendation**: On first Notion-targeted agent (lazy creation)

7. **Slack user ID resolution**:
   - Need to DM user, but have email not Slack user ID
   - Options: (a) Require user ID during OAuth, (b) Look up via `users.lookupByEmail`
   - **Recommendation**: (b) with caching

8. **Draft notification strategy**:
   - Should YARNNN also notify user (push notification, email) when draft is ready?
   - Or rely on platform's native notification (Gmail badge, Slack unread)?
   - **Recommendation**: Start with platform-native only, add YARNNN notification if users miss drafts

---

## Conclusion

**Platform-first is the correct direction.** Users think in platforms, not synthesis engines. The frontend should match this mental model.

**Phase 1 approach**: Platform-centric drafts.
- Gmail: Draft created in Gmail Drafts folder (To/Subject prefilled)
- Slack: Draft DM sent to user from YARNNN Bot (with destination context)
- Notion: Draft page created in YARNNN Drafts database (with target location)

Key shifts:
- Destination becomes step 1 (not optional, not last)
- Synthesis becomes invisible (users see outcomes)
- Drafts meet users where they are (in-platform, not YARNNN UI)
- Ownership is preserved (user reviews and sends)
- Automation is an upgrade, not a default (trust builds over time)

**Implementation priority**:
1. Gmail: Already works, just add context footer
2. Slack: Add DM support + destination header formatting
3. Notion: Create drafts database + target property

---

## Appendix: Platform API Capabilities

### Gmail API

| Capability | Status | Implementation |
|------------|--------|----------------|
| Create draft with To/Subject | ✅ Works | [client.py:845-915](../api/integrations/core/client.py#L845-L915) |
| HTML body support | ✅ Works | ADR-031 Phase 5 platform variants |
| Thread replies (`thread_id`) | ✅ Works | Supported in destination options |
| CC recipients | ✅ Works | In destination options |
| OAuth token refresh | ✅ Works | Automatic refresh flow |

### Slack API

| Capability | Status | Implementation |
|------------|--------|----------------|
| Post to channel | ✅ Works | [slack.py](../api/integrations/exporters/slack.py) via MCP |
| Block Kit formatting | ✅ Works | `generate_slack_blocks()` |
| DM to user | ❌ Missing | Needs `conversations.open` + user ID lookup |
| User ID lookup | ❌ Missing | Needs `users.lookupByEmail` |
| Deep links to channels | ✅ Possible | `slack://channel?team=T&id=C` format |

### Notion API

| Capability | Status | Implementation |
|------------|--------|----------------|
| Create page | ✅ Works | [notion.py](../api/integrations/exporters/notion.py) via MCP |
| Database items | ✅ Works | Supported in destination format |
| Page properties | ✅ Works | Can set Status, URL properties |
| Draft/staging state | ❌ N/A | No native API support (use database status) |
| Markdown body | ✅ Works | Notion converts on creation |

### Implementation Gap Summary

| Platform | Gap | Effort | Status |
|----------|-----|--------|--------|
| Gmail | Add context footer to draft body | Low | ✅ Done |
| Slack | Add DM support + user ID lookup | Medium | ✅ Done |
| Slack | Format with destination header | Low | ✅ Done |
| Slack | User ID caching | Low | Schema ready |
| Notion | Add draft format with target property | Low | ✅ Done |
| Notion | Create drafts database on setup | Medium | User setup |

**Phase 1 Complete**: Backend infrastructure for platform-centric drafts is implemented.
- Migration: `033_platform_centric_drafts.sql`
- Gmail: Draft footer in `platform_output.py`
- Slack: DM support in `client.py` and `slack.py`
- Notion: Draft format in `notion.py`

---

## References

- [ADR-028: Destination-First Agents](./ADR-028-destination-first-agents.md)
- [ADR-031: Platform-Native Agents](./ADR-031-platform-native-agents.md)
- [ADR-023: Supervisor Desk Architecture](./ADR-023-supervisor-desk-architecture.md)
- [useProjectResources Hook](../../web/hooks/useProjectResources.ts)
- [Gmail Exporter](../api/integrations/exporters/gmail.py)
- [Slack Exporter](../api/integrations/exporters/slack.py)
- [Notion Exporter](../api/integrations/exporters/notion.py)
- [MCP Client](../api/integrations/core/client.py)
