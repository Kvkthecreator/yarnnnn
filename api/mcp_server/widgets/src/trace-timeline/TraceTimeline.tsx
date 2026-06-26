// The trace-timeline widget (ADR-372 §7). Renders the `trace` result's revision
// chain as a provenance-colored vertical timeline with click-to-expand inline
// diffs. It renders RETURNED substrate only — no synthesis (D3); the host LLM
// still narrates the evolution in prose.

import { useState } from "react";
import type { TraceResult, TraceRevision } from "./types";
import { provBucket } from "./types";

function fmtWhen(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function DiffBlock({ diff }: { diff: string }) {
  // Colorize unified-diff lines. Pure presentation of the server-computed diff.
  const lines = diff.split("\n");
  return (
    <pre className="tt-diff">
      {lines.map((line, i) => {
        let cls = "";
        if (line.startsWith("+") && !line.startsWith("+++")) cls = "add";
        else if (line.startsWith("-") && !line.startsWith("---")) cls = "del";
        else if (line.startsWith("@@") || line.startsWith("+++") || line.startsWith("---")) cls = "meta";
        return (
          <div key={i} className={cls}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}

function RevisionNode({ rev }: { rev: TraceRevision }) {
  const [open, setOpen] = useState(false);
  const bucket = provBucket(rev.authored_by);
  const hasDiff = typeof rev.diff === "string" && rev.diff.trim().length > 0;
  return (
    <li className={`tt-rev ${bucket}`}>
      <div className="tt-head">
        <span className="tt-who">{rev.authored_by || "unknown"}</span>
        <span className="tt-badge">{bucket}</span>
        <span className="tt-when">{fmtWhen(rev.when)}</span>
      </div>
      {rev.change ? <p className="tt-change">{rev.change}</p> : null}
      {hasDiff ? (
        <>
          <button className="tt-difftoggle" onClick={() => setOpen((v) => !v)}>
            {open ? "hide changes" : "show changes"}
          </button>
          {open ? <DiffBlock diff={rev.diff as string} /> : null}
        </>
      ) : null}
    </li>
  );
}

export function TraceTimeline({ result }: { result: TraceResult | null }) {
  const history = result?.history ?? [];

  if (!result) {
    return <p className="tt-empty">Waiting for trace data…</p>;
  }
  if (history.length === 0) {
    return <p className="tt-empty">{result.explanation || "No recorded history to trace."}</p>;
  }

  return (
    <div>
      {result.subject ? <p className="tt-subject">{result.subject}</p> : null}
      {result.explanation ? <p className="tt-caption">{result.explanation}</p> : null}
      <ol className="tt-timeline">
        {history.map((rev, i) => (
          <RevisionNode key={rev.revision_id || i} rev={rev} />
        ))}
      </ol>
    </div>
  );
}
