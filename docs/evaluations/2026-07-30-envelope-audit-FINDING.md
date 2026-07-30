# Envelope audit 2026-07-30 — the cut has held; the missing piece was the ratchet

**Status**: CLOSED — receipted negative on further cuts; ratchet landed
**Hat**: B (this document); the ratchet test is the one Hat-A artifact (test-only, no shipped behavior change)
**Method**: per-part offline render on live substrate (3 workspaces × 3 trigger shapes), classified against the ADR-306 verdict set (KEEP-THIN / MOVE-PRINCIPLES / MOVE-SUBSTRATE / DELETE-REDUNDANT / DELETE-CODE-ENFORCED)
**Prior receipts consumed**: 2026-06-24 envelope-collapse probe · 2026-06-30 concentrated-envelope PASS · 2026-06-30 perception-completeness · 2026-07-02 rung1/rung2/rung3-armB-v2 · ADR-306/323/360/383/390/397/403

## 1. The question, corrected

The audit brief framed the wake envelope as "unmeasured, no gate anywhere" against a
gated 10,015-char system prompt. Half of that is stale: **ADR-403 (2026-07-02) already
collapsed the envelope** to the thin CC-shape — cached governance prefix + volatile
suffix + bare ask — with rung-level behavioral receipts (6/6 close parity on the weak
model; the ADR-390 attribution catch surviving WITHOUT the fact sections). The half
that is TRUE: **no size assertion held any of it.** The only envelope test assertion
touching size was a field count (`len(_UNIVERSAL_ENVELOPE_DECLS) == 9`,
`test_adr284_standing_intent_substrate.py:122`). An ungated cut regrows — ADR-323
exists because ADR-306's cut left an ungated 11K `cockpit_awareness` bolt-on that no
ceiling saw.

## 2. Measurement (2026-07-30, read-only offline render, live DB)

Probe: scratchpad `measure_envelope.py` — loads `load_freddie_governance_envelope`
for real users, renders `_governance_prefix` / `_volatile_suffix` / `_ask_for_trigger`
/ `_build_user_message_content` per trigger shape. No LLM, no writes.

### Totals (chars; ~4 chars/token)

| workspace | shape | governance (cached) | volatile | ask | total |
|---|---|---|---|---|---|
| kvk-live (2abf3f96) | addressed | 11,168 | 8,343 | 91 | **19,511** |
| kvk-live | reactive-recurrence | 11,168 | 8,644 | 392 | **19,812** |
| kvk-live | reactive-proposal | 11,168 | 8,617 | 358 | **19,785** |
| funded-author (0b7a852d) | all 3 | 7,715 | 739–1,040 | 91–392 | **8,454–8,755** |
| bare (00ab9036) | all 3 | 7,715 | 739–1,040 | 91–392 | **8,454–8,755** |

System prompt: **10,015 chars** on the same render — matches the gated figure exactly.
Envelope load: 2.4–5.1s (`load_ms`), all `asyncio.gather`ed reads.

### Where the bytes are

- **kvk-live governance 11,168** = substrate content, verbatim: principles.md 3,964 +
  mandate 2,592 + budget_yaml 1,379 + identity 1,010 + precedent 998 + occupant 896 +
  headers. Zero coaching.
- **kvk-live volatile 8.3–8.6K** = standing_intent 2,462 (agent-authored) +
  attribution_fact 1,644 + snapshot 1,689 + commons leads 1,191 (kernel prose) +
  principal_commons_fact 761 + peripheral 229 + clock 156 + ask.
- **Bare-steward 8.5K totals** = the ADR-414 B2 kernel steward constants riding in
  place of absent files (identity 1,010 + mandate 2,592 + principles 3,964 = 7,566,
  cached) + ~900 of volatile scaffold. The two non-operator workspaces rendered
  byte-identical scaffolds — the base case is uniform.

### Kernel-authored prose, isolated (empty-context render)

