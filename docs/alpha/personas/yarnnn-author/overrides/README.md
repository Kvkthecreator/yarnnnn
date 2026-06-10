# yarnnn-author persona overrides

> ADR-230 D6 + ADR-283 D5: persona-specific overrides directory for the `yarnnn-author` workspace. Files placed here are applied as Step 4 of `activate_persona.py` after the bundle fork, with `authored_by="operator:yarnnn-author"` per ADR-209 attribution.

## Purpose

The alpha-author bundle ships **medium-agnostic** templates at `docs/programs/alpha-author/reference-workspace/`. The `yarnnn-author` workspace is one specific operator instance running that bundle — founder content + IR-narrative authorship about YARNNN itself. Workspace-specific authored content (specific voice fingerprint, specific editorial principles, specific entity declarations) lives here as overrides.

## What's here (authored 2026-05-18 per ADR-283 step 6 dogfood)

Files mirror substrate paths they override. `activate_persona.py` Step 4 walks every `.md` and writes it to the matching `/workspace/` path with `authored_by="operator:alpha-yarnnn-author"` per ADR-209.

| Override | Bundle template overridden | Why differs |
|---|---|---|
| `constitution/MANDATE.md` | `docs/programs/alpha-author/reference-workspace/constitution/MANDATE.md` | YARNNN founder-corpus Primary Action; thesis-trail success criteria; cross-publish discipline per content/OPS.md |
| `operation/authored/_voice.md` | `docs/programs/alpha-author/reference-workspace/operation/authored/_voice.md` | Claim-first em-dash-fluent founder voice; specific anti-patterns including marketing-speak intensifiers; do/don't examples from canonical docs |
| `operation/authored/_editorial.md` | `docs/programs/alpha-author/reference-workspace/operation/authored/_editorial.md` | Thesis-compounding ship/hold criteria; architecture-grounded over speculation rule; cross-publish-specific criteria for LinkedIn/X/Medium derivatives |

## Source material

Override content distilled from operator's existing repo signal:

- **MANDATE Primary Action + thesis trail** — `docs/THESIS.md`, `docs/ESSENCE.md`, `docs/NARRATIVE.md`.
- **Voice fingerprint** — pattern-matched from `content/posts/` + canonical docs prose. Do/don't examples are real quotes.
- **Editorial principles** — distilled from `content/OPS.md` cross-publish discipline + observable behavior in existing posts.

This is the "persona-canonical paste" pattern per `docs/alpha/CLAUDE-OPERATOR-ACCESS.md` — Claude authored content operator (KVK as YARNNN founder) is structurally responsible for, grounded in operator-attributable repo signal. Drafts land via override application with `authored_by="operator:alpha-yarnnn-author"`; operator review at PR time is the final attribution gate.

## Activation flow

1. `activate_persona.py --persona yarnnn-author` is run.
2. Step 2: `initialize_workspace(program_slug=None)` ensures YARNNN agent row + kernel skeleton (idempotent).
3. Step 3: `_fork_reference_workspace(...)` copies bundle templates into `/workspace/` (ADR-226 three-tier idempotency).
4. **Step 4: this directory's files apply as overrides** — each `.md` writes to the matching path with `authored_by="operator:alpha-yarnnn-author"` per ADR-230 D6.
5. Step 5: specialist agent rows ensured.
6. Step 6: platform connect (skipped — `platform.kind=none`).

After activation, the Reviewer reads this substrate at every pre-ship-audit.

## Override evolution

When operator's stance evolves, the change happens in TWO places:

1. The workspace at `/workspace/` via chat-authored edits.
2. The override file here via PR — so next `activate_persona.py` run + future personas / workspace resets land on updated stance.

Same discipline as `docs/alpha/personas/alpha-trader-2/overrides/`.

## What does NOT go here

- Reference-workspace bundle templates (those live in `docs/programs/alpha-author/reference-workspace/`)
- Generic alpha-author principles (those live in the bundle)
- Per-piece corpus content (`/workspace/operation/authored/{piece-slug}/content.md` — operator-authored at workspace runtime, not in the alpha-ops registry)
- Live `_signal.md` data (accumulated by recurrences at workspace runtime)

The override directory is for *operator authored stance about THIS workspace*, not for any data that recurrences write.
