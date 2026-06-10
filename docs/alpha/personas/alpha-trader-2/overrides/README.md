# alpha-trader-2 persona overrides

ADR-230 D6: persona-specific operator content that differs from the
alpha-trader program's reference-workspace template. Applied as Step 4
of `api/scripts/alpha_ops/activate_persona.py` with
`authored_by="operator:alpha-alpha-trader-2"` per ADR-209.

Files here OVERWRITE the matching paths in the bundle's
reference-workspace fork. Path layout mirrors the operator workspace
structure (relative to `/workspace/`).

## Why these files exist as overrides

kvk's stat-arb pairs strategy is a different operating profile than the
program's default Simons-Option-B momentum-mean-reversion-PEAD-sector
multi-signal model. Both are valid alpha-trader programs (same risk
discipline frame, same capability needs, same Reviewer-gated workflow);
they just declare different signals + different sizing model.

Per ADR-230 the program bundle ships ONE template (Simons-Option-B
default in `docs/programs/alpha-trader/reference-workspace/`); each
alpha persona that runs that program overrides the parts that legitimately
differ for their book. Overrides are opt-in — alpha-trader-1 (seulkim88)
has no overrides directory; she runs the bundle template as-is.

## Files

Paths are current-canon (ADR-308/309 register split + ADR-320 collapse):
`constitution/` for pure intent (MANDATE), `operation/` for the working
substrate (trading domain). The pre-ADR-320 `context/` layout these files
used to ship was migrated 2026-06-10 (it had been silently writing
contaminating duplicates at dead paths on every clean-slate).

| Override | Bundle template | Why differs |
|---|---|---|
| `constitution/MANDATE.md` | `docs/programs/alpha-trader/reference-workspace/constitution/MANDATE.md` | Stat-arb pair-trading vs single-name signal model — primary action is a two-leg beta-neutral pair, not a single-ticker momentum entry |
| `operation/trading/_operator_profile.md` | `docs/programs/alpha-trader/reference-workspace/operation/trading/_operator_profile.md` | 6 cointegrated pairs + z-score signals vs 5 single-name signals; different universe; different sizing formula |
| `operation/trading/_risk.md` | `docs/programs/alpha-trader/reference-workspace/operation/trading/_risk.md` | Stat-arb-shaped risk: per-pair vol target replaces per-position risk %; correlation caps replace sector caps |

**MANDATE heading carries the program slug `alpha-trader`** (not `alpha-trader-2`),
so `parse_active_program_slug` validates against `_all_slugs()` for the ADR-244 D4
re-fork capture on clean-slate. The persona's stat-arb identity lives in the
MANDATE body sections, not the heading — same convention as the bundle's ADR-292
heading-normalization. A heading like `# Mandate — alpha-trader-2` is NOT a valid
bundle slug and silently breaks clean-slate re-fork.

## Re-applying

After editing any file here:

```
.venv/bin/python api/scripts/alpha_ops/activate_persona.py --persona alpha-trader-2
```

Idempotent — re-running re-applies overrides via ADR-209 revision chain
with the operator-attribution. The bundle template fork (Step 3) honors
ADR-223 §5 three-tier rules; overrides (Step 4) overwrite unconditionally
because they're operator-authored.
