# yarnnn-author persona overrides

> ADR-230 D6 + ADR-283 D5: persona-specific overrides directory for the `yarnnn-author` workspace. Files placed here are applied as Step 4 of `activate_persona.py` after the bundle fork, with `authored_by="operator:yarnnn-author"` per ADR-209 attribution.

## Purpose

The alpha-author bundle ships **medium-agnostic** templates at `docs/programs/alpha-author/reference-workspace/`. The `yarnnn-author` workspace is one specific operator instance running that bundle — founder content + IR-narrative authorship about YARNNN itself. Workspace-specific authored content (specific voice fingerprint, specific editorial principles, specific entity declarations) lives here as overrides.

## What goes here

Files in this directory mirror the substrate paths they override. Examples (none authored yet — this is the activation-pending state per ADR-283 step 6):

- `context/_shared/MANDATE.md` — operator's specific Primary Action for yarnnn-author (e.g., *"Author and ship corpus pieces about YARNNN's architecture, thesis, and operational discipline that compound into a recognizable founder voice over months"*)
- `context/_shared/IDENTITY.md` — operator's specific authorial posture
- `context/_shared/BRAND.md` — YARNNN brand voice + visual identity references
- `context/authored/_voice.md` — operator's declared voice fingerprint (positive markers + anti-patterns specific to this workspace)
- `context/authored/_editorial.md` — what gets shipped vs held for yarnnn-author specifically
- `review/IDENTITY.md` — Reviewer persona override (default editor persona may stay, or operator picks a specific editor character)
- `review/principles.md` — workspace-specific Reviewer principle additions

## When this gets populated

Per ADR-283 step 6 (dogfood activation), this directory populates **after first activation** as the operator authors their specific stance against the bundle templates. Pre-activation, the directory is empty (this README is the only file).

Activation flow per ADR-230 + ADR-283 step 5:
1. `activate_persona.py --persona yarnnn-author` is run
2. `_fork_reference_workspace(persona.user_id, persona.program)` copies the bundle templates into `/workspace/`
3. *(step 6)* operator opens chat and walks through the differential-authoring conversation, which lands edits in `/workspace/` substrate
4. Eventually, the operator-authored content lands HERE as a graduated override (the bundle reflexive-loop per ADR-222 roadmap — graduating operator-validated authored content back to a persona-tracked artifact)

## What does NOT go here

- Reference-workspace bundle templates (those live in `docs/programs/alpha-author/reference-workspace/`)
- Generic alpha-author principles (those live in the bundle)
- Per-piece corpus content (`/workspace/context/authored/{piece-slug}/content.md` — operator-authored at workspace runtime, not in the alpha-ops registry)
- Live `_signal.md` data (accumulated by recurrences at workspace runtime)

The override directory is for *operator authored stance about THIS workspace*, not for any data that recurrences write.
