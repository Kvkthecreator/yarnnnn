// The search-results widget (ADR-372, renamed ADR-543). Renders the `search`
// result's ranked matches as scannable cards — each with a timestamp, the
// excerpt text, and the openable path. Renders RETURNED substrate only (D3);
// the host LLM still explains in its own voice.

import type { SearchMatch, SearchResult } from "./types";
import { fmtWhen } from "../shared/provenance";

function Card({ match }: { match: SearchMatch }) {
  return (
    <div className="yz-card">
      <div className="yz-card-head">
        {match.last_updated ? <span className="yz-when">{fmtWhen(match.last_updated)}</span> : null}
      </div>
      {match.excerpt ? <p className="yz-excerpt">{match.excerpt}</p> : null}
      {match.path ? <code className="yz-path">{match.path}</code> : null}
    </div>
  );
}

export function SearchResults({ result }: { result: SearchResult | null }) {
  const results = result?.results ?? [];

  if (!result) {
    return <p className="yz-empty">Searching the workspace…</p>;
  }
  if (results.length === 0) {
    return <p className="yz-empty">{result.explanation || "No file in the workspace matches this yet."}</p>;
  }

  return (
    <div>
      {result.query ? <p className="yz-subject">Files matching “{result.query}”</p> : null}
      <p className="yz-caption">
        {results.length} match{results.length === 1 ? "" : "es"}
        {typeof result.total_matches === "number" && result.total_matches > results.length
          ? ` of ${result.total_matches}`
          : ""}
        , each an openable path.
      </p>
      <div className="yz-cards">
        {results.map((m, i) => (
          <Card key={m.path || i} match={m} />
        ))}
      </div>
    </div>
  );
}
