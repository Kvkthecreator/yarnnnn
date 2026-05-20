# alpha-trader-2 e2e persona flip — Fix 1B execution

**Hat**: External Developer of the System (Hat B observation; live workspace state changes captured here).
**Time captured**: 2026-05-20T10:50Z.
**Author**: Claude (Opus 4.7).
**Reference**: companion to [pre-e2e-readiness-audit-adr296-v2/findings.md](../2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2/findings.md) §4 Fix 1B; operator-confirmed direction 2026-05-20T10:50Z.

---

## What this captures

Per the pre-e2e readiness audit, alpha-trader-2 (`user_id=29a74c63...`) is the operator's chosen e2e validation persona for the ADR-296 v2 wake-architecture demonstration (replacing kvk for the e2e itself; kvk gets a separate hygiene cleanup pass). Three state changes landed in this observation window to make alpha-trader-2 e2e-ready:

1. **MANDATE.md heading normalized** from `# Mandate — alpha-trader-2 (Stat-Arb Pairs)` to `# Mandate — alpha-trader` so `parse_active_program_slug()` resolves to the correct bundle slug. The Phase B parallel-loop test (2026-04-28) authored the heading with the persona slug instead of the program slug, which broke `bundle_update_available()` detection — `_load_manifest("alpha-trader-2")` raised `Bundle reference-workspace not found` because no such bundle exists. The persona's stat-arb identity is preserved in body sections + an explicit comment marker. Attribution: `system:substrate-update`.

2. **Bundle re-fork against post-Checkpoint-2 bundle (v2026-05-20.1)** invoked via the same `apply_substrate_update(scope='bundle', source='harness')` path as kvk + yarnnn-author. Outcome:
   - `_hooks.yaml` created (1336 bytes, `hooks: []` per alpha-trader bundle spec)
   - `_recurrences.yaml` config-conflict auto-resolved — operator's prior content backed up at `_shared/conflict-backups/2026-05-20T10-50-11Z/_recurrences.yaml`
   - tasks index dropped `trade-proposal` row; 8 recurrences remain matching the bundle exactly (mirror-signal-state, outcome-reconciliation, signal-evaluation, track-account, track-orders, track-positions, track-regime, track-universe)
   - MANDATE.md frontmatter advanced: `none → 2026-05-20.1`
   - 24 operator-authored prose files (IDENTITY, BRAND, principles, _voice, _operator_profile, _risk, etc.) preserved untouched per ADR-292 v3 D9 taxonomy

3. **Autonomy flipped from `bounded` to `autonomous`** in `/workspace/context/_shared/_autonomy.yaml`. Prior state was a 2026-05-20 Test C marker `delegation: bounded` for ADR-293 substrate-write-gate validation; now reads `delegation: autonomous` with `ceiling_cents: 5000000` ($50k) + `never_auto: [close_position_market, cancel_other_orders]` preserved. Attribution: `operator` (this is operator intent, executed by the developer harness on the operator's behalf per ADR-294 D2 caller-identity convention).

---

## Post-state verification

| Property | Value | Bundle expectation match? |
|---|---|---|
| `_hooks.yaml` exists | yes, `hooks: []` | ✓ |
| `_recurrences.yaml` matches bundle (no trade-proposal slug) | yes | ✓ |
| tasks index recurrence set | mirror-signal-state, outcome-reconciliation, signal-evaluation, track-account, track-orders, track-positions, track-regime, track-universe (8) | ✓ (matches ADR-296 v2 D2 + ALPHA-1-PLAYBOOK §3A.5 inventory) |
| MANDATE.md `activated_bundle_version` | `2026-05-20.1` | ✓ (matches current bundle MANIFEST) |
| MANDATE.md heading | `# Mandate — alpha-trader` | ✓ (program slug, not persona slug) |
| `_autonomy.yaml::default.delegation` | `autonomous` | ✓ (operator-authored intent) |
| `_autonomy.yaml::default.ceiling_cents` | 5000000 ($50k) | ✓ |
| Alpaca paper-trading platform connection | `active` (existing) | ✓ |
| Probe-residue | None observable | ✓ |

alpha-trader-2 is ready for the e2e: substrate-event hook infrastructure in place, cron-tick recurrences match canon, autonomy permits Reviewer auto-execution under ceiling.

---

## Architectural side-finding: program-slug heading dependency

The MANDATE.md heading-normalization step surfaced a real architectural fragility: `parse_active_program_slug()` reads whatever string appears after `# Mandate — ` and trusts it as a bundle slug. Any operator who manually rewrites MANDATE.md heading without keeping the program slug marker breaks `bundle_update_available()` detection for that workspace.

The Phase B parallel-loop scaffold (2026-04-28) authored alpha-trader-2's MANDATE.md heading with the persona slug `alpha-trader-2 (Stat-Arb Pairs)` instead of the program slug `alpha-trader`. This was a scaffold mistake at the time; under post-ADR-292 the gap surfaces as a hard error during update detection.

The robust solution (out of scope here, ADR seed): move the program-slug marker out of the MANDATE.md heading into something less operator-facing — e.g., MANDATE.md frontmatter `activated_program_slug: alpha-trader` alongside `activated_bundle_version: 2026-05-20.1`. Heading then becomes purely operator-readable identity ("Mandate — alpha-trader-2 (Stat-Arb Pairs)" can be the operator's chosen phrasing), and the bundle-slug-binding lives in machine-parsed frontmatter where it belongs per the file-format discipline in CLAUDE.md §"File Format Discipline (ADR-254)." Would amend ADR-292 v3 or land as ADR-292 v4.

Recording here as a finding-level recommendation. Not pre-fixing — the surgical workaround on alpha-trader-2 is enough to unblock the e2e, and the architectural amendment deserves its own discourse.

---

## What's NOT in this observation

- **kvk probe-residue cleanup** — separate Hat-A action with its own observation folder.
- **The actual e2e run** — this captures only the pre-e2e prep on alpha-trader-2. The e2e itself happens in subsequent observation windows per the existing PLAYBOOK + alpha-trader/alpha-author session-start guides.
- **Render deploy timing** — the API + Unified Scheduler will pick up the new `services/programs.py` (v3 5-branch decision tree) + `substrate_reapply.py` (config-conflict surfacing) on their standard redeploy cycle. The pre-deploy re-fork executed locally with the same code that's now on `main`; the scheduler's first natural fire at 13:30 UTC will be the load-bearing live test.

---

## Cross-references

- [Pre-e2e readiness audit findings](../2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2/findings.md) — the audit that surfaced this fix
- Commit `96acefe` — ADR-292 v3 system canon work
- Commit `687c7ca` — re-fork harness + executed propagation against kvk + yarnnn-author
- ADR-292 v3 D9–D11 (config-vs-prose taxonomy + CI lint)
- ADR-296 v2 D1–D3 (wake architecture)
- ADR-293 D4 (uniform AUTONOMY-mode gating)
- ALPHA-1-PLAYBOOK §3A.5 (alpha-trader 8-recurrence inventory post-ADR-296 v2)
