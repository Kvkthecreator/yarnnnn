# W0 falsifier baseline — pre-rooms snapshot (2026-07-28)

**Why this file exists**: ADR-492 §7's sequencing guard — shipping rooms changes what chat *is*
mid-observation (three-axes §8), so the ADR-457 D8 falsifiers are evaluated per-phase against a
recorded snapshot, never on one clock. This is the snapshot taken immediately **before the rooms
build** (ADR-460 §8 step 4, operator-ordered jump to human rooms 2026-07-28).

**Instrument**: `api/services/falsifiers.py::read_all` (the real module, not ad-hoc SQL), run
against prod, workspace `d5b9029b-bd4e-4757-9fcb-e2b139fd4913` (the live 5-grant commons),
window 90d, read at `2026-07-28T10:29:34Z`.

```json
{
  "falsifier_1": {
    "question": "is chat used only as a command line?",
    "turns_by_surface": {"think": 17, "make": 28, "derive": 0, "steward": 0, "unclassified": 64},
    "classified_turns": 45,
    "unclassified_turns": 64
  },
  "falsifier_2": {
    "question": "is the settle verb used after honest staging?",
    "staged": true,
    "settles": 4,
    "think_turns": 17,
    "settles_per_think_turn": 0.235
  },
  "falsifier_3": {
    "question": "does MCP traffic dwarf desk traffic?",
    "hum_writes": 7,
    "desk_writes": 484,
    "system_writes": 323,
    "hum_to_desk_ratio": 0.014
  }
}
```

Reading (no judgment passed on the bet — the 60–90d pass does that):
- **F1**: make-turns (28) lead think-turns (17); the 64 unclassified are pre-migration-216 rows
  with no `session_id` join — the discriminator only started recording with W0.
- **F2**: settle is *used* — 4 settles against 17 think turns since it shipped (~0.24/turn).
  Small n, but not null and not zero.
- **F3**: the desk dwarfs the hum (484 vs 7 attributed writes) — the D5 investment thesis is
  pointing desk-ward at this workspace, not hum-ward.

Post-rooms reads must be compared against this file, not against memory.
