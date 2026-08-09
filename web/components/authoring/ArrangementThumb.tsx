'use client';

/**
 * ArrangementThumb — the derived wireframe thumbnail (ADR-447 D7.1, landed by
 * ADR-453). A small structural render of an arrangement's slot shape — a
 * heading bar when the fragment carries heading blocks, one column per flow
 * slot, media slots tinted — DERIVED from the registry row, never a
 * hand-drawn asset, so adding an arrangement stays one registry row and its
 * thumbnail comes free (grammar not schema, R4).
 */

interface ArrangementThumbProps {
  slots: Array<{ name: string; role: string }>;
  fragment: string;
}

/** Does this slot's COLUMN carry its own heading? `comparison` seeds an <h3>
 *  per column ("Option A" / "Option B") where `two-column` seeds none — the one
 *  structural fact separating two rows the wireframe otherwise draws
 *  identically (the operator's report: the thumbnails look the same).
 *
 *  The heading is a SIBLING of the slot inside `.col`, not a child of it
 *  (`<div class="col"><h3>…</h3><div data-slot="left"></div></div>`), so this
 *  scans BACKWARD from the slot marker to the column that opens it. Derived
 *  from the registry row — never special-cased by slug. */
function slotHasHeading(fragment: string, name: string): boolean {
  const i = fragment.indexOf(`data-slot="${name}"`);
  if (i < 0) return false;
  const colStart = fragment.lastIndexOf('<div class="col"', i);
  if (colStart < 0) return false;
  return /<h[1-6]\b/.test(fragment.slice(colStart, i));
}

export function ArrangementThumb({ slots, fragment }: ArrangementThumbProps) {
  const hasHeading = fragment.includes('data-block="heading"');
  const inverse = fragment.includes('data-tone="inverse"');
  const regions = slots.filter((s) => s.role !== 'heading');
  return (
    <div
      aria-hidden
      className={`flex aspect-[16/10] w-full flex-col gap-1 rounded-sm border border-border p-1.5 ${
        inverse ? 'bg-foreground/75' : 'bg-background'
      }`}
    >
      {hasHeading && (
        <div
          className={`h-1.5 w-3/5 shrink-0 rounded-sm ${
            inverse ? 'bg-background/70' : 'bg-foreground/35'
          }`}
        />
      )}
      {regions.length > 0 ? (
        <div className="flex min-h-0 flex-1 gap-1">
          {regions.map((s) => (
            <div
              key={s.name}
              className={`flex min-h-0 flex-1 flex-col gap-0.5 rounded-sm p-0.5 ${
                s.role === 'media' ? 'bg-indigo-400/40' : 'bg-muted-foreground/15'
              }`}
            >
              {/* A per-column heading bar — what makes `comparison` (Option A /
                  Option B) read differently from `two-column` at a glance. */}
              {s.role !== 'media' && slotHasHeading(fragment, s.name) && (
                <div
                  className={`h-1 w-2/3 shrink-0 rounded-sm ${
                    inverse ? 'bg-background/60' : 'bg-foreground/30'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="flex-1" />
      )}
    </div>
  );
}
