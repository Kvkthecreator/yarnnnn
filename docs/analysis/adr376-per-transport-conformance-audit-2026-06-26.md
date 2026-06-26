# ADR-376 per-transport conformance audit

**Date**: 2026-06-26
**Hat**: B (external developer — audit + sequencing recommendation; no canon change).
**Purpose**: ground the "which transport conforms to DP32 next" decision in CURRENT
code, refining the blunter 4-path audit in the analysis doc (which was partly from
memory). DP32 invariant = **`retain + attribute + cite`**: a contribution enters as
an attributed RAW observation; understanding is a separate citing act; the raw is
retained (per its transport's mechanism — file or event-row) and never rewritten.
**Receipts**: every claim verified against the live repo 2026-06-26 (cited inline).

---

## The audit (all 7 context-in transports)

| Transport | Raw retained? | Attributed? | Cites source? | DP32 verdict |
|---|---|---|---|---|
| **MCP `remember`** | ✅ `inbound/mcp/{client}/` immutable | ✅ `yarnnn:mcp:{client}` | ✅ derived file `derived_from` | **✅ CONFORMS** (ADR-376 MCP slice, `609df86`/`ae7f470` — implemented + real-run-proven) |
| **Ground-truth (ADR-330)** | ✅ events appended to `_money_truth.md` w/ dedup key + attestation | ✅ `attestation: platform\|operator\|agent` per event | ✅ each event carries its source | **✅ CONFORMS** (event-row raw form — the DP32 mechanism-clause case; `outcomes/ledger.py::fold_outcome_candidates` appends, dedups, never silently overwrites) |
| **Uploads (human)** | ✅ `uploads/{slug}.md` via `write_revision`, agent-unmanaged | ✅ `authored_by="operator"` | n/a (raw IS the artifact — reasoned-against, not derived-from) | **✅ CONFORMS** (the human N=1 case of the raw lane; `routes/documents.py:361`) |
| **Perception (web/RSS, ADR-335/336)** | ❌ **only the distilled signal is kept — fetched raw NOT retained** | ✅ `system:track-web-sources` | ✅ `source_ref` per ADR-335 D3 | **⚠ PARTIAL — retain ✗** (attribute ✓, cite ✓, but the observation behind the distillation is unrecoverable; `track_web_sources.py::_write_signal` writes the contract envelope but "**Never raw payloads**") |
| **Chat (operator addressed)** | n/a — the operator IS the principal authoring directly | ✅ `operator` | n/a | **✅ N/A** (not a foreign contribution; the operator writes substrate as themselves — no raw/derived split needed) |
| **Platform connectors (Slack/Notion)** | n/a — **no sync-to-substrate exists** (ADR-153 sunset `platform_content`; agents read platform APIs LIVE during execution) | — | — | **✅ N/A today** (there is no raw-intake-then-derive path to conform; if a sync-to-substrate returns, it inherits the invariant) |
| **A2A (agent-initiated)** | — spec'd, not built (`a2a:` absent from `VALID_AUTHOR_PREFIXES`) | — | — | **⏸ DEFERRED** (build-deferred per ADR-373/ADR-371; when built, lands `inbound/a2a/{id}/` — same shape as MCP, free conformance) |

---

## The finding that refines the analysis doc

The analysis doc said perception "**discards raw**" — that's *imprecise*. Perception
**cites** (`source_ref`, ADR-335 D3) and **attributes** (`system:track-web-sources`);
it just doesn't **retain** the fetched content the distillation was built from. So
it is **PARTIAL (retain ✗)**, not a flat violation — 2 of 3 clauses already hold.

And the analysis doc's "MCP conflates" + "perception discards" framed *two*
violators. Post-MCP-slice, there is exactly **ONE** non-conformant transport
(perception), and only on **one** clause (retain). Everything else is CONFORMS or
genuinely N/A (chat = operator-direct; connectors = no sync path exists;
ground-truth + uploads already obey).

**Net: the ADR-376 surface is far more converged than the analysis doc implied.**
The only real remaining *conformance* work is perception's retain-gap — and it is
small and well-bounded.

---

## The perception slice (the one remaining violator) — scoped

**The gap**: `TrackWebSources` fetches N web/RSS items, distills them inline into
`_watch_signal.yaml`, and keeps only the distillation. A judgment that fires on a
signal cannot re-read the observation that produced it → the watch is unfalsifiable
(the symptom DP32 predicts for retain-✗).

**The DP32-faithful fix** (mechanism per the invariant's retain-clause — *retain the
observations a derived act CITES, not every fetched byte*):
- Retain the cited raw observations in the raw lane: `inbound/web/{source}/{observed_at}.md`
  (or `.yaml`) — attributed `system:track-web-sources`, immutable.
- The distilled `_watch_signal.yaml` (the derived understanding) carries
  `derived_from` pointing at the retained raw observation(s) it cited.
- **Bounded by citation, not by crawl**: retain only what the signal references, so
  the raw lane stays evidence-not-archive (the §9 DEFER on GC keeps it honest).

**Why it's a clean slice**: the `inbound/` root + `_extract_derived_from` walk +
the derived-first read already exist (built in the MCP slice). Perception conformance
REUSES them — it's a write-side change in one primitive (`track_web_sources.py`),
not new infrastructure. The `derived_from` walk in `compose_trace`/`recall` already
handles any `inbound/` raw + any `derived_from`-carrying derived file generically.

**Honest scoping caveat** (do NOT pre-decide): perception's `derived_from` is the
FIRST real case of a derived object citing **multiple** raw observations (one signal
distills N sources) — which is exactly the ADR-376 §9 DEFER item "derived_from single
vs list." So the perception slice is the **trigger** that promotes that DEFER to a
DECIDE. The slice's first sub-decision: make `derived_from` a list (or a
multi-line/multi-match field) before wiring perception. This is named, not hidden.

---

## Recommendation (sequencing)

1. **Perception slice is the next ADR-376 work** — the sole remaining violator, small,
   reuses the MCP-slice infrastructure. It carries the `derived_from`-as-list decision
   (the §9 DEFER's trigger has arrived for THIS slice).
2. **Connectors / chat / A2A need NO conformance work** — N/A (no sync path / operator-
   direct) or deferred-by-construction (A2A unbuilt). Don't manufacture work for them.
3. **Ground-truth + uploads are DONE** — recognized as conformant instances (doc-only;
   this audit is that recognition). No code.

So the ADR-376 implementation tail is **one slice (perception), not four**. The
analysis doc's "per-transport conformance, each a follow-on" over-counted; this audit
collapses it to the single real piece of work.
