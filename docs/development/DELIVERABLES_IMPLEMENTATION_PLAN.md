# Recurring Deliverables Implementation Plan

**Status:** Ready for execution
**Date:** 2026-02-01
**Reference:** ADR-018, YARNNN_CLAUDE_CODE_BUILD_BRIEF.md

---

## Phase 1: Data Model + Pipeline Foundation

**Goal:** Database schema and backend primitives for deliverables and chained execution.

### Tasks

#### 1.1 Database Migration (019_deliverables.sql)
- [ ] Create `deliverables` table
- [ ] Create `deliverable_versions` table
- [ ] Alter `work_tickets`: add `depends_on_work_id`, `chain_output_as_memory`, `deliverable_id`, `deliverable_version_id`, `pipeline_step`
- [ ] Add index on `depends_on_work_id` for dependency queries
- [ ] Add `agent_output` and `deliverable_feedback` to memories source_type

#### 1.2 Backend Models (api/models/)
- [ ] Create Pydantic models: `Deliverable`, `DeliverableVersion`, `DeliverableCreate`, `DeliverableVersionCreate`
- [ ] Extend `WorkTicket` model with new fields

#### 1.3 Deliverable CRUD API (api/routes/deliverables.py)
- [ ] POST /deliverables - create deliverable
- [ ] GET /deliverables - list user's deliverables
- [ ] GET /deliverables/{id} - get deliverable with recent versions
- [ ] PATCH /deliverables/{id} - update (schedule, sources, template)
- [ ] DELETE /deliverables/{id} - archive deliverable

#### 1.4 Pipeline Execution Service (api/services/deliverable_pipeline.py)
- [ ] `execute_deliverable_pipeline(deliverable_id)` - orchestrates 3-step chain
- [ ] `create_pipeline_work_tickets()` - creates gather/synthesize/stage tickets with dependencies
- [ ] Extend `execute_work_ticket()` to check `depends_on_work_id` before execution
- [ ] Implement `chain_output_as_memory` post-execution hook

#### 1.5 Context Assembly Extension (api/services/work_execution.py)
- [ ] Extend `load_context_for_work()` to include:
  - Past deliverable versions (last 3-5)
  - Feedback memories for this deliverable
  - Template structure
  - Recipient context

### Deliverable
- Pipeline can execute a 3-step chain: gather → synthesize → stage
- Outputs chain into memories automatically
- Synthesis agent receives enriched context

### Estimated Effort
3-4 days

---

## Phase 2: Onboarding + First Deliverable

**Goal:** User can set up a deliverable and receive a first draft in one session.

### Tasks

#### 2.1 Onboarding API Endpoints
- [ ] POST /deliverables/onboard - multi-step onboarding submission
- [ ] POST /deliverables/{id}/examples - upload past examples
- [ ] POST /deliverables/{id}/generate-first - trigger immediate first generation

#### 2.2 Example Parsing Service (api/services/example_parser.py)
- [ ] Parse uploaded documents (MD, DOCX, PDF, TXT)
- [ ] Extract: section structure, typical length, writing style markers
- [ ] Store as `template_structure` in deliverable

#### 2.3 Frontend: Onboarding Wizard (web/app/onboard/)
- [ ] Step 1: "What do you deliver?" - title, description
- [ ] Step 2: "Who receives it?" - recipient name, role, priorities
- [ ] Step 3: "Show me examples" - file upload (2-3 past examples)
- [ ] Step 4: "What sources inform this?" - URL list, document refs, descriptions
- [ ] Step 5: "When is it due?" - schedule picker (weekly/bi-weekly/monthly + day/time)
- [ ] Step 6: "Here's your first draft" - immediate generation, in-page display

#### 2.4 First Draft Generation
- [ ] Trigger pipeline synchronously after onboarding
- [ ] Display draft content with "Edit before approving" option
- [ ] Handle loading state during generation (30-60s expected)

