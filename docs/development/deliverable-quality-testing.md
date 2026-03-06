# Deliverable Quality Testing Framework

**Date**: 2026-03-06
**Objective**: Validate whether each deliverable type produces output that justifies the product's value proposition.

---

## Framework

### The question per type

Do YARNNN's deliverable types represent jobs-to-be-done that people struggle with enough to pay for — and does the current pipeline produce output that proves it?

### Evaluation criteria (wedge assessment)

| Criterion | Why it matters |
|-----------|----------------|
| Cross-platform by nature | YARNNN's differentiator — does it require multi-platform synthesis? |
| Universal need | Do most users in our ICP need this? |
| Natural recipient | Is the output sent to someone? (Prerequisite for sharing loop) |
| Platform independence | Does it work regardless of which platforms are connected? |
| Proves compounding | Does it get better over time? |

### Testing protocol

1. **Select type** — evaluate against criteria above, pick the next type to validate
2. **Create deliverable** — use a real production account with real platform data
3. **Run through full pipeline** — context gathering → headless agent → output
4. **Assess output** — does it deliver on the job-to-be-done? Would a user send this without editing?
5. **Iterate prompt** — refine until output reliably meets the bar
6. **Document** — record issues found, prompt evolution, and final assessment below

### Wedge sequencing (from Pass 1)

| Type | Cross-platform | Universal | Has recipient | Platform-independent | Verdict |
|------|:-:|:-:|:-:|:-:|---|
| Digest | No (single place) | Yes | No (self) | No | Table stakes, not wedge |
| Brief | Yes | Narrow (needs calendar) | Yes | No (calendar-dependent) | Strong but dependent |
| **Status** | **Yes** | **Yes** | **Yes** | **Yes** | **Best wedge candidate** |
| Watch | Yes | Niche | No (self) | Yes | Retention play |
| Deep Research | Partial | Niche | Sometimes | Yes | Commoditized by ChatGPT etc. |
| Coordinator | Yes | Power-user | No | Yes | Advanced capability |
| Custom | Depends | Escape valve | Depends | Depends | Not a wedge |

---

## Pass 1: Status (2026-03-06)

### Test setup

- **User**: kvkthecreator@gmail.com (real production account)
- **Platforms**: Slack (active, synced today), Gmail (active, synced Mar 1), Notion (active, synced Feb 25)
- **Content volume**: Slack 229 items / Gmail 120 emails / Notion 25 pages
- **Deliverable**: `status` type, `recurring` mode, `cross_platform` binding, audience "leadership and stakeholders"

### Issues discovered (and fixed)

**Issue 1: Source type field missing**
- Symptom: Context gathering returned 0 platform items — only user memory.
- Root cause: `CrossPlatformStrategy.gather_context()` filters by `source.get("type") == "integration_import"`. Sources created without the `type` field are silently skipped.
- Fix: Auto-include untyped sources with warning. Ensure all creation paths include `type` field.
- Impact: Without this, the agent gets no platform data and produces a hollow output.

**Issue 2: Resource ID mismatch (Slack + Notion)**
- Symptom: Gmail content fetched correctly but Slack and Notion returned nothing.
- Root cause: `get_content_for_deliverable()` queried by `resource_id` field, but DataSource model uses `source` field. Slack stores channel IDs (`C096DH6TMU3`), not names.
- Fix: Read `source.get("source") or source.get("resource_id")` + `resource_name` fallback query.

**Issue 3: Python 3.9 datetime parsing**
- Symptom: `Invalid isoformat string` error in freshness check.
- Fix: Replaced `datetime.fromisoformat()` with `dateutil.parser.isoparse()`.

**Issue 4: Failed versions still delivered (production scheduler)**
- Symptom: User received email with tool-call text instead of actual synthesis.
- Root cause: Setting `next_run_at = NOW()` caused scheduler to pick up deliverable before local testing completed.
- Lesson: Set `next_run_at` far in the future when creating test deliverables in production.

### Prompt evolution

| Version | Change | Result |
|---------|--------|--------|
| v1 | Original flat prompt | 1918 chars, generic AI output, no platform attribution |
| v2 | Added two-part format (synthesis + breakdown) | Better structure but only Gmail section produced |
| v3 | "No update is still news" directive | Agent still consolidated into umbrella section |
| v4 | Explicit output skeleton with `## Slack`, `## Gmail`, `## Notion` headers | All 3 platforms produced. 3617 chars, 465 words. |

**Key insight:** The model needs explicit structural guidance — "write a section per platform" is too vague. Showing the expected output skeleton reliably produces the desired format.

### Output assessment

**What works:**
- Cross-platform synthesis is real — Slack items + Gmail alerts + Notion docs woven into coherent narrative
- Specific details from actual data — numbers, names, dates from real content
- Per-platform breakdown provides evidence — user sees where each insight came from
- "No update is still news" — low-activity platforms noted rather than omitted

**What needs work:**
- Cross-platform connections still weak — synthesis doesn't always connect dots explicitly *(addressed in prompt v4.1, 2026.03.06.2)*
- Tone defaults to "AI report" — needs more adaptation to audience/tone config
- Stale data not flagged — user doesn't know Gmail was synced 5 days ago
- Content quality depends on source selection — wrong resource_ids = empty output

### Outcome

Status validated as wedge type. Two-part format (intelligence + evidence) confirmed. Prompt at v4 with cross-platform connection language strengthened. Pipeline hardened: untyped source auto-include, resource_name fallback, datetime parsing fix.

---

## Pass 2: Brief

*Not yet started.*

---

## Pass 3: Digest

*Not yet started.*
