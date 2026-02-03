# User Flows

End-to-end user journeys through YARNNN.

> **Updated for ADR-023: Supervisor Desk Architecture**
>
> The desk model: one persistent workspace, one surface at a time, TP always present.

---

## 1. First Open / Cold Start

**Entry**: User opens app with no deliverables

```
User authenticates
    ↓
Check state:
  - deliverable_count = 0
  - memory_count = 0
    ↓
Load Desk with IdleSurface
    ↓
Show onboarding prompts:
  "What recurring work do you produce?"
  [Weekly report] [Monthly update] [Meeting notes]
    ↓
TP bar shows contextual chips:
  [Weekly report] [Research] [My context]
```

**Key interaction**: User clicks chip or types → TP creates deliverable → surface changes to `deliverable-detail`

---

## 2. Daily Check-In (Attention Flow)

**Entry**: User opens app with staged deliverables

```
User opens app
    ↓
Backend: GET /deliverables/staged
    ↓
Load Desk with first attention item:
  { type: 'deliverable-review', deliverableId, versionId }
    ↓
AttentionBar shows: "2 need review [Weekly Report ▸] [Client Update ▸]"
    ↓
User reviews content on desk
    ↓
Actions available:
  [Discard] - Delete version, move to next
  [Skip] - Keep staged, move to next
  [Mark as Done ✓] - Approve version
    ↓
On action: Load next attention item or IdleSurface
```

**Key surfaces**:
- `deliverable-review` - Edit, refine, approve draft
- `idle` - "All caught up" when queue empty

---

## 3. Refining Content with TP

**Entry**: User viewing a deliverable version in review

```
DeliverableReviewSurface displayed
    ↓
TP chips show: [Shorter] [More detail] [More formal]
    ↓
User clicks "Shorter" OR types "Make this more concise"
    ↓
Frontend: POST /chat/stream
  - message: "Make this more concise"
  - surface_context: { deliverableId, versionId }
    ↓
TP receives context, calls refine_deliverable tool
    ↓
Tool result includes updated content
    ↓
TPBar shows status: "Updating content..."
    ↓
DeliverableReviewSurface updates with refined content
    ↓
TPBar returns to idle, shows: "Content updated"
```

**TP tool flow**:
1. User message arrives
2. TP chooses tool: `refine_deliverable` or `respond`
3. Tool executes, returns `ui_action`
4. Frontend handles `ui_action` (update surface, show response)

---

## 4. Conversation with TP (Unified Tool Model)

**Entry**: User asks TP something from any surface

```
User types message in TPBar
    ↓
POST /chat/stream (SSE)
  - session_id (or create new)
  - message content
  - surface_context (current desk surface)
    ↓
Backend builds context:
  - User memories (cross-cutting)
  - Surface-specific context (if deliverable/work)
  - Recent messages
    ↓
Claude processes with tools available
    ↓
TP MUST choose a tool (ADR-023 unified model):
  - respond(message) → Conversational reply
  - clarify(question, options) → Ask for input
  - Navigation tools → Open a surface
  - Action tools → CRUD operations
    ↓
Tool result returns ui_action:
  - RESPOND → Show message in TPBar status area
  - CLARIFY → Show question with inline options
  - OPEN_SURFACE → Change desk surface
    ↓
TPBar handles ui_action:
  - Displays response/clarification
  - Or triggers surface change via DeskContext
```

**TPBar states**:
- `idle` - Clean input, optional history toggle
- `thinking` - Spinner while processing
- `tool` - "Opening context...", "Creating project..."
- `streaming` - Real-time response text
- `clarify` - Question + clickable options
- `complete` - Brief confirmation, fades to idle

---

## 5. Browsing Data (Domain Browser)

**Entry**: User clicks [Browse ≡] button

```
User clicks Browse button in header
    ↓
DomainBrowser panel slides in from right
    ↓
Load data for all sections:
  GET /deliverables/staged → Needs Attention
  GET /deliverables → Deliverables list
  GET /work?limit=5 → Recent Work
  GET /memories/summary → Context counts
  GET /documents?limit=5 → Recent Documents
    ↓
User sees:
  ┌────────────────────────────────────────┐
  │ NEEDS ATTENTION (2)                    │
  │ ├─ ● Weekly Status Report              │
  │ └─ ● Client Update                     │
  │                                        │
  │ DELIVERABLES                           │
  │ ├─ Weekly Status Report                │
  │ ├─ Client Update                       │
  │ └─ + Create new deliverable            │
  │                                        │
  │ CONTEXT                                │
  │ ├─ About Me (12 memories)              │
  │ └─ → Manage all context                │
  │                                        │
  │ RECENT WORK                            │
  │ ├─ Market Analysis                     │
  │ └─ → View all work                     │
  └────────────────────────────────────────┘
    ↓
User clicks item
    ↓
Surface changes, browser closes
```

