"use client";

/**
 * ConnectReplica — the connect-your-AI moment for marketing pages:
 * attach a connector, and the first foreign write lands in the workspace
 * ledger, signed.
 *
 * The ledger row mirrors the shipped ActivityLedger sentence grammar
 * ("{who} updated {basename}") and the resolved attribution label
 * ("ChatGPT (via MCP)", amber accent) — never raw substrate strings.
 *
 * 2026-09-18: the chips named Gemini as an attachable connector. Step 04's
 * PROSE was corrected on 2026-09-18 for exactly this reason — Gemini has no
 * MCP connector, and the docs have always said "ChatGPT, Claude, or any
 * MCP-capable client" — but the replica beside that paragraph was not. The
 * third chip now carries the open-ended claim the prose makes, not a vendor
 * name we cannot honour.
 */

import { Check, FileText } from "lucide-react";
import { ProductWindow } from "./ProductWindow";
import { useStagedLoop, reveal } from "./useStagedLoop";

const CONNECTORS = ["ChatGPT", "Claude", "Any MCP client"];

export function ConnectReplica({ className = "" }: { className?: string }) {
  const step = useStagedLoop(3, 2000);
  const connected = step >= 1;

  return (
    <ProductWindow title="Connections" className={className}>
      <div className="space-y-4 p-4">
        {/* Connector chips — ChatGPT flips to Connected */}
        <div className="flex flex-wrap items-center gap-2">
          {CONNECTORS.map((c) => {
            const isLive = c === "ChatGPT" && connected;
            return (
              <span
                key={c}
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors duration-500 ${
                  isLive
                    ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                    : "border-border bg-background text-foreground/70"
                }`}
              >
                {c}
                {isLive && <Check className="h-3 w-3" />}
              </span>
            );
          })}
          <span className="text-[10px] text-muted-foreground/60">· nothing else to set up</span>
        </div>

        {/* The first foreign write, in the ledger's sentence grammar */}
        <div className={reveal(step >= 2)}>
          <div className="flex items-center gap-2.5 rounded-lg border border-border bg-background px-3 py-2.5">
            <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs text-foreground">
                <span className="font-medium">ChatGPT</span> updated{" "}
                <span className="font-mono">q3-pricing-note.md</span>
              </p>
              <p className="mt-0.5 flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                ChatGPT (via MCP) · just now
              </p>
            </div>
            <span className="rounded-md border border-border px-2 py-0.5 text-[10px] font-medium text-foreground/70">
              Open
            </span>
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground/70">
            The first thing you see is a write you didn&apos;t make — signed by something
            that isn&apos;t you.
          </p>
        </div>
      </div>
    </ProductWindow>
  );
}
