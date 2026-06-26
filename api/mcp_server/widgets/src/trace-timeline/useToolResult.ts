// Subscribe to the trace result the host pushes over the MCP Apps bridge.
//
// Standard contract (works on any MCP Apps host): the host posts a
// `ui/notifications/tool-result` JSON-RPC notification over postMessage; we read
// `params.structuredContent` (the full trace result dict). On ChatGPT the result
// is ALSO available synchronously via `window.openai.toolOutput` — we feature-
// detect that for first paint (graceful degradation, ADR-372 D2). Neither is
// required; whichever arrives first wins.

import { useEffect, useState } from "react";
import type { TraceResult } from "./types";

declare global {
  interface Window {
    openai?: { toolOutput?: unknown };
  }
}

export function useToolResult(): TraceResult | null {
  const [result, setResult] = useState<TraceResult | null>(() => {
    try {
      const seed = window.openai?.toolOutput;
      return seed && typeof seed === "object" ? (seed as TraceResult) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      const msg = event.data;
      if (!msg || typeof msg !== "object") return;
      if (msg.method === "ui/notifications/tool-result" && msg.params) {
        const sc = msg.params.structuredContent;
        if (sc && typeof sc === "object") setResult(sc as TraceResult);
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  return result;
}
