'use client';

/**
 * StudioNavigator — the Studio's left rail (ADR-447 workbench restructure).
 *
 * A PER-TYPE navigator: what it shows follows the artifact's layout —
 *   - deck    → a slide strip (PowerPoint's left thumbnails): one card per
 *               `[data-arrange]` slide, numbered, titled by its heading;
 *               clicking a card selects that slide (anchors Arrange ops).
 *   - article → the outline (h1/h2 headings) — a publishing shape reads as a
 *               table of contents.
 *   - document→ the outline too (sections under one title).
 *
 * It reads the artifact's SOURCE html (the surface passes it), never the
 * projection — the navigator is structure, not rendered content. Selecting a
 * slide reports its index so the toolbar's Arrange ops can target it (the
 * pointer runtime reports slideIndex for on-canvas clicks; this is the same
 * anchor from the rail).
 *
 * Full visual thumbnails (a scaled render of each slide) are Phase 2 — this
 * is the honest structural navigator that ships with the column restructure.
 */

interface SlideEntry {
  index: number;
  arrange: string | null;
  title: string;
}

interface OutlineEntry {
  level: number;
  text: string;
}

/** Extract deck slides from source html: each top-level `section.slide`
 *  (a `[data-arrange]` page), its arrangement slug + its first heading text. */
function extractSlides(html: string): SlideEntry[] {
  if (typeof window === 'undefined' || !html) return [];
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const slides = Array.from(doc.querySelectorAll('section.slide'));
  return slides.map((s, index) => {
    const heading = s.querySelector('h1, h2, h3, .kicker');
    return {
      index,
      arrange: s.getAttribute('data-arrange'),
      title: (heading?.textContent || '').replace(/\s+/g, ' ').trim() || `Slide ${index + 1}`,
    };
  });
}

/** Extract h1/h2 outline from source html (document/article rail). */
function extractOutline(html: string): OutlineEntry[] {
  if (typeof window === 'undefined' || !html) return [];
  const doc = new DOMParser().parseFromString(html, 'text/html');
  return Array.from(doc.querySelectorAll('h1, h2'))
    .map((h) => ({
      level: h.tagName === 'H1' ? 1 : 2,
      text: (h.textContent || '').replace(/\s+/g, ' ').trim(),
    }))
    .filter((h) => h.text)
    .slice(0, 40);
}

interface StudioNavigatorProps {
  /** The artifact's layout slug (document/deck/article). */
  layout: string;
  /** The artifact's SOURCE html (not the projection). */
  html: string;
  /** The currently selected slide index (deck) — highlights the card. */
  selectedSlide: number | null;
  /** Select a slide by index (deck) — anchors the toolbar's Arrange ops. */
  onSelectSlide: (index: number) => void;
}

export function StudioNavigator({
  layout,
  html,
  selectedSlide,
  onSelectSlide,
}: StudioNavigatorProps) {
  if (layout === 'deck') {
    const slides = extractSlides(html);
    return (
      <div className="flex h-full flex-col overflow-y-auto p-2">
        <p className="px-1 pb-2 pt-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          Slides
        </p>
        <ul className="space-y-1.5">
          {slides.map((s) => (
            <li key={s.index}>
              <button
                type="button"
                onClick={() => onSelectSlide(s.index)}
                className={`flex w-full items-start gap-2 rounded-md border p-2 text-left transition-colors ${
                  selectedSlide === s.index
                    ? 'border-indigo-400 bg-indigo-50/60 dark:bg-indigo-950/40'
                    : 'border-border hover:bg-muted/40'
                }`}
              >
                <span className="mt-0.5 shrink-0 text-[10px] font-medium text-muted-foreground">
                  {s.index + 1}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-xs font-medium">{s.title}</span>
                  {s.arrange && (
                    <span className="block truncate text-[10px] text-muted-foreground">
                      {s.arrange}
                    </span>
                  )}
                </span>
              </button>
            </li>
          ))}
          {slides.length === 0 && (
            <li className="px-1 text-[11px] text-muted-foreground">No slides yet.</li>
          )}
        </ul>
      </div>
    );
  }

  // document + article → the outline (a table of contents).
  const outline = extractOutline(html);
  return (
    <div className="flex h-full flex-col overflow-y-auto p-3">
      <p className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        Outline
      </p>
      {outline.length === 0 ? (
        <p className="text-[11px] text-muted-foreground">Headings appear here.</p>
      ) : (
        <ul className="space-y-1">
          {outline.map((h, i) => (
            <li
              key={i}
              className={`truncate text-xs ${
                h.level === 1 ? 'font-medium' : 'pl-3 text-muted-foreground'
              }`}
              title={h.text}
            >
              {h.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