### Deliverable
- Complete onboarding flow produces a first deliverable version
- First draft visibly reflects structure/style of uploaded examples

### Estimated Effort
4-5 days

---

## Phase 3: Review + Feedback Engine

**Goal:** User can edit staged deliverables, edits are captured and categorized.

### Tasks

#### 3.1 Diff Engine (api/services/diff_engine.py)
- [ ] Compute structured diff between draft_content and final_content
- [ ] Implement edit categorization:
  - Addition detection (content in final not in draft)
  - Deletion detection (content in draft not in final)
  - Restructure detection (same content, different position)
  - Rewrite detection (same meaning, different wording) - use LLM for semantic comparison
- [ ] Calculate `edit_distance_score` (normalized 0.0-1.0)

#### 3.2 Feedback Processing (api/services/feedback_processor.py)
- [ ] Convert categorized edits to preference summary
- [ ] Create memory with `source_type='deliverable_feedback'`
- [ ] Update deliverable_version with edit_categories, edit_distance_score

#### 3.3 Review API Endpoints
- [ ] PATCH /deliverable-versions/{id}/approve - with final_content
- [ ] PATCH /deliverable-versions/{id}/reject - with feedback_notes
- [ ] GET /deliverable-versions/{id}/diff - returns structured diff

#### 3.4 Frontend: Review Interface (web/components/deliverables/ReviewEditor.tsx)
- [ ] Rich text editor pre-populated with draft
- [ ] "Approve" button submits final_content
- [ ] "Reject & Refine" option opens chat refinement
- [ ] Optional: side-by-side diff view (draft vs. user edits)

#### 3.5 Staging Notifications
- [ ] Email notification when deliverable is staged
- [ ] Email includes: title, preview, "Review Now" link
- [ ] Use existing email infrastructure

### Deliverable
- Users can edit and approve staged deliverables
- Edits are categorized and stored as feedback
- Feedback memories included in subsequent synthesis

### Estimated Effort
5-6 days

---

## Phase 4: Dashboard + Quality Tracking

**Goal:** Deliverables-first dashboard showing status and quality trends.

### Tasks

#### 4.1 Dashboard API
- [ ] GET /deliverables/dashboard - aggregated view:
  - Upcoming (next due)
  - Staged (awaiting review)
  - Recent (last 5 delivered)
  - Quality summary per deliverable

#### 4.2 Quality Metrics Service
- [ ] Calculate edit_distance trend (last 5 versions)
- [ ] Calculate time-to-approval trend
- [ ] Calculate rejection rate

#### 4.3 Frontend: Deliverables Dashboard (web/app/dashboard/page.tsx)
- [ ] Replace current projects-first view
- [ ] Deliverable cards with:
  - Title, recipient
  - Status badge (due date or "Ready for Review")
  - Quality indicator (trend arrow + last score)
  - Quick actions (review, view history, pause)

#### 4.4 Frontend: Deliverable Detail View (web/app/deliverables/[id]/page.tsx)
- [ ] Version history timeline
- [ ] Per-version: draft/final diff, edit categories, approval status
- [ ] Quality trend chart (sparkline or small line chart)
- [ ] Settings panel: schedule, sources, recipient, template

#### 4.5 Navigation Update
- [ ] Primary nav: Deliverables (new default) | Projects | Settings
- [ ] Preserve project exploration but deprioritize in UI hierarchy

### Deliverable
- Users land on deliverables dashboard
- Quality trends visible per deliverable
- Full version history accessible

### Estimated Effort
4-5 days

---

## Phase 5: MCP Server

**Goal:** Claude Desktop/Chrome users can check deliverables via MCP.

### Tasks

#### 5.1 MCP Server Scaffold (api/mcp/)
- [ ] Basic MCP server using official SDK
- [ ] Authentication layer (API key or OAuth)
- [ ] Health check endpoint

