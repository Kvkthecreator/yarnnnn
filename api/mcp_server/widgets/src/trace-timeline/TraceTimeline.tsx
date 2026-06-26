// The trace-timeline widget (ADR-372 §7). Renders the `trace` result's revision
// chain as a provenance-colored vertical timeline with click-to-expand inline
// diffs. It renders RETURNED substrate only — no synthesis (D3); the host LLM
// still narrates the evolution in prose.

import { useEffect, useState } from "react";
import type { TraceResult, TraceRevision } from "./types";
import { provBucket } from "./types";

// Debug fallback (ADR-372 live-debug): when no result arrives, after a short
// wait show what the iframe CAN see, so we diagnose the binding from ground
// truth instead of guessing. Renders window.openai's keys + any toolOutput/
// toolInput shape. Harmless in production — only appears when data is absent.
function DebugFallback() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const t = window.setTimeout(() => setShow(true), 1500);
    return () => window.clearTimeout(t);
  }, []);
  if (!show) return <p className="tt-empty">Waiting for trace data…</p>;
  let diag: Record<string, unknown> = {};
  try {
    const w = (window as unknown as { openai?: Record<string, unknown> }).openai;
    diag = {
      "window.openai present": !!w,
      "window.openai keys": w ? Object.keys(w) : [],
      "toolOutput type": w ? typeof w.toolOutput : "n/a",
      "toolOutput keys": w && w.toolOutput && typeof w.toolOutput === "object"
        ? Object.keys(w.toolOutput as object) : [],
      "toolInput keys": w && w.toolInput && typeof w.toolInput === "object"
        ? Object.keys(w.toolInput as object) : [],
    };
  } catch (e) {
    diag = { error: String(e) };
  }
  return (
    <div>
      <p className="tt-empty">No trace data reached the widget. Diagnostic (share this):</p>
      <pre className="tt-diff">{JSON.stringify(diag, null, 2)}</pre>
    </div>
  );
}

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
    return <DebugFallback />;
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
