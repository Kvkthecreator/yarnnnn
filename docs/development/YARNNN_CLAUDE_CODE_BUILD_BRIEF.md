# YARNNN Build Brief: Recurring Deliverables Product

> **⚠️ Historical document** — Feb 1, 2026. The architecture has evolved significantly since this was written.
> Key superseded patterns in this doc:
> - `execute_deliverable_pipeline` / `execute_gather_step` → replaced by `deliverable_execution.py` (ADR-042)
> - `create_memory` tool calls → removed (ADR-064); memory extraction is now implicit via `services/memory.py`
> - `chain_output_as_memory` flag → removed (ADR-064)
> - Old 3-step pipeline pseudocode below reflects the **prior** design, not current
>
> For current architecture, see `docs/architecture/context-pipeline.md` and the ADR index.

**For:** Claude Code implementation
**Date:** February 1, 2026
**Repo:** github.com/Kvkthecreator/yarnnnn
**Stack:** FastAPI (api/) + Next.js (web/) + Supabase — monorepo, backend deployed at api.yarnnn.com on Render
**Companion:** `YARNNN_STRATEGIC_DIRECTION.md` (strategic rationale — read for full context)

---

## What We're Building

YARNNN is pivoting from a general-purpose "context-aware AI work platform" to a **recurring deliverables product**. Users set up recurring work they owe to other people (weekly reports, client updates, competitive briefs), YARNNN produces them on schedule, and the deliverables improve every cycle through accumulated context and user feedback.

Under the hood, this is a multi-agent pipeline with a shared context layer — positioned to become agent-to-agent (A2A) infrastructure. But the user-facing product is concrete and simple: "your recurring deliverables, handled and improving."

---

## Product Experience (What Users See)

### Onboarding Flow

The entry point is the deliverable, not the project or knowledge graph.

**Step 1 — "What do you deliver?"**
User describes a recurring deliverable: "Weekly status report for Client X" or "Monthly investor update" or "Bi-weekly competitive landscape brief." This creates both a Project and a Deliverable entity.

**Step 2 — "Who receives it?"**
Recipient context — name, role, what they care about. This informs synthesis tone and emphasis.

**Step 3 — "Show me examples"**
Strongly encourage uploading 2-3 past examples of the deliverable. These are the highest-leverage onboarding input — they encode structure, tone, content priorities, and recipient expectations. Parse and extract: section structure, typical length, writing style markers, recurring content categories.

**Step 4 — "What sources inform this?"**
Connect data sources or describe what information feeds into this deliverable. Could be: uploaded documents, URLs to monitor, descriptions of what information matters. Each becomes a context source.

**Step 5 — "When is it due?"**
Schedule: weekly on Mondays, bi-weekly on the 1st and 15th, monthly on the last Friday, etc.

**Step 6 — "Here's your first draft"**
Produce the first deliverable immediately. User reviews, edits, and either approves or requests refinement via chat (TP). Edits are captured as feedback.

### Ongoing Experience

