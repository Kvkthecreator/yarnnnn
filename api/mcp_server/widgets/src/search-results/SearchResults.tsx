// The search-results widget (ADR-372, renamed ADR-543). Renders the `search`
// result's ranked matches as scannable cards — each with a timestamp, the
// excerpt text, and the openable path. Renders RETURNED substrate only (D3);
// the host LLM still explains in its own voice.

import type { SearchMatch, SearchResult } from "./types";
import { fmtWhen } from "../shared/provenance";

// The honest-state signal, rendered (ADR-543 D2). `confidence` is ALWAYS present
// on a search result — the server computes it precisely so the reader can tell
// "use this" from "ask which one". Until now the widget dropped it and rendered
// `explanation` only on the empty path, so the ambiguous case — the one where
// the server explicitly says ASK — looked identical to a confident hit. The
// card is not deciding anything here: it renders the signal the server sent and
// the sentence the server wrote. The host still narrates (D3).
const CONFIDENCE_LABEL: Record<string, string> = {
  high: "Clear match",
  ambiguous: "Several matches — none dominant",
  weak: "Loose matches only",
  none: "No match",
};

function Confidence({ level }: { level?: string }) {
  if (!level) return null;
  const label = CONFIDENCE_LABEL[level];
  if (!label) return null; // an unknown level renders nothing, never a raw token
  return <span className={`yz-confidence yz-conf-${level}`}>{label}</span>;
}

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
        , each an openable path. <Confidence level={result.confidence} />
      </p>
      {/* The server writes this sentence on `ambiguous` and `weak` — the two
          states where taking the top hit is the wrong move. Dropping it (as
          this widget did) left the reader with a ranked list and no signal that
          ranking alone should not settle it. */}
      {result.explanation ? (
        <p className="yz-caption yz-explanation">{result.explanation}</p>
      ) : null}
      <div className="yz-cards">
        {results.map((m, i) => (
          <Card key={m.path || i} match={m} />
        ))}
      </div>
    </div>
  );
}