| kernel prose surface | chars | condition |
|---|---|---|
| governance scaffold (headers + empty-fallbacks) | 191 | every wake |
| volatile scaffold, addressed | 124 | every addressed wake |
| volatile scaffold, reactive-recurrence (incl. one-WriteFile rule) | 343 | recurrence wakes |
| volatile scaffold, reactive-proposal (incl. verdict-early rule) | 339 | proposal wakes |
| commons-fact leads + section header | 1,191 | only when facts non-empty |
| steward constants (loader-side) | 7,566 | bare workspaces only, cached |

Total uncached kernel prose per wake: **≤ ~1.5K chars**. The envelope's growth axis is
operator/agent substrate, which is the *point* of the design (ADR-276: full governance
at every wake), not dilution.

## 3. Classification — every current part site, ADR-306 verdict set

Governance prefix (11 sites — IDENTITY, principles, PRECEDENT, MANDATE, AUTONOMY,
_budget, _expected_output, _preferences, OCCUPANT, _operator_profile, _risk):
**KEEP-THIN**, all. Verbatim substrate under one-line headers; the June-24 probe
measured this block as ~16K of the 17.8K-token Arm-B envelope and ruled it "legitimate
governance — the CLAUDE.md-analogue"; caching (not stripping) is the ratified cost
lever, and the block carries `cache_control`.

Volatile suffix (13 sites):

