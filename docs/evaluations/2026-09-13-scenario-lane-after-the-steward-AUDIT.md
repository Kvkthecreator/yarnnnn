# AUDIT — the scenario lane after the steward (2026-09-13)

**Hat**: B (evaluation toolchain). **Trigger**: `test_no_undefined_names.py`
flagged `services/operator_proxy/scenarios.py::establish_substrate` reading
eight names the module never binds; the operator asked for the eval pass on it
and to streamline. **Receipts**: commits named below; gates listed at the end.

## What was found

1. **`establish_substrate` was corrupted, not merely stale.** 85c4f7b (ADR-632,
   2026-09-02) deleted the steward-era `_establish_field_equals` helper by
   cutting its head — and left its body spliced into `establish_substrate`
   after the `clear_proposals` branch. The function's own `return` was gone;
   the helper's `return` ran instead, over names that no longer existed.
   `run_eval_suite.py` calls this for every non-accumulating eval at
   pre-flight, so **every thesis-suite run after 2026-09-02 would have raised
   NameError before spending a token**. Nobody noticed because no thesis suite
   fired after the steward left.
2. **The one current thesis suite measured a steward wake.**
   `freddie-bare-workspace-steward.yaml` (status `current` since 07-31) reads a
   `cron_tick` judgment wake — a turn shape ADR-632 deleted. Its runner path
   was already dead on 07-31 (persona slug never registered); its one PASS
   (2026-06-29) came through a probe.
3. **The eval-suite gate was red on the browser lane**, unrelated to the
   steward: four mutating steps in the two ADR-518 click-pass manifests
   declared a `receipt:` but no `restore:` (the d5b9029b read-mostly
   guardrail). The cleanup step in each was the restore of the create step,
   and said so nowhere.

## What survives, and is worth keeping

- **The scenario runner is a lane instrument now.** Its measured-turn shapes
  are `send_message` (a chat turn → `run_lane_turn`), the proposal verbs
  (`emit_proposal` / `approve_proposal` / `reject_proposal`), `write_substrate`
  and `flip_frontmatter_field`; its setup shapes are substrate writes,
  deletes, `clear_proposals`, `seed_draft`. Nothing in it references the wake
  stack any more. Kept.
- **The browser click-pass lane** (five `suite_kind: browser` manifests,
  driven by a browser principal with per-step receipts) is the lane every
  pass since August has actually used. Kept, and green again.
- **`check_preconditions`** still reads `field/equals` assertions. What is
  gone is *establishing* them — that wrote steward dial files.

## What changed

- `establish_substrate` repaired: the field-establishment path and the
  spliced body removed; its return restored
  (`{deleted, wrote, expired_proposals}`); docstring states that `field/equals`
  is checked, never established — a scenario writes what it needs with
  `setup: write_substrate`.
- `freddie-bare-workspace-steward.yaml` → `status: superseded` (the status the
  runner refuses; the vocabulary is current | dormant | superseded), in place;
  `RETIRED-SUITES.md` carries the verdict state (EXERCISED — PASS on the core
  thesis, then DECIDED-ELSEWHERE by ADR-632) and the re-cut note.
- `test_eval_suite_gate.py`: "exactly one current thesis suite" →
  `DECLARED_CURRENT` (a list, at most one entry, **empty today**). Going
  current is one edit here plus the README registry, in the same commit.
- The four ADR-518 steps declare their `restore:` (trash is a lifecycle
  transition; the cleanup step is the create step's restore, and vice versa).
- `test_no_undefined_names.py` allowlist is empty: nothing in `routes/`,
  `services/`, `jobs/`, `integrations/`, `mcp_server/` reads an unbound name.

## Open, deliberately

- **No current thesis suite.** The next one measures a lane turn. Candidate
  subjects already probed by hand this month and worth a declared thesis:
  the register (ADR-638, A/B-validated), the skills index (ADR-630), the
  composite-document skill (ADR-630, measured null). Cutting one is a Hat-B
  decision with a cost line, not a follow-up this audit takes.
- The scenario corpus under `scenarios/` (`anr-scout-*`, `author-*`) still
  spells steward-era setup (`_autonomy.yaml`, `fire`); it is the record of
  those runs and parses today because the runner ignores unknown turn keys.
  A corpus pass belongs to whoever cuts the next thesis suite.

## Gates

`test_no_undefined_names.py` · `test_eval_suite_gate.py` ·
`test_probe_staleness_gate.py` · `test_adr294_operator_proxy.py` — results in
the commit that carries this record.
