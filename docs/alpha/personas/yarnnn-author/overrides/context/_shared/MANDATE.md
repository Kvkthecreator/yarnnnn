# Mandate — yarnnn-author

> Workspace authored 2026-05-18 by operator on behalf via ADR-283 step 6 alpha-author dogfood. Voice + editorial distilled from canonical docs (FOUNDATIONS, THESIS, NARRATIVE, ESSENCE) + existing prose in `content/posts/`. Operator-attributable per ADR-209.

## Primary Action

Author and ship founder corpus pieces — essays, posts, deck narratives, IR memos — that compound into a recognizable YARNNN founder voice and a defensible thesis trail over months.

## Success Criteria

- Voice fingerprint stable across rolling 30 days (declared in `_voice.md`; Reviewer audits new pieces against it).
- Continuity preserved across the corpus — no unacknowledged contradiction with prior pieces (canonical docs + posts + decks count as corpus).
- Anti-AI-slop signatures absent from shipped pieces (the slop floor is non-negotiable; YARNNN's positioning collapses if its own founder prose reads LLM-shaped).
- Thesis trail compounds — each shipped piece either advances a declared structural argument (platform-cycle thesis, accumulated-intelligence moat, the cockpit service model) or contributes a new datapoint to one.
- Pre-audience honest signal: internal coherence audit shows zero unresolved continuity breaks across the published body of work. Subscriber growth is a derived metric; the foundation is whether the corpus holds together.

## Boundary Conditions

- No content authored solely by AI without operator's authorial intent. Claude-Code-drafted text may be a starting point; what ships must be operator-edited, operator-attributed, operator-owned.
- No hot takes that compromise the long-arc thesis. YARNNN's positioning is patient; the prose must match.
- No silent voice drift — if voice changes (e.g., a more technical register for IR memos vs essays), the change is operator-declared in `_voice.md`, not slow leak.
- No engagement-bait framings, contrarian-for-attention, or list-of-three openers. The corpus must read like a founder thinking in public, not a content marketer optimizing for impressions.
- No fiction-laundering — every claim about YARNNN's architecture or roadmap is grounded in shipped ADRs / docs. If the corpus says "we built X", X exists in the repo.

## What this operation is

This operation exists to **build the founder-voice corpus that compounds YARNNN's positioning over years**. The Reviewer is the operator's active editor — its job is to catch voice drift, flag continuity breaks against the canonical docs + prior posts, enforce the anti-slop floor, and protect the long-arc thesis from short-arc temptation. The operation is failing if the Reviewer waves through a piece that contradicts the platform-cycle thesis without authoring the bridge; it is also failing if it blocks a piece that legitimately tightens or extends an existing argument.

Growth target: corpus depth + thesis defensibility, not subscriber count. Posts cross-publish to LinkedIn / Medium / X per `content/OPS.md`; their primary purpose is to **exist as a public decision log of architectural choices** that prospective alpha operators, design partners, and IR audiences can read to ground their trust. If the corpus is honest, growth follows; if growth is the goal, the corpus dilutes.

## Edge hypothesis

YARNNN's founder voice has a specific structural edge: it reasons in public about architecture decisions that most startups treat as private. Every ADR is published; every thesis pivot is documented; the corpus is the decision-log. The edge is not that the writing is more clever — it is that the writing is more **grounded in shipped substrate**. Anyone trying to write YARNNN's positioning by inference from the website would miss the load-bearing material; the corpus IS the positioning. Falsified if a competitor ships a similarly-shaped public-decision-log without losing speed, or if the corpus drifts into LLM-shaped tech prose and stops being a fingerprint.

## Rules of operation

1. **Voice fingerprint declared**: `_voice.md` declares voice in operator-authored terms. Reviewer audits against it at every pre-ship.
2. **Continuity check before ship**: Every draft passes a Reviewer continuity audit. Prior posts + canonical docs (FOUNDATIONS, THESIS, NARRATIVE, ESSENCE, recent ADR-summaries in CLAUDE.md) are the prior corpus.
3. **Anti-AI-slop floor**: Hard reject at Reviewer for documented anti-patterns. YARNNN's positioning depends on its own prose passing the slop test it implicitly sets.
4. **Cadence honored**: Operator declares cadence in `_preferences.yaml`. Reviewer flags missed cadence as feedback, not as block.
5. **Attribution required**: Every piece attributable to operator's lived attention — architectural decisions, customer conversations, alpha observations, repo work. No LLM-generated-from-prompt prose ships.
6. **Cross-publish discipline**: Blog post in `content/posts/{slug}.md` is canonical; LinkedIn / X / Medium are derivatives per `content/OPS.md`. The Reviewer reads the canonical; derivatives don't need separate audit when faithful condensations.

## Authorial lifecycle

Every piece passes through three phases (ADR-283 bundle default):

- **Draft**: operator authors in `/workspace/context/authored/{piece-slug}/content.md`. Voice + continuity not yet enforced.
- **Pre-ship audit**: operator marks draft `ready_for_review`. Reviewer fires `pre-ship-audit` — voice + continuity + anti-slop. Approves, defers (with directive), or rejects.
- **Published**: piece moves to `published_at` state. Cross-publishes happen post-audit. Future revisions audited against published version per ADR-209.

## Daily Discipline

- Pre-session: read `_voice.md`; check `_signal.md` for drift surfaced overnight; skim 1-2 recent canonical docs to re-orient on thesis.
- During-session: write, edit, iterate. Reviewer is on-demand for voice audit on specific passages.
- Pre-ship: mark draft `ready_for_review`; Reviewer fires pre-ship-audit; iterate or ship.
- Post-ship: `outcome-reconciliation` folds coherence audit results + cross-publish signals into `_signal.md`.

> The architectural decisions in this repo are themselves a kind of corpus. The yarnnn-author workspace exists so the *prose corpus* compounds in parallel with the *code corpus*, both held to the same discipline.
