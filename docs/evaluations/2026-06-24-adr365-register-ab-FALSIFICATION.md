# ADR-365 register-follows-consumer — A/B eval: D2/D4 FALSIFIED, D3 retained

**Date**: 2026-06-24
**Verdict**: **FALSIFICATION** of the prose-directive half (D2 frame line + D4 verdict-headline note); **VALIDATION** of the deterministic half (D3 narration strings, retained by construction).
**Probe**: `api/scripts/operator/probe_adr365_register_ab_local.py` (self-contained, no live workspace — isolates the one variable).
**Discourse base**: the 2026-06-24 voice audit that motivated ADR-365 (the screenshot's jargon-heavy `standing_intent` — "recurrences firing on empty substrate," "cadence-drift doesn't apply").

---

## What ADR-365 claimed

The agent wrote operator-facing prose in internal canon vocabulary because nothing told it that vocabulary is insider-only. ADR-365 added:
- **D2** — a persona-frame directive ("Write for the operator, not for yourself") instructing the model to drop internal vocabulary in operator-facing prose.
- **D3** — rewrote the hard-coded feed narration strings to terse plain English (deterministic Python — always plain by construction).
- **D4** — a consumer note on the verdict-headline tool description.

The ADR itself flagged (§5, §6) that D2 "can only guide, not enforce" and that "an eval is owed before claiming D2 worked." This is that eval.

## Method (one variable, isolated)

A/B on the prompt itself — no live workspace, so no DB / scheduler / balance confounds (the harness confounds prior sessions traced every intermittent E2E to):
- **ARM A (treatment)**: the live frame, D2 directive present.
- **ARM B (control)**: the same frame with the D2 block stripped (regex-removed), nothing else changed.
- Same model (Haiku — the recurrence-fire / addressed tier), same realistic **empty-author-workspace** envelope (the screenshot scenario: full framework, zero corpus, a coherence-check recurrence that just fired on nothing).
- Each arm forced to its operator-facing output (write `standing_intent.md` + close with `ReturnVerdict`).
- **4 trials per arm** (single-sample LLM prose is noisy — the first v1 single-draw spuriously flipped). Metric: **length-normalized pure-jargon rate per 1000 chars**, where "pure jargon" = canon-internal plumbing words with no operator-legible meaning (`substrate`, `recurrence`, `cadence-drift`, `no-op`, `_voice.md`…), tracked separately from "mixed" words (`floor`, `aperture`) that are the agent's *legitimate* forward-reasoning vocabulary per ADR-365 §D5.

## Result

| Surface | A (D2 on) | B (D2 off) | Δ |
|---|---|---|---|
| overall pure-jargon rate /k | **2.72** | **2.60** | within noise (+5%) |
| verdict headline rate /k | 0.0 | 0.0 | both already clean |
| standing_intent rate /k | 2.72 | 2.60 | within noise |

Two findings, both visible in the raw prose (captured in the probe output):

1. **D2 does not measurably move the model's free-prose register at Haiku tier.** A vs B differ by ~5% on a 4-trial average — indistinguishable from sampling noise. The directive is a soft prose instruction; the model's pull toward its reasoning vocabulary overrides it.

2. **The verdict headline is already clean in both arms (0.0/k).** It is short and the model naturally writes it plainly. **D4 solved a problem that was not present at this surface.**

3. **The jargon that motivated the ADR lives in `standing_intent` — which is a forward-reasoning surface ADR-365 §D5 deliberately leaves the agent free to reason in canon within.** ARM B's own prose ("low-aperture hold," "nothing to falsify it against") is the agent thinking in its framework, which is *by design* not the operator-facing-only channel D2 targets. A soft directive cannot (and per §D5 should not) suppress it.

## Disposition

- **D2 + D4 REVERTED.** Inert directives are frame bloat under DP22; the eval is the receipt to pull them. (Bonus: the §3.2.1 citation/pedagogy *compressions* made while landing D2 were independently correct — enforcing the partition's "one clause" rule — and were KEPT. With D2/D4 gone they brought the composed system body to **11109 chars, under the 11500 ceiling for the first time** — fixing a debt that was red at HEAD, 12023.)
- **D3 RETAINED.** Deterministic narration strings are plain by construction (`Saved a working note.` can never regress to jargon). This is the proven lever — the operator-facing surface YARNNN actually controls without relying on model compliance.

## The durable lesson

**The operator-legibility lever is the surfaces YARNNN renders deterministically, not the model's free prose.** Where the system emits a fixed string (feed narration, composed summaries), make it plain. Where the model reasons freely (standing_intent, judgment_log), the canon register is partly load-bearing and a soft prose directive neither moves it nor should. If raw `standing_intent` jargon reaching the operator is a real problem, the fix is **a composed plain-English projection the compositor renders FROM standing_intent** (ADR-340 "compose few" — a composition over the substrate), not a frame directive asking the model to self-censor its reasoning. That is a separate, larger ADR — deliberately not attempted here.
