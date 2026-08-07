// The file-header widget (ADR-533 D4). Renders RETURNED substrate only.
//
// It shows the file's IDENTITY, never its content: which exact file, who holds
// the current version, when they made it, and how many attributed revisions sit
// behind it. The content stays in the host's own rendering — a widget that
// re-rendered the text would compete with the host at something it does better,
// and would push the attribution (the thing a plain storage connector cannot
// show) below the fold.
//
// The not-found state matters as much as the found one: `open` never guesses, so
// a miss is a real answer — "that exact reference has no file" — and the card
// says so plainly rather than letting it read as an error.

import type { OpenResult } from "./types";
import { provBucket, fmtWhen } from "../shared/provenance";

function basename(path: string | null | undefined): string {
  if (!path) return "";
  const parts = path.split("/").filter(Boolean);
  return parts[parts.length - 1] || path;
}

export function FileHeader({ result }: { result: OpenResult | null }) {
  if (!result) {
    return <p className="yz-empty">Opening…</p>;
  }

  if (result.found === false) {
    return (
      <div className="yz-receipt">
        <span className="yz-check yz-warn">·</span>
        <div className="yz-receipt-body">
          <p className="yz-receipt-title">No file at that reference</p>
          <p className="yz-receipt-meta">
            Nothing exists at this exact path. Search by subject instead of
            opening by reference.
          </p>
          {result.path || result.reference ? (
            <code className="yz-path">{result.path || result.reference}</code>
          ) : null}
        </div>
      </div>
    );
  }

  const history = result.history || [];
  const bucket = provBucket(result.authored_by);
  const count = history.length;

  return (
    <div className="yz-file">
      <div className="yz-file-head">
        <span className="yz-file-name">{basename(result.path || result.reference)}</span>
        {result.truncated ? <span className="yz-trunc">excerpt</span> : null}
      </div>

      <p className="yz-receipt-meta">
        <span className={`yz-chip ${bucket}`}>{result.authored_by || "unattributed"}</span>
        {result.last_updated ? <> &nbsp;{fmtWhen(result.last_updated)}</> : null}
      </p>

      {count > 0 ? (
        <p className="yz-receipt-meta yz-revcount">
          {count === 1 ? "1 recent revision" : `${count} recent revisions`}
          {history[0]?.message ? <> · latest: “{history[0].message}”</> : null}
        </p>
      ) : null}

      {result.path ? <code className="yz-path">{result.path}</code> : null}
    </div>
  );
}