| site | verdict | note |
|---|---|---|
| operating_context_block (clock) | KEEP-THIN | ADR-301; 156 chars |
| wake-context lines (source/path/revision_id) | KEEP-THIN | receipts, not prose |
| standing_intent + real-path header | KEEP-THIN | ADR-284 + ADR-414 §9a; agent-authored content — WATCH, not gate (2,462 on kvk-live; growth is the agent's own hygiene loop) |
| substrate snapshot (heads + pending proposals) | KEEP-THIN | the gitStatus analogue |
| 3 commons-fact leads (1,191) | KEEP-THIN, **flagged** | see §4 |
| reflection_gap_fact | KEEP-THIN | program-gated (ADR-390 D3), empty-graceful |
| specs_inventory | KEEP-THIN | program-gated, empty-graceful |
| program-declared keys (generic block) | KEEP-THIN | bundle ABI is the program's prerogative (ADR-281 D2) |
| ask: recurrence branch + one-WriteFile rule | KEEP-THIN | interface constraint, not coaching (ADR-403) |
| ask: proposal branch + verdict-early rule | KEEP-THIN | same |
| ask: addressed branch + locator line | KEEP-THIN | ADR-398 D2 |

Loader-side: steward-constant substitution (ADR-414 B2) — **KEEP-THIN**; it is the
highest-leverage kernel prose in the system (reaches every bare workspace at the next
wake) and is now under its own ceiling.

**No DELETE or MOVE verdicts.** Everything that earned one was already executed:
`_TRIGGER_FRAMING` (rung 1), the wake liturgy (rung 2 / ADR-397), the fat partition +
arm toggle + workspace_state injection (ADR-403), the six operation-machinery facts
demoted behind `program_active` (ADR-390), the empty-state scaffolding headers
(ADR-390 D3). The regrowth check over the 7 envelope-touching commits since 07-02
(ADR-407/414/424/463 lanes) found relocation and substitution, no new prose sections.

## 4. The one flagged candidate — NOT proposed, operator's call

The three commons-fact leads (1,191 chars, uncached, fire on active workspaces) are
the single largest kernel-prose block left in the envelope. Two facts point opposite
ways:

- ADR-403's own Evidence: the bare-steward attribution catch **survived without the
  fact sections** — the steward found the mis-attribution by reading revisions itself.
- ADR-403's same-day correction retained them deliberately: they carry the ratified
  ADR-364/389/390 arcs with standing gates, and deleting their loaders "exceeded the
  measured evidence."

**RESOLVED same day (operator authorized the probe): the cut is REFUTED — the
leads stay.** Probe: `api/scripts/operator/probe_commons_leads_removal_local.py`
(wraps the standing bare-steward instrument; strips the lead paragraphs in-process
via a `_volatile_suffix` wrapper — production code untouched; header + fact bodies
retained; strip byte-receipted from the fired wake's own render: 2 leads rendered
and removed, 813 chars, `full 3,791 → stripped 2,978`).

Live wake receipts (bare-kernel `4c106786`, seeded per the standing instrument —
unplaced dump + AI-voiced file stamped `operator`):
- execution_event `619b5d2d-6286-48f3-9dd3-1888b3675a22` — success, 6 rounds,
  2,372 out-tokens, $0.2086, slug `bare-steward-sweep-1785414665`.
- Intake-placement: CLEAN — read the dump, derived it into
  `operation/decisions/q3-pricing-change.md` with a `derived_from` citation,
  cross-referenced the sibling decision (3 `freddie:`-authored revisions).
- **Attribution catch: MISSED.** The steward READ the mis-attributed file
  (action 3, `ReadFile operation/memory/competitor-scan.md`) and closed with
  "no attribution anomalies" — a false negative on the seeded violation. The
  attribution-fact DATA was in the envelope; only the lead pedagogy was absent.
- Contrast: the 2026-06-30 concentrated-envelope run — same workspace, same
  seed, leads present — caught it on wake 1 (verbatim in that finding).

Read: the lead prose is load-bearing for the voice-vs-stamp catch, N=1 against
N=1 on the same rig. This narrows ADR-403's Arm-B note ("the catch survived
without the fact sections") — that wake's discovery ran without competing
intake-placement work; under a real mixed situation the coaching is what turns
the fact data into the catch. The three-halves heuristic passed on the strength
of the placement half — the heuristic cannot see a missed catch, which is why
the human read is authoritative (this is the second time the heuristic's PASS
needed overriding detail; see the 06-30 three-halves false-positive note).

Removal-over-addition cuts both ways: the discipline demands the probe before
the cut, and this probe defended the prose. The ratchet ceiling (≤1,600) now
guards a block with a live justification receipt. Machine capture:
`2026-07-30-envelope-audit-leads-removal-capture.json` (this directory). Rig
restored: seeds + derived residue deleted (the `q3-pricing.md` cross-reference
edit remains as benign wake-authored content).

## 5. What landed (the ratchet)

`api/test_envelope_scaffold_ratchet.py` — 4 tests, offline, no DB:

1. governance scaffold ≤ 400 (baseline 191)
2. volatile scaffold ≤ 700 per trigger shape, enumerated per shape — not a counting
   gate (baselines 124 / 343 / 339)
3. commons leads ≤ 1,600 (baseline 1,191) + the empty-graceful invariant (no facts →
   no section header — the measured Arm-B bare shape stays reachable)
4. steward constants ≤ 9,000 (baseline 7,566)

Raising any ceiling requires the ADR-306/DP22 evidence bar: a repeated observed
failure, named in the raising commit. Operator/agent-authored substrate is
deliberately ungated — gating it would gate the workspace's own content.

Falsifiability receipt (run 2026-07-30, in-process monkeypatch of each prose
source past its ceiling): gov-breach caught · vol-breach caught · leads-breach
caught · empty-graceful-breach caught · constants-breach caught — 5/5. A gate
that has never been red is an unrun gate; this one has been red on every
dimension it defends.

## 6. Housekeeping surfaced

- `api/scripts/operator/probe_envelope_collapse_local.py` — **DELETED same day**
  (operator authorized). It was doubly stale against main: `Recurrence(mode=...)`
  (field deleted, ADR-393) and the `YARNNN_ENVELOPE_ARM` toggle (deleted, ADR-403 —
  both arms rendered byte-identical, so its A/B delta was structurally zero), plus
  the known `action["path"]` instrumentation bug. Its Phase-1 measurement job is
  superseded by the per-part probe pattern here; its Phase-2 live-fire job by the
  standing bare-steward instrument.
- `docs/architecture/reviewer-occupant.md` §symbols may still carry pre-rename
  vocabulary in places (the contract doc's ADR-414 banner is current; CLAUDE.md's
  rows were fixed in 58dbb3e).

## Reproduce

```
# per-part measurement (read-only)
python3 <scratchpad>/measure_envelope.py "label=<user_uuid>" ...
# ratchet
cd api && python3 -m pytest test_envelope_scaffold_ratchet.py -q
```
