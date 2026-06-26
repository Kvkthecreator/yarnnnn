/**
 * inferNarrativeDirection — derive a narrative row's boundary DIRECTION
 * (in / out / internal) from the envelope signals (ADR-377).
 *
 * Direction is NOT a stored field — it's inferred from what the narrative
 * already carries (the "track everything, filter at the surface" model: the
 * narrative log is complete; the Context In/Out/Flow views are filters over
 * it). The signals:
 *
 *   - `writtenTo` present  → an INBOUND crossing landed at a substrate path
 *                            (MCP `remember`, connector sync, upload). The
 *                            content came IN across the boundary.
 *   - `tool` ∈ read verbs  → an external READ (MCP `recall` / `trace`) — a
 *                            query, not an ingestion. Classed `internal`
 *                            (it's boundary traffic but not context coming in).
 *   - everything else      → `internal` (reviewer cycles, operator messages,
 *                            agent runs, probes). The Flow view shows all of
 *                            it; In filters to `in`.
 *
 * NOTE on OUT: outbound sends (emissions) are NOT narrative rows — they live
 * in destination_delivery_log + notifications and are read via /api/emissions
 * (the Out pane mounts EmissionsView directly). So this helper classifies
 * narrative rows as `in` vs `internal`; `out` is included in the union for
 * completeness but a narrative row rarely resolves to it (a future explicit
 * `direction` stamp could unify them — ADR-377 §2 defers that).
 */

export type NarrativeDirection = 'in' | 'out' | 'internal';

// MCP read verbs — queries, not ingestion. (remember is the write verb.)
const READ_TOOLS = new Set(['recall', 'trace']);

export interface DirectionSignals {
  writtenTo?: string;
  tool?: string;
}

export function inferNarrativeDirection(signals: DirectionSignals): NarrativeDirection {
  // An inbound write landed at a substrate path → context came IN. A read
  // verb never writes, so `writtenTo` + a read tool can't co-occur; guard
  // anyway by checking the read set first.
  if (signals.tool && READ_TOOLS.has(signals.tool)) return 'internal';
  if (signals.writtenTo) return 'in';
  return 'internal';
}

/** True when a row is an inbound boundary crossing (the Context In view). */
export function isInbound(signals: DirectionSignals): boolean {
  return inferNarrativeDirection(signals) === 'in';
}
