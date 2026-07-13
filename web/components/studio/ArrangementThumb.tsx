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
              className={`flex-1 rounded-sm ${
                s.role === 'media' ? 'bg-indigo-400/40' : 'bg-muted-foreground/15'
              }`}
            />
          ))}
        </div>
      ) : (
        <div className="flex-1" />
      )}
    </div>
  );
}
