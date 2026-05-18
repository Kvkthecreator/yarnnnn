# Mandate — netflix-script-author

> Workspace authored 2026-05-18 by operator on behalf via ADR-283 step 6 alpha-author dogfood. Premise + character architecture authored from operator prompt; voice / editorial / entity substrate authored by Claude on operator's behalf per ADR-209 attribution discipline (operator-attributable; framed honestly as alpha-bundle stress-test persona — not a real Netflix development project at this moment).

## Project premise

A modern-day Korea-set thriller series in the lineage of *The Thomas Crown Affair* (1968 / 1999) and *The Dark Knight* (2008). An affluent mastermind who never executes the theft himself — he architects layered proxies, manipulates the institutions around him, and treats the heist itself as a secondary art form to the *staging* of it. The target evolves across the series from physical crypto cold-storage (a hard drive holding BTC) to more abstract financial-institutional thefts as the protagonist's ambition compounds.

The series is structurally about the **layering** — the proxy chains, the institutional asymmetries the mastermind exploits, the moral ambiguity of theft from people who themselves stole. Joker-thematic: the mastermind is not after the money; he's after the proof that the system can be moved. Thomas-Crown-thematic: he is not poor, not desperate, not driven by need — driven by the elegance of the act and the puzzle of getting away with it.

## Primary Action

Author screenplay scenes, character beats, episode outlines, and series-bible material for the Korea-modern Thomas-Crown-Joker thriller — building a continuous, contradiction-free narrative substrate over 6+ months of long-arc development, where every shipped scene is consistent with established character voice, established plot continuity, and the series's declared tonal register.

## Success Criteria

- Internal coherence audit shows zero unresolved continuity breaks across the developed corpus (scenes, outlines, character beats).
- Voice fingerprint stable per voice declaration:
  - Author voice (stage directions, scene headings, action lines): clinical, present-tense, no editorializing.
  - Character voices (per-character voice declarations in `entities/{character}.md`): distinct enough that Reviewer can detect character-voice drift.
- No silent contradiction with previously-established character backstory, established plot points, or established institutional facts (which Korean exchange, which year, which character has which alibi).
- Anti-AI-slop signatures absent from shipped material — screenplay format reads as written by a working screenwriter, not an LLM trained on script databases.
- **Pre-audience honest signal**: zero unresolved entity-continuity breaks across full corpus. There is no production interest, no audience, no commerce signal — the only audit signal is internal coherence. This is by design per ADR-283 D7.

## Boundary Conditions

- No scene authored solely by AI without operator's authorial intent. Claude-Code-drafted material may be a starting point; what enters the corpus must be operator-edited, operator-attributed (operator persona = the synthetic screenwriter behind this workspace).
- No silent character-voice drift. If a character's voice meaningfully evolves (a 6-episode arc justifying it), the evolution is operator-declared in the character's `entities/{slug}.md`, not slow leak.
- No new plot-canonical facts that contradict prior plot canon without explicit revision-audit pass.
- No "for the audience" hand-waving. The series is structurally about layering and indirection; the prose must respect that — characters do not explain their motivations to the camera, do not deliver thematic monologues, do not narrate.
- No fiction-laundering of real institutions. Korean exchanges and crypto-firms referenced are fictional composites unless explicitly authored as references to real ones with operator attribution and reason.

## What this operation is

This operation exists to **build the screenplay corpus that can be developed as a series over 12-18 months without losing internal coherence**. The Reviewer is the operator's active script editor — its job is to catch character-voice drift (does Jaewon sound like Jaewon in scene 14?), flag continuity breaks (in episode 2 we established the bridge was rigged at 3am; episode 5 has the bridge timing at 11pm — which is canon?), enforce the anti-slop floor (no LLM-shaped screenplay prose), and protect the tonal control of the series. The operation is failing if the Reviewer waves through a scene where a character's voice has homogenized into the median screenplay voice; it is also failing if it blocks legitimately evolved character beats that the long arc earned.

The pre-audience nature of this workspace is load-bearing — `_signal.md` runs internal-coherence-only. There is no audience growth metric, no commerce signal, no engagement feedback. The audit is purely against the corpus itself: does this scene compose cleanly with everything authored before it? That's the only question.

