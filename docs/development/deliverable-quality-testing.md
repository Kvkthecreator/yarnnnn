# Deliverable Quality Testing — Session Log & Framework

**Date**: 2026-03-06
**Objective**: Validate whether YARNNN's deliverable types produce output that justifies the product's value proposition.

---

## 1. Framing the Question

The initial question was: *does YARNNN have the "magic" for a recursive sharing/growth loop?*

After several iterations, we reframed away from:
- Output polish or formatting (premature — polish is downstream of quality)
- Measurable quality metrics (premature — measuring implies we know what to measure)
- Showcasing a single type (wrong — it's about whether the type itself is right)

**The right question**: Do YARNNN's deliverable types represent jobs-to-be-done that people struggle with enough to pay for — and does the current pipeline produce output that proves it?

---

## 2. Choosing the Wedge Type

We evaluated all 7 deliverable types (ADR-093) against the product's core promise: **"Context in. Deliverables out." / "Autonomous AI that already knows your work."**

### Evaluation criteria:
- **Cross-platform by nature**: Does it require multi-platform synthesis? (This is YARNNN's differentiator)
- **Universal need**: Do most users in our ICP need this?
- **Natural recipient**: Is the output sent to someone? (Prerequisite for sharing loop)
- **Platform independence**: Does it work regardless of which platforms are connected?
- **Proves compounding**: Does it get better over time?

### Results:

| Type | Cross-platform | Universal | Has recipient | Platform-independent | Verdict |
|------|:-:|:-:|:-:|:-:|---|
| Digest | No (single place) | Yes | No (self) | No | Table stakes, not wedge |
| Brief | Yes | Narrow (needs calendar) | Yes | No (calendar-dependent) | Strong but dependent |
| **Status** | **Yes** | **Yes** | **Yes** | **Yes** | **Best wedge candidate** |
| Watch | Yes | Niche | No (self) | Yes | Retention play |
| Deep Research | Partial | Niche | Sometimes | Yes | Commoditized by ChatGPT etc. |
| Coordinator | Yes | Power-user | No | Yes | Advanced capability |
| Custom | Depends | Escape valve | Depends | Depends | Not a wedge |

### Why Status wins:
1. **Everyone writes them** — founders, consultants, team leads, ops managers
2. **Universally hated** — synthesizing across tools is the exact manual work YARNNN eliminates
3. **Natural sharing artifact** — status updates are *always sent to someone* (boss, team, investors)
4. **Platform-independent** — works with any combination of connected platforms
5. **Proves compounding** — a weekly status that learns your tone and audience preferences

### Why not Brief (meeting prep)?
- Calendar dependency makes it less adaptive
- Not all users connect Google Calendar
- Brief is the strongest *second* type once trust is established

### Sequencing model:
```
Acquisition wedge:     Status Update (cross-platform synthesis)
Trust builder:         Brief (meeting/event prep)
Retention foundation:  Digest (daily/weekly rhythm)
Deepening hooks:       Watch, Deep Research, Coordinator
```

---

## 3. Testing Approach

### Test setup:
- **User**: kvkthecreator@gmail.com (real production account)
- **Platforms**: Slack (active, synced today), Gmail (active, synced Mar 1), Notion (active, synced Feb 25)
- **Content volume**: Slack 229 items / Gmail 120 emails / Notion 25 pages
- **Deliverable**: `status` type, `recurring` mode, `cross_platform` binding, audience "leadership and stakeholders"

### What we tested:
Created a "Weekly Work Status" deliverable and ran it through the full production pipeline — context gathering → headless agent generation → output validation.

---

## 4. Issues Discovered (and Fixed)

### Issue 1: Source type field missing
**Symptom**: Context gathering returned 0 platform items — only user memory.
**Root cause**: `CrossPlatformStrategy.gather_context()` filters by `source.get("type") == "integration_import"`. Sources created without the `type` field are silently skipped.
**Fix**: Ensure all deliverable sources include `"type": "integration_import"`. This is a creation-path issue — TP and the UI need to always include this field.
**Impact**: Without this, the agent gets no platform data and produces a hollow output. This was the cause of the v1 production email with only tool-call text.

### Issue 2: Resource ID mismatch (Slack + Notion)
**Symptom**: Gmail content fetched correctly but Slack and Notion returned nothing.
**Root cause**: `get_content_for_deliverable()` queries by `resource_id`. Slack stores channel IDs (`C096DH6TMU3`), not names (`daily-work`). Notion stores page UUIDs, not `all`. Gmail works because `INBOX` normalizes to `label:INBOX` which matches.
**Fix (immediate)**: Used real resource_ids in source config.
**Fix (needed)**: The query should fall back to matching by `resource_name` when `resource_id` doesn't match, or the creation flow should always resolve to real IDs.

### Issue 3: Python 3.9 datetime parsing
**Symptom**: `Invalid isoformat string` error in freshness check.
**Root cause**: Python 3.9's `datetime.fromisoformat()` can't parse Supabase timestamps with microseconds + timezone offset.
**Fix**: Replaced with `dateutil.parser.isoparse()`.

### Issue 4: Failed versions still delivered (production scheduler)
**Symptom**: User received email with tool-call text ("Let me refresh the platform content...") instead of actual synthesis.
**Root cause**: Setting `next_run_at = NOW()` caused the production scheduler to pick up the deliverable before local testing. The scheduler ran it, the agent's output was just its tool-use prelude, and the delivery pipeline shipped that as the final content.
**Lesson**: When creating test deliverables in production, set `next_run_at` far in the future to prevent scheduler pickup.

---

## 5. Prompt Evolution

### v1 (original status prompt):
```
- Lead with a brief executive summary/TL;DR
- Cover what was accomplished, what's in progress, and what's blocked
```
**Result**: Flat summary, no platform attribution. 1918 chars, reads like generic AI output.

### v2 (two-part format):
Added PART 1 (cross-platform synthesis) + PART 2 (per-platform breakdown).
**Result**: Better structure but agent only produced Gmail section — skipped Slack and Notion.

### v3 (all-platforms directive):
Changed "Skip any platform with no meaningful content" → "Include ALL connected platforms... no update is still news."
**Result**: Agent still consolidated into "Platform Health" umbrella section.

### v4 (explicit output structure):
Added literal expected output skeleton:
```
## Slack
(channel-by-channel summary)
## Gmail
(notable emails, action items)
## Notion
(document updates, changes)
```
Plus: "Look for '## Slack:', '## Gmail:', '## Notion:' headers in the context — each platform that appears MUST get its own section."
**Result**: All 3 platforms produced as separate sections. 3617 chars, 465 words. Cross-platform connections visible.

### Key insight:
The model needs explicit structural guidance — "write a section per platform" is too vague. Showing the expected output skeleton (with `## Slack`, `## Gmail`, `## Notion` headers) reliably produces the desired format.

---

## 6. Output Assessment

### Final output structure:
```
# Weekly Work Status
## TL;DR (cross-platform synthesis)
## Key Accomplishments (draws from all platforms)
## Blockers and Risks
## Next Steps
---
## Slack (by channel)
## Gmail (by category)
## Notion (by document)
```

### What works:
- **Cross-platform synthesis is real** — Slack daily work items + Gmail infrastructure alerts + Notion architecture docs woven into a coherent narrative
- **Specific details from actual data** — "70% of free tier limit (500 minutes)", "$110 Anthropic billing", "1,200+ lines of dead code removed"
- **Per-platform breakdown provides evidence** — user can see where each insight came from
- **"No update is still news" works** — old #announcements content noted as "archive of December 2025 activity" rather than omitted

### What needs work:
- **Cross-platform connections are weak** — the synthesis section doesn't explicitly connect dots across platforms (e.g., "the Render build warnings in Gmail correlate with the heavy development activity in Slack")
- **Tone is still "AI report"** — despite user memory saying "prefers brief, conversational tone"
- **Stale data visibility** — Gmail last synced Mar 1, Notion Feb 25. The output doesn't flag this; user might think it's current
- **Content quality depends heavily on source selection** — wrong resource_ids = empty output. This needs to be bulletproof.

---

## 7. Next Steps

### Immediate (production quality):
1. Fix source `type` field requirement — ensure all creation paths include it
2. Fix resource_id resolution — query should match by `resource_name` as fallback
3. Deploy updated status prompt to production
4. Test with a user who has Calendar connected (4-platform status update)

### Short-term (prompt refinement):
5. Strengthen cross-platform connection language in synthesis section
6. Add freshness indicator — "Data as of: Slack (today), Gmail (5 days ago), Notion (9 days ago)"
7. Test tone adaptation — does the output actually shift with different audience/tone configs?

### Medium-term (product validation):
8. Run the same status deliverable for 3-4 weeks consecutively — does deliverable memory make v4 better than v1?
9. Test with a second user to verify it's not overfit to one person's context
10. Compare: would this user send this output to a stakeholder without editing?

---

## 8. Architectural Notes

### The status type is the wedge because:
The landing page promises "Context in. Deliverables out." — status is the purest expression of this. It takes whatever platforms you've connected, synthesizes across them, and produces a document shaped for a specific audience. No single-platform tool can do this. The more platforms connected, the more valuable the output.

### The two-part format is the right structure because:
- Part 1 (synthesis) = the intelligence layer — what YARNNN thinks matters
- Part 2 (platform breakdown) = the evidence layer — what actually happened where
- Users can skim Part 1 for the executive view or drill into Part 2 for specifics
- Recipients of the status update get both narrative and source attribution

### Connection to sharing/growth loop:
A status update that surfaces cross-platform insights the user didn't know about, formatted cleanly with per-platform evidence, is the artifact most likely to trigger the recursive loop: recipient sees polished output → asks "how did you make this?" → creator answers with YARNNN.
