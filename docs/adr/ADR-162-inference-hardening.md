# ADR-162: Inference Hardening — Evaluation, Gap Detection, Upload Triggering, Visibility

**Status:** Proposed
**Date:** 2026-04-07
**Authors:** KVK, Claude
**Extends:** ADR-144 (Inference-First Shared Context), ADR-155 (Workspace Inference Onboarding)
**Related:** ADR-156 (Composer Sunset — single intelligence layer), ADR-141 (Unified Execution Architecture), ADR-161 (Daily Update Anchor)

---

## Context

ADR-144 made inference the single method for shared context creation. ADR-155 extended inference workspace-wide via TP-driven `ManageDomains` scaffolding. Both ADRs are implemented and working — the developer's instinct that "inference is the upstream lever for everything downstream" is validated by the existing architecture.

But inference quality today is **vibes-driven**:

1. **No measurement.** `infer_shared_context()` is calibrated by gut. There's no fixture set, no scoring rubric, no regression detection when prompts change. If a future prompt change degrades entity recall by 20%, no one notices until a user complains.

2. **No follow-up loop.** When inference produces something thin (e.g., user types "I run a consulting firm" with no other input), the system writes a thin IDENTITY.md and proceeds to scaffold downstream. There's no mechanism to recognize "this is too thin to be useful" and reach for one targeted clarifying question.

3. **Document upload doesn't auto-engage TP.** A user can drop a pitch deck into `/workspace/uploads/` outside an active chat session and inference does not run. The document sits there until the user remembers to mention it in chat. The document — the single richest signal a new user can provide — is treated as inert until the user actively re-engages.

4. **Inference is invisible.** IDENTITY.md and BRAND.md are rendered in the Context tab (ADR-144 Phase 2), but users have no reason to look at them and no signal that inference *just happened*. When inference improves IDENTITY.md from "I run a consulting firm" to a richly populated identity card, the user doesn't know unless they actively navigate to the file. The most valuable thing the system does for new users is also the least visible.

The cost of *bad* inference compounds: thin IDENTITY.md → wrong domain entities → expensive bootstrap research against irrelevant entities → wasted budget → mediocre outputs → user disengages. The cost of *good* inference compounds the other way: rich IDENTITY.md → correct entities → cheap targeted research → high-signal outputs → user engages more → richer feedback. Inference is the single highest-leverage prompt in the system.

This ADR makes inference **measurable**, **iterative**, **proactive on uploads**, and **visible**.

### What This ADR Does NOT Do

- **No background LLM calls.** ADR-155 explicitly deleted the prior `workspace_inference.py` shadow Haiku service for violating single-intelligence-layer (ADR-156). This ADR maintains that discipline. Every LLM call this ADR introduces is either (a) explicitly orchestrated by TP in conversation, (b) deterministic/mechanical (no judgment), or (c) offline tooling (eval harness). There is no new background autonomous LLM judgment.

- **No new UI surfaces in Phase 1.** The visibility surface (sub-phase D) reuses existing Context tab and existing notification channel (ADR-155 Phase 3). It adds change-highlighting and gap markers, not a new page.

- **No new task types.** No new agents. No new primitives outside what exists for inference today. This is a hardening pass, not a feature expansion.

---

## Decision

Four sub-phases, ordered by leverage. Sub-phase **C ships first** because measurement is what makes the others improvements rather than guesses.

### Sub-Phase C (Ship First): Inference Evaluation Harness

Build an offline evaluation harness for inference prompts. This is a developer tool, not a user-facing surface.

**Structure:**

```
api/eval/
├── inference_fixtures/
│   ├── 01_minimal_chat.json          # "I run a consulting firm"
│   ├── 02_solo_founder_with_url.json # founder mention + company URL
│   ├── 03_pitch_deck_only.json       # rich PDF, no chat
│   ├── 04_multi_doc_b2b.json         # multiple uploads
│   ├── 05_consultant_2_clients.json  # work-context-rich text
│   ├── 06_re_inference_merge.json    # has existing IDENTITY.md, new info
│   ├── 07_brand_from_website.json    # brand inference test
│   ├── 08_brand_from_voice_doc.json  # voice/tone-only document
│   ├── 09_thin_input_anemic.json     # deliberately thin — should trigger gap
│   └── 10_rich_multi_source.json     # text + doc + url combined
├── ground_truth/
│   ├── 01_minimal_chat.expected.json
│   ├── ... (one per fixture)
└── run_inference_eval.py
```

