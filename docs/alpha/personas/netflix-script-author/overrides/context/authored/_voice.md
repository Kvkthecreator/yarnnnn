# Voice — netflix-script-author multi-voice declaration

> Workspace voice authored 2026-05-18 by operator on behalf via ADR-283 step 6 dogfood. Multi-voice: author voice (for stage directions / action lines) + per-character voices (declared at `entities/{character-slug}.md`). Operator-attributable per ADR-209.

## Multi-voice architecture

This workspace declares **multi-voice** per the alpha-author bundle's optional convention. There are two voice layers:

1. **Author voice** — stage directions, scene headings, action lines, slug-lines, transitions. This is the screenwriter's prose. Declared in this file.
2. **Character voices** — each principal character has a declared voice fingerprint at `entities/{character-slug}.md`. Reviewer audits character dialogue against the relevant character's declaration, not against this author-voice file.

Both layers compose at every pre-ship audit: author-voice-audit checks stage directions; per-character voice-audit checks dialogue.

---

## Author voice (stage directions, action, slug-lines)

### Declared author voice fingerprint

Clinical, present-tense, ungenerous with adjectives. Stage directions describe what the camera would see — never what a character is "feeling" unless that feeling is physical (he steadies his hand; she does not blink). Action lines compress: short sentences when the action is fast, longer when the action requires the audience to read a room. No editorializing — the author voice does not tell the audience what the scene means. No camera-direction in prose ("we PUSH IN on..." is allowed only in specific moments where the visual grammar is load-bearing; never as filler). Slug-lines are conventional (INT. / EXT., LOCATION — TIME).

### Pattern markers (positive, author voice)

- **Present tense, third person observational.** Always.
- **Specific physical detail over emotional description.** "He sets the glass down with exactly the wrong amount of force" — not "he is angry".
- **Compression under load.** Short sentences in action; sentence fragments when the rhythm earns it.
- **No editorializing.** Stage directions do not tell the audience what to think about a character.
- **Slug-lines are minimal.** "INT. JAEWON'S OFFICE — LATE AFTERNOON" — not "INT. THE SLEEK GLASS-WALLED OFFICE OF JAEWON, OUR ANTIHERO — A MOMENT OF QUIET BEFORE THE STORM".
- **Korean place names use canonical romanization (Revised, not McCune-Reischauer).** "Gangnam" not "Kangnam". Korean character names: Jaewon, Minseo, Soo-yeon — no honorifics in prose (Korean honorifics live only in dialogue).
- **Action lines split when actions are sequential and matter individually.** Each beat of consequence gets its own line.

### Anti-patterns (negative, author voice — Reviewer hard rejects)

- **"A figure emerges from the shadows."** — generic noir cliché, lazy staging.
- **"BEAT."** — manufactured tension; the prose should carry the pause.
- **"Suddenly..."** — bad action writing; if the action is sudden, write it suddenly, don't announce it.
- **"He couldn't believe his eyes."** — author telling audience what to feel about character's reaction. Show the reaction physically or cut to next beat.
- **"The room was tense."** — tell-not-show. Tense rooms are written through what specific characters do, not described.
- **"We PUSH IN..." / "CAMERA HOLDS..."** as filler — camera direction only when the visual grammar is load-bearing AND a working director would respect the call. Otherwise it reads as the writer cosplaying as the director.
- **Inline editorializing** — "He thinks about the deal that's about to go wrong, the deal he set up, the deal that will make him untouchable" — author commenting on what's about to happen breaks indirection discipline.
- **Adverb-loaded action lines** — "He slowly, carefully, deliberately turns the lock." Pick one. Better: cut all three.
- **Generic noir slug-lines** — "INT. WAREHOUSE — NIGHT" without specifying which warehouse in this universe.
- **Exposition disguised as action** — "She looks at the photo, remembering the time her father told her about the bridge of 1997." If the audience needs to know about the bridge, find a way to make it dramatically present, don't backfill it through staring at photos.

### Pattern examples (do — author voice)

