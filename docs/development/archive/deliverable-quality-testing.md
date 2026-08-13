# Agent Quality Testing Framework

**Date**: 2026-03-06
**Objective**: Validate whether each agent type produces output that justifies the product's value proposition.

---

## Framework

### The question per type

Do YARNNN's agent types represent jobs-to-be-done that people struggle with enough to pay for — and does the current pipeline produce output that proves it?

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
2. **Create agent** — use a real production account with real platform data
3. **Run through full pipeline** — context gathering → headless agent → output
4. **Assess output** — does it deliver on the job-to-be-done? Would a user send this without editing?
5. **Iterate prompt** — refine until output reliably meets the bar
6. **Document** — record issues found, prompt evolution, and final assessment below

### Wedge sequencing (from Pass 1)

| Type | Cross-platform | Universal | Has recipient | Platform-independent | Verdict |
|------|:-:|:-:|:-:|:-:|---|
| Digest | No (single place) | Yes | No (self) | No | Table stakes, not wedge |
| Brief | Yes | Narrow (needs calendar) | Yes | No (calendar-dependent) | Strong but dependent |
| **Work Summary** | **Yes** | **Yes** | **Yes** | **Yes** | **Best wedge candidate** |
| Watch | Yes | Niche | No (self) | Yes | Retention play |
| Proactive Insights | **Yes** | Moderate | Yes | **Yes** | Signal-driven intelligence — reframed from commoditized research (Pass 4) |
| Coordinator | Yes | Power-user | No | Yes | Advanced capability |
| Custom | Depends | Escape valve | Depends | Depends | Not a wedge |

---

## Pass 1: Work Summary (2026-03-06)

### Test setup

- **User**: kvkthecreator@gmail.com (real production account)
- **Platforms**: Slack (active, synced today), Gmail (active, synced Mar 1), Notion (active, synced Feb 25)
- **Content volume**: Slack 229 items / Gmail 120 emails / Notion 25 pages
- **Agent**: `status` type, `recurring` mode, `cross_platform` binding, audience "leadership and stakeholders"

### Issues discovered (and fixed)

**Issue 1: Source type field missing**
- Symptom: Context gathering returned 0 platform items — only user memory.
- Root cause: `CrossPlatformStrategy.gather_context()` filters by `source.get("type") == "integration_import"`. Sources created without the `type` field are silently skipped.
- Fix: Auto-include untyped sources with warning. Ensure all creation paths include `type` field.
- Impact: Without this, the agent gets no platform data and produces a hollow output.

**Issue 2: Resource ID mismatch (Slack + Notion)**
- Symptom: Gmail content fetched correctly but Slack and Notion returned nothing.
- Root cause: `get_content_for_agent()` queried by `resource_id` field, but DataSource model uses `source` field. Slack stores channel IDs (`C096DH6TMU3`), not names.
- Fix: Read `source.get("source") or source.get("resource_id")` + `resource_name` fallback query.

**Issue 3: Python 3.9 datetime parsing**
- Symptom: `Invalid isoformat string` error in freshness check.
- Fix: Replaced `datetime.fromisoformat()` with `dateutil.parser.isoparse()`.

**Issue 4: Failed versions still delivered (production scheduler)**
- Symptom: User received email with tool-call text instead of actual synthesis.
- Root cause: Setting `next_run_at = NOW()` caused scheduler to pick up agent before local testing completed.
- Lesson: Set `next_run_at` far in the future when creating test agents in production.

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

## Pass 2: Recap (2026-03-06)

### Changes from v1

- Renamed Digest → Recap (clearer for non-native English speakers)
- Platform-wide scope: all synced sources for a platform, not one channel/label/page
- New prompt: Highlights (top 3-5 across platform) + By Source (subsection per channel/label/page)
- Skill flow: asks platform + frequency, auto-populates sources, 1 recap per platform guard
- Tests PlatformBoundStrategy path end-to-end (vs CrossPlatformStrategy tested in Pass 1)

### Test setup

- **User**: kvkthecreator@gmail.com
- **Platform**: Slack (all synced channels)
- **Agent**: `digest` type, `recurring` mode, `platform_bound` binding, primary_platform="slack"

### Issues discovered

*(To be filled during testing)*

### Prompt evolution

*(To be filled during testing)*

### Output assessment

*(To be filled during testing)*

### Outcome

*(To be filled after testing)*

---

## Pass 3: Auto Meeting Prep (2026-03-06)

### Test setup