Each fixture is a JSON file with:

```json
{
  "name": "Solo founder with company URL",
  "target": "identity",
  "inputs": {
    "text": "I'm Sarah, founder of Acme. We make AI tools for designers.",
    "document_ids": [],
    "url_contents": [
      {"url": "acme.com", "content": "Acme — design tools for the AI era. Founded 2024 in SF. 12-person team. Series A."}
    ],
    "existing_content": ""
  },
  "expected": {
    "must_contain_entities": ["Sarah", "Acme", "AI tools", "designers", "Series A"],
    "must_have_sections": ["Who", "Domains of Attention"],
    "must_not_fabricate": ["co-founder names not mentioned", "specific revenue numbers"],
    "min_word_count": 80,
    "max_word_count": 400,
    "expected_richness": "rich"
  }
}
```

**Scoring axes** (each fixture scored 0-1 per axis, then averaged):

| Axis | What it measures | How |
|---|---|---|
| **Entity recall** | Did the output mention all `must_contain_entities`? | Substring match |
| **Section completeness** | Did the output have all `must_have_sections`? | Markdown header check |
| **Anti-fabrication** | Did the output avoid `must_not_fabricate`? | Substring absence |
| **Length appropriateness** | Is the output within `min/max_word_count`? | Word count |
| **Richness classification** | Did the output match `expected_richness` (empty/sparse/rich)? | Heuristic from word count + section count |

**Runner script:**

```python
# api/eval/run_inference_eval.py
async def run_eval(fixture_dir="api/eval/inference_fixtures", verbose=False):
    """Run all fixtures through infer_shared_context and score."""
    fixtures = sorted(Path(fixture_dir).glob("*.json"))
    results = []
    for fixture_path in fixtures:
        fixture = json.loads(fixture_path.read_text())
        output = await infer_shared_context(
            target=fixture["target"],
            **fixture["inputs"],
        )
        score = score_against_expected(output, fixture["expected"])
        results.append({
            "fixture": fixture_path.name,
            "name": fixture["name"],
            "target": fixture["target"],
            "score": score,
            "output_preview": output[:200],
        })
    print_summary(results)
    return results
```

**Usage:**

```bash
cd api && python -m eval.run_inference_eval
# Output:
# === Inference Evaluation ===
# 01_minimal_chat            identity    score: 0.62  (entity_recall: 0.5, sections: 1.0, ...)
# 02_solo_founder_with_url   identity    score: 0.91
# ...
# === Aggregate ===
# Mean score: 0.78
# Mean entity recall: 0.83
# Mean richness accuracy: 0.90
```

**Cost:** ~$0.20-0.50 per full evaluation run (10 fixtures × ~$0.02 per inference call). Free for offline development; should be run before any prompt change. Not gated to CI in v1 — manual discipline. CI gating can come later if prompt changes become frequent enough to warrant it.

**What this enables:** any future change to `INFERENCE_SYSTEM` prompts in `context_inference.py` can be evaluated against the fixture set first. Regressions are visible. Improvements are quantitative. The "is this prompt better?" question stops being a gut call.

### Sub-Phase A: Deterministic Gap Detection (Single Pass, In Conversation)

**The constraint** (from ADR-155 / ADR-156): no shadow LLM calls. Inference's follow-up cannot be a separate background service. It must be either (a) explicitly orchestrated by TP, or (b) mechanical/deterministic.

**The decision: deterministic.** After every successful `infer_shared_context()` call, run a pure-Python gap detection function (zero LLM cost) that examines the output and the source material to identify missing-but-load-bearing fields. The function returns structured gaps, not free-form text. TP then uses the result to issue *at most one* targeted `Clarify` if the gap is significant.

**Why deterministic and not LLM-judged:**
- Zero cost. Runs on every inference, no budget impact.
- Deterministic behavior. Same input → same gap output. Easier to evaluate (Sub-phase C can score gap detection independently).
- No new LLM call to govern. Stays inside the single-intelligence-layer principle without hand-waving.
- Heuristics for "what's missing in IDENTITY.md" are stable enough to be coded directly: missing company name, missing role, missing domain count <2, no work patterns mentioned, no timezone, brand voice missing.

**Function signature:**

