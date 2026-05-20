# Mandate — alpha-author

> **Persona**: korea-thriller-shorts (short-form AI-video-gen prompts in the Jaewon canon). The program-slug heading marker (`alpha-author`) is preserved per ADR-244 D2 + ADR-283 D2 so `parse_active_program_slug` resolves the program for `apply_substrate_update` (ADR-292) and `bundles_active_for_workspace`. Persona-specific Primary Action follows.

> Workspace authored 2026-05-18 by operator on behalf via ADR-283 step 6 alpha-author dogfood. Premise + character canon shared with netflix-script-author (same Jaewon, same modern-Korea Thomas-Crown-Joker universe); format is short-form AI-video-gen prompts (Higgsfield et al.). Synthetic stress-test persona — no production interest, no audience deliverable yet. Operator-attributable per ADR-209.

## Project premise

Short-form video pieces (15-90 seconds each, vertical or horizontal depending on shot) set in the same Korean-modern Thomas-Crown-Joker universe as netflix-script-author. Self-contained vignettes that exist as shoot-ready prompts for AI video generation (Higgsfield, Sora, Runway, Veo) — visual storytelling first, dialogue minimal or absent, every shot generation-ready without further translation.

The shorts are **canon-consistent visual sketches** in Jaewon's world: a proxy executing without context, a Han River walk where the audience reads the indirection from staging alone, a single moment of post-heist composure. The series-bible canon (when netflix-script-author canonizes new plot facts) flows into this workspace via shared entity files. The shorts can be standalone or feed into the series's promotional / pilot-pitch context, but they are not episodes of the series.

## Primary Action

Author shoot-ready AI-video-generation prompts — single shots or 4-8 shot sequences — that are visually specific enough for tools like Higgsfield to generate without ambiguity, canon-consistent with Jaewon's character voice and the universe's tonal register, and architecturally complete (each short closes a visual arc).

## Success Criteria

- Each shipped short generates cleanly in the target AI-video-gen tool on first or second pass (operator-attributable signal: did the prompt land or did it require multiple re-prompts to get something usable?).
- Character canon stays consistent with netflix-script-author entity files — Jaewon's physical staging, register, behavior under stress all hold across both workspaces.
- Tonal control preserved at the short level — no short reads as generic thriller B-roll; each carries the Thomas-Crown / Joker register.
- Anti-AI-slop floor specific to AI-video-gen: no generic noir staging in prompts ("a mysterious figure in shadows"), no thematic monologuing baked into the visual ("a man stares contemplatively"), no Marvel-shaped Korean-American crossover staging.
- Shoot-ready criterion: a working video editor or AI-prompt engineer reading the prompt can produce the shot without operator clarification.

## Boundary Conditions

