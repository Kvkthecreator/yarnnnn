# ADR-254: File Format Discipline — Prose vs. Structured Data

> **Status**: Proposed
> **Date**: 2026-05-07
> **Authors**: KVK, Claude
> **Supersedes**: ADR-253 D2 (ticker/signal file format — corrected here); ADR-217 D2 (AUTONOMY.md machine-read model — replaced by _autonomy.yaml)
> **Amends**: `workspace_paths.py` (new path constants), `review_policy.py` (yaml.safe_load replaces _parse_keyed_yaml), `working_memory.py` (yaml.safe_load replaces regex), `reflection_writer.py` (writes _autonomy.yaml not AUTONOMY.md for structured fields), `workspace_init.py` (seeds _autonomy.yaml + _universe.yaml)
> **Dimensional classification**: **Substrate** (Axiom 1) primary — every write is attributed and retained, format is part of the substrate contract; **Mechanism** (Axiom 5) secondary — deterministic executors become truly deterministic when they read actual YAML

---

## Context

### The over-reliance on `.md` problem

YARNNN's workspace stores two fundamentally different types of content:

1. **Operator prose** — narrative declarations, strategy descriptions, persona definitions, principles. Written by humans (or LLMs acting as humans). Read by LLMs at reasoning time. Format: `.md` (markdown). Parsing: none needed — LLM reads directly.

2. **Machine-parsed structured data** — delegation ceilings, ticker lists, indicator values, signal state, recurrence declarations. Written and read by Python code. Parsed by Python at runtime. Format: should be `.yaml`. Parsing: `yaml.safe_load()`.

Every file currently uses `.md`. Several of those files are machine-parsed with custom regex/string parsers that fail silently on format variations. The evidence:

- `AUTONOMY.md` — machine-parsed by `review_policy._parse_keyed_yaml()` and `working_memory._extract_autonomy_signal/pause()`. The YAML frontmatter IS the content; the markdown body is documentation only.
- `{ticker}.md` indicator files — machine-parsed by regex in `trading_signal_evaluator._parse_frontmatter()`. Pure YAML frontmatter, no meaningful prose body.
- `signals/{slug}.md` signal state files — machine-parsed by regex. Same issue.
- `_operator_profile.md` — prose doc that Python tries to extract tickers from with regex. Wrong parsing target.

The already-existing files that get it right: `back-office.yaml`, `_spec.yaml`, `_action.yaml`, `_recurring.yaml` — all machine-parsed, all `.yaml`, all read via `yaml.safe_load`. No fragile parsers.

### The rule, stated plainly

**If Python code parses the content, the file is `.yaml`. If the LLM reads the content, the file is `.md`. Never both.**

The only exception is YAML frontmatter in `.md` files — acceptable when the primary consumer is the LLM (reads the full file as text) and a secondary machine reader needs a few structured fields. But when the machine is the *primary* consumer and the prose is documentation, the file should be `.yaml` with a comment header.

### Why purge-and-restart is right here

The alpha-trader workspaces were created before ADR-254. They contain:
- `AUTONOMY.md` with YAML frontmatter being machine-parsed
- `{ticker}.md` files written with YAML frontmatter
- `signals/{slug}.md` written with YAML frontmatter

All of these will be superseded by new format files. Migrating in-place requires dual-write bridges and backwards-compat shims. Per singular implementation discipline: purge the affected structured files, re-activate from the corrected reference workspace, test end-to-end from a clean state. The prose files (MANDATE, IDENTITY, BRAND, principles, etc.) are preserved — only the machine-parsed structured files are purged.

---

## Decisions

### D1: The format rule — canonical and enforced

**`.md` files** — primary consumer is an LLM or human. Written in markdown prose. Machine code may read the file but treats it as opaque text passed to the LLM. No structured parsing in Python.

**`.yaml` files** — primary consumer is Python code. Machine-parsed via `yaml.safe_load()`. May contain comments for human readability but the structure is the contract. LLMs may also read these (they handle YAML fine) but the format is optimized for machine reading.

