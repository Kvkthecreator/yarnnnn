'use client';

/**
 * BlockThumb — the schematic block-kind thumbnail (ADR-586 D3).
 *
 * The insert door's galleries are drawn schematics — the PowerPoint SmartArt
 * approach the operator locked: crisp at 64px, instant, no live render and no
 * iframes inside a menu (live mini-renders are deliberately refused for v1).
 * The `ArrangementThumb` idiom, per kind: small structural drawings keyed by
 * the served kind name. An unknown kind (a future registry row, a library
 * component) falls back to a generic composed schematic rather than a hole —
 * so a new kind ships with a legible cell before anyone draws its glyph.
 */

const BAR = 'rounded-[1px] bg-foreground/35';
const SOFT = 'rounded-[1px] bg-muted-foreground/25';
const TINT = 'rounded-[1px] bg-indigo-400/40';

function Frame({ children }: { children: React.ReactNode }) {
  return (
    <div
      aria-hidden
      className="flex aspect-[16/10] w-full flex-col justify-center gap-0.5 overflow-hidden rounded-sm border border-border bg-background p-1.5"
    >
      {children}
    </div>
  );
}

/** One schematic per kernel kind. Each is a few positioned bars — the shape,
 *  never the content. */
export function BlockThumb({ kind }: { kind: string }) {
  switch (kind) {
    case 'heading':
      return (
        <Frame>
          <div className={`${BAR} h-2 w-4/5`} />
          <div className={`${SOFT} mt-0.5 h-1 w-3/5`} />
        </Frame>
      );
    case 'prose':
      return (
        <Frame>
          <div className={`${SOFT} h-1 w-full`} />
          <div className={`${SOFT} h-1 w-full`} />
          <div className={`${SOFT} h-1 w-2/3`} />
        </Frame>
      );
    case 'quote':
      return (
        <Frame>
          <div className="flex gap-1">
            <div className={`${BAR} h-6 w-0.5`} />
            <div className="flex flex-1 flex-col justify-center gap-0.5">
              <div className={`${SOFT} h-1 w-full`} />
              <div className={`${SOFT} h-1 w-4/5`} />
            </div>
          </div>
        </Frame>
      );
    case 'callout':
      return (
        <Frame>
          <div className="flex flex-1 items-center gap-1 rounded-sm bg-amber-400/15 p-1">
            <div className={`${BAR} h-full w-0.5`} />
            <div className={`${SOFT} h-1 flex-1`} />
          </div>
        </Frame>
      );
    case 'list':
    case 'checklist':
    case 'numbered':
      return (
        <Frame>
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex items-center gap-1">
              {kind === 'checklist' ? (
                <div className="h-1.5 w-1.5 rounded-[1px] border border-foreground/40" />
              ) : (
                <div className={`${BAR} h-1 w-1 ${kind === 'list' ? 'rounded-full' : ''}`} />
              )}
              <div className={`${SOFT} h-1 flex-1`} />
            </div>
          ))}
        </Frame>
      );
    case 'toggle':
      return (
        <Frame>
          <div className="flex items-center gap-1">
            <div className="h-0 w-0 border-y-[3px] border-l-4 border-y-transparent border-l-foreground/40" />
            <div className={`${BAR} h-1 flex-1`} />
          </div>
          <div className={`${SOFT} ml-2 h-1 w-3/4`} />
        </Frame>
      );
    case 'divider':
      return (
        <Frame>
          <div className={`${SOFT} h-px w-full`} />
        </Frame>
      );
    case 'button':
      return (
        <Frame>
          <div className="mx-auto h-3 w-3/5 rounded-full bg-foreground/35" />
        </Frame>
      );
    case 'metrics':
      return (
        <Frame>
          <div className="flex justify-around">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex flex-col items-center gap-0.5">
                <div className={`${BAR} h-2.5 w-3`} />
                <div className={`${SOFT} h-0.5 w-4`} />
              </div>
            ))}
          </div>
        </Frame>
      );
    case 'stat':
      return (
        <Frame>
          <div className={`${BAR} h-4 w-2/5`} />
          <div className={`${SOFT} h-1 w-1/3`} />
          <div className={`${TINT} h-1 w-1/4`} />
        </Frame>
      );
    case 'comparison':
      return (
        <Frame>
          <div className="flex flex-1 gap-1">
            {[0, 1].map((i) => (
              <div key={i} className="flex flex-1 flex-col gap-0.5 rounded-sm border border-border p-1">
                <div className={`${BAR} h-1 w-2/3`} />
                <div className={`${SOFT} h-0.5 w-full`} />
                <div className={`${SOFT} h-0.5 w-4/5`} />
              </div>
            ))}
          </div>
        </Frame>
      );
    case 'timeline':
      return (
        <Frame>
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex items-center gap-1">
              <div className="h-1.5 w-1.5 rounded-full bg-indigo-400/60" />
              <div className={`${SOFT} h-1`} style={{ width: `${70 - i * 15}%` }} />
            </div>
          ))}
        </Frame>
      );
    case 'person':
      return (
        <Frame>
          <div className="flex items-center gap-1.5">
            <div className="h-4 w-4 rounded-full bg-indigo-400/40" />
            <div className="flex flex-col gap-0.5">
              <div className={`${BAR} h-1 w-8`} />
              <div className={`${SOFT} h-0.5 w-6`} />
            </div>
          </div>
        </Frame>
      );
    case 'figure':
      return (
        <Frame>
          <div className={`${TINT} flex-1`} />
          <div className={`${SOFT} h-0.5 w-1/2`} />
        </Frame>
      );
    case 'gallery':
      return (
        <Frame>
          <div className="grid flex-1 grid-cols-3 gap-0.5">
            {[0, 1, 2].map((i) => (
              <div key={i} className={`${TINT}`} />
            ))}
          </div>
        </Frame>
      );
    case 'logo-row':
      return (
        <Frame>
          <div className="flex items-center justify-around">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className={`${TINT} h-2 w-3`} />
            ))}
          </div>
        </Frame>
      );
    case 'table':
      return (
        <Frame>
          <div className="grid flex-1 grid-cols-3 gap-px overflow-hidden rounded-[1px] bg-border p-px">
            {[...Array(9)].map((_, i) => (
              <div key={i} className={i < 3 ? 'bg-foreground/20' : 'bg-background'} />
            ))}
          </div>
        </Frame>
      );
    case 'chart':
      return (
        <Frame>
          <div className="flex flex-1 items-end justify-around gap-0.5">
            {[40, 75, 55, 90].map((h, i) => (
              <div key={i} className="w-2 rounded-t-[1px] bg-indigo-400/50" style={{ height: `${h}%` }} />
            ))}
          </div>
        </Frame>
      );
    case 'component':
    default:
      // The composite card — ALSO the fallback for unknown kinds and the
      // library's generic cell (a component file has no drawn glyph yet).
      return (
        <Frame>
          <div className="flex flex-1 flex-col gap-0.5 rounded-sm border border-border p-1">
            <div className={`${SOFT} h-0.5 w-1/3`} />
            <div className="flex items-center gap-1">
              <div className={`${TINT} h-2 w-2 rounded-[2px]`} />
              <div className={`${BAR} h-1 flex-1`} />
            </div>
          </div>
        </Frame>
      );
  }
}
