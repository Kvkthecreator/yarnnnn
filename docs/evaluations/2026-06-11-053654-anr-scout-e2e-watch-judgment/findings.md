# Findings — THE FINAL E2E: the standing-watch perception loop, closed on real data

**Verdict: PASS, all cells.** The loop ADR-335 ratified and ADR-336 built ran end-to-end on the live soak with real-world data — the validation the perception arc had been missing:

> operator watch declaration (`_sources.yaml`, rev `e03259bd`) → mechanical transport (TrackWebSources binding contract test: 2/2 real feeds, 0 errors) → distilled attributed observations (`_watch_signal.yaml`, real Stereogum/BrooklynVegan entries, `system:track-web-sources` attribution) → **judgment reads substrate** (never the web) → framework-conformant discrimination → autonomous standing-intent update.

| Cell | Verdict | Receipt |
|---|---|---|
| Reads substrate, not web | **PASS** | Response names both sources + a specific feed artist ("proun"); zero web fetches in the wake |
| Noise/signal discrimination | **PASS (strong)** | "press-side data, not scouting signals… no artists matching the structural evidence bar… it shows what the press is covering — but that feeds the watchlist, not scouting judgment" — and it still extracted the one genuine lead (proun, debut album coming) as a *monitoring* candidate, not a conviction |
| Honest headline epistemics | **PASS** | "Stereogum enthusiasm is a lead" — leads ≠ signals, platform-attested publication facts treated as exactly that |
| Autonomous delegation works | **PASS** | `standing_intent.md` AUTO-APPLIED, attributed `reviewer:ai:reviewer-sonnet-v8` — direct write narration, no proposal queue (the corrected `_autonomy.yaml`, revisions `f9ed9b28`+`98755939`, doing its job) |

**Standing state from tomorrow**: the scheduler runs the loop unattended — track-sources 11:30 UTC (deployed primitive, commit `b449bf0`) → corpus-coherence-check 12:00 UTC reads a fresh watch signal (envelope `watch_signal` key live post-deploy). Check 7 (transport-blind) covers the watch in the soak's survival reads; prediction grading (ADR-336 D3) accumulates from the reconciliation cycles.
