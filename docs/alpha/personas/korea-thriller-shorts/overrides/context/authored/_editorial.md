# Editorial — korea-thriller-shorts ship / hold criteria

> Workspace editorial authored 2026-05-18 by operator on behalf via ADR-283 step 6 dogfood. Reviewer reads at every pre-ship audit. Operator-attributable per ADR-209.

## Declared editorial principles

1. **Every shipped short either generates cleanly OR teaches the prompt-writing how to generate cleaner next time.** Generation failures are signal — `_signal.md` captures iteration counts. Shorts that take 8+ iterations to land a usable take get held for prompt-revision rather than shipped.

2. **Canon-consistency is non-negotiable.** Jaewon in this workspace = Jaewon in netflix-script-author. A short that contradicts the entity-file declaration (e.g., shows him raising his voice, or in a posture the canon explicitly excludes) is a hard reject regardless of how visually clean it is.

3. **Shoot-ready criterion is the load-bearing audit.** A prompt that a working AI-prompt engineer could not generate from without operator clarification is incomplete. Reviewer defers (not rejects) when the prompt is mostly right but has 1-2 under-specified elements — operator fixes and re-submits.

4. **Tonal control over generation cleanliness.** A short that generates pristinely but reads as generic Korean-thriller B-roll is a worse outcome than a short that takes 3 iterations but lands in-tone. Reviewer prioritizes tonal-control audits over "is this prompt easy to generate."

5. **Anti-AI-slop visual floor is harder here than in audience-bearing workspaces.** AI-video-gen tools produce generic compositions by default; the corpus depends on the prompts pushing past defaults. Reviewer rejects on `_voice.md` anti-patterns aggressively.

6. **Format discipline.** Shot-spec format, not screenplay format. Slug-line creep (`INT. JAEWON'S OFFICE — DAY`) is a hard reject — that's screenplay, not AI-video-gen prompt.

7. **Per-tool targeting.** Different tools accept different prompt shapes. Each short declares `target_tool` in `profile.md`; Reviewer respects tool-specific syntax (Higgsfield aspect-ratio overrides, Sora long-form prompt structure, Runway camera-direction syntax). Tool-agnostic prompts may exist but are explicitly declared.

8. **Sync-discipline with netflix-script-author.** When character canon evolves in either workspace, the entity files in both update via PR. The shorts workspace does not invent new Jaewon canon unilaterally — invent in netflix, reflect here.

## What gets canonized

A short / sequence **canonizes** when all of these hold:

- Prompt is shoot-ready per the criterion above.
- All character-canon depictions consistent with shared entity files (`entities/jaewon.md` etc.).
- No tonal-control violation (per `_voice.md` cross-prompt declarations).
- No anti-slop signature (per `_voice.md` anti-patterns).
- Format is shot-spec (not screenplay slug-lines).
- Target tool declared in `profile.md`.
- Generation produced a take that matches the prompt's intent (or operator explicitly accepts a divergence as canonical — declared in `profile.md`).
- Operator's self-audit complete (the prompt reads cleanly; the generation lands the intended feeling).

## What gets deferred (with directive)

The Reviewer **defers with directive** (operator iterates and re-submits) when:

- Prompt is mostly shoot-ready but has 1-2 under-specified elements (lighting direction missing, frame position vague) — Reviewer flags the specific gaps.
- 1-2 adjectives are doing emotional work that should be physical staging — Reviewer suggests the replacement.
- Canon-character depiction is mostly right but has 1 visual choice that contradicts entity-file (e.g., framing Jaewon's face in a close-up that the canon says should stay back-three-quarters) — operator-fixable.
- Sequence has internal connective tissue but 1 transition is under-specified — Reviewer flags the specific shot pair.
- Generation didn't quite land but the prompt looks correct — Reviewer flags "this may be a tool-specific syntax issue; try $alternative phrasing for $tool".

## What gets rejected

The Reviewer **hard rejects** when:

- Prompt contains multiple anti-patterns from `_voice.md` ("mysterious figure" + "atmospheric lighting" + adjective-stacks).
- Canon contradiction with shared entity files AND no operator-authored canon-update first.
- Format is screenplay slug-lines, not shot-spec.
- Character does the thing the canon prohibits (Jaewon raises voice, Jaewon explains himself in shot).
- Generic AI-video-gen filler shots that could appear in any Korean thriller AI demo — no specific canon-grounding.
- Camera-aware staging (character looks at camera, fourth-wall breaks) without operator-authored exception in `profile.md`.
- "In the style of [director]" or other reference-laundering as substitute for visual specification.
- Inline editorial about character motivation ("a man who is clearly hiding something...").
- Length-padding adjectives (very, quite, dramatic, stunning) — present at all.

## Per-tool editorial criteria

Different tools have different "what works" patterns. Operator + Reviewer learn over time; observed patterns get folded into `_signal.md`:

| Tool | Known strengths | Known weaknesses | Editorial notes |
|---|---|---|---|
| Higgsfield | Static + slow-motion shots, vertical 9:16, character holding still | Dialogue, fast cuts, complex tracking | Lean into stillness; short durations (3-8s). |
| Sora | Long-form sequences, complex scene composition | Specific Korean cultural elements may default to generic Asian aesthetic | Over-specify Korean cultural detail. |
| Runway Gen-3 | Camera-direction execution, tracking shots | Faces, lip-sync, fine-grained motion | Lean into camera moves; avoid close-up face work. |
| Veo | High-resolution interiors, lighting control | Real-world location accuracy (avoid named-real-place specificity) | Specify lighting + interior surfaces; keep locations fictional-composite. |

> Operator authors per-tool observations into `_signal.md` over time; Reviewer reads them at audit. New tool added → add row here + declare its observed patterns.

## Long-arc-specific criteria

This workspace is pre-audience by design (no distribution target yet per ADR-283 D7). Internal audit signal is the sole truth source:

- **`pre-ship-audit`** runs on every short marked `ready_for_review`. Most load-bearing per-piece audit.
- **`corpus-coherence-check`** runs twice-weekly. Audits cross-short canon-consistency, tonal-control patterns, prompt-format drift.
- **`revision-audit`** runs Friday EOD. Compares week's prompt revisions against prior state (ADR-209 revision chain). Surfaces drift: was this prompt evolution intentional or generation-failure-driven?
- **`outcome-reconciliation`** runs daily. Folds the day's audit + generation observations into `_signal.md`.

`_signal.md` accumulates per-tool generation patterns over time — operator + Reviewer reference at next prompt-write session.

## When external signals arrive

If shorts get used in pilot pitch, marketing distribution, or social media — that's meaningful state. At graduation, operator authors:

- Revised MANDATE (synthetic-stress-test framing becomes obsolete).
- `_signal.md` external_outcomes per ADR-283 step 2 (pitch outcome, distribution metric, audience signal).
- `_editorial.md` audience-facing additions (platform-specific concerns, audience-target editorial criteria).

Architecture supports graduation without rebuilding; the audit substrate just gains an audience layer.

## Series-bible interaction

Unlike netflix-script-author, this workspace doesn't own a series bible. The shared canon (Jaewon's entity file + future plot canon) is authored in netflix-script-author and synced here. When canon changes in netflix:

- Operator PRs the updated entity file to `docs/alpha/personas/korea-thriller-shorts/overrides/context/authored/entities/{slug}.md`.
- Re-run `activate_persona.py --persona korea-thriller-shorts` to land the updated canon.
- Reviewer reads updated canon at all subsequent audits.

If a short establishes visual canon that the series should respect (e.g., a specific staging convention for Jaewon's office), operator authors the reverse direction: PR to netflix-script-author's entity file.

## Per-short editorial exceptions

Each short's `profile.md` may carry `editorial_exceptions: [...]` naming specific rules the short bends — fourth-wall break in a one-off art piece, a close-up of Jaewon's face for a canon-specific moment, etc. Reviewer respects exceptions; doesn't respect drift. Accumulating exceptions signal a discipline that needs revisiting.

## Audit cadence summary

| Cadence | Recurrence | Audit scope |
|---|---|---|
| Per short | `pre-ship-audit` | Prompt format + visual specificity + canon consistency + tonal control + anti-slop |
| Twice weekly | `corpus-coherence-check` | Cross-short canon, tonal-control patterns, per-tool generation patterns |
| Friday EOD | `revision-audit` | This week's prompt revisions vs prior state (ADR-209) |
| Daily | `outcome-reconciliation` | Folds audit + generation outcomes into `_signal.md` |