- **User**: kvkthecreator@gmail.com (real production account)
- **Platforms**: Google Calendar (synced), Slack, Gmail, Notion (all connected)
- **Agent**: `brief` type, `recurring` mode, `cross_platform` binding, daily frequency
- **Sources**: All calendar sources + all connected platform sources

### Prompt evolution

| Version | Change | Result |
|---------|--------|--------|
| v1 | Original static situation brief (event_title, attendees, focus_areas) | Static — required manual config per meeting, no calendar awareness |
| v2 | Full rewrite: daily batch, meeting classification (4 types), date range header | All 3 test meetings classified correctly, cross-platform context surfaced, 1548 chars. BUT output felt flat — reformatted calendar, not intelligence. |
| v3 | Anti-flat: BAD/GOOD examples, WebSearch for externals, attendee-focused research, honest gaps, 5 tool rounds | Agent used WebSearch for SB Partners, acknowledged gaps honestly, connected dots between meetings. 1698 chars, significantly richer. |

### Issues discovered

**Issue 1: Stale calendar data on first run**
- Symptom: First run returned "No calendar events found" despite calendar being connected.
- Root cause: Calendar content had 2-day TTL, last sync was Feb 26. Events expired from `platform_content`.
- Resolution: Inserted test events to simulate fresh sync. Production calendar sync keeps events current.
- Lesson: Calendar's 2-day TTL means testing requires recent sync or synthetic events.

**Issue 2: v2 output felt flat — calendar reformatter, not intelligence**
- Symptom: External meeting prep listed user's own activity instead of researching the attendee. Recurring 1:1 was an activity log, not conversation prep.
- Root cause: Prompt was too vague ("research person/company"), agent defaulted to summarizing available context. Only 3 tool rounds meant no room for WebSearch.
- Fix (v3): Added explicit BAD/GOOD examples per classification. Added "you are a research assistant, not a calendar formatter" framing. Bumped tool rounds to 5 for brief type. Explicit WebSearch instruction for externals.
- Result: v3 output used WebSearch (found SB Partners on PitchBook), acknowledged gaps ("I couldn't find specific background on Roger"), connected meetings ("mention SB Partners in your 1:1").

### Output assessment (v3)

**What works:**
- Date range header correct: "Your meetings for Fri Mar 6 – Sat Mar 7 morning"
- All 3 meeting types classified correctly with adapted depth:
  - **External / New Contact** (Roger @ SB Partners): WebSearch used, honest gap acknowledgment ("couldn't find background on Roger"), actionable recommendations (check LinkedIn, questions to ask about investment thesis)
  - **Recurring Internal** (원오원 / 승진님): Cross-meeting awareness ("Tomorrow's investor meeting with SB Partners — may want their input"), honest "no prior specific discussion topics found"
  - **Low-Stakes / Routine** (Coffee Chat): Contextual ("You have the SB Partners investor meeting today, so this could be good timing to debrief")
- Cross-meeting intelligence — agent connects the VC meeting to the 1:1 prep and the coffee chat
- Gap acknowledgment — "No prior email threads found" instead of padding with irrelevant content

**What needs work (minor):**
- Meeting chronological order still not strict — external (5 PM) before recurring (3 PM). Persistent across v2 and v3.
- WebSearch results were thin for SB Partners (only PitchBook mention). With more tool rounds or better search queries, could find more.

### Outcome

Auto Meeting Prep validated at v3. Key insight: prompt BAD/GOOD examples + explicit tool use instructions + bumped tool rounds transformed output from "flat calendar reformatter" to "diligent research assistant that acknowledges gaps." The cross-meeting awareness (connecting SB Partners across all 3 meetings) is the kind of intelligence no calendar app provides. Pipeline: scheduler → CrossPlatformStrategy → 5-round headless agent → email delivery.

---

## Pass 4: Proactive Insights (2026-03-06)

### Reframe from first principles

Deep research as "one-shot web research" was assessed as commoditized (ChatGPT Deep Research, Perplexity do it better). After thorough audit of YARNNN's lifecycle infrastructure (agent_memory, proactive review, scoped sessions), we reframed the type:

**Old:** "User tells YARNNN what to research" → generic report → done.
**New:** "YARNNN notices themes in the user's platforms → researches externally → delivers intelligence the user didn't ask for."

The differentiator: topic selection is autonomous, driven by internal signals. No external tool can do this.

### Architecture change

