# ADR-010 Stress Tests: TP Movement Scenarios

**Purpose**: Validate that TP correctly follows the user across scopes, maintaining continuity while loading appropriate context.

**Metaphor**: TP is a personal assistant who physically follows you throughout your day, moving between projects and personal time.

---

## Test Scenario 1: Single Session, Multiple Scope Transitions

**User Journey:**
```
9:00am - User opens YARNNN (Dashboard/Orchestration)
9:05am - Clicks into "API Redesign" project
9:30am - Clicks back to Dashboard
9:35am - Clicks into "Marketing Campaign" project
10:00am - Closes browser
```

**Expected TP Behavior:**

| Time | Location | TP Should... |
|------|----------|--------------|
| 9:00 | Dashboard | Load user-level memories, list all projects, show pending work across all |
| 9:05 | API Redesign | Load user + API Redesign memories, API Redesign docs/work |
| 9:30 | Dashboard | Return to orchestration context, but remember we were just in API Redesign |
| 9:35 | Marketing | Load user + Marketing memories, Marketing docs/work |
| 10:00 | Close | Session persists for resume later |

**Stress Questions:**
1. Is this ONE session or multiple sessions?
2. When user returns to Dashboard at 9:30, does TP say "back from API Redesign"?
3. If user asks "what was I working on?" at 9:35 in Marketing, does TP know about API Redesign?

**Architectural Implication:**
- Session should be ONE continuous session with scope transitions logged
- Session needs `scope_history` or messages need `scope` field
- TP context loading must be dynamic per message, not per session

---

## Test Scenario 2: Conversation Continues Across Scope Change

**User Journey:**
```
User in Dashboard: "I need to research AI competitors"
TP: "I can start that research. Which project should I add the findings to?"
User: "The Product Strategy project"
[User clicks into Product Strategy project]
User: "Actually, let's also look at their pricing"
```

**Expected TP Behavior:**

| Message | Location | TP Should... |
|---------|----------|--------------|
| "research AI competitors" | Dashboard | Understand intent, ask for project scope |
| "Product Strategy project" | Dashboard | Create work_intent scoped to Product Strategy |
| [click into project] | Product Strategy | Seamlessly continue, now with project context loaded |
| "also look at pricing" | Product Strategy | Understand this continues the research request |

**Stress Questions:**
1. Does the work_intent get created BEFORE or AFTER user navigates to project?
2. When user clicks into project, does TP lose the conversation context?
3. Can TP reference "the research we just discussed" after scope change?

