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
          {/* The guard is only reassuring if you can SEE what it wants. The
              server returns the head revision id on both conflict errors; it is
              the exact value the retry must carry as base_revision, so name it
              rather than leaving the reader to fetch it back out of `open`. */}
          {head.revision_id ? (
            <p className="yz-receipt-meta yz-basis">
              Save again with <code>base_revision</code>:{" "}
              <code className="yz-rev">{head.revision_id}</code>
            </p>
          ) : null}
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
        {/* The provenance edge, made visible. `derived_from` is what separates
            an attributed commons from a folder that happens to hold files: this
            document was made FROM those, and the workspace will warn before one
            of them is deleted. It is recorded on every such save and was, until
            now, invisible at the point of writing. */}
        {result.derived_from && result.derived_from.length > 0 ? (
          <p className="yz-receipt-meta yz-derived">
            Made from{" "}
            {result.derived_from.map((p, i) => (
              <span key={p}>
                {i > 0 ? ", " : ""}
                <code className="yz-rev">{p}</code>
              </span>
            ))}
          </p>
        ) : null}
        {result.path ? <code className="yz-path">{result.path}</code> : null}
      </div>
    </div>
  );
}