```python
# api/services/context_inference.py

def detect_inference_gaps(
    target: Literal["identity", "brand"],
    inferred_content: str,
    source_material_summary: dict,  # what TP gathered
) -> dict:
    """Identify missing-but-load-bearing fields in inference output.

    Pure Python. No LLM call. Deterministic heuristic.

    Returns:
        {
            "richness": "empty" | "sparse" | "rich",
            "gaps": [
                {
                    "field": "company_name",
                    "severity": "high" | "medium" | "low",
                    "suggested_question": "What's the name of your company or main project?",
                    "options": ["I'll tell you", "I'm independent / no company"],
                },
                ...
            ],
            "single_most_important_gap": {...} | None,  # Highest-severity gap, or None
        }
    """
```

**Gap heuristics for identity** (deterministic rules):

| Gap field | Detection | Severity | Suggested question |
|---|---|---|---|
| `company_name` | No `## Who` block has a capitalized non-pronoun noun other than the user's name | high | "What company or project are you building?" |
| `role` | `## Who` block missing words like "founder", "engineer", "CEO", "consultant", "designer", etc. | medium | "What's your role?" |
| `domain_count` | Fewer than 2 bullets under `## Domains of Attention` | high | "What are 2-3 areas you spend most of your work attention on?" |
| `work_patterns` | `## Work Patterns` section missing or empty | medium | "What recurring rhythms do you have? (e.g., weekly investor updates, daily standup)" |
| `industry` | No words like "industry", "market", "sector", "space" appear anywhere | low | "What industry or space are you in?" |
| `timezone` | `## Timezone` section missing | low | (skipped — TP doesn't ask, not load-bearing) |

**Gap heuristics for brand:**

| Gap field | Detection | Severity | Suggested question |
|---|---|---|---|
| `voice` | `## Voice` section empty or <10 words | high | "How would you describe your communication style? (e.g., direct and technical, warm and conversational)" |
| `audience` | `## Audience` section missing or empty | high | "Who do you typically write for?" |
| `tone` | `## Tone` section missing | medium | "What tone fits your work? (formal/casual/technical/playful)" |
| `terminology` | `## Terminology` empty | low | (skipped — terminology emerges from doc uploads, not direct asks) |

**Severity → action mapping:**

- `high` → TP issues `Clarify` with the suggested question + options
- `medium` → surfaced in TP's next response as a soft offer ("If you want, I can ask about X next")
- `low` → ignored (not load-bearing enough to interrupt the user)

**The "single most important gap"** is computed as: highest severity, ties broken by which gap blocks the most downstream scaffolding (e.g., missing `domain_count` blocks domain inference; missing `voice` blocks brand-aware writing).

**Where it plugs in:**

1. `infer_shared_context()` is called by `UpdateSharedContext` primitive (TP tool).
2. After the inference call returns, `UpdateSharedContext` calls `detect_inference_gaps()` on the result.
3. The gap structure is added to the primitive's response (alongside the markdown content).
4. TP receives the response, sees the `single_most_important_gap` field, and decides whether to issue a `Clarify`.
5. The TP onboarding prompt is extended to teach this pattern: *"After UpdateSharedContext, check the `gaps` field in the response. If `single_most_important_gap` has severity='high', issue a single Clarify with that question and options. Do not issue more than one Clarify per inference cycle — if the user has already been asked once, just proceed to scaffolding."*

**Why this is safe:** the gap detector cannot fabricate. It only matches patterns against the inference output. The worst case is "no gaps detected" (silent fall-through), not "wrong gap surfaced." The heuristics are simple enough to test directly, and Sub-phase C's eval harness can include gap-detection accuracy as a scoring axis.

### Sub-Phase B: Auto-Engage TP on Document Upload

Today, document upload writes the file to `/workspace/uploads/` and stops. TP only learns about the upload if the user mentions it in chat or if TP independently lists the directory.

**The change:** when a document is uploaded *outside an active chat session*, the upload route writes a notification to the TP notification channel (the same channel ADR-155 Phase 3 introduced) that says: *"User uploaded `<filename>`. This is rich source material — consider running UpdateContext(target='identity') with this document to enrich workspace context."*

When the user next opens chat, TP sees the notification in working memory, recognizes the upload, and offers:

> "I noticed you uploaded `pitch-deck.pdf` while I wasn't here. Want me to read it and update your identity context? It looks like the kind of source that could really fill in your workspace."

If the user says yes, TP calls `UpdateSharedContext(target='identity', document_ids=[...])` which runs the existing inference path (now augmented with gap detection from sub-phase A).

**Why we route through TP and not auto-fire inference:**

- **Single intelligence layer** (ADR-156). Inference is a TP tool. The decision to call it stays with TP, not with the upload route.
- **User consent.** Auto-running inference on every upload could surprise the user or process sensitive documents they didn't intend to feed into IDENTITY.md.
- **Cost discipline.** A user dragging in 5 documents shouldn't trigger 5 inference calls. TP can batch.
- **Conversation continuity.** When TP brings up the upload, the user is already in a chat context where they can correct or extend.

**Implementation (simplified at implementation time):**

The original plan called for a notification table. At implementation, a simpler approach emerged: **the upload itself IS the notification**. No new table, no upload route changes.

1. `api/services/working_memory.py` gains `_get_recent_uploads_sync()` — a 10-line SQL query that returns documents uploaded in the last 7 days.
2. The function is added to the working memory gather.
3. `format_compact_index()` surfaces them as a one-line "Recent uploads" section with TP guidance.
4. TP reads this surface in its prompt context every chat turn, sees recent uploads when they exist, and proactively offers to process them via `UpdateContext(target='identity', document_ids=[...])`.
5. No "mark as read" mechanism — after 7 days the upload falls off the surface naturally, and TP's prompt instructs it to offer once per session and respect the user if they decline.

This is filesystem-as-memory taken seriously (ADR-159): the upload's existence in `filesystem_documents` is the notification. No second source of truth.

**Why this is better than the original notification-table design:**
- Zero new schema
- Zero new code in the upload route
- Naturally idempotent (re-reading the same upload doesn't double-fire)
- Naturally expires (7-day window)
- Composable with the rest of the compact index
- TP gets the signal in the same place it gets all other workspace state

**Cost:** zero for the notification itself (pure DB write). Inference cost only fires when the user agrees to TP's offer. Same per-call cost as today (~$0.02). No new background spend.

### Sub-Phase D: Inference Visibility — Change Highlighting + Gap Markers

The Identity and Brand surfaces already render IDENTITY.md and BRAND.md (ADR-144 Phase 2). What's missing:

1. **Change highlighting after inference.** When TP runs `UpdateSharedContext`, the user has no visible signal that the file changed. They have to navigate to the Identity tab to find out. The change should surface *automatically* in the next chat response.

2. **Gap markers on the rendered file.** The gap detector (sub-phase A) knows what's missing. The Identity surface should *show* those gaps as inline markers ("Missing: company name — click to add" / "Missing: domains of attention — click to add"), not just feed them to TP. This makes the gap discovery user-actionable.

3. **Source provenance.** Each section should optionally show "Last updated from: pitch-deck.pdf (2 hours ago)" or "Last updated from: chat conversation (just now)". This gives the user a sense of where the inference came from and lets them re-run with different sources if the result is wrong.

**Implementation:**

1. **Change highlighting via existing notification channel.** The `UpdateSharedContext` primitive (already streams notifications via ADR-155 Phase 3's `TPContext.tsx`) gains a richer payload: `{target, what_changed: ["added Domain X", "updated Voice section", ...], gaps: [...]}`. The notification card on the chat surface renders this with a "View updated identity" link.

2. **Gap markers on Identity/Brand tab.** The Identity tab fetches IDENTITY.md content (existing) AND the latest gap analysis (new endpoint or stored alongside the file). Gap markers render inline as small "needs more info" pills. Clicking a gap marker drops the user back into chat with a pre-filled message like "I want to add my company name."

3. **Source provenance via inline HTML comments in IDENTITY.md.** `infer_shared_context()` is extended to write source comments alongside each section: `<!-- source: pitch-deck.pdf | inferred 2026-04-07 -->`. The Identity tab parses these and renders them as small captions below each section.

**No new endpoint complexity:** the gap analysis is computed at inference time, written into the IDENTITY.md as an HTML comment block at the bottom (`<!-- gaps: [...] -->`), and parsed by the frontend when rendering. This keeps the storage model simple — IDENTITY.md remains the single source of truth, gaps are metadata co-located with the content they're about.

**Why this is the smallest possible visibility win:**
- No new routes
- No new tables
- No new background processes
- Reuses existing notification channel and existing surface
- Adds three inline conventions (change payload, gap comment, source comment) that are all parseable from the existing markdown content

The user gets: a notification in chat when their identity changes, a one-click path to see what changed, visible "needs more info" markers on their context surfaces, and provenance for every inference. The system gets: zero new infrastructure.

---

## Sub-Phase Sequencing & Costs

| Sub-phase | Ships | LLM cost added | Lines of code (rough) | Risk |
|---|---|---|---|---|
| **C — Eval harness** | First | Pennies per eval run (offline) | ~400 lines + 10 fixtures + ground truth | Low (offline tooling) |
| **A — Gap detection** | After C | $0 (deterministic) | ~150 lines + TP prompt updates | Low |
| **B — Upload trigger** | After A | $0 baseline (only fires when user agrees) | ~80 lines | Low |
| **D — Visibility surface** | After B | $0 (inline metadata) | ~250 lines (frontend + minor backend) | Medium (frontend touch) |

Total per-user monthly cost added: **$0** for dormant users, **~$0.01-0.05** for engaged users (slightly more inference calls because TP is now better at offering them).

Total developer-side cost: pennies per `python -m eval.run_inference_eval` invocation.

---

## What Gets Deleted

Per execution discipline #1 (singular implementation):

- **Nothing in this phase.** Sub-phase A *adds* a function to `context_inference.py`. Sub-phase B *adds* a notification path. Sub-phase C *adds* a directory. Sub-phase D *adds* inline conventions to IDENTITY.md.

The reason there's no deletion: ADR-155 already deleted the shadow inference path. The current inference architecture is clean. This ADR hardens it without re-introducing parallelism.

If sub-phase B finds that the upload route's notification path duplicates something already in `tp_notifications`, the duplicate is removed in the same commit as B.

---

## Schema Changes

**None required.** All four sub-phases ride on existing tables:

- Eval harness: filesystem (`api/eval/`)
- Gap detection: in-memory function, no persistence
- Upload trigger: existing `tp_notifications` infrastructure (or equivalent — verified at implementation time)
- Visibility: HTML comments inside `workspace_files.content`, existing notification stream payload extension

If implementation reveals an existing table that needs a new column (e.g., upload notifications need a flag for "TP has read this"), it will be added as a small migration in the same commit and documented in `docs/database/ACCESS.md`.

---

## Code Changes (Map)

### Sub-phase C (Eval Harness)

| File | Change |
|---|---|
| `api/eval/inference_fixtures/*.json` | NEW — 10 fixture files |
| `api/eval/ground_truth/*.json` | NEW — expected outputs per fixture |
| `api/eval/run_inference_eval.py` | NEW — runner + scorer |
| `docs/architecture/inference-evaluation.md` | NEW — how to add fixtures, how to interpret scores |

### Sub-phase A (Gap Detection)

| File | Change |
|---|---|
| `api/services/context_inference.py` | ADD `detect_inference_gaps()` function (deterministic) |
| `api/services/primitives/shared_context.py` | EXTEND `UpdateSharedContext` to call gap detector and return gaps in response |
| `api/agents/tp_prompts/onboarding.py` | TEACH TP to read `gaps` field and issue at-most-one Clarify on high-severity |
| `api/prompts/CHANGELOG.md` | Entry |

### Sub-phase B (Upload Trigger)

| File | Change |
|---|---|
| `api/routes/uploads.py` (verified at impl time) | On successful upload, write TP notification |
| `api/services/working_memory.py` | Surface pending upload notifications in compact index |
| `api/agents/tp_prompts/onboarding.py` | Proactive upload-handling guidance |
| `api/prompts/CHANGELOG.md` | Entry |

### Sub-phase D (Visibility)

| File | Change |
|---|---|
| `api/services/context_inference.py` | EXTEND output to include `<!-- source: ... -->` and `<!-- gaps: ... -->` HTML comments |
| `api/services/primitives/shared_context.py` | EXTEND notification payload with `what_changed` and `gaps` |
| `web/contexts/TPContext.tsx` | Handle richer payload, render change cards |
| `web/components/context/IdentityCard.tsx` (or equivalent) | Parse HTML comments, render gap markers + source captions |
| `web/components/tp/NotificationCard.tsx` | New "identity updated" card variant |

---

## Documentation Changes

| File | Change |
|---|---|
| `docs/adr/ADR-162-inference-hardening.md` | This file |
| `docs/architecture/SERVICE-MODEL.md` | Add "Inference Hardening" subsection under Perception Model |
| `docs/architecture/inference-evaluation.md` | NEW — eval harness usage guide |
| `docs/architecture/FOUNDATIONS.md` | Small extension to Axiom 5 (Composer) — note that compositional judgment quality is now measurable |
| `CLAUDE.md` | ADR-162 entry in Key Architecture References |
| `api/prompts/CHANGELOG.md` | Entries for sub-phases A, B, D |

---

## Open Questions

1. **Should the eval harness be wired into CI?** Decision: not in v1. Manual discipline. The fixtures take 10-30 seconds to run and pennies to execute, so the cost of running them before every prompt PR is trivial. CI gating adds complexity (Anthropic API key in CI, rate limits, flakiness handling) without obvious benefit at current prompt-change cadence. Revisit when prompt changes become frequent.

2. **Should gap detection support custom heuristics per workspace?** Decision: no in v1. The heuristics are domain-agnostic (every workspace needs a company/role/domains regardless of industry). If specific industries need different gap criteria later, they can be added as a registry — but this is over-engineering for now.

3. **What happens when TP issues a Clarify and the user dismisses it?** Decision: gap is marked "user_skipped" in the IDENTITY.md HTML comment. TP will not re-ask in the same session. Future inference re-runs can see "user already declined to provide company_name" and skip that gap. This is the lightest-weight respect-the-user mechanism.

4. **Do we need a separate brand fixture set?** Decision: yes — 4-5 of the 10 fixtures are brand-targeted. Brand inference has different success criteria than identity (voice/tone are more subjective). The eval harness handles both target types via the `target` field on fixtures.

5. **Should sub-phase B (upload trigger) also fire for URL pastes?** Decision: yes, but in a follow-up. The first cut handles file uploads only because they're the highest-leverage signal. URL pastes are easier to handle (TP can fetch URLs synchronously in chat), so they're already covered indirectly by the existing TP flow.

6. **What if the gap detector misses something the LLM would catch?** Acceptable cost. Deterministic gap detection is conservative by design — it only flags things that are clearly missing per stable patterns. The LLM is still doing the hard work in `infer_shared_context()`. The gap detector is the safety net, not the brain. False negatives (missed gaps) are recoverable in subsequent inference cycles. False positives (gaps that aren't really gaps) are the actual risk, mitigated by careful heuristic design and Sub-phase C scoring.

---

## Cost Summary

**Sub-phase C (Eval Harness):**
- Per eval run: ~$0.20-0.50 (10 fixtures, manual)
- Per month: 0-5 runs depending on prompt change cadence ≈ $0-2.50
- One-time build cost: developer time, ~1 day

**Sub-phase A (Gap Detection):**
- Per inference call: $0 (pure Python)
- Per follow-up Clarify: $0 (TP issues it as part of normal chat flow, no extra cost)
- Per user per month: $0 net new

**Sub-phase B (Upload Trigger):**
- Per upload: $0 (DB write)
- Per inference triggered by user accepting TP's offer: ~$0.02 (same as today)
- Per user per month: $0.02-0.10 incremental, only when uploads happen

**Sub-phase D (Visibility):**
- Per inference: $0 (HTML comment generation is deterministic)
- Per render: $0 (frontend parses inline)
- Per user per month: $0

**Total per user per month for active users:** ~$0.05 incremental on top of current.
**Total per user per month for dormant users:** $0.

The inference cost ceiling stays bounded by what it has always been bounded by: how many `UpdateSharedContext` calls TP makes, which is itself governed by user engagement.

---

## Why This Sequence

1. **C ships first** because measurement comes before improvement. Without C, A's gap detection heuristics are guesses; with C, they're testable. Without C, D's visibility changes might mask quality issues; with C, you can prove they don't.

2. **A ships second** because gap detection is the highest-leverage prompt-side improvement and it's cheap. It also makes the gap data structure available to D, so D doesn't need to re-derive it.

3. **B ships third** because it depends on A (the gap-aware UpdateContext flow is what TP calls when the user agrees to process an upload). Without A, B just runs vanilla inference, which is still a win but not as much.

4. **D ships last** because it's frontend-touching and benefits from A's gap data and B's upload-driven inference being in place. Doing D first would mean displaying incomplete data.

Each sub-phase can ship as its own commit. They are not strictly dependent in the sense that A could ship without C and still work — but the philosophy is "measure before changing," so C goes first.

---

## Revision History

| Date | Change |
|---|---|
| 2026-04-07 | v1 — Initial. Four sub-phases (C eval, A gap detection, B upload trigger, D visibility). Deterministic gap detection chosen over LLM gap judgment to preserve single-intelligence-layer (ADR-156). All sub-phases additive, no deletions. |