**Architectural Implication:**
- Conversation continuity must survive scope transitions
- Work creation should happen at orchestration layer, scoped to target project
- Message history carries across scope changes (it's the same session)

---

## Test Scenario 3: Document Upload During Scope Transition

**User Journey:**
```
User in "Client Project": "Here's the brief they sent" [uploads document]
TP: "Got it, I'll add this to Client Project and extract key points"
User clicks to Dashboard
User: "Actually, that brief has info relevant to Marketing too"
```

**Expected TP Behavior:**

| Action | Location | TP Should... |
|--------|----------|--------------|
| Upload | Client Project | Store doc with project_id = Client Project |
| Click Dashboard | Dashboard | Know about the just-uploaded document |
| "relevant to Marketing" | Dashboard | Offer to: copy to Marketing, move to user-level, or extract specific memories to Marketing |

**Stress Questions:**
1. After leaving Client Project, can TP still reference the document?
2. How does TP "copy" a document to another project? (duplicate? or just memories?)
3. If doc stays in Client Project, can Marketing project access its memories?

**Architectural Implication:**
- TP needs cross-project document awareness at orchestration layer
- Documents belong to ONE project, but memories extracted can be scoped differently
- "Copy to project" = extract memories with different project_id, not duplicate file

---

## Test Scenario 4: Work Started in One Project, Discussed in Another

**User Journey:**
```
User in "Research Project": "Research the competitor landscape"
TP: [creates work_intent, scoped to Research Project]
[Later that day]
User in "Strategy Project": "How's that competitor research going?"
```

**Expected TP Behavior:**

| Message | Location | TP Should... |
|---------|----------|--------------|
| "Research competitor landscape" | Research Project | Create work scoped to Research Project |
| "How's that research going?" | Strategy Project | Find the work (even though in different project), report status |

**Stress Questions:**
1. Can TP see work from other projects when scoped to Strategy Project?
2. If research completes, can Strategy Project access the outputs?
3. Should TP offer to "link" or "share" the research with Strategy Project?

**Architectural Implication:**
- At orchestration layer: TP sees ALL work across projects
- At project layer: TP sees project work + can query cross-project if user asks
- Work outputs can be "shared" by promoting memories to user-level or target project

---

## Test Scenario 5: Proactive TP Reaches User in Wrong Context

**User Journey:**
```
Background: Research for "Product Project" completes
User is currently in "Sales Project"
TP sends notification: "Your research is ready!"
User clicks notification
```

**Expected TP Behavior:**

| Event | What Happens |
|-------|--------------|
| Work completes | TP knows it's for Product Project |
| Notification | Message says "Your Product Project research is ready" |
| User clicks | Should user land in Product Project? Or current location with context? |

**Stress Questions:**
1. Does clicking notification navigate user to Product Project?
2. If user stays in Sales Project but asks "show me", what happens?
3. Should notification deep-link to specific project?

**Architectural Implication:**
- Notifications should include project context
- Deep-link should navigate to relevant project (or offer choice)
- TP should handle "show me X from project Y" even when in project Z

---

## Test Scenario 6: Memory Scope Ambiguity

**User Journey:**
```
User in "Client A Project": "Remember that they prefer formal tone"
[Next day]
User in "Client B Project": "What tone should I use?"
```

**Expected TP Behavior:**

| Message | Location | TP Should... |
|---------|----------|--------------|
| "they prefer formal" | Client A | Create memory scoped to Client A (they = this client) |
| "what tone?" | Client B | NOT surface Client A's preference (different project) |

**But what if:**
```
User in Dashboard: "Remember that I prefer concise writing"
[Later]
User in any project: "What's my writing style?"
```

| Message | Location | TP Should... |
|---------|----------|--------------|
| "I prefer concise" | Dashboard | Create user-level memory (project_id = NULL) |
| "my writing style?" | Any project | Surface the user-level preference |

**Stress Questions:**
1. How does TP decide: user-level vs project-level memory?
2. "They" (client) vs "I" (user) - can TP infer scope from pronouns?
3. If user says "Remember this for all projects" - explicit user-level?

**Architectural Implication:**
- Memory scope inference is critical
- Default: project-level if in project, user-level if at orchestration
- Explicit override: "for all projects" / "just for this project"
- TP should confirm scope for important memories

---

## Test Scenario 7: The "Where Am I?" Problem

**User Journey:**
```
User has 5 projects, hasn't used YARNNN in a week
Opens app to Dashboard
User: "What was I working on?"
```

**Expected TP Behavior:**

TP should provide orchestration-level summary:
```
"Welcome back! Here's where things stand:

📁 Projects with recent activity:
- API Redesign: Last active 3 days ago, research pending review
- Marketing: Draft content ready for review
- Client Project: No pending items

⏳ Pending your review:
- Competitor analysis (API Redesign) - completed 2 days ago
- Blog post draft (Marketing) - completed yesterday

Would you like to dive into any of these?"
```

**Stress Questions:**
1. Does TP have access to cross-project summary at orchestration layer?
2. Can TP show "last active" per project?
3. How much history does TP load for a "cold start" session?

**Architectural Implication:**
- Orchestration layer needs aggregate queries across projects
- Need to track "last activity" per project
- Session cold-start should load: projects list, pending work, pending review

---

## Test Scenario 8: Rapid Context Switching (Mobile UX)

**User Journey (on mobile):**
```
User gets push: "Research ready for Product Project"
Taps notification → Opens Product Project
Reads for 30 seconds
Gets another push: "Meeting reminder" (from calendar, not YARNNN)
Switches away, comes back 5 minutes later
App reopens to... where?
```

**Expected Behavior:**

| Event | Expected State |
|-------|----------------|
| Tap notification | Land in Product Project, research context loaded |
| Switch away | Session suspended |
| Return after 5 min | Resume in Product Project, same context |
| Return after 1 hour | Resume in Product Project, but TP might re-summarize |
| Return next day | Start fresh at Dashboard? Or last location? |

**Stress Questions:**
1. How long does "current location" persist?
2. Should app remember last project or always start at Dashboard?
3. If session times out, is conversation history still available?

**Architectural Implication:**
- Session has timeout but should persist "last location"
- App state: last_project_id, last_active_at
- Fresh day = new session, but can reference yesterday's session

---

## Validation Matrix

For each scenario, validate these dimensions:

| Dimension | Question |
|-----------|----------|
| **Session** | Is it the same session or new? |
| **Context** | What memories/docs/work are loaded? |
| **Continuity** | Does TP remember what we were discussing? |
| **Scope** | Is TP aware of current scope? Can it cross-scope query? |
| **Navigation** | Where does user land after action? |
| **Persistence** | What survives browser close / next day? |

---

## Architectural Requirements Derived

From these stress tests, the architecture must support:

### 1. Single Session, Multiple Scopes
```python
Session {
    id
    user_id
    started_at
    current_scope: "orchestration" | project_id
    # Messages track their own scope
}

Message {
    session_id
    scope: "orchestration" | project_id  # Scope when message was sent
    content
    ...
}
```

### 2. Dynamic Context Loading
```python
def load_context(user_id, scope, query=None):
    if scope == "orchestration":
        return OrchestrationContext(
            user_memories=...,
            all_projects=...,
            all_pending_work=...,
            all_pending_review=...,
        )
    else:
        return ProjectContext(
            user_memories=...,  # Always included
            project_memories=...,
            project_documents=...,
            project_work=...,
            # Can still query other projects if explicitly asked
        )
```

### 3. Cross-Scope Awareness
- At orchestration: full visibility
- At project: project-focused but can query other projects when asked
- Work/outputs can be "surfaced" across projects via TP

### 4. Scope Transition Logging
```python
# When scope changes within session
log_scope_transition(
    session_id,
    from_scope,
    to_scope,
    timestamp,
    trigger: "user_click" | "tp_suggestion" | "notification_deeplink"
)
```

### 5. Memory Scope Inference
```python
def infer_memory_scope(content, current_scope, explicit_scope=None):
    if explicit_scope:
        return explicit_scope
    if current_scope == "orchestration":
        return "user"  # Default to user-level
    if contains_user_reference(content):  # "I prefer", "my style"
        return "user"
    return current_scope  # Default to current project
```

### 6. Notification Deep-Linking
```python
Notification {
    user_id
    target_scope: project_id | "orchestration"
    action: "view_output" | "review_work" | ...
    deep_link: "/projects/{id}?focus=output-{output_id}"
}
```

---

## Next Steps

1. Review these scenarios with Kevin
2. Identify which current implementation handles correctly vs needs work
3. Prioritize gaps based on user impact
4. Update ADR-010 with any architectural refinements
