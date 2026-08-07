// The save-receipt widget (ADR-533 D4). Renders RETURNED substrate only.
//
// Why this verb earns a widget when `share` does not: `save`'s most important
// outcome is the CONFLICT (stale_write / base_required) — someone else changed
// the file since the host read it. That state carries four facts the user must
// act on (who, when, what they called it, what to do next), and a chat host
// renders it as a paragraph the user skims past. A card makes the conflict
// unmissable and names the resolution.
//
// The success path is deliberately small — a receipt, not a UI. The value is
// making the attributed write legible, not decorating it.

import type { SaveResult } from "./types";
import { isConflict } from "./types";
import { provBucket, fmtWhen } from "../shared/provenance";

export function SaveReceipt({ result }: { result: SaveResult | null }) {
  if (!result) {
    return <p className="yz-empty">Saving…</p>;
  }

  // ── The conflict: someone else holds the head ──────────────────────────────
  if (isConflict(result)) {
    const head = result.current_head || {};
    const who = head.authored_by || "someone else";
    const bucket = provBucket(head.authored_by);
    return (
      <div className="yz-receipt yz-conflict">
        <span className="yz-check yz-warn">⚠</span>
        <div className="yz-receipt-body">
          <p className="yz-receipt-title">Not saved — the file changed</p>
          <p className="yz-receipt-meta">
            <span className={`yz-chip ${bucket}`}>{who}</span>
            {head.when ? <> &nbsp;{fmtWhen(head.when)}</> : null}
          </p>
          {head.change ? (
            <p className="yz-receipt-meta yz-change">“{head.change}”</p>
          ) : null}
          <p className="yz-receipt-meta yz-resolve">
            Their version is now the current one. Re-open the file, merge your
            change over theirs, and save again — nothing was overwritten.
          </p>
          {result.path ? <code className="yz-path">{result.path}</code> : null}
        </div>
      </div>
    );
  }

  // ── Any other failure ─────────────────────────────────────────────────────
  if (result.success === false) {
    return (
      <div className="yz-receipt">
        <span className="yz-check yz-warn">!</span>
        <div className="yz-receipt-body">
          <p className="yz-receipt-title">Not saved</p>
          <p className="yz-receipt-meta">
            {result.message || result.error || "The write did not complete."}
          </p>
        </div>
      </div>
    );
  }

  // ── The receipt ───────────────────────────────────────────────────────────
  return (
    <div className="yz-receipt">
      <span className="yz-check">✓</span>
      <div className="yz-receipt-body">
        <p className="yz-receipt-title">
          {result.created ? "Created in your workspace" : "Saved to your workspace"}
        </p>
        <p className="yz-receipt-meta">
          Signed as you, versioned — every earlier version is still there.
        </p>
        {result.path ? <code className="yz-path">{result.path}</code> : null}
      </div>
    </div>
  );
}