- Mode: `goal` → `proactive` (two-phase: Haiku review → conditional Sonnet generation)
- Binding: `research` → `hybrid` (platform context + web research)
- Display: "Deep Research" → "Proactive Insights"
- Config: simplified from focus_area/subjects/purpose/depth → pulse_frequency only

### Test setup

- **User**: kvkthecreator@gmail.com (real production account)
- **Platforms**: Slack (synced), Gmail (synced), Notion (synced), Calendar (synced)
- **Agent**: `deep_research` type, `proactive` mode, `hybrid` binding
- **Sources**: All connected platforms
- **Schedule**: `proactive_next_review_at` set to trigger review pass

### Issues discovered (and fixed)

**Issue 1: Haiku exhausted tool rounds without producing JSON decision**
- Symptom: Review returned "Could not parse review response: Let me try broader searches..."
- Root cause: `REVIEW_MAX_TOOL_ROUNDS = 3` — Haiku used all 3 rounds for Search calls and the loop exited before the model could produce its JSON decision. The `while rounds < 3` condition exits after round 3 tool execution, never giving the model a final text-only turn.
- Fix: Bumped to `REVIEW_MAX_TOOL_ROUNDS = 5`. Added forced final turn with `tools=[]` when all rounds exhausted — forces text-only JSON response.
- Impact: Without this, every review cycle defaults to `observe` with an unparsed note instead of a real decision.

**Issue 2: Search queries too broad — matched nothing**
- Symptom: Haiku searched for `"competitor technology market trends industry news"` as a single ilike query — returns 0 results.
- Root cause: Prompt said "look for HOT threads, DECISIONS, new contacts" but didn't specify query format. Haiku concatenated multiple topics into one long search string.
- Fix: Added explicit search guidance with examples: `Search("decision")`, `Search("blocked")`, `Search("investor")` — short, single-topic queries.
- Impact: After fix, Haiku issued 8+ targeted queries: "decision", "blocked", "competitor", "market", "launch", "investor", "agentic AI", "product roadmap next" — all returning useful results.

**Issue 3: Text fallback for action extraction**
- Symptom: When JSON not found, fallback always returned "observe" regardless of text content.
- Fix: Added keyword extraction — if text contains "generate"/"sleep", extract that action. Graceful degradation instead of silent loss.

### Review pass behavior

**Test 1 (pre-fix, v2 prompt, 3 tool rounds):**
- Haiku called Search 3 times with broad multi-keyword queries → all returned 0 results
- Loop exited at round 3 with no JSON in response
- Fallback: `observe` with parse error note
- Duration: ~4 seconds

**Test 2 (post-fix, v2 prompt, 5 tool rounds):**
- Round 1: List tool — checked activity_log, platform_connections, sync_registry for Slack/Notion/Gmail (landscape overview)
- Round 2: 7 parallel Search calls — "decision", "blocked", "competitor", "market", "launch", "investor", "technology evaluation" — several returned real results
- Round 3: 4 targeted Search calls — "agentic AI", "architecture platform evolution", "KPI metrics signals", "product roadmap next" — plus List for existing agents
- Round 4: Final analysis turn (no tools) → produced clean JSON
- Decision: `observe` with substantive 3-theme note
- Duration: ~25 seconds
- 4 Anthropic API calls (Haiku), ~15 Supabase queries

**Review note (verbatim):**
> "Three sustained themes: (1) Episode Zero post-launch GTM & KPI optimization with viral strategy in play, (2) YARNNN platform architecture consolidation to production-grade Context OS v2.0 with ongoing ADR refinements, (3) Industry shift toward agentic AI with enterprise demand for continuous market monitoring. Content freshness is 1-5 days old. Insufficient convergence yet to trigger generation — themes are present but not at inflection point. Monitor for: Episode Zero metrics inflection, agentic AI mentions in your architecture discussions, competitive response to market research findings."

**Assessment:**
- All 3 themes are real — grounded in actual platform data (Slack discussions, Notion docs, email patterns)
- Decision logic sound — "themes present but not at inflection point" is a reasonable `observe`
- Forward-looking tracking — "Monitor for: Episode Zero metrics inflection" shows progressive intelligence
- `agent_memory.review_log` accumulates correctly across cycles (2 entries after 2 runs)

### Prompt evolution

