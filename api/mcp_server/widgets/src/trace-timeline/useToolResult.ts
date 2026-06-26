// Subscribe to the trace result the host provides. Two paths, both supported:
//
//   1. ChatGPT (skybridge): the result is on `window.openai.toolOutput`, and the
//      host fires an `openai:set_globals` CustomEvent when it changes. This is
//      the PRIMARY path on ChatGPT (verified against OpenAI's Apps SDK docs) —
//      the generic bridge notification below does not fire there.
//   2. Open MCP Apps hosts: a `ui/notifications/tool-result` JSON-RPC message
//      over postMessage carries `params.structuredContent`.
//
// We read `window.openai.toolOutput` at mount (first paint) AND subscribe to
// both update channels, so whichever the host uses, the timeline renders.

import { useEffect, useState } from "react";
import type { TraceResult } from "./types";

declare global {
  interface Window {
    openai?: { toolOutput?: unknown };
  }
}

function coerce(value: unknown): TraceResult | null {
  return value && typeof value === "object" ? (value as TraceResult) : null;
}

export function useToolResult(): TraceResult | null {
  const [result, setResult] = useState<TraceResult | null>(() => {
    try {
      return coerce(window.openai?.toolOutput);
    } catch {
      return null;
    }
  });

  useEffect(() => {
    // ChatGPT skybridge: host state changed.
    function onSetGlobals(event: Event) {
      const detail = (event as CustomEvent).detail;
      const next = coerce(detail?.globals?.toolOutput) ?? coerce(window.openai?.toolOutput);
      if (next) setResult(next);
    }
    // Open MCP Apps host: tool-result notification over postMessage.
    function onMessage(event: MessageEvent) {
      const msg = event.data;
      if (msg && typeof msg === "object" && msg.method === "ui/notifications/tool-result" && msg.params) {
        const next = coerce(msg.params.structuredContent);
        if (next) setResult(next);
      }
    }
    window.addEventListener("openai:set_globals", onSetGlobals as EventListener, { passive: true } as AddEventListenerOptions);
    window.addEventListener("message", onMessage);
    return () => {
      window.removeEventListener("openai:set_globals", onSetGlobals as EventListener);
      window.removeEventListener("message", onMessage);
    };
  }, []);

  return result;
}
