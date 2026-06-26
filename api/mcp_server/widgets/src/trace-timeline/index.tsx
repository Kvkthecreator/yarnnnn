// Entry point for the trace-timeline widget bundle (ADR-372 §7).
// Mounts the React component, subscribes to the host's tool-result bridge, and
// injects the inline stylesheet. Built by build.mjs → dist/trace-timeline.html.

import { createRoot } from "react-dom/client";
import { TraceTimeline } from "./TraceTimeline";
import { useToolResult } from "./useToolResult";
import { injectStyles } from "./styles";

function App() {
  const result = useToolResult();
  return <TraceTimeline result={result} />;
}

injectStyles();
const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<App />);
}
