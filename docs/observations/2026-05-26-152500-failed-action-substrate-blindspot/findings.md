# Two structural substrate blindspots — failed-actions silent, exit-prose unrecorded

**Captured**: 2026-05-26T15:25Z. Hat-B observation.

**Shape**: structural finding from operator-directed deepening of the silent-wake population audit. Surfaces two distinct substrate-design blindspots that together explain the operator's "true autonomy not realized" experience — both are structurally invisible to operator surfaces by design (not by accident), and they explain why ~48% persona-frame adherence does not correlate with what the operator can SEE.

**Predecessor chain**:
- `2026-05-25-053951-reviewer-behavior-population-audit/findings.md` (the population audit)
- `2026-05-26-145500-silent-wake-hypothesis-verification/findings.md` (text-only-fallback confirmed at code-log level)

**Why this folder over reopening the predecessor**: this finding identifies TWO structural causes, neither of which the predecessor named. Worth its own load-bearing entry.

---

## Headline

**The operator-facing surfaces have two structural blind spots in the Reviewer's actual cognition.** They are not bugs in instrumentation — they are choices baked into the substrate-surfacing layer:

1. **Failed Reviewer actions are filtered out of narrative substrate at the surface layer.** `services/reviewer_chat_surfacing.py::surface_reviewer_actions` line 408 explicitly skips actions with `success=False`. This means every failed WriteFile, failed ProposeAction, failed SyncPlatformState the Reviewer attempts is invisible to the feed, cockpit, and any operator-facing surface — even though the Reviewer DID try, DID spend tokens, DID encounter a substrate constraint worth knowing about.

2. **The Reviewer's final prose at silent-exit is unrecorded in canonical substrate.** When the model exits via the text-only fallback (the failure mode confirmed in the predecessor), its last prose is captured in memory inside `invoke_reviewer` as `verdict_raw.reasoning`. Downstream, this reasoning lands in `judgment_log.md` (per ADR-289 D4 verdict-of-record substrate) ONLY when the Reviewer also called `ReturnVerdict`. On silent-exit, the dispatcher constructs a synthetic `stand_down` verdict but the rendering path for silent-exit-prose into `judgment_log.md` is not exercised. The prose exists transiently in Render logs (capped retention) and nowhere else.

The two blindspots compound to produce the operator-experience symptom: "I'm not seeing real information and updates on feed, cockpit information that feels like reviewer agent is really working." The Reviewer IS working; the substrate is structurally biased to show only its successes and only its formal verdicts.

---

## Evidence

### Finding 1: Narrative substrate filters failed actions

**Source: `api/services/reviewer_chat_surfacing.py::surface_reviewer_actions` line 408**

```python
for action in folded_actions:
    if not isinstance(action, dict):
        continue
    if not action.get("success", True):
        continue  # ← failed actions never reach narrative
    ...
```

**Source: `_fold_key()` line 307** — same filter applied earlier in the folding pass:

```python
def _fold_key(action: Any) -> Optional[tuple]:
    if not isinstance(action, dict):
        return None
    if not action.get("success", True):
        return None  # ← failed actions never fold (i.e. never narrate)
    ...
```

**Substrate query verification:**

```sql
SELECT role, content, metadata
FROM session_messages
WHERE role IN ('system_agent','reviewer','agent','external','system')
  AND created_at >= '2026-05-22'
  AND (content ILIKE '%WriteFile%' OR metadata::text ILIKE '%WriteFile%')
ORDER BY created_at DESC LIMIT 10;
```

Returns 10 hits, ALL of which read "Wrote to Reviewer substrate on its direction. path=..." with metadata `"tools_used": ["WriteFile"]`. **Zero hits with `success: False` semantics.** Failed attempts at the WriteFile primitive are not narrated anywhere in `session_messages` even though the in-memory `action_record` carries `success=False` and downstream surfacing is the only thing that reads it.

