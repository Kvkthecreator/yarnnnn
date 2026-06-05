# Voice Audit Spec

Spec for the Reviewer's voice-fingerprint check. Used at every `pre-ship-audit` recurrence fire and as a sub-check inside `corpus-coherence-check`.

## Purpose

Detect drift between the operator's declared voice fingerprint (`_voice.md`) and the draft under audit. Specifically catches:
1. AI-shaped prose signatures (the anti-patterns enumerated in `_voice.md` plus a baseline anti-slop list applied universally).
2. Departure from declared positive pattern markers (e.g., "leads with claim, backs into evidence" — flag if draft buries the lede).
3. Hedge stacking and adverb intensifier accumulation that flattens specific voice.

## Inputs

- `/workspace/operation/authored/_voice.md` — operator's declared voice (positive markers + anti-patterns).
- The draft content at `/workspace/operation/authored/{piece-slug}/content.md`.
- Optional: the most recent 5 published pieces from `/workspace/operation/authored/` for comparison-against-corpus context.

## Output structure

The Reviewer writes audit results to `/workspace/persona/judgment_log.md` per ADR-281, plus structured findings to `/workspace/operation/authored/_signal.md` per ADR-282/283 instance.

Each audit result includes:

```yaml
piece_slug: <slug>
audit_timestamp: 2026-05-15T14:32:00Z
voice_match: pass | fail | mixed
positive_marker_hits: [<marker-name>, ...]
anti_pattern_hits:
  - location: "para 3, sentence 2"
    pattern: "hedge stack"
    excerpt: "I think it's worth considering that maybe..."
  - location: "headline"
    pattern: "list-of-three opener"
    excerpt: "It's fast, it's reliable, and it's affordable."
overall_verdict: approve | defer | reject
defer_directive: <if defer> specific operator-actionable defect description
```

## Anti-pattern baseline (universal — applied regardless of `_voice.md` declarations)

These anti-patterns are applied to every audit; operators can override per-piece by declaring `voice_override: true` in piece profile.md:

1. List-of-three openers ("It's fast, it's reliable, and it's affordable")
2. "It's worth noting" / "It's important to note" hedge constructions
3. "In conclusion" / "To summarize" / "Let's dive in" / "Let's explore" framing markers
4. Adverb intensifiers without content ("fascinating", "incredibly", "absolutely", "truly")
5. Hedge stacks (≥2 hedge words in one sentence: "I think it's worth considering that maybe")
6. "As we know" / "As you can see" assumed-context constructions
7. "This is fascinating" / "This is interesting" reaction-summary openings to paragraphs

## Operator-declared anti-patterns

In addition to the baseline, the Reviewer applies anti-patterns the operator declared in `_voice.md` "Anti-patterns (negative)" section. Each declared anti-pattern is treated as hard-reject unless operator override declared per-piece.

## Quality criteria

- Every flagged anti-pattern includes the specific location (paragraph, sentence) and the exact excerpt.
- Reviewer does NOT rewrite the offending passage — only locates and names the defect. The operator authors the fix.
- Audit-EV reasoning per `principles.md` weights live `_signal.md` calibration data against the audit verdict (if rolling-30-day false-positive rate for a specific anti-pattern is high, that anti-pattern's enforcement weakens slightly).
