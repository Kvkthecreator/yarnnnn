// Entry point for the remember-receipt widget bundle (ADR-372). Built by
// build.mjs → dist/remember-receipt.html.

import { createRoot } from "react-dom/client";
import { RememberReceipt } from "./RememberReceipt";
import { isRememberResult, type RememberResult } from "./types";
import { useToolResult } from "../shared/useToolResult";
import { injectStyles } from "../shared/styles";

function App() {
  const result = useToolResult<RememberResult>(isRememberResult);
  return <RememberReceipt result={result} />;
}

injectStyles("yz-styles");
const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<App />);
}
