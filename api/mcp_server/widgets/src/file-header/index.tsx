// Entry point for the file-header widget bundle (ADR-533 D4). Built by
// build.mjs → dist/file-header.html.

import { createRoot } from "react-dom/client";
import { FileHeader } from "./FileHeader";
import { isOpenResult, type OpenResult } from "./types";
import { useToolResult } from "../shared/useToolResult";
import { injectStyles } from "../shared/styles";

function App() {
  const result = useToolResult<OpenResult>(isOpenResult);
  return <FileHeader result={result} />;
}

injectStyles("yz-styles");
const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<App />);
}
