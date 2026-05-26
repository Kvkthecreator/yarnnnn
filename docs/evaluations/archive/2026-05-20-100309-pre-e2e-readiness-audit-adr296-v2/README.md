# Pre-E2E Readiness Audit — ADR-296 v2 Validation Setup

**Hat**: External Developer of the System (Hat B observation; the system-canon fixes themselves land via continuous-arc commits — the hat distinction is vocabulary discipline, not session boundary).
**Captured**: 2026-05-20T10:03Z, ~3h27m before RTH open (13:30Z).
**Author**: Claude (Opus 4.7).
**Status**: Findings captured; operator confirmed sustainable-fix direction 2026-05-20T10:50Z; system-canon work proceeds in subsequent commits (separate logical commits per fix area). This folder is the audit trail of why the work was warranted.

## One-line verdict

**Both workspaces are unfit for honest ADR-296 v2 e2e in their current state.** Three load-bearing issues — pre-Checkpoint-2 bundle staleness, missing `_hooks.yaml` substrate-event sibling, and probe-residue (kvk only) — combine such that any e2e run today would surface bundle-migration artifacts rather than architecture defects. Sustainable fix direction selected by operator; system-canon commits follow.

See `findings.md` for the full report (substrate evidence + operator-chosen direction in §4).

## Files in this folder

- `README.md` — this file
- `findings.md` — full readiness report (cross-workspace findings, operator-chosen direction, open-questions resolution log)

## What's NOT in this folder (and why)

The actual system-canon changes (ADR-292 v3, `services/programs.py` content-hash gate, CI lint, bundle MANIFEST version bumps, canon vocabulary propagation, live workspace re-forks, alpha-trader-2 autonomy flip, kvk hygiene cleanup) land in their respective system locations: `docs/adr/`, `docs/architecture/`, `docs/programs/`, `api/`, `scripts/`. This folder captures the evidence that warranted the work; the work itself lives where canon lives. The kvk hygiene cleanup gets its own observation folder when executed.
