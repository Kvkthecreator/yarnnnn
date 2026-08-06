# STUDIO.md → moved to [AUTHORING.md](AUTHORING.md)

**Renamed 2026-08-06.** This file was named for one of its two consumers while being the
authoritative interaction contract for both Docs and Studio (and Images). After ADR-525
and ADR-526 gave Docs its own tier law and its own structure model, the name had become
something a Docs reader had to see through.

**The contract did not split, and that was measured, not assumed.** Docs-specific content
is ~16% of the file, and ~44% of the `document` column is `—`/`🚫` cells that mean nothing
once the `deck` column is removed. Eight of twelve normative rules and thirteen of eighteen
refusals are global. Normative rule 11 is a recorded incident of what happens when one
contract gets derived in two places. The adjacency is load-bearing — it is what made
ADR-525 and ADR-526 findable in the first place.

→ **[AUTHORING.md](AUTHORING.md)** — the grain × medium interaction contract.

Historical ADRs and `docs/analysis/` keep their `STUDIO.md` references verbatim: those are
dated records of what was written at the time, and rewriting them would falsify the
record. This stub is why those links still resolve.
