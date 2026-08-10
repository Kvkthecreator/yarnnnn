// The `save` result shape (server.py save → mcp_composition.compose_save).
// ADR-533 D4. Three states the widget renders, in order of how much the user
// needs to SEE rather than read:
//   stale_write / base_required — a CONFLICT: someone else holds the head. The
//     user must decide (re-open, merge, save again). This is the state the
//     widget exists for; prose buries it.
//   success — a receipt: it landed, here's the new head to chain from.
//   other failure — the message, plainly.

export interface SaveHead {
  revision_id?: string | null;
  authored_by?: string | null;
  when?: string | null;
  change?: string | null;
}

export interface SaveResult {
  success?: boolean;
  reference?: string;
  path?: string | null;
  created?: boolean;
  revision_id?: string | null;
  /** Present on stale_write + base_required — who holds the head you must read first. */
  current_head?: SaveHead | null;
  error?: string;
  message?: string;
  explanation?: string;
}

/** Accept only a `save` result. `reference`+`revision_id` is the success shape;
 *  `current_head` is the conflict shape; both are distinctive enough that no
 *  other verb's result matches (open has `found`, history has `history`). */
export function isSaveResult(v: Record<string, unknown>): boolean {
  if ("current_head" in v) return true;
  if ("created" in v && "reference" in v) return true;
  return "revision_id" in v && "reference" in v;
}

/** The two conflict errors share one rendering: someone else holds the head. */
export function isConflict(result: SaveResult): boolean {
  return result.error === "stale_write" || result.error === "base_required";
}