## Edge hypothesis

The series's structural edge is **showing the layering at the prose level**, not just at the plot level. Most heist thrillers tell the audience "the mastermind never gets his hands dirty"; this corpus has to *demonstrate* it in how scenes are constructed — the mastermind appears at moments where the wrong-handed proxies execute, and the prose has to make the asymmetry visible without naming it. Falsified if scenes routinely read as "mastermind dialogue with proxy executing in next scene" — that's the average heist structure. Working when scenes routinely show proxies operating from incomplete information, the mastermind's hand visible only by absence.

## Rules of operation

1. **Voice declaration is multi-voice.** Author voice (stage directions, action) is distinct from each character's spoken voice. Per-character voice declared in `entities/{character-slug}.md`. Reviewer audits each scene's character dialogue against the relevant character's declared voice.
2. **Entity continuity check before ship.** Every scene passes a Reviewer entity-continuity audit. The character's established backstory, the institutional facts, the plot canon — all checked. This is the load-bearing audit for this workspace.
3. **Tonal control non-negotiable.** Joker-thematic + Thomas-Crown-thematic + no audience-pandering. Reviewer hard rejects scenes where a character explains the theme to the camera, monologues motivation, or breaks the indirection discipline.
4. **Anti-AI-slop floor.** Screenplay-specific anti-patterns (see `_voice.md`): no "INT. WAREHOUSE — NIGHT — A figure emerges from the shadows", no "BEAT" used to manufacture tension where the prose should carry it, no exposition disguised as dialogue.
5. **Revision discipline.** `revision-audit` recurrence runs Friday EOD comparing current scene/outline state against prior revisions. The Reviewer surfaces what changed and asks: was this evolution operator-authored or accidental drift?
6. **Attribution required.** Every scene attributable to the operator (synthetic screenwriter persona) — not LLM-generated from prompt. Where Claude drafts a scene the operator edits it before it enters the corpus.

## Authorial lifecycle

Every scene / outline / character beat passes through:

- **Draft**: operator authors in `/workspace/context/authored/{scene-slug}/content.md`. Voice + continuity not yet enforced.
- **Pre-ship audit**: operator marks draft `ready_for_review`. Reviewer fires `pre-ship-audit` — voice (author + relevant characters) + entity-continuity + tonal-control + anti-slop. Approves, defers (with directive — e.g., "Jaewon's voice has drifted toward the proxy's register in para 5"), or rejects.
- **Canonized**: scene moves into the corpus as canon. Future scenes audited against it. Revisions tracked per ADR-209.

## Daily Discipline

- Pre-session: read `_voice.md` (author voice); read 1-2 relevant `entities/{character}.md` voice declarations for the characters in today's scenes; check `_signal.md` for drift flags.
- During-session: write scenes, outline beats, develop character. Reviewer available on demand for per-passage voice audit (especially useful when shifting between characters mid-scene).
- Pre-ship: mark scene `ready_for_review`; Reviewer fires pre-ship-audit; iterate or canonize.
- Friday EOD: `revision-audit` recurrence runs across the week's revisions; Reviewer surfaces drift patterns to address in next-week's authoring.

## Series-bible status

The series bible (premise, character architecture, episode arcs, institutional landscape) is itself a piece in the corpus — lives at `/workspace/context/authored/series-bible/content.md`. The bible declares what's canonical; the entity files declare per-entity detail. When the bible changes, it's a revision-audit-level event; the Reviewer surfaces whether existing scenes still compose with the updated bible.

> This is a **synthetic stress-test persona** for the alpha-author bundle. The premise is real (Korean-modern Thomas-Crown-Joker thriller), the workspace is real (provisioned on prod, ADR-283 step 6), but no production interest, no agent, no studio is involved. The dogfood goal is to exercise the bundle's load-bearing surfaces — long-arc multi-character coherence, multi-voice declaration, tonal-control discipline — not to develop a Netflix project. Future graduation to real-project status would re-author this MANDATE accordingly.
