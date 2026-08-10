// Entry point for the search-results widget bundle (ADR-372, renamed ADR-543).
// Built by build.mjs → dist/search-results.html.

import { createRoot } from "react-dom/client";
import { SearchResults } from "./SearchResults";
import { isSearchResult, type SearchResult } from "./types";
import { useToolResult } from "../shared/useToolResult";
import { injectStyles } from "../shared/styles";

function App() {
  const result = useToolResult<SearchResult>(isSearchResult);
  return <SearchResults result={result} />;
}

injectStyles("yz-styles");
const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<App />);
}
