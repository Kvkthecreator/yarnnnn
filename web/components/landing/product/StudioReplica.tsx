"use client";

/**
 * StudioReplica — pixel-level replica of the shipped Studio workbench
 * (components/authoring/StudioSurface.tsx + PagedNavigator.tsx +
 * StudioToolbar.tsx) for marketing pages, with a staged loop:
 *
 *   you ask in the bound chat → Lisa replies → the canvas updates and the
 *   edit lands as a revision ("r7 · current").
 *
 * Faithful details: the toolbar breadcrumb ("Studio / investor-update")
 * with the grain-ordered verbs (New slide · Re-arrange · Insert); the
 * slide strip with position numbers, indigo selection ring and captions;
 * the right pane's Properties/Chat tabs with the bound lane.
 */

import { LayoutGrid, LayoutTemplate, Plus, PanelLeft } from "lucide-react";
import { ProductWindow } from "./ProductWindow";
import { useStagedLoop, reveal } from "./useStagedLoop";

const SLIDES = [
  { n: "1", caption: "Traction", active: true },
  { n: "2", caption: "Model", active: false },
  { n: "3", caption: "The ask", active: false },
];

export function StudioReplica({ className = "" }: { className?: string }) {
  const step = useStagedLoop(3, 2200);
  const updated = step >= 2;

  return (
    <ProductWindow title="Studio" className={className}>
      {/* Toolbar row — breadcrumb + the three verbs, grain-ordered */}
      <div className="flex items-center gap-2 border-b border-border px-2 py-1.5">
        <PanelLeft className="h-3.5 w-3.5 text-muted-foreground/60" />
        <span className="text-xs text-muted-foreground">Studio</span>
        <span className="text-xs text-muted-foreground/40">/</span>
        <span className="text-xs font-medium text-foreground">investor-update</span>
        <div className="ml-auto flex items-center gap-1">
          <span className="flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] text-foreground/70">
            <LayoutGrid className="h-3 w-3" /> New slide <Plus className="h-2.5 w-2.5" />
          </span>
          <span className="hidden md:flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] text-foreground/70">
            <LayoutTemplate className="h-3 w-3" /> Re-arrange
          </span>
          <span className="flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] text-foreground/70">
            <Plus className="h-3 w-3" /> Insert
          </span>
        </div>
      </div>

      <div className="flex h-[300px]">
        {/* Slide strip — position number · thumbnail · caption */}
        <div className="hidden sm:flex w-[92px] shrink-0 flex-col gap-2 border-r border-border p-2">
          <span className="text-[9px] font-medium uppercase tracking-wide text-muted-foreground">
            Slides
          </span>
          {SLIDES.map((s) => (
            <div key={s.n} className="flex items-stretch gap-1">
              <span className="w-3 pt-1 text-right text-[9px] font-medium leading-none text-muted-foreground">
                {s.n}
              </span>
              <div className="min-w-0 flex-1">
                <div
                  className={`aspect-video rounded-sm border bg-white p-1 ${
                    s.active
                      ? "border-indigo-400 ring-1 ring-indigo-400"
                      : "border-border/60"
                  }`}
                >
                  <div className="h-1 w-2/3 rounded-sm bg-foreground/15" />
                  <div className="mt-0.5 h-0.5 w-1/2 rounded-sm bg-foreground/[0.07]" />
                </div>
                <p className="mt-0.5 truncate text-[9px] text-muted-foreground">{s.caption}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Canvas — the live slide */}
        <div className="flex min-w-0 flex-1 items-center justify-center bg-muted/20 p-4">
          <div className="aspect-video w-full max-w-[280px] rounded border border-border bg-white p-4 shadow-sm">
            <p className="text-sm font-semibold text-foreground">Traction</p>
            <p
              className={`mt-0.5 text-[11px] transition-colors duration-500 ${
                updated ? "text-foreground/80" : "text-muted-foreground"
              }`}
            >
              {updated ? "3× retention vs. baseline" : "2.4× retention vs. baseline"}
            </p>
            <div className="mt-3 flex items-end gap-1.5" aria-hidden="true">
              {[10, 16, updated ? 30 : 22].map((h, i) => (
                <div
                  key={i}
                  className={`w-6 rounded-sm transition-all duration-700 ${
                    i === 2 && updated ? "bg-indigo-400/70" : "bg-foreground/15"
                  }`}
                  style={{ height: h }}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Right pane — Properties / Chat tabs + the bound lane */}
        <div className="hidden md:flex w-[168px] shrink-0 flex-col border-l border-border">
          <div className="flex border-b border-border">
            <span className="flex-1 py-1.5 text-center text-[11px] font-medium text-muted-foreground">
              Properties
            </span>
            <span className="flex-1 border-b-2 border-foreground py-1.5 text-center text-[11px] font-medium text-foreground">
              Chat
            </span>
          </div>
          <div className="flex-1 space-y-2 p-2">
            <div className="flex justify-end">
              <p className="max-w-[90%] rounded-lg bg-primary px-2 py-1.5 text-[10px] leading-relaxed text-primary-foreground">
                Lead this slide with the strongest number.
              </p>
            </div>
            <div className={reveal(step >= 1)}>
              <p className="max-w-[90%] rounded-lg bg-muted px-2 py-1.5 text-[10px] leading-relaxed text-foreground">
                Done — pulled &ldquo;3× retention&rdquo; from your metrics file.
              </p>
            </div>
            <p className={`font-mono text-[9px] text-muted-foreground ${reveal(updated)}`}>
              r7{" "}
              <span className="rounded border border-primary/30 bg-primary/10 px-1 py-px text-primary">
                current
              </span>{" "}
              · saved as a revision
            </p>
          </div>
        </div>
      </div>
    </ProductWindow>
  );
}
