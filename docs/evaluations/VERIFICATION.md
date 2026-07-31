# VERIFICATION.md — lane criteria for the verification radar

**Consumed by**: the `verification-radar.sh` SessionStart hook (which lanes are
due) and any session doing refactor work (what "verified" means per lane).
**Updated by**: `.claude/hooks/mark-validated.sh <lane>` after a lane's exit
criteria are MET — never before. The ledger (`.claude/validation-ledger.json`)
is committed with the validation work so state survives sessions.

The shape of every lane follows the prompt-structure principles
(`docs/analysis/prompt-engineering-principles-2026-07-30.md`): what to verify
(task), what must not happen (guardrails), and what "done" means (exit
criteria). Standing rules that already bind: gates are proven RED before
trusted green; a claim without a receipt is narrative; verify before finishing.

---

## prompt — `api/agents/` · `api/services/primitives/` · `api/prompts/`

- **Verify**: `cd api && python3 -m pytest test_adr383_trigger_framing_recarved.py test_adr323_frame_collapse_finished.py test_envelope_scaffold_ratchet.py -q`
- **Guardrails**: Prompt Change Protocol (CLAUDE.md) — CHANGELOG entry naming the
  repeated observed failure; adding is last resort; raising any ceiling needs the
  ADR-306/DP22 evidence bar.
- **Exit**: ratchets green + CHANGELOG entry in the same commit. Behavior-shaped
  changes additionally: one bare-steward probe preflight
  (`python3 -m scripts.operator.probe_freddie_bare_steward`, free) — and a funded
  `--live` wake if judgment behavior itself changed.

## api — `api/services/` · `api/routes/` · `api/jobs/` · `api/mcp_server/`

- **Verify**: targeted pytest for the touched module's gates (grep
  `api/test_*.py` for the module name); wake-path changes (`wake*`, `freddie*`,
  `scheduling`, `recurrence`) → bare-steward probe preflight; studio changes →
  the studio gates (`python3 <gate>.py` from `api/`, NOT pytest).
- **Guardrails**: schema names current (SCHEMA-NOTES.md); Render parity check for
  env/infra changes (all 3 services); an app-layer scoping change is HALF a
  sweep — RLS is the other half.
- **Exit**: touched-module gates green; for permission/scoping changes, a live
  two-principal probe receipt (the ADR-501/503 pattern — mint JWTs via
  `alpha_ops._shared`, real `X-Workspace-Id`), not config inspection.

## web — `web/`

- **Verify**: `cd web && pnpm build` (tsc alone is NOT verification — dirty-tree
  lesson). UI-visible changes → a browser click-pass (E2E lane below).
- **Guardrails**: redirect stubs stay pure server transport (ADR-308); surface
  slugs against the live `SurfaceRegistry`, never from memory.
- **Exit**: build green; for UI changes, a click-pass session record with BOTH a
  DOM observation and a substrate receipt where the click writes.

## migrations — `supabase/migrations/`

- **Verify**: apply via psql per `docs/database/ACCESS.md`; refresh PostgREST
  cache; RLS-touching migrations → probe with the USER client, not service key
  (service-role-only reads fail silently).
- **Guardrails**: a migration with its own BEGIN/COMMIT swallows your wrapper;
  verify the migration number is unclaimed at commit time (parallel lanes).
- **Exit**: applied receipt (psql output) + a read-back query proving the shape +
  RLS probe for policy changes.

## evals — `api/scripts/operator/` · `docs/evaluations/eval-suites/` · `docs/alpha/personas.yaml`

- **Verify**: `cd api && python3 -m pytest test_probe_staleness_gate.py test_eval_suite_gate.py -q`
- **Guardrails**: personas.yaml is the probe-target roster — NEVER add a real
  user (probes seed/delete substrate and fire funded wakes); new manifests carry
  `status:`; retiring a suite = RETIRED-SUITES.md entry with its thesis-verdict
  state (falsifier discipline).
- **Exit**: both gates green; any NEW gate proven red once before trusted green.

## claude-md — `CLAUDE.md`

- **Verify**: `cd api && python3 -m pytest test_claude_md_ratchet.py -q` + spot
  reference sweep on edited rows (paths + `::symbols` against live code).
- **Guardrails**: instruction vs reference split — reference detail goes to
  ADR-LEDGER/SCHEMA-NOTES, not here; ceiling raise needs the evidence bar.
- **Exit**: ratchet green; edited rows' pointers verified live.

---

## E2E browser lane (the human-parity layer — extension-gated)

Claude Code acts as the testing principal via Claude in Chrome, logging into
the declared TEST ACCOUNTS ONLY (the personas registry + `kvkthecreator@*` +
`seulkim88@gmail.com` — the owner/member pair on the live workspace). Login via
`alpha_ops/_shared.py` magic-link machinery when a persona session is needed.

- **Precondition**: the session has browser tools (operator: `/chrome` →
  Enable by default; extension v1.0.36+ signed in).
- **Task shape**: click-pass manifests carry `suite_kind: browser` in the
  eval-suites registry (landed 2026-07-31) and follow Describe / Task /
  Guardrails / Exit. Each step declares `expect_dom:`; each state-changing step
  additionally declares `receipt:` (the substrate query) + `restore:` — held by
  `api/test_eval_suite_gate.py`. The runner deliberately refuses this kind (a
  browser principal fires it, not the LLM). First manifest:
  `eval-suites/settings-surfaces-click-pass.yaml`, with a repo-free operator
  form at `OPERATOR-PACKET-settings-click-pass.md`.
- **Login**: `cd api && python3 -m scripts.operator.browser_login_link <email>`
  mints a navigable single-use magic link (roster-guarded in code — it refuses
  any email that is not a declared test principal).
- **Guardrails**: destructive/seeded scenarios on rig accounts
  (`kvk-yarnnn`, `bare-kernel`, `testacct`) — the live workspace (`d5b9029b`)
  is read-mostly; reset-to-clean before seeded passes (S2).
- **Exit**: a dated session record under `docs/evaluations/` with the click
  path, screenshots where load-bearing, and the SUBSTRATE receipt for every
  state-changing click (revision id / execution_event / proposal state). A
  browser pass without a substrate receipt is narrative.
