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

## What's here (authored 2026-05-18 per ADR-283 step 6 dogfood)

Files mirror substrate paths they override. `activate_persona.py` Step 4 walks every `.md` and writes it to the matching `/workspace/` path with `authored_by="operator:alpha-netflix-script-author"` per ADR-209.

| Override | Bundle template overridden | Why differs |
|---|---|---|
| `constitution/MANDATE.md` | `docs/programs/alpha-author/reference-workspace/constitution/MANDATE.md` | Modern Korea Thomas-Crown-Joker thriller series-specific Primary Action; pre-audience honest signal as sole audit; framed honestly as synthetic stress-test persona |
| `operation/authored/_voice.md` | `docs/programs/alpha-author/reference-workspace/operation/authored/_voice.md` | Multi-voice architecture — author voice (stage directions, action) + per-character voices declared at `entities/{character-slug}.md`; screenplay-specific anti-patterns (BEAT, generic noir, exposition-as-dialogue); tonal-control declarations cross-voice |
| `operation/authored/_editorial.md` | `docs/programs/alpha-author/reference-workspace/operation/authored/_editorial.md` | Series-bible discipline; long-arc-specific cadence (corpus-coherence-check + revision-audit + outcome-reconciliation); pre-audience honest signal as sole audit |
| `operation/authored/_entities.md` | `docs/programs/alpha-author/reference-workspace/operation/authored/_entities.md` | Roster index with declared principal characters (Jaewon); entity-continuity discipline notes for screenplay-specific failure modes |
| `operation/authored/entities/jaewon.md` | *(no bundle template — new file)* | Principal character entity. Voice fingerprint (Joker-thematic + Thomas-Crown register, Korean honorific calibration, code-switching rules); stress-state behavior declaration; do/don't examples. |

## Source material

Premise authored from operator prompt (2026-05-18 session): *"a thomas-crown affair inspired series. thriller, crime, thieves mastermind. however, its in modern day korea, related to more modern day theft like crypto and trying to steal some hard-drive with BTC, the mastermind main character that is also affluent, and he never really does the theft himself or is layered by hiring people around him (this is similar to the dark knight joker thematics and thomas crown)"*.

Voice, editorial, entity substrate, and Jaewon character file authored by Claude on operator's behalf with the synthetic-stress-test framing explicit in MANDATE. Honest attribution: there is no production interest, no agent, no studio — this is alpha-author bundle stress-test exercising the load-bearing surfaces (long-arc multi-character coherence, multi-voice declaration, tonal-control discipline).

Operator review at PR time is the final attribution gate. If operator wants to keep this persona's premise but rewrite specific declarations, edit the files here and re-run `activate_persona.py`.

## Activation flow

1. `activate_persona.py --persona netflix-script-author` is run.
2. Step 2: `initialize_workspace(program_slug=None)` ensures YARNNN agent row + kernel skeleton (idempotent).
3. Step 3: `_fork_reference_workspace(...)` copies bundle templates into `/workspace/` (ADR-226 three-tier idempotency).
4. **Step 4: this directory's files apply as overrides** — each `.md` (including `entities/jaewon.md`) writes to the matching path with `authored_by="operator:alpha-netflix-script-author"` per ADR-230 D6.
5. Step 5: specialist agent rows ensured.
6. Step 6: platform connect (skipped — `platform.kind=none`).

After activation, the Reviewer reads this substrate (including the entity layer) at every pre-ship-audit. The `entities/jaewon.md` voice declaration is the load-bearing audit substrate the first time any scene with Jaewon's dialogue gets authored.

## Override evolution

When operator's stance evolves (new characters, refined voice, premise pivots), changes happen in TWO places:

1. The workspace at `/workspace/` via chat-authored edits.
2. The override file here via PR — so next `activate_persona.py` run + future personas / workspace resets land on updated stance.

For new characters specifically: add the file at `entities/{slug}.md` here AND add the row to `_entities.md` roster table. Both in the same PR.

## Graduation path

If this workspace ever transitions from synthetic-stress-test to real Netflix project status (production interest surfaces), the MANDATE's framing changes from "synthetic stress-test persona" to a real-project MANDATE. The override file here gets revised; `_signal.md` gains external_outcomes per ADR-283 step 2. The architecture supports this graduation without rebuilding the workspace.

## Why this workspace specifically matters for the bundle

The alpha-author bundle's claim to medium-agnosticism is *stress-tested* by this workspace. If alpha-author works for both a multi-piece-per-week founder-content cadence (yarnnn-author) AND a single-artifact-over-18-months screenplay (this workspace), the bundle's claim holds. If it works for only one, the bundle is accidentally tilted and the architecture needs amendment.

The revision-pulse recurrence (`revision-audit`, ADR-283 step 2) was authored specifically to handle the screenplay shape — without it, the reactive `pre-ship-audit` loop is the wrong shape for an operator who iterates daily on a single artifact for months.

## What does NOT go here

- Reference-workspace bundle templates (those live in `docs/programs/alpha-author/reference-workspace/`)
- The screenplay itself (lives at `/workspace/operation/authored/screenplay/content.md` or similar — operator-authored at workspace runtime, not in the alpha-ops registry)
- Per-character entity files (those land in `/workspace/operation/authored/entities/{character-slug}.md` at workspace runtime per ADR-283 step 2)
- Live `_signal.md` data (accumulated by recurrences at workspace runtime)
