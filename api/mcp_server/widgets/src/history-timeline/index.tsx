// Entry point for the history-timeline widget bundle (ADR-372 §7, renamed
// ADR-543). Mounts the React component, subscribes to the host's tool-result
// bridge, and injects the inline stylesheet. Built by build.mjs →
// dist/history-timeline.html.

import { createRoot } from "react-dom/client";
import { HistoryTimeline } from "./HistoryTimeline";
import { useToolResult } from "./useToolResult";
import { injectStyles } from "./styles";

function App() {
  const result = useToolResult();
  return <HistoryTimeline result={result} />;
}

injectStyles();
const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<App />);
}
