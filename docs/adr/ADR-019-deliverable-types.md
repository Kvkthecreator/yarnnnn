# ADR-019: Deliverable Types System

**Status:** Proposed
**Date:** 2026-02-02
**Extends:** ADR-018 (Recurring Deliverables Product Pivot)

## Context

ADR-018 established the recurring deliverables model but left deliverable creation freeform—users describe what they want in text. This creates two problems:

1. **Quality unpredictability**: We can't guarantee quality for arbitrary deliverable types
2. **Expectation mismatch**: Users may expect outputs we can't reliably produce (dashboards, slide decks, etc.)

We need to constrain the product to deliverable types we can confidently produce, enabling:
- Clear user expectations (positioning)
- Type-specific generation (quality)
- Measurable success criteria (validation)

## Decision

### Deliverable Type System

Replace freeform deliverable creation with a **type-first** approach. Users select from supported types, each with:
- Defined structure and sections
- Type-specific configuration options
- Quality criteria and validation
- Tailored generation prompts

### Tier 1 Types (Launch)

These types represent what LLM-generated written content does well: synthesis, summarization, and professional communication.

#### 1. Status Report
Weekly/recurring updates on project or team progress.

**Use cases:**
- Weekly team status to manager
- Project updates to stakeholders
- Sprint summaries

**Structure:**
- Summary/TL;DR
- Accomplishments (what was done)
- Blockers/challenges
- Upcoming/next steps
- Optional: metrics/numbers

**Configuration:**
```typescript
interface StatusReportConfig {
  subject: string;           // "Engineering Team", "Project Alpha"
  audience: 'manager' | 'stakeholders' | 'team' | 'executive';
  sections: {
    summary: boolean;        // default: true
    accomplishments: boolean; // default: true
    blockers: boolean;       // default: true
    next_steps: boolean;     // default: true
    metrics: boolean;        // default: false
  };
  detail_level: 'brief' | 'standard' | 'detailed';
  tone: 'formal' | 'conversational';
}
```

**Quality criteria:**
- All enabled sections present and populated
- Length appropriate to detail level (brief: 200-400 words, standard: 400-800, detailed: 800+)
- No hallucinated specifics (dates, numbers) without source data
- Appropriate tone for audience

---

#### 2. Stakeholder Update
Formal communications to investors, board, clients, or executives.

**Use cases:**
- Monthly investor letter
- Quarterly board update
- Client progress report

**Structure:**
- Executive summary
- Key highlights/wins
- Challenges and mitigations
- Financial/metric snapshot (if applicable)
- Outlook/next period focus

**Configuration:**
```typescript
interface StakeholderUpdateConfig {
  audience_type: 'investor' | 'board' | 'client' | 'executive';
  company_or_project: string;
  relationship_context?: string; // "Series A investor", "Enterprise client"
  include_sections: {
    executive_summary: boolean;  // default: true
    highlights: boolean;         // default: true
    challenges: boolean;         // default: true
    metrics: boolean;            // default: false
    outlook: boolean;            // default: true
  };
  formality: 'formal' | 'professional' | 'conversational';
  sensitivity: 'public' | 'confidential';
}
```

**Quality criteria:**
- Professional, polished language appropriate to audience
- Balanced (highlights AND challenges, not just positive spin)
- Executive summary captures essence in 2-3 sentences
- Actionable outlook section

---

#### 3. Research Brief
Synthesized intelligence on competitors, market, or topic.

**Use cases:**
- Weekly competitive intelligence
- Market monitoring digest
- Technology landscape update

**Structure:**
- Key takeaways (TL;DR)
- Findings by topic/competitor
- Implications/what this means
- Recommended actions (optional)

**Configuration:**
```typescript
interface ResearchBriefConfig {
  focus_area: 'competitive' | 'market' | 'technology' | 'industry';
  subjects: string[];        // ["Competitor A", "Competitor B"] or ["AI trends", "Regulation"]
  purpose?: string;          // "Inform product roadmap decisions"
  sections: {
    key_takeaways: boolean;  // default: true
    findings: boolean;       // default: true
    implications: boolean;   // default: true
    recommendations: boolean; // default: false
  };
  depth: 'scan' | 'analysis' | 'deep_dive';
}
```

**Quality criteria:**
- Findings are specific and sourced (not generic)
- Implications connect findings to user's context
- Key takeaways are actionable, not just summaries
- Appropriate depth (scan: 300-500 words, analysis: 500-1000, deep_dive: 1000+)