- No prompt authored solely by AI without operator's authorial intent. Claude-Code-drafted prompts may be starting points; what gets generated must be operator-edited, operator-attributed.
- No silent character-canon drift. Jaewon in this workspace = Jaewon in netflix-script-author. When canon evolves in either, the entity files sync via PR.
- No format-laundering: this is AI-video-gen prompts, not screenplay format. Don't use screenplay slug-lines (`INT. JAEWON'S OFFICE — DAY`); use shot-spec format (e.g., "Wide shot, glass-walled high-rise office, late afternoon golden light from camera left, Han River through windows, single figure at desk in mid-frame, back to camera").
- No prompts that generate dialogue-heavy shots — AI-video-gen tools handle lip-sync poorly. If a short needs spoken dialogue, the shot is wrong for this format; downgrade to wordless visual or use post-gen audio overlay.
- No fiction-laundering of real institutions. Korean exchanges, crypto firms, government bodies stay fictional composites consistent with the shared canon.

## What this operation is

This operation exists to **build a visual corpus that lives in Jaewon's universe**, exercising the AI-video-gen workflow as a meaningful authorial discipline rather than a "type a prompt and hope" activity. The Reviewer is the operator's active director — catches prompt vagueness ("a Korean man in an office" is not shoot-ready), flags character-canon drift (does Jaewon's posture in this short match the entity-file declaration?), enforces tonal control (does this shot read as Thomas-Crown-Joker or generic thriller B-roll?), and protects the visual anti-slop floor.

The pre-audience nature is identical to netflix-script-author — `_signal.md` runs internal-coherence-only. The shorts may eventually be used as pilot-pitch context or social-media-distribution pieces, but at activation they have no audience metric. The audit is purely against canon + visual quality + shoot-readiness.

## Edge hypothesis

Most AI-video-gen output reads as "AI-shaped" — generic compositions, default cinematography choices, no specific cultural texture. The edge here is **canon-grounding + specificity**: every prompt is authored against a declared character entity + a declared visual register, so the AI tool generates IN-canon shots rather than median-shaped shots. Falsified if shorts routinely come out looking like generic Korean-thriller AI-video output, or if Jaewon's visual identity homogenizes into "Asian businessman in suit."

## Rules of operation

1. **Shot-spec format, not screenplay format.** Each prompt explicitly declares: shot type (wide/medium/close), location, lighting (direction + quality + time of day), subject position in frame, action (what moves), tonal register cue (clinical / tense / contemplative). No screenplay slug-lines.
2. **Character canon shared with netflix-script-author.** Jaewon's `entities/jaewon.md` here is canon-consistent with the netflix workspace's version. Visual cues (his physical staging, his stress-state behavior, his posture) must respect the entity declaration. When evolved, sync both workspaces via PR.
3. **Visual specificity over verbal economy.** Long prompts are better than vague ones. AI-video-gen tools need concrete detail; under-specification produces median-shaped results.
4. **Anti-slop visual floor.** Reviewer hard-rejects on documented prompt anti-patterns (see `_voice.md`): no "mysterious figure", no "dramatic atmosphere", no "stunning cinematography", no adjective-stacked prompts.
5. **Tool-targeted prompts.** Each short declares target tool in its `profile.md`. Prompts may differ per-tool — what Higgsfield accepts well differs from what Sora handles. Operator declares + Reviewer respects.
6. **Attribution required.** Every prompt operator-edited before generation; operator runs the generation; operator selects the canonical take. No "AI authored the prompt, AI generated the video, operator just clicked" — operator hand throughout.

## Authorial lifecycle

Every short passes through:

- **Prompt draft**: operator authors prompt(s) for the short at `/workspace/context/authored/{short-slug}/prompts.md`. Visual + canon + tonal not yet enforced.
- **Pre-shoot audit**: operator marks `ready_for_review`. Reviewer fires `pre-ship-audit` adapted for shorts — visual specificity check, canon-consistency check (against shared entity files), tonal-control check, AI-video-gen-anti-slop check. Approves, defers (with directive — "shot 3 needs lighting direction specified"), or rejects.
- **Generated**: operator runs the prompt through the target tool, lands a canonical take, saves at `/workspace/context/authored/{short-slug}/canonical.mp4` (or URL). Post-generation review pass — does the generation match the prompt's intent?
- **Canonized**: short moves to canon state. Linked to canon entity files (if Jaewon appears, the entity file may reference this short as a visual canon anchor). Future shorts audit against established visual canon.

## Daily Discipline

- Pre-session: read `_voice.md` (prompt format + visual conventions); skim relevant entity files (Jaewon's posture / register / stress-state cues); check `_signal.md` for prompt-pattern drift.
- During-session: write prompts, iterate via Reviewer, generate, select canonical takes. Tool-specific iteration is part of authoring.
- Pre-shoot: mark short `ready_for_review`; Reviewer fires pre-ship-audit; iterate or shoot.
- Post-shoot: operator review of generation; updates `profile.md` with the canonical take + tool used + iteration count signal.
- Friday EOD: `revision-audit` covers any prompt revisions across the week (per ADR-209). Surface drift patterns.

## Canon sync with netflix-script-author

The shared entity universe is load-bearing. Sync discipline:

- When netflix-script-author canonizes a new fact about Jaewon (a new backstory beat, a new capability, a new relationship), the netflix workspace's `entities/jaewon.md` updates first.
- Operator PRs the change to `docs/alpha/personas/korea-thriller-shorts/overrides/context/authored/entities/jaewon.md` to keep the shorts workspace aligned.
- Re-run `activate_persona.py --persona korea-thriller-shorts` to land the updated entity file in the shorts workspace.
- Same direction flow when shorts establishes visual canon that the series should respect.

The two workspaces share canon; the Reviewer in each audits its own workspace; the operator is the cross-workspace canon-sync agent.

> This is a **synthetic stress-test persona** for the alpha-author bundle — same honest framing as netflix-script-author. The premise is real (Jaewon universe, AI-video-gen authoring discipline), the workspace is real (provisioned on prod, ADR-283 step 6), but no commercial generation target yet. The dogfood goal is to exercise the bundle's load-bearing surfaces at a different format + cadence than netflix — visual-first instead of dialogue-first, ship-pulse instead of revision-pulse, AI-tool-targeted instead of audience-targeted. Future graduation to real commercial use (pilot pitch reels, marketing pieces, social distribution) would re-author this MANDATE.