**Surface mappings**:
- Click "Weekly Status Report" (attention) → `deliverable-review`
- Click "Weekly Status Report" (deliverables) → `deliverable-detail`
- Click "About Me" → `context-browser` (scope: user)
- Click "Market Analysis" → `work-output`

---

## 6. Context/Memory Management

**Entry**: User wants to see/manage what TP knows

### 6a. View Context via TP

```
User types: "What do you know about me?"
    ↓
TP calls list_memories tool
    ↓
Tool returns memories + ui_action: OPEN_SURFACE
    ↓
Desk surface changes to: context-browser (scope: user)
    ↓
ContextBrowserSurface shows memories grouped by tags:
  PREFERENCES
  ├─ Prefers bullet points over paragraphs
  ├─ Uses "we" not "I" in reports

  COMPANY INFO
  ├─ Works at Acme Corp
  ├─ Engineering Manager, 8 reports
```

### 6b. Add Memory via TP

```
User types: "Remember that my manager's name is Sarah"
    ↓
TP calls create_memory tool:
  { content: "Manager's name is Sarah", tags: ["people"] }
    ↓
Tool returns: { success: true, message: "Got it, I'll remember that." }
    ↓
TPBar shows response, stays on current surface
```

### 6c. Edit Memory Directly

```
User on ContextBrowserSurface
    ↓
Clicks [Edit] on a memory
    ↓
Surface changes to: context-editor (memoryId)
    ↓
User edits content/tags
    ↓
Save → PUT /memories/{id}
    ↓
Return to context-browser
```

### 6d. Delete Memory

```
User on ContextBrowserSurface or via TP
    ↓
Option A: Click [Delete] on memory
Option B: "Forget the thing about Vue"
    ↓
TP calls delete_memory OR direct API call
    ↓
Memory removed, UI updates
```

---

## 7. Creating a Deliverable

**Entry**: User wants to set up recurring content

```
Option A: User types in TPBar
  "I need to send weekly status reports to my manager"
    ↓
Option B: User clicks chip in IdleSurface
  [Weekly report]
    ↓
TP recognizes intent, calls create_deliverable tool:
  {
    title: "Weekly Status Report",
    type: "status_update",
    schedule: { type: "weekly", day: "monday", hour: 9 }
  }
    ↓
Tool returns deliverable + ui_action: OPEN_SURFACE
    ↓
Surface changes to: deliverable-detail
    ↓
User can:
  - Click "Run Now" to generate first version
  - Adjust settings
  - Provide more context to TP
```

---

## 8. Running a Deliverable

**Entry**: Scheduled trigger or user request

### 8a. Scheduled Run

```
Cron job triggers at scheduled time
    ↓
Backend: Generate deliverable version
  - Load deliverable config
  - Load context (user memories, deliverable memories)
  - Call Claude to generate content
  - Store as new version (status: staged)
    ↓
Version ready for review
    ↓
Next time user opens app → appears in attention queue
```

### 8b. Manual Run

```
User on deliverable-detail surface
    ↓
User types "Run now" OR clicks Run Now button
    ↓
TP calls run_deliverable tool
    ↓
Backend generates version (same as scheduled)
    ↓
Tool returns version + ui_action: OPEN_SURFACE
    ↓
Surface changes to: deliverable-review
```

---

## 9. Approving a Deliverable Version

**Entry**: User reviewing a staged version

```
User on deliverable-review surface
    ↓
Reviews content, optionally refines with TP
    ↓
Clicks [Mark as Done ✓]
    ↓
PUT /deliverables/{id}/versions/{vid}/approve
    ↓
Version status: approved
    ↓
Background: Extract learnings from user edits
    ↓
Move to next attention item OR idle
```

**Learning extraction**:
- Compare original vs final content
- Extract patterns (length preference, tone, sections added)
- Store as deliverable-scoped memories

---

## 10. Research Work

**Entry**: User needs TP to research something

