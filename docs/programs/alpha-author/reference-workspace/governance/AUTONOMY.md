# Autonomy — alpha-author

> Per ADR-254: **machine-parsed delegation config lives in `_autonomy.yaml` (sibling file)**. This file is prose documentation for human and LLM reading. Edit `_autonomy.yaml` to change delegation ceilings.

## What autonomy controls

**Autonomy is the witness dial, not a ceiling on the agent (ADR-345).** Your Reviewer always works the full job — it is a judgment seat acting in your absence, not an assistant waiting for permission to start. This dial does not decide *whether* it works; it decides **which consequential beats you witness before they bind**. `autonomous` = the whole operation runs subconsciously (you read the trail — `judgment_log.md`, `standing_intent.md` — at your leisure); `bounded`/`manual` = the beats you choose surface to your Queue first. A ship that routes to your Queue is the Reviewer having *decided* and *waiting for you to witness it* — never the Reviewer being *blocked from working*.

`_autonomy.yaml` declares which beats surface: how much the Reviewer's approve verdict on a pre-ship audit binds automatically vs. routes to your Queue for a click.

**Levels (canonical 3-value enum per ADR-261 D5):**
- `manual` — every ship action requires your click, regardless of Reviewer verdict
- `bounded` — Reviewer auto-ships approved drafts within `ceiling_categories`; defers categories not in the ceiling list
- `autonomous` — Reviewer auto-ships all approved drafts within scope

**`ceiling_categories`** — the *category list* for `bounded`. Drafts whose `piece_type` matches an entry in `ceiling_categories` auto-ship on Reviewer approve. Drafts of other types defer to your Queue.

**`never_auto`** — piece types that always route to Queue regardless of level. Hard safety list. Examples: `essay` and `screenplay-scene` for operators who want every long-arc piece to ship by their own hand even when other categories are auto-approved.

## Default posture (bundle ships, operator overrides)

**Phase 0 — Accumulation default**: `delegation: manual`, `ceiling_categories: []`, `never_auto: []`.

Every ship action requires operator click. Reviewer's approve verdict on a pre-ship audit is visible but advisory. The loop runs end-to-end (operator drafts → Reviewer audits → operator approves Reviewer's approval → ship). Stay here until you've watched ~10 closed-loop cycles and trust the Reviewer's voice-audit + continuity-audit + anti-slop reasoning shape.

## Phase progression (reference)

- **Phase 0 — Accumulation (default)**: `manual`. Every ship action is operator-clicked. Build confidence in the Reviewer's reasoning quality.
- **Phase 1 — Cadence Discipline**: shift to `bounded` for one low-stakes piece-type — e.g., `newsletter-weekly-edition`. Reviewer's approve verdict binds auto-ship for that category only. Keep `essay`, `long-arc-scene`, anything high-stakes at `manual`. Stay here until you've shipped at least 4 weeks of the bounded category without false-positive auto-ship (Reviewer never wrongly cleared a draft with voice drift you would have caught).
- **Phase 2 — Selective Autonomy**: expand `ceiling_categories` per the Phase 1 calibration data. Newsletter weekly + daily social posts may be auto-ship while essays stay `manual`. Adjust based on operator confidence.
- **Phase 3 — Corpus Compounds (success bar)**: per operator's chosen success bar. Autonomy posture continues to be operator-tuned; not preset.

## The honest math: ceiling vs. piece type

Unlike alpha-trader's `ceiling_cents` (numeric notional check), alpha-author's `ceiling_categories` is a **categorical match** against `piece.piece_type`. This is appropriate because shipping risk in authoring isn't proportional to dollar size — it's proportional to corpus position. A botched newsletter weekly edition is recoverable in a week; a botched essay or screenplay scene damages the long-arc thesis disproportionately.

## Reviewer-written pause (ADR-248 D3)

The Reviewer's periodic reflection can write `paused_until` and `pause_reason` into `_autonomy.yaml` when it detects structural drift (e.g., voice fingerprint drifted significantly across last 4 pieces, calibration suggests anti-slop check needs to tighten before more auto-ships). While set, all proposals queue for your click regardless of level. Expires automatically at the timestamp. You can remove it via chat at any time.

## What AUTONOMY does NOT control

- Reviewer's evaluation framework (`principles.md` + `_principles.yaml`)
- Voice fingerprint declaration (`_voice.md`)
- Editorial principles (`_editorial.md`)
- Operator authorial identity (MANDATE.md, IDENTITY.md, BRAND.md)
- **Whether a recurrence wakes the Reviewer** — that's the recurrence's `mode` field per ADR-263 (`judgment` | `mechanical`), declared at authoring time in `_recurrences.yaml`.
