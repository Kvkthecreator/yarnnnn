# Inference Evaluation Harness

**Status:** Canonical
**Date:** 2026-04-07
**Related:** ADR-162 (Inference Hardening), ADR-144 (Inference-First Shared Context), ADR-155 (Workspace Inference Onboarding)

---

## Purpose

The inference evaluation harness (`api/eval/run_inference_eval.py`) is the developer-facing tool for measuring inference quality. It runs a fixture set through `infer_shared_context()` and scores each output against a structured `expected` block.

This harness exists to make inference quality **measurable**. Before this harness, inference prompts were calibrated by gut. With it, prompt changes are quantitative — every change can be evaluated against a known fixture set, regressions are visible, and improvements are real.

---

## Quick Start

```bash
cd api
python -m eval.run_inference_eval                       # all fixtures
python -m eval.run_inference_eval --fixture 02          # one fixture (substring match)
python -m eval.run_inference_eval --verbose             # full inference outputs
```

Cost: roughly **$0.20–0.50 per full run** (10 fixtures × ~$0.02 per Sonnet inference call). Free for offline use; not gated to CI.

---

## Output

```
=== Inference Evaluation (10 fixtures) ===

  Running 01_minimal_chat.json... done (0.62)
  Running 02_solo_founder_with_url.json... done (0.91)
  ...

=== Per-Fixture Results ===

  01_minimal_chat                     identity   ██████░░░░ 0.62
  02_solo_founder_with_url            identity   █████████░ 0.91
  03_pitch_deck_only                  identity   █████████░ 0.93
  04_multi_doc_b2b                    identity   ████████░░ 0.85
  ...

=== Aggregate (10 fixtures) ===
  Mean aggregate score:    0.78
  Mean entity recall:      0.83
  Mean section coverage:   0.91
  Mean anti-fabrication:   0.95
  Mean length adherence:   0.88
  Mean richness accuracy:  0.90
```

If any fixture scores below 0.6, the harness flags it explicitly with the missed entities and sections so you can investigate.

---

## Scoring Axes

Each fixture is scored on five axes, then weighted:

| Axis | Weight | What it measures | How |
|---|---|---|---|
| **Entity recall** | 30% | Did the output include all `must_contain_entities`? | Case-insensitive substring match |
| **Section completeness** | 25% | Did the output have all `must_have_sections`? | Markdown header regex |
| **Anti-fabrication** | 15% | Did the output avoid `must_not_fabricate` strings? | Substring absence (concrete proper-noun fabrications only — descriptive phrases like "specific revenue numbers" are skipped) |
| **Length adherence** | 10% | Word count within `min/max_word_count`? | Linear penalty outside range |
| **Richness accuracy** | 20% | Did the output match `expected_richness` (empty/sparse/rich)? | Heuristic from word count + section count |

The aggregate score is a weighted mean. Anything ≥ 0.8 is considered passing; anything below 0.6 is flagged as a failure that needs investigation.

---

## Anatomy of a Fixture

Fixtures live in `api/eval/inference_fixtures/` as JSON files. Each one has two main blocks:

```json
{
  "name": "Solo founder with company URL",
  "description": "Founder mention plus a fetched company URL.",
  "target": "identity",
  "inputs": {
    "text": "I'm Sarah, founder of Acme...",
    "document_contents": [],
    "url_contents": [
      {"url": "acme.com", "content": "Acme — design tools..."}
    ],
    "existing_content": ""
  },
  "expected": {
    "must_contain_entities": ["Sarah", "Acme", "designers"],
    "must_have_sections": ["Who", "Domains of Attention"],
    "must_not_fabricate": ["co-founder names", "specific revenue numbers"],
    "min_word_count": 80,
    "max_word_count": 400,
    "expected_richness": "rich",
    "expected_high_severity_gaps": []
  }
}
```

### `inputs` — what gets fed to inference

These fields map directly to `infer_shared_context()`'s parameters. Use realistic content. The point of the harness is to test the prompt against believable user input, not against minimal stubs.

### `expected` — what success looks like

| Field | Purpose |
|---|---|
| `must_contain_entities` | List of strings the output should contain. Substring match, case-insensitive. Use specific entities the inference should preserve from the source — names, companies, roles, industries. |
| `must_have_sections` | List of markdown header text the output should include. Use the section names from the `IDENTITY_SYSTEM` / `BRAND_SYSTEM` prompt schemas. |
| `must_not_fabricate` | List of things the LLM might invent. Two flavors: concrete proper-noun strings (checked strictly) and descriptive phrases (currently informational only). Concrete: `"Acme Competitor Inc"`. Descriptive: `"specific revenue numbers"`. |
| `min_word_count` / `max_word_count` | Acceptable length range. Penalty scales linearly outside the range. |
| `expected_richness` | One of `empty` / `sparse` / `rich`. Used by the richness classifier. |
| `expected_high_severity_gaps` | (Sub-phase A) List of gap field names that the gap detector should flag. Currently informational; will be scored once gap detection ships. |