---

#### 4. Meeting Summary
Recurring notes and action items from standing meetings.

**Use cases:**
- Weekly team sync notes
- 1:1 meeting summaries
- Project standup digests

**Structure:**
- Attendees/context
- Key discussion points
- Decisions made
- Action items (with owners)
- Follow-ups for next meeting

**Configuration:**
```typescript
interface MeetingSummaryConfig {
  meeting_name: string;      // "Engineering Weekly", "Product Sync"
  meeting_type: 'team_sync' | 'one_on_one' | 'standup' | 'review' | 'planning';
  participants?: string[];
  sections: {
    context: boolean;        // default: true
    discussion: boolean;     // default: true
    decisions: boolean;      // default: true
    action_items: boolean;   // default: true
    followups: boolean;      // default: true
  };
  format: 'narrative' | 'bullet_points' | 'structured';
}
```

**Quality criteria:**
- Action items have clear owners
- Decisions are explicitly stated
- Discussion points are substantive, not filler
- Appropriate length for meeting type

---

### Type: Custom (Legacy/Escape Hatch)

For users with needs outside Tier 1 types. Preserved from current freeform approach but:
- Clearly labeled as "experimental" or "custom"
- No quality guarantees
- May require more user guidance

```typescript
interface CustomConfig {
  description: string;
  structure_notes?: string;
  example_content?: string;
}
```

---

### Data Model Changes

```typescript
// New deliverable type enum
type DeliverableType =
  | 'status_report'
  | 'stakeholder_update'
  | 'research_brief'
  | 'meeting_summary'
  | 'custom';

// Type-specific config union
type TypeConfig =
  | { type: 'status_report'; config: StatusReportConfig }
  | { type: 'stakeholder_update'; config: StakeholderUpdateConfig }
  | { type: 'research_brief'; config: ResearchBriefConfig }
  | { type: 'meeting_summary'; config: MeetingSummaryConfig }
  | { type: 'custom'; config: CustomConfig };

// Updated Deliverable interface
interface Deliverable {
  id: string;
  title: string;

  // NEW: Type system
  deliverable_type: DeliverableType;
  type_config: TypeConfig['config'];

  // Preserved from ADR-018
  recipient_context?: RecipientContext;
  schedule: ScheduleConfig;
  sources: DataSource[];
  status: DeliverableStatus;

  // Metadata
  project_id?: string;
  created_at: string;
  updated_at: string;
  last_run_at?: string;
  next_run_at?: string;
  version_count?: number;
  latest_version_status?: VersionStatus;
}
```

**Database migration:**
- Add `deliverable_type` column (default: 'custom' for existing)
- Add `type_config` JSONB column
- Migrate existing `template_structure` to `type_config` for 'custom' type
- Deprecate `description` field (absorbed into type_config)

---

### Wizard Flow Changes

#### Current Flow (5 steps)
1. What do you deliver? (freeform title + description)
2. Who receives it?
3. Show me examples
4. What sources inform this?
5. When is it due?

#### New Flow (5 steps, type-aware)

**Step 1: Select Type**
- Visual cards for Tier 1 types
- "Custom" option at bottom
- Each card shows: icon, name, 1-line description, example use case

**Step 2: Configure Type** (type-specific)
- Status Report: subject, audience, sections to include, detail level
- Stakeholder Update: audience type, what to include, formality
- Research Brief: focus area, subjects to monitor, depth
- Meeting Summary: meeting name, type, format
- Custom: title, description, structure notes

**Step 3: Recipient Context** (unchanged)
- Who receives this?
- Tone/formality (may be pre-filled from type)

**Step 4: Sources** (unchanged, but type-aware hints)
- What informs this deliverable?
- Type-specific suggestions (e.g., "For competitive briefs, add competitor websites")

**Step 5: Schedule** (unchanged)
- When is it due?

---

### Generation Prompt Structure

Each type has a dedicated prompt template:

```python
TYPE_PROMPTS = {
    'status_report': """
You are writing a {detail_level} status report for {audience}.
Subject: {subject}

Include these sections:
{sections_list}

Tone: {tone}

Sources and context:
{sources_context}

Previous feedback (if any):
{feedback_history}

Write the status report now:
""",

    'stakeholder_update': """
You are writing a {formality} update for {audience_type}.
Company/Project: {company_or_project}
Relationship: {relationship_context}

Include these sections:
{sections_list}

This is {sensitivity} information.

Sources and context:
{sources_context}

Previous feedback (if any):
{feedback_history}

Write the stakeholder update now:
""",

    # ... similar for other types
}
```