### Finding 2: Silent-exit prose is captured in memory, lost at substrate boundary

**Source: `api/agents/reviewer_agent.py::invoke_reviewer`** — text-only fallback at line ~1482 and budget-exhausted fallback at line ~1640. Both construct:

```python
verdict_raw = {
    "verdict": "stand_down",
    "reasoning": text_fallback[:1000],  # ← model prose preserved in MEMORY
    "confidence": "medium",
}
```

**Downstream**: the dispatcher writes `verdict_raw.reasoning` into `judgment_log.md` per ADR-289 D4 IF the verdict was produced via `ReturnVerdict`. Silent-exit verdicts are synthetic (not `ReturnVerdict`-sourced), and the rendering path treats them as "exit anomaly" — the prose lands nowhere persistent. Render log retention is the only place that prose exists; Render rotates these.

**Implication**: the structural design says "if the Reviewer didn't formally close with ReturnVerdict, its last words aren't substrate-worthy." This was a defensible design choice when silent-exit was assumed rare. The population audit (predecessor finding) showed it's ~41%.

### Finding 3: Failed-WriteFile pattern has a structural root cause

Render Scheduler log scan, 2026-05-22 → 2026-05-26 window, filter `"tool=WriteFile success=False"` returned ~10-12 failed events. **Concentration pattern:**

| persona | user_id | failed WriteFile events | recurrences with failure | success rate elsewhere |
|---|---|---|---|---|
| korea-shorts | ca478643 | many (across outcome-recon + revision-audit cadence) | concentrated 05:01-05:08 UTC + 22:01-22:09 UTC | high success on other writes |
| netflix-author | 23cc7951 | many (same cadence pattern) | same | high success on other writes |
| yarnnn-author | 0b7a852d | 0 | n/a | 100% success |
| alpha-trader | 2be30ac5 | 0 | n/a | 100% success |
| kvk | 2abf3f96 | 0 | n/a | 100% success |
| alpha-trader-2 | 29a74c63 | rare | n/a | usually success |

**Trace pattern (e.g. korea revision-audit 22:04 UTC 2026-05-22):**

```
22:04:05.879  GET _autonomy.yaml          ← Reviewer reads autonomy
22:04:05.881  tool=WriteFile success=False ← attempts to write autonomy.yaml
22:04:08.203  GET _autonomy.yaml          ← reads again (looking for understanding)
22:04:08.204  tool=ReadFile success=True
22:04:18.082  tool=Clarify success=True
22:04:22.486  TELEMETRY judgment/revision-audit success
22:04:22.522  DISPATCH done — actions=20 proposals=0 compose=—
```

**Root cause:** `DEFAULT_REVIEWER_WRITE_LOCKS` in `api/services/workspace_paths.py:198` locks `_autonomy.yaml` (operator-authored substrate). The persona-frame canon (FOUNDATIONS Derived Principle 21 + ADR-295 self-amendment discipline) tells the Reviewer it can meta-aware-edit operator-canon under autonomous mode. The actual lock prevents it. The Reviewer reads the persona-frame guidance, attempts the write, gets refused, has no clean recovery path, falls back to Clarify, eventually exits text-only.

**This is not a code bug — the lock is structurally correct (operator authority over autonomy.yaml is canon).** The bug is a **canon contradiction**: persona-frame says "you can meta-amend operator-canon when accumulated outcome data warrants"; lock-set says "no, autonomy.yaml is operator-only." Both can be true at the same time only if the persona-frame disambiguates *which* operator-canon files are Reviewer-amendable vs. operator-only. Currently it doesn't.

**Concentration on author-class personas (korea, netflix) but not on trader-class (kvk, alpha-trader, alpha-trader-2) or yarnnn-author** is itself a finding. Hypothesis: author bundles have different `_autonomy.yaml` content that encourages the model to attempt amendments more often. Or the personas-frame canon was authored against trader-class assumptions and breaks for author-class. Out of scope for this finding; flagged for posture-taxonomy work.

