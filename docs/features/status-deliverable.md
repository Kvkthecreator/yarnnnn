# Status Deliverable

**Status:** Canonical
**Date:** 2026-03-06
**Related:** [ADR-093: Deliverable Type Taxonomy](../adr/ADR-093-deliverable-type-taxonomy.md), [Quality Testing Session](../development/deliverable-quality-testing.md)

The status deliverable is YARNNN's wedge type — the purest expression of "Context in. Deliverables out."

---

## What it does

Synthesizes activity across all connected platforms (Slack, Gmail, Notion, Calendar) into a structured status update for a specific audience. No single-platform tool can produce this — the value scales with each platform connected.

## Why status is the wedge

| Criterion | Status |
|-----------|--------|
| Cross-platform by nature | Yes — synthesizes across all connected platforms |
| Universal need | Yes — founders, consultants, team leads, ops managers |
| Natural recipient | Yes — status updates are always sent to someone |
| Platform-independent | Yes — works with any combination of platforms |
| Proves compounding | Yes — learns tone, audience preferences over time |

## Output format: two-part structure

**Part 1 — Cross-Platform Synthesis** (intelligence layer):
- TL;DR executive summary
- Key accomplishments (drawn from all platforms)
- Blockers and risks
- Next steps with owners
- Cross-platform connections — cause-and-effect chains across platforms

**Part 2 — Platform Activity** (evidence layer):
- Separate `## Section` per connected platform
- Slack: grouped by channel
- Gmail: notable emails, action items
- Notion: document updates, changes
- Calendar: upcoming events (when present)

**Design rule:** Every platform with data gets a section. No update is still news — low activity is reported briefly ("Quiet week in #channel") to confirm nothing was missed.

## Why two parts

- Part 1 = what YARNNN thinks matters (the intelligence)
- Part 2 = what actually happened where (the evidence)
- Recipients get both narrative and source attribution
- Users can skim Part 1 or drill into Part 2

## Execution details

- **Binding:** `cross_platform` (via `CrossPlatformStrategy`)
- **Default mode:** `recurring` (weekly)
- **Headless agent:** 3 tool rounds max
- **Delivery:** Email via Resend (ADR-066)
- **Prompt version:** v4 — tracked in `api/prompts/CHANGELOG.md`

## Key files

| Concern | Location |
|---------|----------|
| Type prompt | `api/services/deliverable_pipeline.py` (TYPE_PROMPTS["status"]) |
| Execution strategy | `api/services/execution_strategies.py` (CrossPlatformStrategy) |
| Content fetching | `api/services/platform_content.py` (get_content_for_deliverable) |
| Generation pipeline | `api/services/deliverable_execution.py` (generate_draft_inline) |
| Quality testing | `docs/development/deliverable-quality-testing.md` |