---

### Quality Validation Pipeline

Before staging a version, run type-specific validation:

```python
def validate_output(deliverable_type: str, content: str, config: dict) -> ValidationResult:
    """
    Returns: { valid: bool, issues: list[str], score: float }
    """
    validators = {
        'status_report': validate_status_report,
        'stakeholder_update': validate_stakeholder_update,
        'research_brief': validate_research_brief,
        'meeting_summary': validate_meeting_summary,
        'custom': lambda c, cfg: ValidationResult(valid=True, issues=[], score=0.5),
    }

    return validators[deliverable_type](content, config)

def validate_status_report(content: str, config: dict) -> ValidationResult:
    issues = []

    # Check required sections present
    required_sections = [k for k, v in config['sections'].items() if v]
    for section in required_sections:
        if not section_present(content, section):
            issues.append(f"Missing section: {section}")

    # Check length
    word_count = len(content.split())
    expected = {'brief': (200, 400), 'standard': (400, 800), 'detailed': (800, 2000)}
    min_words, max_words = expected[config['detail_level']]
    if word_count < min_words:
        issues.append(f"Too short: {word_count} words (expected {min_words}+)")
    if word_count > max_words * 1.5:
        issues.append(f"Too long: {word_count} words (expected ~{max_words})")

    # Check for hallucination markers (dates, numbers without sources)
    if has_unsourced_specifics(content):
        issues.append("Contains specific dates/numbers not in sources")

    score = 1.0 - (len(issues) * 0.2)
    return ValidationResult(valid=len(issues) == 0, issues=issues, score=max(0, score))
```

---

### Success Metrics

Per-type tracking:

| Metric | Definition | Target |
|--------|------------|--------|
| First-run acceptance | User approves first version without major edits | >40% |
| Edit distance | How much user changes before approval | <0.3 (70%+ kept) |
| Discard rate | User discards instead of editing | <20% |
| Feedback sentiment | Thumbs up vs. thumbs down | >60% thumbs up |

---

## Consequences

### Positive
- **Clear value prop**: Users know exactly what YARNNN can produce
- **Predictable quality**: Type-specific prompts and validation
- **Better onboarding**: Concrete options vs. blank slate
- **Measurable improvement**: Track metrics per type
- **Foundation for expansion**: Easy to add Tier 2 types later

### Negative
- **Constrained scope**: Users can't request arbitrary deliverables
- **Migration complexity**: Existing deliverables need type assignment
- **Prompt engineering**: Each type needs tuned prompts
- **More code paths**: Type-specific UI, validation, generation

### Technical Debt
- Current freeform deliverables become 'custom' type
- May need to revisit 'custom' type if overused (indicates missing type)

---

## Implementation Plan

### Phase 1: Data Model (Backend)
1. Add `deliverable_type` and `type_config` columns
2. Create Pydantic models for each type config
3. Migrate existing deliverables to 'custom' type
4. Update create/update endpoints to handle types

### Phase 2: Wizard Refactor (Frontend)
1. New Step 1: Type selection cards
2. Step 2: Type-specific configuration forms
3. Update remaining steps with type-aware hints
4. Update TypeScript types

### Phase 3: Generation Pipeline
1. Create type-specific prompt templates
2. Implement validation functions per type
3. Add validation step before staging
4. Log validation results for analysis

### Phase 4: Quality Tracking
1. Add per-type metrics to dashboard
2. Track edit distance by type
3. Surface type-specific feedback patterns

---

## Open Questions

1. **Should 'custom' be hidden or discouraged?**
   - Option A: Available but with "experimental" label
   - Option B: Require explicit unlock (e.g., after 3 typed deliverables)
   - Recommendation: Option A for now, monitor usage

2. **How to handle type changes?**
   - User created as 'status_report' but wants to change to 'stakeholder_update'
   - Recommendation: Allow type change, clear type_config, preserve sources/schedule

3. **Type-specific examples?**
   - Should "Show me examples" step show type-appropriate samples?
   - Recommendation: Yes, include 1-2 example outputs per type

---

## Appendix: Tier 2 Types (Future)

After validating Tier 1, consider:

- **Email Draft**: Recurring outreach, follow-ups
- **Newsletter Section**: Content for regular newsletters
- **Preparation Brief**: Pre-meeting background docs
- **Changelog/Release Notes**: Product update communications
- **Performance Summary**: Individual or team performance digests