---

## Why the operator can't see what's happening

The operator's "true autonomy not realized" experience now decomposes into:

1. **What the operator sees on the feed**: only `success=True` Reviewer actions (filtered by `surface_reviewer_actions`). Plus formal `ReturnVerdict` verdicts (which only fire ~52% of judgment-shape wakes). So at most ~52% of Reviewer wakes show ANYTHING on the feed, and within those, only the success-actions surface.

2. **What the operator sees on the cockpit**: per-domain substrate that the Reviewer successfully wrote to (`standing_intent.md`, `judgment_log.md`, decisions.md, etc.). Same ~52% filter applies because writes to those paths only happen when the Reviewer formally completes its cycle.

3. **What the operator sees during the ~48% silent-exit wakes**: nothing. Despite spending $0.20-$0.30 per wake on Sonnet/Haiku, despite running 30-90 seconds of substantive reasoning, despite (in many cases) trying to write substrate and being structurally refused, the operator surface shows nothing.

This is why "the architecture is GREEN" (1984/1985 wake_queue events succeeded — predecessor §A6) AND "the system feels broken" are both correct simultaneously. The plumbing is operational; the operator-facing substrate is design-biased to show ~half of what happens.

---

## What is NOT a finding

- This is NOT a claim that filtering failed actions is the wrong design. It might be correct discipline — failed actions are often noise (model tried a non-existent path, fat-fingered an arg, etc.). The claim is that the discipline applies uniformly and produces a specific operator-experience consequence.
- This is NOT a claim that silent-exit prose MUST land in `judgment_log.md`. The right substrate target is an open question (see Step 2b on the parent session todo).
- This is NOT a claim that the locked-autonomy.yaml design is wrong. The lock is structurally correct. The claim is that the persona-frame canon and the lock-set are contradicting each other in the personas-frame's "meta-amendment under autonomous mode" clause, with no operator-visible signal when the contradiction fires.

---

## Implications for posture-taxonomy work

The forthcoming posture-taxonomy ADR (next step on the parent session todo) must address at minimum:

1. **A "model-tried-was-gated" posture cell** — defined behavior when the Reviewer attempts a substrate write that the lock-set refuses. Should it Clarify? Should it record the attempt + refusal somewhere substrate-visible? Should the persona-frame be sharpened to not suggest writes to locked paths? Likely all three with different cells.

2. **A "model-genuinely-decided-nothing-material" posture cell** — defined behavior when the Reviewer reads, decides correctly that no action is warranted, and exits. Today this exits silently. The question: is silence the right substrate signal, or does the operator deserve a structured "I looked, found nothing material" marker per cycle?

3. **Per-cell substrate-side-effect requirements** — what each posture MUST write to be considered a complete cycle. Today the implicit contract is "standing_intent.md if reactive recurrence" and nothing else. The posture taxonomy needs to articulate per-cell requirements grounded in operator-visibility, not in author convenience.

4. **Failed-action visibility policy** — should the narrative substrate's `success=True` filter be relaxed for specific tool/outcome combinations (e.g., a failed WriteFile to a locked path is operator-relevant; a failed SyncPlatformState because rate-limited is noise)? This is per-cell.

5. **Author-class vs trader-class persona-frame divergence** — the concentration of failed writes on author-class personas suggests the persona-frame may be implicitly trader-class-shaped. Worth examining whether the same persona-frame should apply across both classes or whether bundle-supplied per-program overrides are needed.

---

## Status

**OPEN** — this finding is load-bearing input to the posture-taxonomy ADR (next on parent session todo). Re-runnable: §Finding 3 trace query reproduces any time; §Finding 1 & 2 are code-structural and don't need re-verification unless the code changes.

## Last updated

2026-05-26T15:25Z — initial capture from operator-directed deepening of silent-wake population audit.
