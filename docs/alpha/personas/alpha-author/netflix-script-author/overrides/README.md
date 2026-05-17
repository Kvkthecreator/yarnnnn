# netflix-script-author persona overrides

> ADR-230 D6 + ADR-283 D5: persona-specific overrides directory for the `netflix-script-author` workspace. Files placed here are applied as Step 4 of `activate_persona.py` after the bundle fork, with `authored_by="operator:netflix-script-author"` per ADR-209 attribution.

## Purpose

The alpha-author bundle ships **medium-agnostic** templates at `docs/programs/alpha-author/reference-workspace/`. The `netflix-script-author` workspace is one specific operator instance running that bundle — long-arc screenplay-in-development authorship.

This workspace is the **load-bearing disconfirming case** for the alpha-author archetype per ADR-283 + the 2026-05-15 discourse memo:
- No external audience until shipped (months)
- Revision-pulse loop (single artifact iterated continuously) rather than ship-pulse
- Internal coherence is the sole ground-truth signal for most of the workspace's tenure
- Sparse external-outcome events arrive episodically (table read, optioned, produced)

The ADR-283 step 2 substrate enrichment (entity-continuity substrate + revision-pulse recurrence + sparse external-outcome frontmatter) was authored specifically to handle this workspace's shape.

## What goes here

Files in this directory mirror the substrate paths they override. Examples (none authored yet — this is the activation-pending state per ADR-283 step 6):

- `context/_shared/MANDATE.md` — operator's specific Primary Action for screenplay (e.g., *"Author a feature screenplay over 12-18 months that compounds into a producible, voice-consistent dramatic work"*)
- `context/_shared/IDENTITY.md` — operator's specific authorial posture for long-arc dramatic writing
- `context/authored/_voice.md` — voice fingerprint relevant for screenplay (likely declares multi-voice — author-voice for stage directions, character-voice declarations per character)
- `context/authored/_editorial.md` — what gets shipped at scene/act level vs held for revision
- `context/authored/_entities.md` + `entities/{slug}.md` — populated heavily over time per ADR-283 step 2 entity-continuity substrate (characters, locations, established arc beats)
- `review/IDENTITY.md` — Reviewer persona override (likely a specific editor character — script editor, dramaturg, or operator-authored figure who applies dramatic-writing judgment)
- `review/principles.md` — workspace-specific Reviewer principle additions (e.g., character-voice consistency rules, act-structure load-bearing rules)

## When this gets populated

Per ADR-283 step 6 (dogfood activation), this directory populates **after first activation** as the operator authors their specific stance against the bundle templates. Pre-activation, the directory is empty (this README is the only file).

## Why this workspace specifically matters for the bundle

The alpha-author bundle's claim to medium-agnosticism is *stress-tested* by this workspace. If alpha-author works for both a multi-piece-per-week founder-content cadence (yarnnn-author) AND a single-artifact-over-18-months screenplay (this workspace), the bundle's claim holds. If it works for only one, the bundle is accidentally tilted and the architecture needs amendment.

The revision-pulse recurrence (`revision-audit`, ADR-283 step 2) was authored specifically to handle the screenplay shape — without it, the reactive `pre-ship-audit` loop is the wrong shape for an operator who iterates daily on a single artifact for months.

## What does NOT go here

- Reference-workspace bundle templates (those live in `docs/programs/alpha-author/reference-workspace/`)
- The screenplay itself (lives at `/workspace/context/authored/screenplay/content.md` or similar — operator-authored at workspace runtime, not in the alpha-ops registry)
- Per-character entity files (those land in `/workspace/context/authored/entities/{character-slug}.md` at workspace runtime per ADR-283 step 2)
- Live `_signal.md` data (accumulated by recurrences at workspace runtime)
