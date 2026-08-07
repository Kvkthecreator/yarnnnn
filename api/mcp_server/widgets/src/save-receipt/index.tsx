// Entry point for the save-receipt widget bundle (ADR-533 D4). Built by
// build.mjs → dist/save-receipt.html.

import { createRoot } from "react-dom/client";
import { SaveReceipt } from "./SaveReceipt";
import { isSaveResult, type SaveResult } from "./types";
import { useToolResult } from "../shared/useToolResult";
import { injectStyles } from "../shared/styles";

function App() {
  const result = useToolResult<SaveResult>(isSaveResult);
  return <SaveReceipt result={result} />;
}

injectStyles("yz-styles");
const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<App />);
}
