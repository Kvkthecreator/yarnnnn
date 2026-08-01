"use client";

/**
 * ChatReplica — pixel-level replica of the shipped Chat surface
 * (components/chat-surface/ChatSurface.tsx + LanePanel.tsx) for marketing
 * pages, with a staged animation loop:
 *
 *   you ask → "Lisa is working… · EditFile" → the grounded reply →
 *   the ArtifactCard (the reply landing as a real file).
 *
 * Faithful details: w-72-proportioned navigator rail with "Search chats…"
 * and identity-first lane rows (name leads, "Critic · GPT-5" rides behind);
 * Messenger-shaped conversation header; bg-primary user bubble right /
 * bg-muted assistant bubble left at max-w-[85%]; the tool footer hairline;
 * the "Message Lisa…" composer with the bg-primary ArrowUp send.
 */

import { Search, Plus, Paperclip, ArrowUp, Wrench, Loader2 } from "lucide-react";
import { ProductWindow, FaceCircle } from "./ProductWindow";
import { useStagedLoop, reveal } from "./useStagedLoop";

const LANES = [
  { initial: "L", name: "Lisa", sub: "Critic · GPT-5", when: "now", tone: "indigo" as const, active: true },
  { initial: "T", name: "Thinker", sub: "GPT-5", when: "1d", tone: "muted" as const, active: false },
  { initial: "M", name: "Mara", sub: "Direct chat", when: "3d", tone: "teal" as const, active: false },
];

export function ChatReplica({ className = "" }: { className?: string }) {
  const step = useStagedLoop(4);

  return (
    <ProductWindow title="Chat" className={className}>
      <div className="flex h-[340px]">
        {/* Navigator rail */}
        <div className="hidden sm:flex w-44 shrink-0 flex-col border-r border-border">
          <div className="flex items-center justify-between px-3 pt-2.5 pb-1.5">
            <span className="text-sm font-medium text-foreground">Chat</span>
            <Plus className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <div className="mx-2 mb-1.5 flex items-center gap-1.5 rounded-md border border-border px-2 py-1">
            <Search className="h-3 w-3 text-muted-foreground/60" />
            <span className="text-[11px] text-muted-foreground/60">Search chats…</span>
          </div>
          {LANES.map((l) => (
            <div
              key={l.name}
              className={`flex items-start gap-2.5 border-b border-border/50 px-3 py-2.5 ${
                l.active ? "bg-muted" : ""
              }`}
            >
              <FaceCircle initial={l.initial} tone={l.tone} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground leading-tight">
                  {l.name}
                </p>
                <p className="truncate text-[10px] text-muted-foreground/70 leading-tight mt-0.5">
                  {l.sub} <span className="text-muted-foreground/50">· {l.when}</span>
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Conversation pane */}
        <div className="flex min-w-0 flex-1 flex-col">
          {/* Header — identity leads, the spec rides behind */}
          <div className="flex items-center gap-2.5 border-b border-border px-3 py-2">
            <FaceCircle initial="L" tone="indigo" />
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground leading-tight">Lisa</p>
              <p className="text-[10px] text-muted-foreground leading-tight">Critic · GPT-5</p>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 space-y-2.5 overflow-hidden px-3 py-3">
            {/* You */}
            <div className={`flex justify-end ${reveal(step >= 0)}`}>
              <p className="max-w-[85%] rounded-lg bg-primary px-3 py-2 text-[12px] leading-relaxed text-primary-foreground">
                Does the pricing section still hold up against our latest numbers?
              </p>
            </div>

            {/* Working indicator (only during step 1) */}
            <div
              className={`flex items-center gap-1.5 transition-opacity duration-300 ${
                step === 1 ? "opacity-100" : "opacity-0"
              } ${step > 1 ? "hidden" : ""}`}
            >
              <Loader2 className="h-3 w-3 animate-spin text-muted-foreground/60" />
              <span className="text-[11px] text-muted-foreground/70">
                Lisa · ReadFile · EditFile…
              </span>
            </div>

            {/* Reply + tool footer */}
            <div className={reveal(step >= 2)}>
              <div className="max-w-[85%] rounded-lg bg-muted px-3 py-2">
                <p className="text-[12px] leading-relaxed text-foreground">
                  The retention claim was stale — your metrics file says 3×, not 2.4×.
                  I tightened the section and saved it.
                </p>
                <div className="mt-1.5 flex items-center gap-1 border-t border-border/60 pt-1">
                  <Wrench className="h-2.5 w-2.5 text-muted-foreground/60" />
                  <span className="text-[10px] text-muted-foreground">EditFile</span>
                </div>
              </div>
            </div>

            {/* ArtifactCard — the reply landing as a real file */}
            <div className={reveal(step >= 3)}>
              <div className="max-w-[85%] overflow-hidden rounded-xl border border-border bg-background">
                <div className="flex items-center gap-2 border-b border-border bg-muted/20 px-3 py-2">
                  <span className="truncate text-xs font-medium text-foreground">
                    positioning-memo.md
                  </span>
                  <span className="text-[10px] text-muted-foreground/70">revised · context/</span>
                  <span className="ml-auto rounded-md border border-border px-2 py-0.5 text-[10px] font-medium text-foreground/70">
                    Open
                  </span>
                </div>
                <div className="space-y-1 px-3 py-2">
                  <div className="h-1.5 w-3/4 rounded-sm bg-muted" />
                  <div className="h-1.5 w-1/2 rounded-sm bg-muted" />
                </div>
              </div>
            </div>
          </div>

          {/* Composer */}
          <div className="flex items-end gap-2 border-t border-border px-3 py-2">
            <Paperclip className="mb-1 h-3.5 w-3.5 text-muted-foreground/70" />
            <div className="min-h-[30px] flex-1 rounded-md border border-border px-2.5 py-1.5">
              <span className="text-[12px] text-muted-foreground/50">Message Lisa…</span>
            </div>
            <span className="mb-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-primary">
              <ArrowUp className="h-3 w-3 text-primary-foreground" />
            </span>
          </div>
        </div>
      </div>
    </ProductWindow>
  );
}
