# Freddie Envelope Refactor — Posture-First, Model-Agnostic

**Date**: 2026-07-02
**Hat**: A (plan for system changes; validation sub-turns are Hat-B)
**Status**: Plan — rungs execute sequentially, each its own commit(s) to main, each gated + probed before the next opens.
**Operator directive**: the model-tier evaluation is the LAST rung, deliberately — the fundamental behavior and posture must hold strong despite lower model quality (the Claude Code property). Model optionality (swap models like Claude Code's model selection; eventually non-Anthropic occupants) is a design constraint on every rung: nothing may deepen model coupling.

---

## 0. The diagnosis this plan answers (2026-07-02 session)

Operator experience: Freddie is wordy, tool-inefficient, low quality vs Claude Code. Cross-checked against `docs/analysis/src_claudeCC` (Claude Code source snapshot) + the live code. Four findings:

1. **Model tier**: `addressed` (operator chat) + recurrence fires run Haiku 4.5; only proposal wakes get Sonnet 4.6 — and those get 3 rounds (`freddie_agent.py:1384,1478`). The comparison baseline (Claude Code) runs a frontier model.
2. **Eager envelope vs lazy retrieval**: every wake pre-loads ~23 sections (~16k cached governance block); Claude Code pre-loads a compact prompt + operator canon and pulls the rest on demand. ADR-390's removal pass proved the failure mode is DILUTION (4 addition-wakes failed, 1 removal passed).
3. **Trigger-framing scar tissue + kernel/program violation**: `_TRIGGER_FRAMING["addressed"]` (`freddie_agent.py:508-572`) hardcodes alpha-trader nouns (`_money_truth`, `signal_files`, `_risk`, "ProposeAction with sizing math", mirror-wait choreography) in the KERNEL frame — an ADR-222 violation and the capital-judgment residue ADR-383 flagged; the re-carve landed in `_compute_minimal_frame` but NOT in `_TRIGGER_FRAMING`. Verified: the same content already lives in the trader bundle's `persona/principles.md` (decision tree, standing-intent/mirror choreography, writable-path test) — the kernel block is pure duplication.
4. **Ceremony tax on chat**: the full wake liturgy (ReturnVerdict + standing_intent + judgment_log + forward-reasoning + citation discipline) applies uniformly to a chat turn.

Findings 2–4 are structural; the prescriptive prose is downstream of them (weak model + tight rounds + eager context → failures → prompt patches → dilution → more failures). Fix structure first (rungs 1–3), evaluate model last (rung 4).

**Governing discipline (proven, [[feedback_envelope_removal_over_addition]]):** every rung 1–3 is net-NEGATIVE prompt tokens. If a rung wants to add prose, that is a design smell — fold or remove instead.

**Model-agnostic validation rule:** every rung is validated on the CURRENT models (Haiku for addressed). If posture holds on the weak model, it holds anywhere. Never "fix" a rung by assuming a stronger model — that is rung 4's question.

---

## Rung 0 — Baseline capture (Hat-B, no code)

Before any edit, capture the comparison baseline:

- Run `api/scripts/operator/probe_freddie_bare_steward.py` (bare-steward wake) — save transcript.
- Scripted addressed-turn set on the kvkthecreator test account (5–8 turns: "what's in my workspace", a placement request, a connector question, an ambiguous ask) — save transcripts.
- Record per turn: input tokens, output tokens, rounds used, tools called (count + which), close rate (ReturnVerdict reached), output length, and a qualitative wordiness note.
- Store under `docs/evaluations/2026-07-XX-freddie-envelope-baseline/` per Hat-B discipline.

Every subsequent rung re-runs this exact set and diffs. Success metrics per rung: output length ↓, rounds-to-close ≤ baseline, close rate = 100%, reactive gates green, no new confabulation.

---

## Rung 1 — `_TRIGGER_FRAMING` re-carve (ADR-383's named downstream work; pure removal)

**Authority**: ADR-383 already ratified this ("the persona-frame re-carve — its OWN commit + CHANGELOG + coherence test + Hat-B eval"). No new ADR needed; this completes it.

**Changes** (`api/agents/freddie_agent.py`):

- **`addressed` block → steward-first, program-neutral, ~⅓ size.** Keep only: (a) the operator delegated — act, then report; (b) governing substrate is pre-loaded above — do not re-read it; ReadFile only for files not shown; (c) the default is action — pick the most disciplined action *your principles.md declares* and execute it; enumerating options is deferral (ADR-352 pointer stays — it is runtime contract); (d) close with ReturnVerdict, reasoning in first person. DELETE: every program noun (`_money_truth`, `signal_files`, `_risk`, sizing math, ProposeAction menu item), the mirror-wait choreography, the "you OWN your workspace like an engineer owns a repo" attestation paragraph (already in trader principles.md §freshness), the stand-down-is-last-option litany (principles.md content per §3.2.1 partition — the trader bundle already carries the decision tree).
- **`reactive` block → compressed.** Keep: proposal → ReturnVerdict EARLY with approve|reject|defer (runtime interface under round budget); recurrence → the recurrence prompt is the instruction, read cited substrate, act. Compress the audit-write choreography to two sentences (one WriteFile for the long document, one ReturnVerdict headline — that is a genuine interface constraint, keep it terse). DELETE the "Common shapes for recurrence fires" menu (duplicates the recurrence prompts themselves — the recurrence prompt IS the operator's instruction; a kernel menu of shapes is dilution).
- **Partition check** (agent-composition.md §3.2.1): after the edit, confirm no rule-of-judgment content remains in kernel strings; confirm the trader + author bundles' principles.md carry what was removed (verified for trader 2026-07-02; verify author bundle in-session).

**Gates**:
- New `api/test_adr383_trigger_framing_recarved.py`: CI ratchet asserting no program nouns (`_money_truth`, `signal_evaluation`, `signal_files`, `_risk`, `sizing`, ticker/trade vocabulary) in `_TRIGGER_FRAMING` or `_compute_minimal_frame` output (pattern: the ADR-379 no-host-leak gate).
- Existing frame gates green: `test_adr323_frame_collapse_finished.py`, `test_adr314_substrate_conditional_posture.py`, `test_adr302_phase1_section_registry.py`, `test_adr301_reviewer_pulse_envelope.py`.
- `api/prompts/CHANGELOG.md` entry (Prompt Change Protocol).

**Hat-B validation**: re-run Rung-0 set. Expected: shorter outputs on addressed turns, no trading vocabulary in bare-steward narration, close rate unchanged.

**Commit**: `refactor(ADR-383): re-carve _TRIGGER_FRAMING — steward-first, program-neutral kernel framing` → push main → Render deploys API + Scheduler (both import freddie_agent; no env changes).

---

## Rung 2 — Right-size the ceremony by trigger shape

**Decision shape** (needs a small doc-first ADR in the same session as the code, or the ADR commit immediately preceding):

- **Option (a) — RECOMMENDED FIRST**: keep ReturnVerdict as the uniform close across all triggers (preserves ADR-360's honest-terminal, ADR-291 telemetry, one contract across rungs per ADR-381), but strip the addressed-turn liturgy: the standing_intent guidance, judgment_log conventions, reflection-write prompt, and wake-is-a-situation forward-reasoning paragraph become REACTIVE-scoped (moved from the cached frame into the `reactive` trigger framing — trigger framing is already per-trigger, the frame stays cached/static per ADR-302 D6).
- **Option (b) — only if (a) doesn't move the needle**: change the addressed close contract itself (prose-close, verdict synthesized by the runtime). Higher blast radius: touches `routes/feed.py` stream handling, `write_freddie_message(verdict=...)`, the failed-close accounting. Do not start here.

**Changes** (option a): `_compute_minimal_frame` loses the "Close every cycle with a verdict" + standing_intent/reflection paragraph (~15 lines) → folded (compressed) into `_TRIGGER_FRAMING["reactive"]`. The addressed block keeps one line: "Close with ReturnVerdict; reasoning = what you did, first person." Net prompt tokens: negative (the frame is cached, but addressed turns stop carrying reactive liturgy).

**Gates**: frame gates + a new assertion in the rung-1 test file (addressed framing contains no standing_intent/judgment_log/reflection references; reactive does). CHANGELOG entry.

**Hat-B**: Rung-0 set again. Expected: addressed turns stop volunteering standing-intent updates and forward-planning narration on simple asks.

**Commit(s)**: `docs(ADR-NNN): addressed-turn ceremony right-sizing` + `refactor(ADR-NNN): scope the wake liturgy to reactive triggers`.

---

## Rung 3 — Lazy-envelope experiment (probe-gated; ratify only on measurement)

**Build on the existing Arm-B scaffolding** (`YARNNN_ENVELOPE_ARM`, freddie_agent.py:1440-1454). Add **Arm C — compact index**:

- Envelope = MANDATE + principles.md + AUTONOMY (these three are the governing floor, always eager) + a compact workspace map (file tree + recent-revisions summary — the gitStatus analogue the envelope-collapse probe already sketched) + the ask. Everything else (domain substrate, inventory, the four synthesized facts) becomes ReadFile-on-demand.
- The four facts (`_reflection_gap_fact`, `_attribution_fact`, `_principal_commons_fact`, `_peripheral_field_fact`) each earn their place back ONLY with evidence: fold each into the compact map as one line, or drop to on-demand.
- Env-gated (`YARNNN_ENVELOPE_ARM=C`), zero production impact until measured.

**Measurement** (Hat-B, on Haiku deliberately — the model-agnostic test): Rung-0 set + 3 reactive recurrence fires under Arm C vs production arm. Compare: input tokens (expect large ↓), rounds used (expect ↑ — reads move into the loop), close rate, quality, cost per wake (input savings vs extra rounds), retrieval accuracy (does Haiku ReadFile the right things?).

**Decision rule**: if Haiku retrieval is unreliable, do NOT force it — record the result as rung-4 input ("lazy envelope requires model tier X") and keep the eager-23-section envelope as the weak-model configuration. If it holds, ratify with a new ADR (envelope-as-index) and make Arm C the production path. Either outcome is a win: it converts the eager-vs-lazy question from philosophy into a measured model-capability threshold.

---

## Rung 4 — Model routing as data + the tier evaluation (LAST, per operator directive)

**Part A — model-selection-as-data (code, small):**
- Replace the hardcoded `_SONNET`/`_HAIKU` constants + `use_sonnet` branch (freddie_agent.py:76-78, 1384-1386, 1478) with a routing table: `{trigger_shape: {model, max_rounds}}` for shapes `addressed | proposal | recurrence`, defined in one place (e.g. `api/services/model_routing.py`), env-overridable per deployment, operator-facing later (a governance dial candidate — but NOT in this rung; keep it kernel config first).
- `FREDDIE_MODEL_IDENTITY` / the occupant attribution string derives from the table (ADR-315 occupant naming preserved — occupant identity already encodes model).
- **Provider-optionality constraint** (the operator's horizon: Gemini/GPT occupants): the seam already exists — the occupant contract (`api/agents/occupant_contract.py`, ADR-315 ABI). Rung 4 does NOT build a provider abstraction; it enforces the boundary: model ids live only in the routing table; Anthropic client usage stays inside the occupant module; nothing outside `freddie_agent.py` may branch on model. A future non-Anthropic occupant implements the same `invoke_freddie` contract.
- Pricing note: model choice changes cost-per-invocation (ADR-396 meters LLM judgment invocations); the routing table change is where tier economics get decided — surface the cost delta to the operator when the experiment reports.

**Part B — the tier experiment (Hat-B):**
- Same envelope + frame (posture already hardened by rungs 1–3), run the Rung-0 addressed set on Sonnet (and optionally a frontier model) vs the Haiku baseline. Also re-test the routing inversion hypothesis: proposal verdicts (structured, discrete) on Haiku vs Sonnet.
- Decide production routing from evidence; record in the routing table + an ADR (model routing + the economics).
- Expected insight: rungs 1–3 shrink the tier gap; whatever gap remains is the honest price signal for the routing decision.

---

## Cross-cutting execution rules

- **Sequential rungs, gated**: a rung's commit does not open until the prior rung's Hat-B validation is captured (transcripts in `docs/evaluations/`). No parallel rung work.
- **Every prompt-string change** → `api/prompts/CHANGELOG.md` entry (Prompt Change Protocol).
- **Every commit to main**: run the new + sibling test gates locally first (`test_adr383_trigger_framing_recarved.py`, `test_adr323_*`, `test_adr314_*`, `test_adr302_*`, `test_adr301_*`); push deploys API + Scheduler (both import the agent; no env-var changes except the existing `YARNNN_ENVELOPE_ARM` probe gate).
- **Rollback**: each rung is one revertable commit; probe arms are env-gated (flip the env, no revert needed).
- **Net-token ratchet**: rungs 1–3 must each reduce total prompt tokens on the addressed path. The rung-1 CI test can assert a character-count ceiling on `_TRIGGER_FRAMING` to prevent re-bloat (the anti-scar-tissue ratchet).
- **Bundle check**: before removing any kernel guidance, verify both bundles' `persona/principles.md` carry the operation-specific version (trader verified 2026-07-02; author to verify in Rung 1).

## Why this ordering serves the model-optionality goal

Claude Code's portability across model tiers comes from exactly the three properties rungs 1–3 install: a terse, universal frame (no domain residue), context earned by relevance (not eager dumps), and ceremony proportional to the act. A frame with trading choreography baked in is un-swappable — a different model (or provider) amplifies the incoherence differently. Harden the posture first and the model becomes a routing-table entry; evaluate tiers last and the result measures the MODEL, not the prompt's scar tissue.