#### 5.2 MCP Resources
- [ ] `deliverables://list` - list active deliverables
- [ ] `deliverables://{id}/latest` - latest version
- [ ] `deliverables://{id}/history` - version history
- [ ] `projects://{id}/context` - project memories

#### 5.3 MCP Tools
- [ ] `submit_deliverable_feedback` - external feedback
- [ ] `add_project_context` - contribute memory
- [ ] `trigger_deliverable_run` - ad-hoc generation

#### 5.4 Testing
- [ ] Test with Claude Desktop MCP connection
- [ ] Test with Claude Code MCP connection
- [ ] Document setup instructions

### Deliverable
- Claude Desktop users can check deliverable status via MCP
- External agents can contribute context and trigger runs

### Estimated Effort
4-5 days

---

## Phase 6: Refinement

**Goal:** Polish, edge cases, advanced features.

### Tasks

#### 6.1 TP Integration for Refinement
- [ ] "Refine via Chat" option in review interface
- [ ] TP receives deliverable context + draft
- [ ] TP responses update draft in-place

#### 6.2 Cold-Start Collaborative Flow
- [ ] Fallback when no examples uploaded
- [ ] TP walks user through improving first draft
- [ ] Refinement conversation becomes initial context

#### 6.3 Multiple Deliverables per Project
- [ ] Support linking multiple deliverables to one project
- [ ] Shared context across deliverables

#### 6.4 Advanced Feedback Analytics
- [ ] Dashboard showing aggregate learning progress
- [ ] "YARNNN has learned: you prefer bullet points, executive-level tone..."

### Deliverable
- Smooth experience for users without past examples
- TP integrated for ongoing refinement
- Analytics showing feedback impact

### Estimated Effort
3-4 days

---

## Total Estimated Effort

| Phase | Days |
|-------|------|
| Phase 1: Data Model + Pipeline | 3-4 |
| Phase 2: Onboarding + First Deliverable | 4-5 |
| Phase 3: Review + Feedback Engine | 5-6 |
| Phase 4: Dashboard + Quality Tracking | 4-5 |
| Phase 5: MCP Server | 4-5 |
| Phase 6: Refinement | 3-4 |
| **Total** | **23-29 days** |

---

## Dependencies & Blockers

### None Identified
- All required infrastructure exists (email, scheduling, agents, context assembly)
- No external API dependencies beyond current Anthropic usage
- No blocking architectural changes needed

### Risks
- **LLM-based edit categorization** (Phase 3) may need iteration to get accuracy right
- **Example parsing** (Phase 2) quality depends on document formats received
- **Cold-start quality** - first deliverable without examples may disappoint

---

## Success Criteria

### Phase 2 Complete (Demo-Ready)
- [ ] User completes onboarding and receives first draft in <2 minutes
- [ ] First draft reflects structure of uploaded examples

### Phase 4 Complete (Product-Ready)
- [ ] User with 4+ versions sees decreasing edit_distance
- [ ] Version 5 requires noticeably less editing than version 1

### Phase 5 Complete (A2A-Ready)
- [ ] Claude Desktop user can check deliverable status via MCP
- [ ] Pipeline output demonstrably better than manual Claude prompts

---

## Open Questions Before Execution

1. **Schedule picker UI**: Use existing cron-like syntax or provide friendly presets (weekly on Monday, bi-weekly, monthly)?
   - **Recommendation:** Friendly presets with optional advanced mode

2. **Example upload limits**: How many examples? Max file size?
   - **Recommendation:** 2-5 examples, 10MB per file (existing limit)

3. **First draft timeout**: Synchronous generation may take 30-60s. Show progress or move to async with notification?
   - **Recommendation:** Synchronous with progress indicator for Phase 2, can optimize later

4. **Edit categorization accuracy**: Start with rule-based or LLM-based?
   - **Recommendation:** Start LLM-based for accuracy, optimize later if cost is issue

5. **Recipient context storage**: Just text description or structured fields?
   - **Recommendation:** Start with text description, add structure if patterns emerge