```
User types: "Research the AI assistant market"
    ↓
TP calls create_work tool:
  { task: "Research AI assistant market", type: "research" }
    ↓
Work item created, status: pending
    ↓
Background agent starts research:
  - Web search
  - Synthesize findings
  - Generate output
    ↓
Work status: completed
    ↓
User can view via:
  - TP: "Show me that research" → work-output surface
  - Browser: Click in Recent Work section
```

---

## 11. Document Upload

**Entry**: User uploads a document for context

```
User clicks upload (or drags file)
    ↓
POST /documents/upload (multipart)
    ↓
Backend validates:
  - File type (PDF/DOCX/TXT/MD)
  - Size < 25MB
    ↓
Upload to storage
    ↓
Process document:
  1. Extract text
  2. Chunk into segments
  3. Generate embeddings
  4. Extract memories (LLM)
  5. Store memories with user scope
    ↓
Document available in browser
Memories available to TP for context
```

**Key change from old model**: Documents extract user-scoped memories, not project-scoped.

---

## 12. Subscription Flow

### 12a. Upgrade to Pro

```
User clicks "Upgrade" in settings
    ↓
GET /subscription/checkout
    ↓
Redirect to payment provider
    ↓
User completes payment
    ↓
Webhook: subscription_created
    ↓
Update workspace:
  - subscription_status: pro
  - subscription_expires_at
```

### 12b. Manage Subscription

```
User clicks "Manage" in settings
    ↓
GET /subscription/portal
    ↓
Redirect to customer portal
    ↓
User cancels/updates
    ↓
Webhook updates workspace status
```

---

## Data Flow Summary (ADR-023)

```
                         ┌─────────────┐
                         │    User     │
                         └──────┬──────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        ┌───────────┐    ┌───────────┐    ┌───────────┐
        │   Desk    │    │   TPBar   │    │  Browser  │
        │ (Surface) │    │  (Input)  │    │ (Escape)  │
        └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
              │                │                │
              └────────────────┼────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │   Tool Execution    │
                    │                     │
                    │  respond()          │
                    │  clarify()          │
                    │  navigate tools     │
                    │  action tools       │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌───────────┐   ┌───────────┐   ┌───────────┐
        │OPEN_SURFACE│  │  RESPOND  │   │  CLARIFY  │
        └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
              │               │               │
              │               │               │
              ▼               ▼               ▼
        ┌───────────┐   ┌───────────┐   ┌───────────┐
        │  Change   │   │   Show    │   │   Show    │
        │  Surface  │   │  Message  │   │  Options  │
        └───────────┘   └───────────┘   └───────────┘
```

---

## Surface Type Reference

| Surface Type | Entry Points | Purpose |
|--------------|--------------|---------|
| `idle` | No attention items, cleared desk | Onboarding, quick actions |
| `deliverable-review` | Attention queue, TP navigation | Edit and approve draft |
| `deliverable-detail` | Browser, TP navigation | View metadata, history, run |
| `deliverable-list` | Browser, TP "show all deliverables" | List all deliverables |
| `work-output` | Browser, TP navigation | View research/work result |
| `work-list` | Browser, TP "show all work" | List work items |
| `context-browser` | Browser, TP "what do you know" | View memories by scope |
| `context-editor` | Click edit on memory | Edit single memory |
| `document-viewer` | Browser, TP navigation | View document content |
| `document-list` | Browser | List all documents |
| `project-detail` | Browser | View project settings |
| `project-list` | Browser | List all projects |

---

## Error Handling

| Flow | Error | User Experience |
|------|-------|-----------------|
| Surface load | Data fetch fails | Show error state with retry |
| TP message | Tool execution fails | TPBar shows error, stays on surface |
| Deliverable run | Generation fails | Version marked failed, show in review |
| Document upload | File too large | "Maximum size is 25MB" |
| Document upload | Extraction fails | Status: failed, error in record |
| Memory create | Duplicate detected | Silently merged or skipped |

---

## Key Differences from Previous Model

| Aspect | Old Model | ADR-023 Model |
|--------|-----------|---------------|
| Navigation | Tabs, drawers, pages | Single desk, surfaces flow through |
| TP presence | Floating chat, embedded inputs | Always-present TPBar |
| Context scope | Project-scoped | User-scoped (cross-cutting) |
| TP output | Free-form text | Explicit tool choice (respond/clarify/navigate/act) |
| Review flow | Tab per deliverable | Attention queue, one at a time |
| Browse data | Sidebar navigation | Domain browser escape hatch |
