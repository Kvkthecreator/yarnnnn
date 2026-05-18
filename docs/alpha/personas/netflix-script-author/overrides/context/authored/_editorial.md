# Editorial — netflix-script-author ship / hold criteria

> Workspace editorial authored 2026-05-18 by operator on behalf via ADR-283 step 6 dogfood. Reviewer reads at every pre-ship audit. Operator-attributable per ADR-209.

## Declared editorial principles

1. **Every canonized scene either advances character / plot / tone OR contributes a load-bearing setup for a future payoff.** Scenes that serve none of these get held. The series is long-arc — every minute of screen time has to compound.

2. **Continuity is non-negotiable.** Once a fact is canonized (a character did X in episode 2, an institution operates in way Y, the bridge of 1997 happened in March not April), it stays canon until an operator-authored revision-audit pass declares otherwise. Silent contradiction is the single biggest threat to the corpus's defensibility — the series collapses if a writer's room reading the substrate finds plot canon contradicting itself.

3. **Tonal control over plot momentum.** If a scene moves the plot forward but reads as out-of-tone (a character monologues, an action sequence becomes generic thriller staging, the indirection-discipline breaks), the scene gets held. Plot can be re-staged; tonal control compromises compound.

4. **Author voice and character voice both must hold.** Stage directions in author voice; dialogue in the relevant character's voice. Reviewer audits both. A scene where the action lines are clean but the dialogue has drifted into generic-thriller voice gets deferred (not rejected — operator-fixable).

5. **No "fix it in post" thinking.** This is screenplay corpus, not draft-and-revise-later. What ships into the canonized state is what the canon is. Revisions happen via explicit revision-audit, not via accumulated quiet edits.

6. **Anti-AI-slop floor is harder here than in audience-bearing workspaces.** Screenplay format has very specific anti-patterns (BEAT, generic noir slug-lines, exposition-disguised-as-dialogue, etc.) that an LLM trained on script databases produces by default. The Reviewer rejects these on sight per `_voice.md` anti-patterns.

7. **The series-bible is the canon of canons.** When series-bible canonical premise / character architecture / institutional landscape changes, it's a revision-audit-level event affecting all prior scenes. Bible changes get held until the operator has time to do a corpus-wide audit pass — they're not made casually.

## What gets canonized

A scene / outline / character beat **canonizes** when all of these hold:

- Advances character, plot, or tone (or load-bearing setup for future payoff).
- Author voice fingerprint matches `_voice.md` author voice declaration.
- All character dialogue matches the relevant character's declared voice in `entities/{character-slug}.md`.
- No entity-continuity break — established character facts, institutional facts, plot canon all consistent.
- No tonal-control violation — no character explains theme, no camera-aware dialogue, no exposition-disguised-as-dialogue, no "smart-character" monologuing.
- No screenplay-specific anti-slop signature (BEAT, generic noir staging, etc.).
- The scene reads aloud cleanly — operator self-audit pass complete.

## What gets deferred (with directive)

The Reviewer **defers with directive** (operator iterates and re-submits) when:

- Author voice mostly holds but has 1-2 anti-pattern leaks (one adverb-stack, one "BEAT" that should be deleted, one over-staged slug-line).
- A character's dialogue has drifted toward the median screenplay voice in 1-2 lines but is mostly in-voice — Reviewer flags the specific lines.
- A continuity break is detected but operator-fixable in a pass (a minor inconsistency that can be revised without affecting plot canon).
- The scene's tonal control is mostly right but has one moment of editorializing the author voice slipped into.
- The scene is in-tone but reads thin — Reviewer flags "this scene needs one specific physical detail to land" and defers.

## What gets rejected

The Reviewer **hard rejects** when:

- A character monologues motivation or explains theme to the camera.
- A scene has multiple anti-patterns from `_voice.md` (author or character).
- A continuity break with plot canon AND no operator-authored revision-audit pass to update the canon.
- Exposition disguised as dialogue ("As you know, the bridge of 1997...").
- Camera-aware dialogue or fourth-wall break (unless explicitly operator-authored as a series device with `editorial_exceptions` in the scene's profile.md).
- A character's voice has homogenized into another character's — distinctness broken.
- Generic noir staging that betrays no specific work — "A figure emerges from the shadows" / "The room is heavy with tension" / etc.

## Long-arc-specific criteria

This workspace is pre-audience by design (no production interest, no agent, no studio per ADR-283 D7). The audit signal is purely internal coherence. Specifically:

- **`pre-ship-audit`** runs on every scene marked `ready_for_review`. Most load-bearing single audit.
- **`corpus-coherence-check`** runs twice-weekly. Audits the whole corpus for emerging continuity breaks across episodes / scenes — patterns that single-scene audits miss.
- **`revision-audit`** runs Friday EOD. Compares the week's revisions against prior state per ADR-209. Surfaces drift: was this evolution operator-authored or accidental?
- **`outcome-reconciliation`** runs daily. Folds the day's audit findings into `_signal.md` for next-session re-orientation.

There is no external audience signal to fold. `_signal.md` is purely a coherence-state ledger.

## When external signals do arrive

If production interest, a writers' room, or studio engagement ever surfaces, that's a meaningful state change for this workspace. At that point, operator authors:

- Revised MANDATE (this workspace's framing as synthetic stress-test becomes obsolete — it's now a real project).
- `_signal.md` external_outcomes frontmatter per ADR-283 step 2 (option, produced, optioned, dropped — operator-authored events).
- `_editorial.md` additions — audience-facing concerns return (which platform, what episode length, what showrunner sensibility).

The Reviewer reads the updated MANDATE / `_editorial.md` / `_signal.md` at every subsequent audit. The architecture supports this graduation without rebuilding; the audit substrate just gains an audience signal layer.

## Series-bible interaction

The series-bible at `/workspace/context/authored/series-bible/content.md` declares what's canonical at the series-level (premise, character architecture, institutional landscape, episode arc structure). The bible is itself a piece in the corpus and gets the same audit treatment:

- Bible changes go through `pre-ship-audit` with extra weight — the Reviewer flags downstream impact (which existing scenes would now have continuity breaks against the updated bible?).
- Operator decides per change: revise the bible and accept the downstream audit pass, or hold the bible change and revise scenes that suggested it.
- The bible is the canon of canons; when it changes, the canon-trail is operator-authored, never silent.

## Per-scene editorial exceptions

Each scene's `profile.md` may carry `editorial_exceptions: [...]` frontmatter naming specific declared rules that scene legitimately bends. The Reviewer respects exceptions when present and operator-attributed. Don't author exceptions casually — they accumulate and signal an editorial discipline that needs revising at the `_editorial.md` level. If a pattern recurs as exception, promote it to the declaration.

## Audit cadence summary

| Cadence | Recurrence | Audit scope |
|---|---|---|
| Per scene | `pre-ship-audit` | Voice (author + character) + entity continuity + tonal control + anti-slop |
| Twice weekly | `corpus-coherence-check` | Cross-scene continuity, voice homogenization patterns |
| Friday EOD | `revision-audit` | This week's revisions vs prior state (ADR-209 revision chain) |
| Daily | `outcome-reconciliation` | Folds audit findings into `_signal.md` |

The cadence reflects this workspace's pre-audience reality — heavy on internal-coherence audits, light on external signal folds.
