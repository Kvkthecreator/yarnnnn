# Editorial — yarnnn-author ship / hold criteria

> Workspace editorial authored 2026-05-18 by operator on behalf via ADR-283 step 6 dogfood. The Reviewer reads this when deciding ship / defer / reject on pre-ship audits. Operator-attributable per ADR-209.

## Declared editorial principles

1. **Every shipped piece advances or extends a declared thesis I'm willing to defend in 6 months.** No hot takes, no contrarian-for-attention, no engagement-bait framings. The corpus compounds; pieces that don't compound dilute.

2. **Continuity over volume.** If shipping a piece this week means contradicting a piece from last month — or a canonical doc, or a recent ADR — without acknowledgment, hold the piece until the bridge is authored. Silent contradiction is the single biggest threat to the corpus's defensibility.

3. **Architecture-grounded over speculation.** Every claim about YARNNN's capabilities is grounded in shipped ADRs / docs / files in this repo. The corpus is a decision-log; it does not write future-tense as if it were past-tense. If something is on the roadmap, it's named as on-the-roadmap; if it's shipped, the ADR is linked.

4. **Reader respect over reach.** I'd rather lose 5% of subscribers monthly to people I'm not serving than dilute the work for retention. The yarnnn-author corpus is for alpha operators, design partners, IR audiences, and prospective hires — not for SEO-driven growth. If a piece would only land on LinkedIn-influencer audiences, it's the wrong audience.

5. **Cadence is a floor, not a ceiling.** If I have nothing on-thesis to ship in a given week, the slot goes empty or slips. Flattening a piece to fit a cadence slot is worse than skipping. The Reviewer flags missed cadence as feedback, not block — that's the right shape.

6. **Slop floor is non-negotiable.** YARNNN's positioning collapses if its own founder prose reads LLM-shaped. Any draft that ships with anti-patterns from `_voice.md` is a positioning failure, not just a style miss.

7. **Cross-publish discipline.** The blog post in `content/posts/{slug}.md` is canonical. LinkedIn / X / Medium are derivatives per `content/OPS.md`. Derivatives may condense, never extend — every claim in a derivative must be in the canonical. If a derivative wants to make a new claim, it goes back to the canonical first.

## What gets shipped

The Reviewer reads these literally at pre-ship audit. A piece **ships** when all of these hold:

- Advances a declared thesis (platform-cycle thesis, accumulated-intelligence moat, the cockpit service model, Authored Substrate, anti-vibes alpha discipline) **OR** contributes a new datapoint to one (alpha observation, ADR ratification narrative, design-partner conversation distilled).
- Voice fingerprint matches `_voice.md` (Reviewer auto-checks).
- No unacknowledged contradiction with prior corpus (Reviewer continuity audit against `content/posts/` + canonical docs + recent ADR-summaries in CLAUDE.md).
- No anti-slop signature present (`_voice.md` anti-pattern hard-reject list).
- Architecture claims are repo-grounded — every named capability is either shipped (ADR Implemented) or named as roadmap.
- Operator's self-audit complete: the piece reads aloud cleanly; no paragraph the operator would skip if reading someone else's prose.

## What gets held / deferred

The Reviewer **defers with directive** (not hard reject) when:

- Voice is mostly right but has 1-2 anti-pattern leaks the operator can fix in a pass (e.g., one "incredibly" intensifier, one list-of-three opener).
- A continuity break is detected but acknowledgment paragraph is missing — Reviewer directives the operator to add the bridge paragraph and re-submit.
- The piece is on-thesis but reads thin — Reviewer flags "this needs a specific datapoint / proper noun / ADR reference to land" and defers.
- Cadence is missed (piece is going out late) but the piece itself ships — Reviewer notes the cadence slip in `_signal.md` for next-cycle awareness, doesn't block ship.

## What gets rejected

The Reviewer **hard rejects** when:

- Anti-slop signature present and operator hasn't authored explicit exception in `profile.md`.
- Continuity contradiction with prior corpus AND no acknowledgment paragraph.
- Architectural claim that's neither shipped (ADR-Implemented) nor named as roadmap — fiction-laundering.
- Engagement-bait framing as opener ("Here's what nobody is talking about", "You won't believe...").
- Marketing-speak intensifiers ("industry-leading", "game-changing", "next-generation").
- Voice has drifted enough that the piece reads as a different author's prose — hard reset.

## Cross-publish-specific criteria

LinkedIn condensation (200-400 words):
- Must condense a single canonical claim, not blend multiple.
- No new claims; every sentence traceable to canonical post.
- Hook is operator-voiced, not LinkedIn-shaped (no "Here's a story", no "I learned X yesterday").
- Closing CTA is the blog URL, never inline-newsletter-signup-bait.

X thesis post (<280 chars):
- Single declarative thesis sentence + blog URL.
- No thread unless the canonical specifically benefits from progressive disclosure.
- Em-dash discipline maintained even in shortform.

X Article cross-post (3-7 days after blog):
- Full cross-post of canonical, with native title.
- No new prose; no engagement-tuning edits.

Medium import (auto canonical):
- Import via blog URL; set canonical to blog URL.
- No platform-specific edits.

Reddit (Kevin posts manually):
- Claude drafts based on canonical + subreddit norms.
- Operator (KVK) does final read + posts personally.

## Signal feedback

After each shipped piece, `outcome-reconciliation` recurrence folds into `_signal.md`:

- Voice audit findings (Reviewer assessment of what voice patterns held / drifted).
- Continuity audit findings (which prior corpus pieces / canonical docs the piece composed with cleanly vs needed bridges).
- Cross-publish signal slices (engagement on canonical post, LinkedIn condensation pickup, any direct outbound from the piece — alpha operator inquiry, design partner conversation, IR follow-up).

The operator reads `_signal.md` at the start of each authoring session to re-orient on drift surfaces.

## Override surface

Per-piece editorial exceptions live in the piece's `profile.md` (`editorial_exceptions: [...]` frontmatter). The Reviewer respects exceptions when present and operator-attributed. Don't author exceptions casually — they accumulate, and after 5+ exceptions the editorial discipline starts looking ad-hoc. If a pattern keeps surfacing as an exception, promote it to the `_editorial.md` or `_voice.md` declaration.
