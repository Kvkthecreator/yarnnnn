# Structured Output Schemas Per Skill

**Status:** Parked / Superseded — the problem this addresses (unstructured markdown outputs) is now solved architecturally. Section kinds (ADR-170, [output-substrate.md](../architecture/output-substrate.md)) define a typed component vocabulary with explicit data contracts per kind (narrative, metric-cards, entity-grid, trend-chart, etc.). The compose pipeline (ADR-177/213) parses LLM output into section partials. No further action needed on this doc — the thesis was correct; the implementation path is different (section kinds, not per-skill schemas). Retained as reasoning trail.
**Date:** 2026-03-17 (parked note updated 2026-05-04)
**Context:** Emerged from agent-native ecosystem discourse (conversation 2026-03-17)

---

## Problem

Agent outputs today are markdown text in `agent_runs.content`. All skills produce the same unstructured shape. This limits:
- **UI rendering** — can't render tables, charts, action items, citations distinctly per skill
- **Inter-agent consumption** — downstream agents can't reliably parse sections from upstream outputs
- **Export** — no structured data to generate PPT/Excel/PDF from

## Proposal

Define output schemas per skill. Agents produce structured JSON alongside (or instead of) markdown. Frontend renders richly per skill type.

### Candidate Schemas

| Skill | Output Shape | Key Sections |
|-------|-------------|-------------|
| **digest** | `{summary, items: [{source, title, excerpt, priority}], stats}` | Prioritized item list with source attribution |
| **prepare** | `{event, attendees: [{name, context}], agenda, action_items, background}` | Structured brief with attendee intelligence |
| **monitor** | `{baseline_ref, changes: [{type, description, severity}], recommendation}` | Diff-against-baseline with severity |
| **research** | `{thesis, findings: [{claim, evidence, confidence}], gaps, citations}` | Evidence-linked findings |
| **synthesize** | `{narrative, patterns: [{description, sources, confidence}], recommendations}` | Cross-source pattern detection |

### Implementation Approach

1. Define JSON schemas per skill (pydantic models or JSON Schema)
2. Inject schema into headless system prompt: "Structure your output as..."
3. Parse and store structured output in `agent_runs` (new `structured_content` JSONB column alongside `content`)
4. Frontend renders per-skill components
5. Inter-agent reading can query structured fields directly

### Why Parked

- Not architecturally blocking — can be added to existing pipeline without schema changes to agents table
- Least relevant to the agent identity/ecosystem questions being explored
- Value increases *after* inter-agent consumption exists (structured outputs are more useful when agents read them)
- File format generation (PPT/Excel) is downstream of structured schemas, not a separate decision

### Dependencies

- ADR-106 workspace architecture (structured outputs should write to workspace, not just agent_runs)
- Inter-agent reading (consumer of structured outputs)

---

*Parked 2026-03-17. Revisit when workspace + inter-agent reading are implemented.*
