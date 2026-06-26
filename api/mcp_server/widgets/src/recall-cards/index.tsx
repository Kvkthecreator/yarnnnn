// Entry point for the recall-cards widget bundle (ADR-372). Built by build.mjs
// → dist/recall-cards.html.

import { createRoot } from "react-dom/client";
import { RecallCards } from "./RecallCards";
import { isRecallResult, type RecallResult } from "./types";
import { useToolResult } from "../shared/useToolResult";
import { injectStyles } from "../shared/styles";

function App() {
  const result = useToolResult<RecallResult>(isRecallResult);
  return <RecallCards result={result} />;
}

injectStyles("yz-styles");
const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<App />);
}