**YAML-frontmatter `.md` files** — acceptable ONLY when the LLM reads the full file AND a small number of structured fields are also needed by machine code (e.g., `recurrence_paths.py` reading schedule from `_spec.yaml` — but that's already `.yaml`). No new mixed-format files after ADR-254.

### D2: `_autonomy.yaml` replaces machine-parsed content of `AUTONOMY.md`

**`AUTONOMY.md` (preserved)**: Operator-authored prose documentation explaining what autonomy means, how to think about phases, when to revisit. LLM reads this for context. Humans read this to understand the system. Not machine-parsed.

**`_autonomy.yaml` (new)**: The machine-readable declaration. Read by `review_policy.load_autonomy()` and `working_memory._extract_autonomy_signal/pause()`. Written by `reflection_writer._apply_pause_autonomy()`.

Schema:
```yaml
# _autonomy.yaml — machine-parsed delegation declaration (ADR-254)
# Edit this file to tune delegation ceilings. See AUTONOMY.md for documentation.

default:
  level: bounded_autonomous           # manual | assisted | bounded_autonomous | autonomous
  ceiling_cents: 20000               # threshold for bounded_autonomous ($200)
  never_auto: []                     # action_type substrings always deferred
  # paused_until: ""                 # ISO-8601 UTC — Reviewer-written circuit breaker
  # pause_reason: ""

heartbeat_triggers:
  - after: signal_evaluation
  - after: outcome_reconciliation
  - cron: "10 8 * * 1-5"
```

`review_policy.py` changes:
- `_parse_keyed_yaml()` **deleted** — replaced by `yaml.safe_load()`
- `load_autonomy()` reads `/workspace/context/_shared/_autonomy.yaml` via `yaml.safe_load()`
- `load_principles()` reads `/workspace/review/_principles.yaml` (see D3)
- `SHARED_AUTONOMY_PATH` in `workspace_paths.py` → `SHARED_AUTONOMY_YAML_PATH = "context/_shared/_autonomy.yaml"`

`working_memory.py` changes:
- `_extract_autonomy_signal()` → reads `_autonomy.yaml` via `yaml.safe_load`, no regex
- `_extract_autonomy_pause()` → reads `paused_until`/`pause_reason` directly from yaml dict, no regex

`reflection_writer._apply_pause_autonomy()` changes:
- Reads `_autonomy.yaml` via `yaml.safe_load`, mutates the dict, writes back via `yaml.dump()` + `write_revision()`
- No more regex substitution on AUTONOMY.md content

### D3: `_principles.yaml` for the machine-parsed portion of principles

`principles.md` serves two consumers:
1. **Reviewer LLM** — reads the full prose to understand the evaluation framework, reasoning posture, defer posture. This is the primary use. Keep as `.md`.
2. **`review_policy.load_principles()`** — reads `high_impact_threshold_cents` per domain for outcome routing (ADR-195 Phase 5).

The LLM-read portion stays in `principles.md`. The machine-parsed portion moves to `_principles.yaml`:

```yaml
# _principles.yaml — machine-parsed thresholds (ADR-254)
# For the Reviewer's reasoning framework, see principles.md.

trading:
  high_impact_threshold_cents: 50000   # outcomes >= $500 route to feedback.md
  auto_approve_below_cents: 20000      # Reviewer approve binds below this threshold
```

`review_policy.load_principles()` reads `_principles.yaml`. `principles.md` stays as the LLM's reasoning reference — no machine parsing.

**This also fixes the `auto_approve_below_cents` misdocumentation** from ADR-253: the field now actually lives where `load_principles()` reads from, and `should_auto_execute_verdict()` gains a new check against `principles_for_domain(principles, domain).get("auto_approve_below_cents")`. Both gates (AUTONOMY ceiling + Reviewer's own threshold) must pass.

### D4: `_universe.yaml` — operator-declared ticker list

New file at `/workspace/context/trading/_universe.yaml`:

```yaml
# _universe.yaml — operator-declared universe (ADR-254)
tickers:
  - AAPL
  - MSFT
  - NVDA
  - SPY
  - TSLA
```

`trading_universe_tracker._read_universe()` reads this via `yaml.safe_load`. No regex, no section header guessing. Operator edits this file directly to add/remove tickers. The universe update workflow becomes: operator says "add AMD to the universe" → System Agent writes `_universe.yaml` via `WriteFile` → next track-universe run picks it up.

`_operator_profile.md` retains the prose universe description (strategy rationale, candidate criteria) but is no longer parsed by Python.

### D5: `{ticker}.yaml` and `signals/{slug}.yaml` — indicator and signal state files

**`{ticker}.yaml`** replaces `{ticker}.md` for universe tracker output:

```yaml
# NVDA.yaml — indicator state (ADR-254, written by trading_universe_tracker)
ticker: NVDA
last_updated: "2026-05-07T08:01:23Z"
price: 851.20
sma_20: 842.10
sma_50: 820.55
sma_200: 750.30
rsi_14: 48.2
atr_14: 12.45
volume_20d_avg: 45230000
```

`trading_signal_evaluator._load_ticker_indicators()` reads via `yaml.safe_load`. No frontmatter parsing, no regex. One `yaml.safe_load()` per file.

**`signals/{slug}.yaml`** replaces `signals/{slug}.md`:

```yaml
# IH-2-or-breakout-long.yaml — signal state (ADR-254, written by trading_signal_evaluator)
signal_slug: ih-2-or-breakout-long
evaluated_at: "2026-05-07T08:05:12Z"
state: active
watch_tickers: []
triggered_today: []
trigger_count: 0
expectancy_r_20: null
expectancy_r_40: null
evaluable: false
evaluation_note: "Intraday signal (ORB) requires live 1H bar data — not evaluable from daily bars. Evaluated by trade-proposal at session open."
```

The `evaluable: false` field is the correct handling of intraday signals: the signal evaluator writes the state file but marks it as not evaluable from daily bars, with an explanation. No false signal fires. The trade-proposal recurrence handles intraday evaluation at session open via live Alpaca data.

### D6: Workspace path constants updated

`workspace_paths.py` new constants:
```python
SHARED_AUTONOMY_YAML_PATH = "context/_shared/_autonomy.yaml"   # machine-parsed (ADR-254)
SHARED_AUTONOMY_DOC_PATH = "context/_shared/AUTONOMY.md"       # prose doc (LLM reads)
TRADING_UNIVERSE_PATH = "context/trading/_universe.yaml"        # operator ticker list
REVIEW_PRINCIPLES_YAML_PATH = "review/_principles.yaml"        # machine-parsed thresholds
```

Old `SHARED_AUTONOMY_PATH` **deleted** — callers migrated to YAML path.

### D7: Workspace initialization — correct formats from day one

`workspace_init.py` Phase 2 seeds `_autonomy.yaml` (not just `AUTONOMY.md`). The reference workspace bundle ships `_autonomy.yaml` as `tier: canon` alongside `AUTONOMY.md` as `tier: authored`.

New workspaces get both:
- `AUTONOMY.md` — prose doc for human/LLM reading
- `_autonomy.yaml` — machine-parsed delegation config

For alpha-trader programs: `_universe.yaml` also seeded at activation with the declared 5 tickers. Signal state files seeded as `.yaml` from first run.

### D8: Purge and re-activate alpha-trader workspaces

Per singular implementation discipline: delete the now-superseded `.md` structured files from both live alpha-trader workspaces, seed the new `.yaml` files, re-run the activation flow. Prose files (MANDATE, IDENTITY, BRAND, principles, OCCUPANT, decisions, etc.) are **not** purged — only the machine-parsed structured files:

**Purge (delete):**
- `/workspace/context/_shared/AUTONOMY.md` → content migrated to `_autonomy.yaml`; `AUTONOMY.md` seeded fresh as prose-only doc
- `/workspace/context/trading/{ticker}.md` all ticker indicator files
- `/workspace/context/trading/signals/{slug}.md` all signal state files

**Seed (write new):**
- `/workspace/context/_shared/_autonomy.yaml` from `_autonomy.yaml` reference workspace
- `/workspace/context/trading/_universe.yaml` with the 5 declared tickers
- `/workspace/review/_principles.yaml` with trading thresholds

Signal and ticker `.yaml` files populate on next run of the respective executors.

---

## Implementation plan

### Commit 1 — `_autonomy.yaml` schema + reference workspace files
- `docs/programs/alpha-trader/reference-workspace/context/_shared/_autonomy.yaml` (NEW)
- `docs/programs/alpha-trader/reference-workspace/context/_shared/AUTONOMY.md` (rewritten as prose-only)
- `docs/programs/alpha-trader/reference-workspace/context/trading/_universe.yaml` (NEW)
- `docs/programs/alpha-trader/reference-workspace/review/_principles.yaml` (NEW)

### Commit 2 — `workspace_paths.py` + `review_policy.py` rewrite
- `api/services/workspace_paths.py`: new constants, old `SHARED_AUTONOMY_PATH` deleted
- `api/services/review_policy.py`: `_parse_keyed_yaml()` deleted, `load_autonomy()` → `yaml.safe_load(_autonomy.yaml)`, `load_principles()` → `yaml.safe_load(_principles.yaml)`, `should_auto_execute_verdict()` gains `auto_approve_below_cents` check
- Update all import sites of `SHARED_AUTONOMY_PATH`

### Commit 3 — `working_memory.py` + `reflection_writer.py`
- `working_memory.py`: `_extract_autonomy_signal/pause()` → reads `_autonomy.yaml` via `yaml.safe_load`, regex deleted
- `reflection_writer.py`: `_apply_pause_autonomy()` → `yaml.safe_load` → mutate dict → `yaml.dump` → `write_revision`

### Commit 4 — Trading executors rewrite
- `trading_universe_tracker.py`: writes `{ticker}.yaml` not `{ticker}.md`; reads `_universe.yaml` via `yaml.safe_load`; `_read_universe()` regex deleted
- `trading_signal_evaluator.py`: writes `signals/{slug}.yaml` not `signals/{slug}.md`; reads `{ticker}.yaml` via `yaml.safe_load`; `_parse_frontmatter()` regex deleted; intraday signals marked `evaluable: false` with note

### Commit 5 — `workspace_init.py` + purge script + re-activation
- `workspace_init.py` Phase 2: seeds `_autonomy.yaml` alongside `AUTONOMY.md`
- Purge script: deletes old `.md` structured files from both live workspaces, seeds new `.yaml` files
- Re-run track-universe and signal-evaluation to populate fresh `.yaml` state files
- ADR-254 → Implemented

---

## What this does NOT change

- `AUTONOMY.md` — still exists as prose documentation. Just not machine-parsed.
- `principles.md` — LLM still reads this. `_principles.yaml` is the machine-read twin.
- All `.md` prose files (MANDATE, IDENTITY, BRAND, PRECEDENT, decisions, reflections, handoffs) — unchanged
- All existing `.yaml` declaration files (back-office.yaml, _spec.yaml, _action.yaml) — unchanged
- `ReadFile` / `WriteFile` primitives — unchanged (format-agnostic)
- `workspace_files` DB schema — unchanged

---

## Relationship to existing ADRs

| ADR | Relationship |
|---|---|
| ADR-245 | Three-layer content rendering: L2 content-shape parsers now have a clean `yaml.safe_load` entry point. No more ad-hoc regex as L2. |
| ADR-217 | AUTONOMY.md authorship preserved. Machine-read content moves to `_autonomy.yaml`. |
| ADR-253 D2 | Ticker/signal file format corrected from `.md` to `.yaml`. D2 is superseded by ADR-254 D5. |
| ADR-209 | All writes still go through `write_revision()`. Format change doesn't affect attribution. |
| ADR-231 | `.yaml` recurrence declarations already correct. No change. |
| FOUNDATIONS Axiom 1 | Substrate grows from work — now the format is correct for the content class. Authored Substrate attribution unchanged. |
