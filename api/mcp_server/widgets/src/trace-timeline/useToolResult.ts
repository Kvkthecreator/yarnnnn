// Subscribe to the trace result the host provides. Mirrors OpenAI's reference
// reader (openai-apps-sdk-examples/src/use-openai-global.ts) because the live
// test found a real race: ChatGPT may set `window.openai.toolOutput` WITHOUT (or
// before) the widget's `openai:set_globals` listener catches it, so a read-once-
// at-mount widget sits forever on "Waiting for trace data…". The fix is three
// channels, any of which resolves it:
//
//   1. read window.openai.toolOutput at mount (already-present case);
//   2. subscribe to the `openai:set_globals` CustomEvent (the push case);
//   3. POLL window.openai.toolOutput every 250ms up to ~10s (the race case the
//      reference implementation relies on — this is what was missing).
//
// Also supports the open MCP Apps host path (`ui/notifications/tool-result`
// postMessage) so the same bundle renders on non-ChatGPT hosts.

import { useEffect, useState } from "react";
import type { TraceResult } from "./types";

declare global {
  interface Window {
    openai?: { toolOutput?: unknown };
  }
}

const SET_GLOBALS_EVENT = "openai:set_globals";

function coerce(value: unknown): TraceResult | null {
  if (!value || typeof value !== "object") return null;
  const v = value as Record<string, unknown>;
  // Hosts differ on whether toolOutput is the bare result dict or the full
  // CallToolResult (with structuredContent nested). Accept both: prefer a
  // nested structuredContent, else use the object directly. We recognize a
  // trace result by its `history` array (or the explicit empty `explanation`).
  if (v.structuredContent && typeof v.structuredContent === "object") {
    return v.structuredContent as TraceResult;
  }
  if ("history" in v || "explanation" in v || "subject" in v) {
    return v as TraceResult;
  }
  return null;
}

function readToolOutput(): TraceResult | null {
  try {
    return coerce(window.openai?.toolOutput);
  } catch {
    return null;
  }
}

export function useToolResult(): TraceResult | null {
  const [result, setResult] = useState<TraceResult | null>(() => readToolOutput());

  useEffect(() => {
    let settled = result != null;

    // 2. ChatGPT push: host globals changed.
    function onSetGlobals(event: Event) {
      const detail = (event as CustomEvent).detail;
      const next = coerce(detail?.globals?.toolOutput) ?? readToolOutput();
      if (next) {
        settled = true;
        setResult(next);
      }
    }
    // open MCP Apps host: tool-result notification over postMessage.
    function onMessage(event: MessageEvent) {
      const msg = event.data;
      if (msg && typeof msg === "object" && msg.method === "ui/notifications/tool-result" && msg.params) {
        const next = coerce(msg.params.structuredContent);
        if (next) {
          settled = true;
          setResult(next);
        }
      }
    }

    window.addEventListener(SET_GLOBALS_EVENT, onSetGlobals as EventListener, { passive: true } as AddEventListenerOptions);
    window.addEventListener("message", onMessage);

    // 3. Poll fallback for the at-mount race (the missing piece). Stops on first
    //    hit or after ~10s (40 × 250ms).
    let remaining = 40;
    const pollId = window.setInterval(() => {
      if (settled) {
        window.clearInterval(pollId);
        return;
      }
      const next = readToolOutput();
      if (next) {
        settled = true;
        window.clearInterval(pollId);
        setResult(next);
        return;
      }
      remaining -= 1;
      if (remaining <= 0) window.clearInterval(pollId);
    }, 250);

    return () => {
      window.removeEventListener(SET_GLOBALS_EVENT, onSetGlobals as EventListener);
      window.removeEventListener("message", onMessage);
      window.clearInterval(pollId);
    };
  }, []);

  return result;
}