The primary surface is a **Deliverables dashboard** (not a Projects explorer). Users see:
- Upcoming deliverables (what's due soon)
- Staged deliverables awaiting review (edit and approve)
- Recent deliveries with quality indicators
- Quality trend (edit distance decreasing over time)

### Deliverable Review Flow

When a deliverable is staged:
1. User receives notification (email via existing infrastructure)
2. User opens the staged deliverable
3. User can: approve as-is, edit before approving, reject with feedback, or refine via chat
4. On approval: deliverable is marked as delivered, user copies/exports to send via their own channels
5. Edits are captured and categorized for the feedback engine

---

## Data Model Changes

### New Entity: Deliverable

The Deliverable is the core new entity. It represents a recurring commitment.

```
deliverables
├── id (UUID, PK)
├── user_id (UUID, FK → users)
├── project_id (UUID, FK → projects)
├── title (text) — "Weekly Status Report for Client X"
├── description (text) — what this deliverable is about
├── recipient_context (jsonb) — who receives it, what they care about
├── template_structure (jsonb) — extracted/defined sections, format preferences
├── schedule (jsonb) — cron expression or structured schedule
├── sources (jsonb) — connected data sources, URLs, document references
├── status (enum) — active, paused, archived
├── created_at (timestamp)
├── updated_at (timestamp)
```

### New Entity: Deliverable Version

Each execution produces a version. Versions are NOT overwritten — they accumulate.

```
deliverable_versions
├── id (UUID, PK)
├── deliverable_id (UUID, FK → deliverables)
├── version_number (integer) — sequential, 1-indexed
├── status (enum) — generating, staged, reviewing, approved, rejected
├── draft_content (text) — what YARNNN produced
├── final_content (text, nullable) — what the user actually approved/sent (after edits)
├── edit_diff (jsonb, nullable) — structured diff between draft and final
├── edit_categories (jsonb, nullable) — categorized feedback (additions, deletions, restructures, rewrites)
├── edit_distance_score (float, nullable) — 0.0 = no edits, 1.0 = complete rewrite
├── context_snapshot_id (UUID, nullable) — reference to the context state used for generation
├── feedback_notes (text, nullable) — explicit user feedback if rejected or refined via chat
├── pipeline_run_id (UUID, nullable) — reference to the work chain that produced this
├── created_at (timestamp)
├── approved_at (timestamp, nullable)
```

### Modified Entity: Work Tickets

Add chaining support to existing work_tickets table:

```sql
ALTER TABLE work_tickets ADD COLUMN depends_on_work_id UUID REFERENCES work_tickets(id);
ALTER TABLE work_tickets ADD COLUMN chain_output_as_memory BOOLEAN DEFAULT false;
ALTER TABLE work_tickets ADD COLUMN deliverable_id UUID REFERENCES deliverables(id);
ALTER TABLE work_tickets ADD COLUMN deliverable_version_id UUID REFERENCES deliverable_versions(id);
ALTER TABLE work_tickets ADD COLUMN pipeline_step (text); -- 'gather', 'synthesize', 'format'
```

### Modified Entity: Memories

Add agent-output source type:

```sql
-- Add to source_type enum or check constraint:
-- Existing: 'chat', 'document', 'manual', 'import'
-- Add: 'agent_output', 'deliverable_feedback'
```

---

## Execution Pipeline (Backend)

### The Deliverable Pipeline

Each deliverable execution runs a 3-step chained agent pipeline:

**Step 1: Gather**
- Agent type: research (existing)
- Input: deliverable sources configuration + project memories
- Action: pull latest context from configured sources, recent memories, any new inputs since last delivery
- Output: gathered context summary → saved as memory with source_type='agent_output'
- On completion: triggers Step 2

**Step 2: Synthesize**
- Agent type: content or reporting (existing, may need adaptation)
- Input: ContextBundle (existing load_context_for_work) enriched with Step 1 output + past deliverable versions + template structure + learned preferences from feedback history
- Action: produce the deliverable content following template structure and incorporating learned preferences
- Output: draft content → saved to deliverable_versions.draft_content
- On completion: triggers Step 3

**Step 3: Format & Stage**
- May not need a separate agent — could be a post-processing step
- Action: apply template formatting, generate staging notification
- Output: deliverable_version status set to 'staged', notification sent to user

### Chained Execution Logic

This requires the dependency-aware scheduling that the codebase assessment identified as a gap:

```python
# Pseudocode for the execution flow

async def execute_deliverable_pipeline(deliverable_id: str, version_number: int):
    deliverable = get_deliverable(deliverable_id)
    version = create_deliverable_version(deliverable_id, version_number)
    
    # Step 1: Gather
    gather_work = create_work_ticket(
        project_id=deliverable.project_id,
        agent_type="research",
        task=build_gather_prompt(deliverable),
        deliverable_id=deliverable_id,
        deliverable_version_id=version.id,
        pipeline_step="gather",
        chain_output_as_memory=True
    )
    await execute_work(gather_work)
    
    # Step 2: Synthesize (depends on gather)
    synthesize_work = create_work_ticket(
        project_id=deliverable.project_id,
        agent_type="content",
        task=build_synthesize_prompt(deliverable, version, gather_work.output),
        deliverable_id=deliverable_id,
        deliverable_version_id=version.id,
        pipeline_step="synthesize",
        depends_on_work_id=gather_work.id,
        chain_output_as_memory=True
    )
    await execute_work(synthesize_work)
    
    # Step 3: Stage
    version.draft_content = synthesize_work.output.content
    version.status = "staged"
    save(version)
    send_staging_notification(deliverable, version)


async def execute_work(ticket):
    # Check dependency
    if ticket.depends_on_work_id:
        dependency = get_work_ticket(ticket.depends_on_work_id)
        if dependency.status != "completed":
            raise DependencyNotMetError()
    
    # Execute using existing agent execution pipeline
    result = await run_agent(ticket)
    
    # Chain output as memory if flagged
    if ticket.chain_output_as_memory and result.work_output:
        create_memory(
            user_id=ticket.user_id,
            project_id=ticket.project_id,
            content=f"[{ticket.pipeline_step.upper()}] {result.work_output.content}",
            source_type="agent_output",
            importance=0.8,
            tags=[f"pipeline:{ticket.pipeline_step}", f"deliverable:{ticket.deliverable_id}"],
        )
```

### Context Assembly for Synthesis Step

The existing `load_context_for_work()` (scored 9/10) needs to be extended to include:

- **Past deliverable versions** — what was produced and approved previously
- **Edit feedback history** — categorized edits from past versions, synthesized into preferences
- **Template structure** — expected sections, format, length
- **Recipient context** — who this is for, what they care about

This is the most critical piece. The synthesis agent needs to receive a prompt that says, in effect: "Here is the project context. Here is what was gathered this cycle. Here is the template structure. Here are the past 3 versions and what the user changed in each. The user tends to add budget details (you've been missing those) and remove technical jargon (keep it executive-level). Produce version N."

---

## Feedback Engine (Core Feature — Invest Heavily)

### Edit Capture

When a user edits a staged deliverable before approving:

1. Compute structured diff between `draft_content` and `final_content`
2. Categorize each edit:
   - **Addition** — user added content not in draft → context gap signal
   - **Deletion** — user removed content from draft → irrelevance signal
   - **Restructure** — user moved sections or reordered → format preference signal
   - **Rewrite** — user rephrased content keeping same meaning → tone/voice signal
3. Store categorized edits in `deliverable_versions.edit_categories`
4. Compute `edit_distance_score` (0.0 = no edits, 1.0 = complete rewrite)

### Feedback-to-Preference Loop

After categorized edits are captured:

1. Create a memory with `source_type='deliverable_feedback'` summarizing learned preferences:
   - "User consistently adds budget line items → include budget section"
   - "User consistently removes technical implementation details → keep executive-level"
   - "User prefers bullet points in the metrics section"
2. These feedback memories are included in the context bundle for subsequent synthesis steps
3. Over time, these accumulate into a robust preference model per deliverable

### Quality Metrics

Track per deliverable:
- `edit_distance_score` trend across versions (should decrease)
- Categories of edits over time (additions should decrease as context improves)
- Time-to-approval trend (should decrease)
- Rejection rate (should approach zero)

---

## Frontend Changes

### Primary Surface: Deliverables Dashboard

Replace the current Projects-first navigation with a Deliverables-first dashboard.

**Dashboard view shows:**
- Cards for each active deliverable
- Status badge: next due date, or "ready for review" if staged
- Quality indicator: edit distance trend (last 3-5 versions)
- Quick actions: review staged, view history, pause/edit schedule

### Deliverable Detail View

- Version history (accordion or timeline)
- For each version: draft vs. final diff view, edit categories, approval status
- Quality trend chart (edit distance over versions)
- Settings: schedule, sources, recipient context, template

### Onboarding Wizard

Multi-step form following the onboarding flow described above. Prioritize: getting to the first draft fast. Don't make the user configure everything before seeing output.

### Deliverable Review/Edit Interface

- Side-by-side or inline editor showing the staged draft
- Rich text editing for making changes
- On approval: diff computed automatically, feedback categorized
- Option to add explicit notes ("next time, include the Q1 comparison")

### What to Deprioritize in the Frontend

- Block/memory exploration UI — keep it accessible but don't make it primary
- Agent configuration UI — agents are pipeline stages now, not user-configured entities  
- General-purpose chat as entry point — TP becomes a support tool within deliverable refinement, not the landing experience

---

## MCP Integration (Build From Start, Ship Incrementally)

### MCP Server Exposing:

**Resources (read):**
- `deliverables://list` — list active deliverables with status
- `deliverables://{id}/latest` — latest version of a deliverable
- `deliverables://{id}/history` — version history
- `projects://{id}/context` — project context (existing memories/blocks)

**Tools (write):**
- `submit_deliverable_feedback` — external agent provides feedback on a deliverable
- `add_project_context` — external agent contributes context to a project
- `trigger_deliverable_run` — request an ad-hoc deliverable generation

This means a Claude Desktop user could say "check my YARNNN deliverables" and see what's due and what needs review. This makes YARNNN feel native to Claude power users.

### Implementation Note

The existing tool infrastructure (THINKING_PARTNER_TOOLS schema) is structurally similar to MCP tool definitions. The codebase assessment estimated 2-3 days for basic MCP server exposing current tools. Extend that to 4-5 days to include the deliverable-specific resources and tools.

---

## Scheduling Changes

### Current State
Cron-based scheduling for recurring work — time-based only.

### Needed
1. **Deliverable-aware scheduling:** Scheduler reads deliverable schedules and triggers pipeline execution at the right times
2. **Dependency-aware execution:** Within a pipeline run, Step 2 waits for Step 1, Step 3 waits for Step 2
3. **Event-based triggers:** "When gather completes, run synthesize" — not polling-based

### Implementation Approach
The simplest path: deliverable scheduler creates all pipeline work tickets with dependencies at trigger time, then the executor processes them in dependency order. No need for a complex event bus initially — sequential execution within a pipeline run is sufficient.

---

## Existing Infrastructure to Preserve

Per codebase assessment, these are strong and should not be refactored:

- **Context assembly pipeline** (`load_context_for_work`, ContextBundle) — extend, don't replace
- **Agent architecture** (BaseAgent, factory pattern) — add pipeline step awareness
- **Work execution pipeline** (timeout, error capture, status tracking) — add dependency awareness
- **Scheduling infrastructure** — extend with deliverable triggers
- **Email infrastructure** — use for staging notifications
- **Projects and Memories data model** — extend with new source types and relationships

---

## Implementation Sequence

### Phase 1: Data Model + Pipeline Foundation
- Deliverable and DeliverableVersion tables/models
- Work ticket chaining (depends_on, chain_output_as_memory, pipeline_step)
- Memory source_type extensions (agent_output, deliverable_feedback)
- Basic deliverable CRUD API endpoints
- Pipeline execution logic (3-step chain with dependency resolution)

### Phase 2: Onboarding + First Deliverable
- Onboarding wizard frontend (5-step flow)
- Past example upload and parsing
- Template structure extraction from examples
- First deliverable generation (immediate, in-session)
- Staging notification via email

### Phase 3: Review + Feedback Engine
- Deliverable review/edit interface
- Diff computation (draft vs. final)
- Edit categorization engine (additions, deletions, restructures, rewrites)
- Edit distance scoring
- Feedback-to-memory conversion (deliverable_feedback source type)
- Feedback inclusion in synthesis agent context

### Phase 4: Dashboard + Quality Tracking
- Deliverables dashboard (primary frontend surface)
- Version history view with diff display
- Quality trend visualization (edit distance over time)
- Schedule management UI

### Phase 5: MCP Server
- MCP server exposing deliverable resources and tools
- Authentication for external agent callers
- Claude Desktop / Claude in Chrome integration testing

### Phase 6: Refinement
- TP integration for deliverable refinement chat
- Cold-start collaborative flow (for users without past examples)
- Advanced feedback analytics
- Multiple deliverables per project support

---

## What NOT to Build

- Don't build automated direct delivery (email/Slack sending to recipients) — staging only for now
- Don't build a general-purpose "explore your knowledge graph" interface — context is a byproduct
- Don't build agent-type selection UI — agents are pipeline stages, not user choices
- Don't build complex workflow configuration — the pipeline is fixed (gather → synthesize → format)
- Don't build multi-provider agent routing (Claude vs. OpenAI selection) — use Claude API for all agents initially

---

## Success Criteria

**For the demo (end of Phase 2):**
- A user can set up a deliverable, upload past examples, and receive a first draft within the same session
- The first draft visibly reflects the structure and style of the uploaded examples

**For the product (end of Phase 4):**
- A user with 4+ deliverable versions sees measurably decreasing edit distance
- The 5th version requires noticeably less editing than the 1st
- The feedback engine correctly identifies and applies at least the most common preference patterns

**For the A2A thesis (end of Phase 5):**
- A Claude Desktop user can check deliverable status and trigger runs via MCP
- The pipeline demonstrably produces better output than running the same prompts manually in Claude, because of accumulated context and learned preferences

---

*This brief should be read alongside `YARNNN_STRATEGIC_DIRECTION.md` for the full strategic rationale behind these decisions. Questions about "why" are answered there; this document focuses on "what" and "how."*
