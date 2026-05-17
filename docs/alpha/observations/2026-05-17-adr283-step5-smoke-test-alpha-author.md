# ADR-283 step 5 — alpha-author activation harness smoke test (2026-05-17)

> Smoke test of `activate_persona.py --dry-run` against the alpha-author bundle personas (`yarnnn-author`, `netflix-script-author`) added in ADR-283 step 4 (commit `904f9a4`). Surfaces what real-activation would require and one harness gap closed in-place.

## Setup

- ADR-283 steps 1-4 shipped: bundle authored, substrate-enrichment landed, cockpit faces shipped, persona rows + override directories scaffolded.
- Personas declared with `platform.kind="none"` + `credentials_env: {}` per ADR-283 D7 (alpha-author requires no external writes).
- Placeholder all-zeros UUIDs for `user_id` + `workspace_id` (real Supabase provisioning is step 6 work).

## Dry-run output (post-fix)

```
$ api/venv/bin/python api/scripts/alpha_ops/activate_persona.py --persona yarnnn-author --dry-run

Persona:      yarnnn-author  (yarnnn-author@yarnnn.com)
  user_id:    00000000-0000-0000-0000-000000000000
  workspace:  00000000-0000-0000-0000-000000000000
  program:    alpha-author
  platform:   none (none)

DRY RUN. No writes.
Step 3 fork: docs/programs/alpha-author/reference-workspace/* → /workspace/* (.md + .yaml)
Step 4 overrides: skip (docs/alpha/personas/yarnnn-author/overrides/)
Step 5 specialists: ensure × 0:
Step 6 (DELETED — ADR-231): recurrence YAMLs are scaffolded via Step 3 fork.
Step 7 connect: attempt platform connect
```

Identical output for `netflix-script-author`.

## Findings

### Finding 1 — `platform.provider` is required (closed in step 4 commit)

`Persona.platform_provider` accesses `self.platform["provider"]` unconditionally; the original alpha-author persona rows declared only `platform.kind`. Closed by adding `provider: none` to both rows in step 4 commit (initial step 4 commit `904f9a4` was patched in this session to add the field — see committed state).

### Finding 2 — Zero specialists discovered (correct by design)

`_bundle_recurrence_roles()` walks the bundle's `reference-workspace/*.yaml` for recurrence entries with `agent` / `agent_slug` / `agents` fields. For alpha-author, the discovery returns 0 roles — which is correct by design:

- All 4 alpha-author recurrences (`pre-ship-audit`, `corpus-coherence-check`, `revision-audit`, `outcome-reconciliation`) are Reviewer-judgment-mode with `required_capabilities: []`.
- The substrate-continuity archetype dispatches no specialists — the Reviewer audits directly (vs alpha-trader's autonomous-execution archetype which commissions specialist sub-LLM calls for capital actions).

No fix needed. Step 5 of the harness ("ensure specialist rows × 0") is a no-op for alpha-author, which is architecturally correct.

### Finding 3 — `_platform_connect` failed for `kind: none` (FIXED IN-PLACE)

**Surfaced bug**: `_platform_connect()` checks `if missing:` for empty-env-var skip — but with `credentials_env: {}`, the `missing` list is empty (no keys to check) so the skip doesn't trigger. Execution falls through to `_build_payload(persona)` which raises `SystemExit("Unsupported platform kind: none")`.

This is a real bug surfaced by adding the first archetype-agnostic persona to the registry. The harness was designed assuming every persona has a platform (trading or commerce).

**Fix shipped in this commit** (~5 line patch to `_platform_connect`): added an early `if persona.platform_kind == "none": skip` branch with explicit ADR-283 D7 framing. Now the harness recognizes archetype-agnostic personas as a first-class case rather than a configuration error. Helps any future substrate-continuity bundle (not just alpha-author).

Real-activation behavior post-fix:
- `kind: none` → "SKIP platform connect — persona.platform.kind=none (no external writes by design)"
- `kind: trading|commerce` + missing env vars → "SKIP platform connect — missing env vars: ..."
- `kind: trading|commerce` + present env vars → POST through ProdClient (unchanged)

### Finding 4 — Real activation requires real Supabase IDs (expected, not a bug)

The dry-run validates the plan shape but does not actually exercise:
- The `_fork_reference_workspace(persona.user_id, persona.program)` call against Supabase (would need real `user_id` row + workspace_files privileges)
- The `_apply_overrides` write through `UserMemory` (same)
- The specialist `ensure_infrastructure_agent` calls (same)

This is correct deferred state per ADR-283 step 6 framing. To do real activation:
1. Provision a real Supabase user + workspace for `yarnnn-author@yarnnn.com` (and same for `netflix-script-author@yarnnn.com`)
2. Replace the placeholder all-zeros UUIDs in `personas.yaml` with the real values
3. Run `activate_persona.py --persona yarnnn-author` (without `--dry-run`) against the live API

Step 5's job (this memo) is verifying the harness plumbing is correct end-to-end *up to* the Supabase boundary. That's now verified.

## What's now true on `main` after this commit

- `personas.yaml`: both alpha-author rows have `provider: none` so `Persona.platform_provider` doesn't KeyError
- `activate_persona.py`: `_platform_connect` recognizes `kind == "none"` as a first-class case (clean skip with explicit framing), not a configuration error
- Dry-run for both alpha-author personas exits cleanly with the expected plan
- Real-activation against placeholder UUIDs would fail at the Supabase fork step (expected; documented in personas.yaml inline comments)

## What step 6 requires (preview)

Step 6 (dogfood activation) — operator-driven — would:
1. Provision Supabase users + workspaces (2 of them — one for yarnnn-author, one for netflix-script-author)
2. Replace placeholder UUIDs in personas.yaml with real values (operator commit)
3. Run `activate_persona.py --persona yarnnn-author` against live API
4. Verify the activation succeeded via the cockpit (visit `/work` for the workspace, see the four AuthorMandate / AuthorCorpus / AuthorVoice / AuthorPipeline faces render with appropriate empty-state messaging since `_signal.md` doesn't exist yet)
5. Operator authors first content into `/workspace/context/authored/` and walks through the first `pre-ship-audit`
6. Observe Reviewer behavior end-to-end; record findings as `docs/alpha/observations/2026-XX-XX-adr283-alpha-author-first-wake-*.md` per the alpha-ops observation convention

That is genuine operator dogfood work and lives at the operator's pace. The architecture is ready.
