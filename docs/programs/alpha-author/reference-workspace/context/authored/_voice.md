# Voice — authored corpus voice fingerprint

> **Operator**: author this file. This is the single source of truth for *what your voice sounds like* — the operator-authored declaration the Reviewer reads at every pre-ship audit to detect drift. Be specific. "I'll know it when I see it" doesn't survive contact with a draft you almost shipped because you were tired.

## Declared voice fingerprint

> 4-8 sentences in your own voice, demonstrating the voice you're declaring. The Reviewer reads this both as a description and as a sample — the prose itself is a fingerprint.

Example shapes (overwrite — each is illustrative for a different ICP):

- *"Numbers-first, sentence-fragment-tolerant. I cut hedge words. 'I think', 'maybe', 'perhaps' — out. I lead with the claim and back into evidence. Paragraph one names the argument. The rest pays it off. I link liberally; I do not summarize what I link."*
- *"Working-class register at the dialogue level; clinical register in stage directions. Characters from Bayonne don't say 'utilize'; the script-author voice can. Contractions in dialogue, never in description. Sentence length compresses under emotional pressure; expands during exposition."*
- *"Earnest, mid-length sentences, occasional rhetorical question to signal turn. I do not chase punchy. I do not chase smart. I chase clear and load-bearing."*

## Pattern markers (positive)

> Specific prose patterns you *do* use. The Reviewer pattern-matches new drafts against these.

Examples:
- Lead with the claim; back into evidence.
- Use the second person sparingly and only when addressing a specific reader profile.
- Em-dashes for emphasis, never the parenthetical-comma alternative.
- Paragraph breaks every 2-4 sentences in prose; every 1 sentence in conversational asides.
- No "in conclusion" / "to summarize" / "let's dive in" / "this is fascinating" framings.

## Anti-patterns (negative)

> Specific prose patterns you actively avoid. The Reviewer hard-rejects drafts containing these unless operator authors an explicit exception in a piece's profile.md.

Anti-patterns the Reviewer treats as **default hard rejects** (operator may override per-piece):

- **List-of-three openers**: "It's fast, it's reliable, and it's affordable." Default AI-shaped pattern.
- **"It's worth noting" / "It's important to note"** — hedge construction signalling unconfident insertion.
- **"In conclusion" / "To summarize" / "Let's dive in"** — generic framing markers.
- **"Fascinating" / "incredibly" / "absolutely" / "truly"** — adverb intensifiers with low content.
- **Hedge stacks**: "I think it's worth considering that maybe..." — multiple hedges in a single sentence.
- **Em-dash-replacement of commas without rhythm purpose**: dashes that don't carry emphasis weight.
- **"As we know" / "As you can see"** — assumed-context constructions.

> Author here: add anti-patterns specific to your voice — phrases YOU don't use that an LLM trained on the median would.

## Multi-voice declaration (optional)

> For operators with multiple voices (a screenwriter who writes their own author-voice essays separately from screenplay character voices; a newsletter writer who occasionally posts to a different-toned platform): declare each voice separately. Each piece's `profile.md` references which voice it expresses.

Default for most operators: single voice; no need for this section.

## Relationship to entity substrate

The voice fingerprint declared here governs **how prose sounds**. The entity substrate at `_entities.md` + `entities/{slug}.md` governs **what characters / concepts / facts the prose commits to**. The two compose at every `pre-ship-audit`: voice-audit checks tone + pattern; entity-continuity-audit checks consistency of established facts about persistent entities. For multi-voice workspaces (screenplay character voices), each entity's `entities/{slug}.md` may reference which voice that entity speaks in — keeping voice-fingerprint and entity-continuity load-bearing together. Per ADR-283 step 2 + `/workspace/specs/entity-continuity.md`.
