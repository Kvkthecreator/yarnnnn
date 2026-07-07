# Revision Audit Spec

Spec for the `revision-audit` recurrence. Distinct from `pre-ship-audit` (reactive, per-draft, before publication). Revision audit is the **long-arc author's primary loop** — periodic Reviewer pass that compares the current state of a draft against its prior revision, surfaces what changed, flags structural shifts.

## Purpose

The reactive `pre-ship-audit` loop assumes drafts progress through `ready_for_review` flag toward publication. For long-arc workspaces (novel-in-progress, screenplay-in-development, longform book project, multi-month essay), that loop is the wrong shape. The operator iterates on a single artifact daily / weekly for months. The artifact rarely goes through `ready_for_review` — it accumulates revisions in place.

The Reviewer's job in that loop is different: **track how the draft is evolving against its own prior state.** What changed since last week? Did voice tighten or drift? Did entity-continuity hold? Did a character's voice register slip? Did an argument's structural load-bearing shift?

`revision-audit` is the spec for that recurrence.

## Trigger shape

Scheduled judgment-mode recurrence. Default in this bundle's `_recurrences.yaml`:

```yaml
- slug: revision-audit
  schedule: "0 22 * * 5"   # Friday 22:00 UTC ≈ Friday afternoon US Pacific
  mode: judgment
  required_capabilities: []
  prompt: |
    (see below)
```

The Friday-EOD default is operator-tunable via the chat surface — operators with daily revision pulse may want a daily fire, operators with monthly cadence may want monthly. Operator declares preference via `_preferences.yaml` and the Reviewer authors the actual `Schedule()` call per ADR-275.

**Why scheduled rather than reactive**: reactive-on-edit would fire too often (operator may save a draft 30+ times per session). Scheduled gives a coherent comparison surface — "what changed across the week" is a useful audit lens; "what changed in the last 90 seconds" is not.

## What the Reviewer compares

Per ADR-209 revision chain — every workspace_files mutation produces a revision row. The Reviewer at `revision-audit` time:

1. Lists all draft-state pieces (status: `draft` per piece profile.md) in `/workspace/operation/authored/{piece-slug}/`.
2. For each draft, calls `ListRevisions` on `content.md` to enumerate revisions in the audit window (default: last 7 days for weekly cadence; tune per `_preferences.yaml`).
3. For each draft with >= 1 revision in the window, calls `DiffRevisions` between the window-start revision and the current head.
4. Audits the diff against:
   - **Voice fingerprint**: did the changes drift voice per `_voice.md`? (Subset of voice-audit, applied to diff scope.)
   - **Entity continuity**: did the changes contradict any entity's `What's been established` per `entities/{slug}.md`? (Subset of entity-continuity audit, applied to diff scope.)
   - **Structural load-bearing**: did a passage that other passages depend on shift? (E.g., an argument's premise was rewritten — Reviewer surfaces dependent passages that may now be inconsistent.)
   - **Open-question state**: did the revision implicitly close an entity's `What's open` question without acknowledgment in the draft?

## Inputs the Reviewer reads

- Draft `content.md` files in `draft` status (current head + window-start revision via ADR-209 `ReadRevision`).
- `_voice.md` (voice fingerprint).
- `_entities.md` + `entities/{slug}.md` for entities the draft touches (per `entity-continuity.md` spec).
- `_editorial.md` (editorial principles — for high-level "is this still in scope" check).
- `_preferences.yaml` (cadence configuration — determines audit window length).

## Output structure

The Reviewer's findings land:

1. **`/workspace/agents/alpha-author/judgment_log.md`** — append-only audit entry per `pre-ship-audit` shape, with `audit_type: revision-audit`:
   ```yaml
   piece_slug: <slug>
   audit_timestamp: <ISO-8601>
   audit_type: revision-audit
   window_start_revision: <revision_id>
   window_end_revision: <revision_id>
   revisions_in_window: <int>
   voice_findings: [<voice-audit hits scoped to diff>]
   entity_findings: [<entity-continuity hits scoped to diff>]
   structural_findings: [<load-bearing shift descriptions>]
   open_question_implicit_closes: [<entity-slug + which open question was closed>]
   overall_verdict: clean | notable-changes | concerning-drift
   surface_to_operator: true | false
   ```

2. **Draft's `profile.md`** updated with `last_revision_audit: <timestamp>` and `revision_audit_state: <verdict>`.

3. **`Clarify` proposal** when `surface_to_operator: true` — Reviewer surfaces the specific findings as an operator-facing message (e.g., "Friday revision audit on `chapter-7-draft`: voice tightened (positive); entity `Sarah` had her established stoicism contradicted in para 4 (operator: was this intentional?); structural shift — para 3 premise was rewritten, paragraphs 5-7 may now be inconsistent").

4. **No `feedback.md` write at this stage.** Revision audit is informative, not corrective — it surfaces patterns. Operator iterates against the surfaced findings; subsequent `pre-ship-audit` (when the operator eventually marks `ready_for_review`) consumes the iteration.

## Quality criteria

- Each finding includes specific revision references (window-start revision ID + window-end revision ID) so operator can diff inline via the cockpit if needed.
- Diff scope is bounded to the audit window — Reviewer does NOT re-audit the entire draft, only the changes within the window. (Full-draft audit happens at `pre-ship-audit` time.)
- Voice findings scoped to diff use the universal anti-pattern baseline + operator-declared `_voice.md` anti-patterns; the universal baseline does not need re-declaration per-recurrence.
- Entity findings scoped to diff cite the specific entity file + specific established-fact contradiction, per `entity-continuity.md` spec.
- Verdict `clean` produces no `Clarify` (silent pass). Verdict `notable-changes` may produce a `Clarify` if the operator's `_preferences.yaml` opts into notable-change surfacing (default: surface). Verdict `concerning-drift` always surfaces.
- Drafts in `published` status are excluded — revision audit is for in-progress work only. Post-publication revisions audit through a different lens (`continuity-audit` cross-piece check).

## How this composes with other audits

- `pre-ship-audit` (reactive, per-draft, full-content audit before publication): unchanged. Long-arc workspaces eventually mark drafts `ready_for_review` and pre-ship-audit fires the full audit chain.
- `corpus-coherence-check` (periodic, cross-corpus, post-publication): unchanged. Audits published corpus for cross-piece drift.
- `revision-audit` (periodic, in-progress drafts, diff-scoped): **new**. Fills the gap between draft-saved-but-not-yet-ready-for-review and published.
- `outcome-reconciliation` (daily): now folds revision-audit findings into `_signal.md` alongside pre-ship-audit and corpus-coherence-check findings.

The three audit recurrences compose without redundancy: pre-ship-audit is *moment* (per-draft, gate); corpus-coherence-check is *aggregate* (cross-corpus, post-pub); revision-audit is *trajectory* (per-draft-over-time, in-progress).

## Out of scope

- Revision audit does not enforce anything — it surfaces patterns. The gate is `pre-ship-audit`; revision audit is observational.
- Revision audit does not write to operator-canon (`_voice.md`, `_editorial.md`, `_entities.md`). Findings surface via `Clarify` for operator authoring.
- Revision audit does not run on `archived` or `retired` pieces.
- For workspaces with no drafts in window (operator on vacation, no edits made), the recurrence fires, finds zero drafts to audit, writes a one-line `stand_down: no drafts in window` entry to `judgment_log.md`, exits silently. No `Clarify`. No noise.
