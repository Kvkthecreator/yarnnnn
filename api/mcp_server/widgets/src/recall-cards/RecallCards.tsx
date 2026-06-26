// The recall-cards widget (ADR-372). Renders the `recall` result's ranked
// excerpts as scannable cards — each with a provenance chip, timestamp, the
// excerpt text, and the source path. Renders RETURNED substrate only (D3); the
// host LLM still explains in its own voice.

import type { RecallChunk, RecallResult } from "./types";
import { provBucket, fmtWhen } from "../shared/provenance";

function Card({ chunk }: { chunk: RecallChunk }) {
  const bucket = provBucket(chunk.source_tag);
  return (
    <div className="yz-card">
      <div className="yz-card-head">
        <span className={`yz-chip ${bucket}`}>{chunk.source_tag || bucket}</span>
        {chunk.domain ? <span className="yz-chip">{chunk.domain}</span> : null}
        {chunk.last_updated ? <span className="yz-when">{fmtWhen(chunk.last_updated)}</span> : null}
      </div>
      {chunk.excerpt ? <p className="yz-excerpt">{chunk.excerpt}</p> : null}
      {chunk.path ? <code className="yz-path">{chunk.path}</code> : null}
    </div>
  );
}

export function RecallCards({ result }: { result: RecallResult | null }) {
  const chunks = result?.chunks ?? [];

  if (!result) {
    return <p className="yz-empty">Loading memory…</p>;
  }
  if (chunks.length === 0) {
    return <p className="yz-empty">{result.explanation || "YARNNN has nothing recorded on this yet."}</p>;
  }

  return (
    <div>
      {result.subject ? <p className="yz-subject">What YARNNN knows about “{result.subject}”</p> : null}
      <p className="yz-caption">
        {chunks.length} excerpt{chunks.length === 1 ? "" : "s"}
        {typeof result.total_matches === "number" && result.total_matches > chunks.length
          ? ` of ${result.total_matches} matches`
          : ""}
        , each attributed to its source.
      </p>
      <div className="yz-cards">
        {chunks.map((c, i) => (
          <Card key={c.path || i} chunk={c} />
        ))}
      </div>
    </div>
  );
}
