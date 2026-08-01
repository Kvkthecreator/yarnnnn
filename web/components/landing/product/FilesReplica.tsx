"use client";

/**
 * FilesReplica — pixel-level replica of the shipped Files surface
 * (app/(authenticated)/files + components/workspace/FileListView.tsx +
 * RevisionHistoryPanel.tsx) for marketing pages, with a staged loop:
 *
 *   a connected AI writes in → the new row lands at the top of the list,
 *   signed "● ChatGPT (via MCP)" → the revision count ticks up.
 *
 * Faithful details: the tree rail with Recents/Trash + the Intent-first
 * sections (Identity · Context · Reports · Uploads); the Finder columns
 * (Name · Author · When, uppercase text-[11px] headers); accent-dot +
 * RESOLVED attribution labels; the revision panel's r{N} grammar with the
 * "current" pill and revert/diff affordances.
 */

import {
  Folder,
  FolderPlus,
  Upload,
  History,
  Trash2,
  FileText,
  Undo2,
  GitCompare,
} from "lucide-react";
import { ProductWindow } from "./ProductWindow";
import { useStagedLoop, reveal } from "./useStagedLoop";

const BASE_ROWS = [
  { name: "positioning-memo.md", author: "You", dot: "bg-blue-500", when: "2h" },
  { name: "competitor-scan.md", author: "Claude (via MCP)", dot: "bg-amber-400", when: "2d" },
  { name: "launch-plan.md", author: "Mara", dot: "bg-teal-500", when: "5d" },
];

const TREE = ["Identity", "Context", "Reports", "Uploads"];

export function FilesReplica({ className = "" }: { className?: string }) {
  const step = useStagedLoop(3, 2400);
  const landed = step >= 1;

  return (
    <ProductWindow title="Files" className={className}>
      <div className="flex h-[340px]">
        {/* Tree rail */}
        <div className="hidden sm:flex w-36 shrink-0 flex-col border-r border-border p-2">
          <div className="mb-1.5 flex items-center gap-2 px-1">
            <FolderPlus className="h-3.5 w-3.5 text-muted-foreground/70" />
            <Upload className="h-3.5 w-3.5 text-muted-foreground/70" />
          </div>
          <span className="flex items-center gap-1.5 rounded-md bg-muted px-2 py-1 text-xs font-medium text-foreground">
            <History className="h-3 w-3" /> Recents
          </span>
          <span className="flex items-center gap-1.5 px-2 py-1 text-xs text-muted-foreground">
            <Trash2 className="h-3 w-3" /> Trash
          </span>
          <div className="my-1.5 border-t border-border/60" />
          {TREE.map((t) => (
            <span
              key={t}
              className={`flex items-center gap-1.5 px-2 py-1 text-xs ${
                t === "Context" ? "font-medium text-foreground" : "text-muted-foreground"
              }`}
            >
              <Folder className="h-3 w-3 text-sky-600" /> {t}
            </span>
          ))}
        </div>

        {/* List + revision panel */}
        <div className="flex min-w-0 flex-1 flex-col">
          {/* Column headers */}
          <div className="grid grid-cols-[minmax(0,1fr)_auto_44px] gap-3 border-b border-border px-3 py-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            <span>Name</span>
            <span>Author</span>
            <span className="text-right">When</span>
          </div>

          {/* The landing MCP row */}
          <div
            className={`grid grid-cols-[minmax(0,1fr)_auto_44px] items-center gap-3 border-b border-border/50 bg-amber-50/40 px-3 py-2 transition-all duration-500 ${
              landed ? "opacity-100 max-h-10" : "opacity-0 max-h-0 overflow-hidden py-0 border-b-0"
            }`}
          >
            <span className="flex min-w-0 items-center gap-1.5">
              <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
              <span className="truncate font-mono text-xs text-foreground/80">
                q3-pricing-note.md
              </span>
            </span>
            <span className="flex items-center gap-1.5 text-[10px] font-medium text-foreground/70">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              ChatGPT (via MCP)
            </span>
            <span className="text-right font-mono text-[10px] text-muted-foreground/70">now</span>
          </div>

          {BASE_ROWS.map((r) => (
            <div
              key={r.name}
              className="grid grid-cols-[minmax(0,1fr)_auto_44px] items-center gap-3 border-b border-border/50 px-3 py-2"
            >
              <span className="flex min-w-0 items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
                <span className="truncate font-mono text-xs text-foreground/80">{r.name}</span>
              </span>
              <span className="flex items-center gap-1.5 text-[10px] font-medium text-foreground/70">
                <span className={`h-1.5 w-1.5 rounded-full ${r.dot}`} />
                {r.author}
              </span>
              <span className="text-right font-mono text-[10px] text-muted-foreground/70">
                {r.when}
              </span>
            </div>
          ))}

          {/* Revision history — the product's exact grammar */}
          <div className="m-3 mt-auto rounded-lg border border-border">
            <div className="flex items-center gap-1.5 border-b border-border/60 px-2.5 py-1.5">
              <History className="h-3 w-3 text-muted-foreground/70" />
              <span className="text-[11px] font-medium text-foreground/80">
                Revision history{" "}
                <span className="text-muted-foreground">({landed ? "12" : "11"})</span>
              </span>
              <span className="ml-auto text-[10px] text-muted-foreground/60">hide</span>
            </div>
            <div className={`flex items-center gap-2 px-2.5 py-1.5 ${reveal(step >= 2)}`}>
              <span className="font-mono text-[10px] text-muted-foreground">r12</span>
              <span className="inline-flex items-center gap-1 rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[9px] text-amber-700">
                ChatGPT (via MCP)
              </span>
              <span className="truncate text-[10px] text-foreground/80">
                Added the Q3 numbers
              </span>
              <span className="ml-auto rounded border border-primary/30 bg-primary/10 px-1.5 py-0.5 text-[9px] text-primary">
                current
              </span>
            </div>
            <div className="flex items-center gap-2 px-2.5 py-1.5 pt-0">
              <span className="font-mono text-[10px] text-muted-foreground">r11</span>
              <span className="inline-flex items-center gap-1 rounded border border-blue-200 bg-blue-50 px-1.5 py-0.5 text-[9px] text-blue-700">
                You
              </span>
              <span className="truncate text-[10px] text-foreground/80">
                Tightened the pricing section
              </span>
              <span className="ml-auto flex items-center gap-2 text-muted-foreground/50">
                <Undo2 className="h-3 w-3" />
                <GitCompare className="h-3 w-3" />
              </span>
            </div>
          </div>
        </div>
      </div>
    </ProductWindow>
  );
}
