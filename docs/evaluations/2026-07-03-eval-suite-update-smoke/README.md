# Eval-suite update — instrument-validation smoke (2026-07-03)

Single-ask (`--only 1`) live run validating the probe upgrades landed this
session (usage/cost block from the `reviewer_response` FreddieOutput, sentinel
checks, auto-diff vs `CURRENT_BASELINE`). Not a behavioral arm — instrument
receipt only. Result: closed 1/1, Sonnet 4.6, est. $0.1202 (cold cache write,
matching the canonical baseline's turn-1 cold pattern), sentinels 0/0.
Canonical baseline: `../2026-07-03-rung4-partB-sonnet-addressed/`.