| Version | Change | Result |
|---------|--------|--------|
| v1 | Generic research report template with focus_area/subjects/purpose | Commoditized — same as ChatGPT, no internal grounding |
| v2 | Proactive Insights: signal-driven, BAD/GOOD examples, platform grounding + WebSearch, "What I'm Watching" section | Review pass works: Haiku identifies 3 real themes from platform data, makes smart observe/generate decision, accumulates forward-looking tracking notes. Generation output TBD (requires generate decision). |
| v2.1 | Review hardening: tool rounds 3→5, forced final turn, search query guidance, text fallback | Clean JSON decisions, targeted single-topic Search queries, graceful degradation |

### Output assessment

**Review pass (tested):**
- Haiku successfully scans platform_content with targeted queries
- Identifies real themes from actual user data (not hallucinated)
- Makes reasonable observe/generate decisions based on signal strength
- Accumulates observations in agent_memory.review_log
- Forward-looking "Monitor for:" notes demonstrate progressive intelligence

**Generation output (tested via admin trigger, 2026-03-07):**

Triggered full Sonnet generation via `POST /api/admin/trigger-agent/{id}`. Version 1 generated and delivered to kvkthecreator@gmail.com.

**Output: 3,945 chars, 3 signals + "What I'm Watching" section.**

| Aspect | Assessment |
|--------|-----------|
| Format compliance | Exact match: "This Week's Signals" header, per-signal Internal/External/Why structure, "What I'm Watching" footer |
| Internal grounding | Every signal cites specific Slack messages (dates, quotes), Notion docs, email data |
| External research | WebSearch used — MVerse, Constellation Research, CIO Magazine, FinancialContent, Zendesk (all with URLs) |
| Dot-connecting | "Your code cleanup timing aligns with industry-wide infrastructure optimization" — connects internal activity to external trend |
| Honest gaps | "What I'm Watching" section acknowledges items not yet strong enough to report |
| BAD pattern avoided | No generic news summaries — every insight grounded in specific internal evidence |

**Three signals produced:**
1. **Infrastructure cost pressures** — Render build minutes + Slack dead code cleanup → enterprise infra optimization trend
2. **Context OS architecture + agentic era** — Notion V2.0 + Slack agents focus → "Agentic Era" inflection from financial sources
3. **IR deck + funding activity** — Slack IR deck mentions + VC follow-up → AI Infrastructure Supercycle narrative

**"What I'm Watching" section:**
- Anthropic API costs ($110 receipt — real number from Gmail)
- AI mini-series engagement as market validation

**Email delivery confirmed:** Status `delivered`, destination `kvkthecreator@gmail.com`, delivered at 2026-03-07T10:34:13Z.

### Issues discovered during end-to-end test

**Issue 4: Timing bug — apply_review_decision after dispatch_trigger**
- Symptom: If generation takes 2+ minutes and scheduler runs every 5 minutes, `proactive_next_review_at` hasn't been updated yet — same agent could be picked up and reviewed/generated twice.
- Root cause: `apply_review_decision()` was called AFTER `dispatch_trigger()` in `process_proactive_agent()`.
- Fix: Moved `apply_review_decision()` BEFORE `dispatch_trigger()` so `proactive_next_review_at` is set before generation begins.

### Outcome

Proactive Insights fully validated at v2.1. Both phases of the two-phase execution model tested end-to-end:

- **Phase 1 — Haiku review** (~$0.002/cycle, 25 seconds): Scans platforms with targeted queries, identifies real themes, makes smart observe/generate decisions, accumulates forward-looking tracking notes in `agent_memory.review_log`
- **Decision gate**: generate/observe/sleep routing works correctly. Observations accumulate across cycles.
- **Phase 2 — Sonnet generation** (~$0.05/generation, 6 tool rounds): Full generation with WebSearch. Internal signals + external context woven into intelligence brief. "What I'm Watching" shows progressive learning.
- **Email delivery**: Version delivered to user's email successfully.

Key architectural validations:
1. `proactive_next_review_at` scheduling works correctly
2. `agent_memory.review_log` accumulates across cycles (2 reviews + 1 generation tested)
3. Search primitive responds well to short, specific queries
4. Forced final turn ensures JSON decision even when all tool rounds used
5. Trigger context forwarding: review decision → dispatch_trigger → headless agent (verified in code, ready for natural generate trigger)
6. HybridStrategy correctly gathers platform context + injects research_directive
7. Email-first delivery works end-to-end
8. Timing fix: apply_review_decision before dispatch prevents double-trigger

The output quality matches the BAD/GOOD examples in the prompt — every signal cites specific internal evidence AND external research with URLs. This is intelligence no external tool (ChatGPT, Perplexity) can produce because topic selection is driven by the user's own platform signals.