---

## Adding a New Fixture

1. **Pick a real scenario.** What kind of input do you want to test inference against? Be specific. Use cases worth covering:
   - Minimal input (anemic, should produce sparse)
   - Single rich source (one good doc)
   - Multi-source merge (text + doc + url)
   - Re-inference with existing content
   - Brand voice from website
   - Brand voice from style document
   - Edge cases (very short, very long, multilingual, etc.)

2. **Write the fixture file.** Number it sequentially (`11_new_scenario.json`). Use realistic content in `inputs` — don't stub it down.

3. **Author `expected`.** Run the fixture once first to see what inference actually produces, then write the expected block to capture what *should* be true. Don't reverse-engineer the expected block to match the current output exactly — that defeats the purpose. Write what *should* hold even after reasonable prompt variation.

4. **Run the harness** and confirm your fixture scores reasonably (≥ 0.7). If it's stuck below that, either the fixture is too strict or the prompt has a real gap.

5. **Commit the fixture** alongside any prompt changes that motivated it.

---

## When to Run the Harness

**Always before:**
- Modifying `INFERENCE_SYSTEM` or `BRAND_SYSTEM` prompts in `api/services/context_inference.py`
- Changing the `INFERENCE_MODEL` constant
- Adjusting how `infer_shared_context()` assembles its source material
- Changing token limits (`max_tokens` in the inference call)

**Periodically:**
- When Anthropic releases a new Sonnet/Haiku model
- When considering switching to a cheaper model for cost reasons
- After accumulating 3+ user-reported quality issues to verify they're real

**Before merging:**
- Any PR touching the inference path. Aggregate score should not regress.

---

## Interpreting Score Drops

If your aggregate score drops after a prompt change:

1. **Look at per-fixture scores first.** If only one or two fixtures dropped, the change might be a targeted improvement that disturbed an edge case. Look at which fixtures.

2. **Check entity recall.** This is the most diagnostic axis. If entity recall dropped, the new prompt is letting the LLM drop facts. Bad.

3. **Check anti-fabrication.** If anti-fabrication dropped, the new prompt is encouraging the LLM to invent. Worse than dropping entities.

4. **Check richness.** If richness accuracy dropped, the new prompt is producing output of the wrong shape (sparse when it should be rich, or vice versa). Usually means a structural issue.

5. **Length and section completeness** are usually the easiest to fix — they respond well to explicit prompt instructions ("output 100-300 words", "always include a Domains of Attention section").

---

## Limitations (v1)

- **Substring matching is shallow.** Entity recall doesn't catch synonyms or paraphrases. If the fixture says `must_contain_entities: ["AI tools"]` and the output says `"AI products"`, it's marked as missed. Future improvement: embedding-based similarity scoring.

- **Anti-fabrication is conservative.** Descriptive phrases like `"specific revenue numbers"` are skipped because we can't reliably detect them via substring. The harness scores them as "checked, no violation" rather than risk false positives. Concrete fabrication strings (specific made-up names) ARE strictly checked.

- **Richness heuristic is hard-coded.** Word count + section count thresholds are fixed in the runner. If the prompt schema changes (e.g., more sections expected), the thresholds need to be updated.

- **No structured gap-detection scoring yet.** `expected_high_severity_gaps` is currently informational. Once Sub-phase A ships the deterministic gap detector, the harness will be extended to score gap detection accuracy as a sixth axis.

- **No CI integration in v1.** Manual discipline only. CI gating can be added once prompt-change cadence justifies it.

---

## Files

| File | Role |
|---|---|
| `api/eval/__init__.py` | Package marker |
| `api/eval/run_inference_eval.py` | Runner + scorer |
| `api/eval/inference_fixtures/*.json` | Fixture set (10 files) |
| `docs/architecture/inference-evaluation.md` | This file |

---

## See Also

- ADR-162 (Inference Hardening) — the ADR that motivated this harness
- ADR-144 (Inference-First Shared Context) — what inference is and why it matters
- ADR-155 (Workspace Inference Onboarding) — how inference cascades into domain scaffolding
- `api/services/context_inference.py` — the inference function being measured
