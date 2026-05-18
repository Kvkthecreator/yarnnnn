# Voice — yarnnn-author corpus voice fingerprint

> Workspace voice authored 2026-05-18 by operator on behalf via ADR-283 step 6 dogfood. Distilled from FOUNDATIONS / THESIS / NARRATIVE / ESSENCE / existing posts in `content/posts/`. Operator-attributable per ADR-209; treated as fingerprint at every pre-ship audit.

## Declared voice fingerprint

Claim-first, hedge-free, em-dash-fluent. Paragraph one names the argument. The rest pays it off. Sentences compress under load — short clauses chain when the stakes are real, long clauses unspool when establishing a frame. Numbers and proper nouns earn their place; vague intensifiers do not. The register is a founder thinking in public — direct enough to commit, careful enough to back up. Em-dashes carry emphasis, not parenthetical decoration. Two-em-dashes in a paragraph are fine; three signals overuse. Links are load-bearing references, never summarized in the prose around them.

Anti-vibes: the prose treats readers as smart and time-constrained. It does not pander, does not chase punchy, does not chase smart. It chases clear and load-bearing. When something is uncertain, the uncertainty is named directly ("this is the bet we're making" / "this could be wrong if X"), not hedged with "perhaps" or "I think". When something is decided, the decision is stated with the reasoning, not with hedge-stack throat-clearing.

## Pattern markers (positive)

- **Lead with the claim**: paragraph one names the argument; the rest is payoff.
- **Em-dashes for emphasis**: weight-bearing breaks, not comma replacements. Two per paragraph max.
- **Numbered list discipline**: lists carry sequence (1, 2, 3) or carry parallel structure; never use a list to dress up flat prose.
- **Proper nouns and version numbers earn their place**: "Claude Code 1.0", "ADR-209", "Anthropic API" — specificity over genericism ("the leading LLM provider").
- **"Let's be honest" / "The honest answer is X"** — declarative framing when surfacing a hard truth. Used sparingly; loses force if repeated.
- **Architecture-as-corpus framing**: prose treats the repo's decisions as part of the body of work being written about. ADR-XXX references are normal.
- **Short paragraphs (2-4 sentences)** in essays; **single-sentence paragraphs** allowed as rhetorical turn.
- **Direct second person sparingly**: only when addressing a specific reader profile (alpha operator, design partner, IR audience).
- **Numbers without rhetorical inflation**: "$3 signup grant", "2x Anthropic API rate", "5-8 hours of operator-driven dogfood" — the number IS the rhetoric.

## Anti-patterns (negative)

Reviewer **hard rejects** drafts containing these unless operator authors per-piece exception:

- **List-of-three openers**: "It's fast, it's reliable, and it's affordable." Default AI-shaped pattern.
- **"It's worth noting" / "It's important to note"** — hedge-construction signal of unconfident insertion.
- **"In conclusion" / "To summarize" / "Let's dive in" / "Let me unpack this"** — generic framing markers.
- **"Fascinating" / "incredibly" / "absolutely" / "truly" / "genuinely" (when intensifier)** — adverbs with low content. "Genuinely" is allowed when it carries weight ("genuinely looks like" — yes; "genuinely interesting" — no).
- **Hedge stacks**: "I think it's worth considering that maybe..." — multiple hedges in a single sentence.
- **"As we know" / "As you can see" / "Imagine..."** — assumed-context or imagined-reader constructions.
- **Engagement-bait framings**: "Here's why this matters." / "You won't believe what happened next." / "The thing nobody talks about is..." — operator does not write LinkedIn-influencer prose.
- **Marketing-speak intensifiers**: "industry-leading", "best-in-class", "game-changing", "next-generation", "cutting-edge" — none ever.
- **AI-shaped tech prose**: "leverage", "utilize", "ecosystem", "enable" (verb), "empower" — bureaucratic register substitution for direct verbs.
- **Vague claims without artifact backing**: "we built a powerful X" — either name the ADR / file / shipped component, or don't claim it.
- **"At the end of the day"** — colloquial filler that signals nothing.
- **Em-dash-replacement of commas without rhythm purpose**: dashes must carry emphasis weight; if a comma works, use the comma.

## Multi-voice declaration

yarnnn-author is **single-voice** for v1. Essays, posts, IR memos, and deck narratives all share the founder-thinking-in-public register declared above. Internal IR audiences get more dense thesis density; external posts get more setup; the *voice* doesn't shift, the *audience-density* does.

If a meaningfully different voice surfaces (e.g., a separate Korean-language version of the corpus for the Korean ecosystem, or a deliberate satirical voice for a one-off piece), declare it here as a new sub-voice with its own fingerprint section. Default: single voice; no operator-author needed.

## Relationship to entity substrate

The voice declared here governs **how the prose sounds**. The entity substrate at `_entities.md` + `entities/{slug}.md` governs **what concepts the corpus commits to** — load-bearing architectural concepts (the platform-cycle thesis, accumulated-intelligence moat, the cockpit service model, Authored Substrate, etc.) get their own entity files as the corpus references them repeatedly across pieces. Reviewer composes both audits at every pre-ship: voice-audit checks tone + pattern; entity-continuity-audit checks consistency of established positioning across the corpus.

## Pattern examples (do these)

> Operator-authored examples below. Real prose from `content/posts/` and canonical docs. Treat as voice samples the Reviewer matches against.

Example 1 — claim-first opener (from `docs/NARRATIVE.md`):

> *"Let's be honest about the current moment: it genuinely looks like the big LLM providers will own every layer. Claude has Code, Cowork, desktop agents. ChatGPT has memory, browsing, GPTs. Google is embedding Gemini into everything. The prevailing market assumption is that OpenAI, Anthropic, or Google will just do everything. And right now, that assumption feels correct."*

Why it works: opens with the honest framing, lists specifics with proper nouns, names the market assumption directly, closes by conceding the strong form of the argument before pivoting. No hedge, no setup.

Example 2 — em-dash discipline (from `docs/ESSENCE.md`):

> *"YARNNN is an autonomous agent platform for recurring knowledge work — the team you build by chatting."*

One em-dash, weight-bearing, definitional. The second clause is the payoff.

Example 3 — declarative thesis (from `docs/THESIS.md` style):

> *"The product promise in one sentence: Describe your work. Create the agents that do it."*

Two imperative sentences. No "we believe", no "our mission is", no "imagine if". Just the promise.

## Pattern examples (do not do these)

Example 1 — list-of-three opener (hard reject):

> *"YARNNN is fast, reliable, and built for the next generation of knowledge workers."*

Why it fails: list of three, marketing intensifiers, no specific claim, no proper nouns.

Example 2 — hedge stack (hard reject):

> *"I think it's worth considering that maybe the agent platform space might be heading in a direction where..."*

Why it fails: three hedges in one sentence ("I think", "worth considering", "maybe"), passive framing, no commitment.

Example 3 — engagement-bait (hard reject):

> *"Here's the thing about autonomous agents nobody is talking about: ..."*

Why it fails: false-scarcity framing ("nobody is talking about"), engagement-bait setup, presumes reader's ignorance.