> *INT. JAEWON'S OFFICE — LATE AFTERNOON*
>
> *Glass walls. The Han River through them, sunlight cutting low. Jaewon's at the desk, reading something on a tablet. He does not look up when the door opens.*
>
> *Minseo waits.*
>
> *Jaewon swipes once. Sets the tablet down. Now he looks at her.*

Why it works: specific staging, no adjectives doing emotional work, the indirection is in what's *not* said — Minseo's silence, Jaewon's deliberate non-acknowledgment.

### Pattern examples (don't — author voice, hard reject)

> *INT. JAEWON'S LUXURIOUS OFFICE — LATE AFTERNOON*
>
> *The room exudes power. Jaewon, our mysterious antihero, sits at a sleek desk, his expression unreadable, mysterious, dangerous. He doesn't look up — a power move designed to put Minseo in her place.*
>
> *We PUSH IN on Jaewon's face. BEAT. We can feel the tension.*

Why it fails: "luxurious" / "exudes power" doing emotional work, "mysterious antihero" labels the character for the audience, "unreadable, mysterious, dangerous" adverb-stacking, "a power move designed to" — author explaining the staging, "we PUSH IN" as filler, "BEAT", "we can feel the tension" — all the anti-patterns at once.

---

## Character voice declaration (overview)

Each principal character has their own voice file at `entities/{character-slug}.md`. Each file declares:

- **Spoken voice fingerprint**: 2-4 sentences in operator's prose describing how the character speaks — register, Korean honorifics they use / don't use, sentence length, what they reach for under stress, what they refuse to say.
- **Vocabulary markers (positive)**: specific words / phrases / constructions the character uses.
- **Vocabulary markers (negative)**: specific words / phrases / constructions the character actively avoids.
- **Code-switching**: Korean ↔ English boundaries (which language for which contexts; honorific levels in Korean).
- **Stress-state behavior**: how the voice shifts under pressure — does it compress, expand, formalize, drop register?

The Reviewer reads the relevant character's voice file at every pre-ship audit. Drift detection runs per-character — the system can tell when Jaewon's dialogue has homogenized into the median voice or has started sounding like a different character.

### Why per-character matters here

The series is structurally about **layering**. The mastermind Jaewon, the proxies he hires, the institutional officials he manipulates, the investigators tracking the proxies — each occupies a distinct register. The whole series collapses if the voices flatten into one homogenized "thriller dialogue" register. Per-character voice declaration is the load-bearing audit substrate.

### Initial character roster (declared in `_entities.md`)

- **jaewon** — the mastermind. Affluent, never executes directly. Declared at `entities/jaewon.md`.
- *(operator authors additional character entities as the corpus grows)*

---

## Tonal control declarations (cross-voice)

Some tonal rules apply across all voices in this workspace — they're meta-voice constraints:

1. **No character explains the theme.** Characters do not deliver monologues about what the heist *means*; the meaning is constructed visually + structurally.
2. **No camera-aware dialogue.** Characters do not break the fourth wall, do not deliver lines aimed at the audience, do not echo the series's tagline.
3. **No "as you know" exposition.** Characters do not tell each other things they both already know for the audience's benefit. If exposition is needed, find dramatic situations that surface it.
4. **No "smart" dialogue.** No character is "the smart one who explains everything" — Jaewon is not the Joker's explain-himself-monologue; he is the Joker's *let-the-chaos-do-the-explaining*.
5. **No translation hand-holding.** Korean dialogue stays in Korean (Hangul + romanization in script format); subtitles do the work. Don't translate inline.

The Reviewer treats violations of these as hard rejects at any voice layer.

## Relationship to entity substrate

The voice declarations here (author voice + per-character voices in `entities/{slug}.md`) govern **how the prose sounds**. The entity substrate at `_entities.md` + `entities/{slug}.md` also governs **what the corpus commits to about each character / institution / location** — backstory, capabilities, relationships, alibis. Voice + entity-continuity compose at every pre-ship audit per ADR-283 step 2.

For multi-voice screenplays specifically: each character's `entities/{slug}.md` carries BOTH their continuity facts (what they've done, what they know, who they know) AND their voice fingerprint. The Reviewer reads the whole entity file when auditing dialogue.
