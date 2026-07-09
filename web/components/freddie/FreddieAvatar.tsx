'use client';

/**
 * FreddieAvatar — the mascot for Freddie, the system agent (v4, 2026-07-01).
 *
 * THE DESIGN LANGUAGE (the operator's "Freddie Design System" framing):
 *   - ONE iconic mascot: Freddie = FRANKENSTEIN's monster (flat-top head, brow
 *     scar, temple bolts), rendered in the CRYPTOPUNKS idiom — a literal 24×24
 *     pixel grid of hard-edged blocks.
 *   - ONE APPEARANCE, LIKE A BRAND LOGO. Freddie is ALWAYS the full-color Frankie
 *     (green skin · dark flat-top · steel bolts). No monochrome variant.
 *   - THE FACE is the friendly "grin" — dot eyes + a fanged open smile (the
 *     operator picked this over a flat neutral mouth). One face, always.
 *   - MOTION IS THE STATE (the loader model, think Claude Code's streaming
 *     shimmer). Freddie is STILL at rest and ANIMATES while working: the eyes
 *     BLINK (dots briefly flatten to a line) and the temple bolt caps PULSE.
 *     Motion = the activity signal; stillness = nothing running. Dot-eyes can't
 *     show a visible pupil-scan (the v3 attempt was invisible — dark pupil on a
 *     dark socket), so the working tell is blink + bolt-pulse instead.
 *   - SEAT, NOT PERSONA. The face is Freddie-the-seat (ADR-381/383); an operator
 *     persona (IDENTITY.md) changes the NAME, never the face (ADR-315).
 *
 * ANIMATION: pure CSS keyframes SCOPED inside the SVG (inline <style> + a
 * per-instance id via useId) — GPU-cheap, no JS tick, no global-CSS dependency.
 * The blink cross-fades an "eyes-open" layer against an "eyes-closed" layer via
 * opacity keyframes (open most of the cycle, a brief closed flash). `animate=
 * false` renders the still grin (eyes open, bolts steady).
 *
 * GRID: 24×24, viewBox 0 0 24 24, one pixel = one <rect>.
 */

import { useId } from 'react';
import { cn } from '@/lib/utils';

export interface FreddieAvatarProps {
  /**
   * Whether Freddie is WORKING. true → the loader motion (eyes blink + bolts
   * pulse). false → the still grin. Default true for now — v4 ships the motion
   * always-on to prove it reads; a follow-up wires it to real activity signals
   * (a response streaming, a wake running).
   */
  animate?: boolean;
  /**
   * MONOCHROME variant for CHROME (launcher / dock / top-bar), added 2026-07-09.
   * The design system's "one appearance, always full-color" rule is the BRAND
   * mark (chat FAB, card, hero) — but in a glyph row next to monochrome lucide
   * icons the full-color Frankie reads as a heavy color block, and on the active
   * tile (`bg-foreground text-background`) it ignores the white recolor. `mono`
   * renders the SAME Frankenstein silhouette (head · bolts · dot-eyes · grin)
   * in a SINGLE ink — `currentColor` — so it inherits `text-*` exactly like a
   * lucide glyph (white on the black active tile, dark otherwise). The face
   * survives; only the palette collapses. Motion is off in chrome, so `mono`
   * implies still. Default false (full-color brand mark).
   */
  mono?: boolean;
  /** Sizing. Default 'w-4 h-4'. */
  className?: string;
  /** Accessible label. */
  title?: string;
}

// ── Palette ──────────────────────────────────────────────────────────────
const PALETTE: Record<string, string> = {
  K: '#1f2937', //  hair / flat-top + outline (near-black slate)
  G: '#5bbf57', //  skin (Frankenstein green)
  D: '#3f9a45', //  skin shadow (jaw / cheek)
  B: '#9ca3af', //  bolt metal (steel)
  H: '#e5e7eb', //  bolt highlight (shiny cap — pulses while working)
  M: '#4b5563', //  bolt shadow / dark rim
  E: '#111827', //  eyes / mouth / fang ink
  W: '#ffffff', //  fang teeth (white, inside the grin)
  S: '#3f9a45', //  forehead stitch scar
};

// ── Base grid (24×24) ─────────────────────────────────────────────────────
// The GRIN face, baked in: dot EYES (single E pixels at r11 c8 / c15), a fanged
// open SMILE (dark mouth with two white fang pixels). Temple BOLTS (M B B H) at
// ear level. Eyes are rendered from this grid when still / open; the blink
// overlay flattens them while working.
// prettier-ignore
const BASE: string[] = [
  '........................',  // 0
  '........................',  // 1
  '......KKKKKKKKKKKK......',  // 2  hair crown
  '.....KKKKKKKKKKKKKK.....',  // 3
  '.....KKKKKKKKKKKKKK.....',  // 4  flat-top block
  '.....KKK.KKKK.KKKKK.....',  // 5  hair fringe
  '.....KGGGGGGGGGGGGK.....',  // 6  forehead
  '.....KGGGGGGGGGGGGK.....',  // 7  TALL forehead
  '.....KGGGSSSSSSGGGK.....',  // 8  stitch scar
  '.MBBHKGGGGGGGGGGGGKHBBM.',  // 9  temple bolts
  '.MBBHKGGGGGGGGGGGGKHBBM.',  // 10
  '.....KGGGGGGGGGGGGK.....',  // 11 (eyes drawn as overlay layers — see below)
  '.....KGGGGGGGGGGGGK.....',  // 12
  '.....KGGGGGGGGGGGGK.....',  // 13
  '.....KGGGGGGGGGGGGK.....',  // 14 (mouth drawn as overlay — the grin)
  '.....KGGGGGGGGGGGGK.....',  // 15
  '.....KDGGGGGGGGGGDK.....',  // 16 cheek/jaw shadow
  '.....KKDDDDDDDDDDKK.....',  // 17 jaw
  '......KKKKKKKKKKKK......',  // 18 chin/neck
  '......KKKKKKKKKKKK......',  // 19
  '........................',  // 20
  '........................',  // 21
  '........................',  // 22
  '........................',  // 23
];

// Feature pixels drawn ON TOP of the base skin, so the blink can swap the eye
// layer cleanly. Cols: left eye 8, right eye 15 (2px tall dot). Grin: a dark
// mouth line (r14 c8-15) that dips at the corners (r15 c8 & c15) with two white
// FANG pixels (r15 c10 & c13) — the friendly fanged smile.
type Px = { r: number; c: number; k: string };

// Eyes OPEN — the resting grin's round-ish dark dots (2px tall).
const EYES_OPEN: Px[] = [
  { r: 11, c: 8, k: 'E' }, { r: 12, c: 8, k: 'E' },
  { r: 11, c: 15, k: 'E' }, { r: 12, c: 15, k: 'E' },
];
// Eyes CLOSED — the blink: a single flat line (1px) where the dots were.
const EYES_CLOSED: Px[] = [
  { r: 12, c: 8, k: 'E' },
  { r: 12, c: 15, k: 'E' },
];
// The fanged grin mouth (always drawn; doesn't change with blink).
const MOUTH: Px[] = [
  // top lip line
  { r: 14, c: 8, k: 'E' }, { r: 14, c: 9, k: 'E' }, { r: 14, c: 10, k: 'E' },
  { r: 14, c: 11, k: 'E' }, { r: 14, c: 12, k: 'E' }, { r: 14, c: 13, k: 'E' },
  { r: 14, c: 14, k: 'E' }, { r: 14, c: 15, k: 'E' },
  // open mouth interior with two white fangs
  { r: 15, c: 9, k: 'E' }, { r: 15, c: 10, k: 'W' }, { r: 15, c: 11, k: 'E' },
  { r: 15, c: 12, k: 'E' }, { r: 15, c: 13, k: 'W' }, { r: 15, c: 14, k: 'E' },
];

// Temple bolt CAP highlight pixels (H) — pulsed while working. Rows 9-10, cols 4 & 19.
function isBoltCap(r: number, c: number): boolean {
  return (r === 9 || r === 10) && (c === 4 || c === 19);
}

// ── Monochrome chrome variant ──────────────────────────────────────────────
// The SAME silhouette in one ink (currentColor), with the eyes + grin punched
// out as negative space so the face still reads. The head body (skin + outline
// + bolts) is one solid currentColor mass; the feature pixels (eyes, mouth,
// fangs) are rendered in the tile BACKGROUND so they show as holes. Because a
// surface icon can sit on either a light row (dark ink) or the active tile
// (white ink on bg-foreground), the "hole" color must be the surrounding
// surface, which we can't know statically — so we cut the holes with a mask
// instead: draw the body, then knock out the feature pixels via a <mask>.
function FreddieMono({ className, title }: { className?: string; title?: string }) {
  const uid = useId().replace(/:/g, '');
  const maskId = `freddie-mono-mask-${uid}`;

  // Body pixels: everything in the base grid that is NOT a background dot.
  const body: React.ReactNode[] = [];
  for (let r = 0; r < BASE.length; r++) {
    for (let c = 0; c < BASE[r].length; c++) {
      if (BASE[r][c] === '.') continue;
      body.push(
        <rect key={`mb-${r}-${c}`} x={c} y={r} width={1} height={1} fill="white" />
      );
    }
  }
  // Feature holes: eyes (open) + the grin mouth, painted BLACK in the mask so
  // they subtract from the body (mask white = keep, black = cut).
  const holes = [...EYES_OPEN, ...MOUTH].map((p, i) => (
    <rect key={`mh-${i}`} x={p.c} y={p.r} width={1} height={1} fill="black" />
  ));

  return (
    <svg
      viewBox="0 0 24 24"
      className={cn('shrink-0', className ?? 'w-4 h-4')}
      role="img"
      aria-label={title ?? 'Freddie'}
      shapeRendering="crispEdges"
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>{title ?? 'Freddie'}</title>
      <mask id={maskId}>
        {/* white = visible ink, black = cut hole (eyes/grin show the tile) */}
        {body}
        {holes}
      </mask>
      {/* One solid fill in currentColor, shaped by the mask — inherits text-* */}
      <rect x={0} y={0} width={24} height={24} fill="currentColor" mask={`url(#${maskId})`} />
    </svg>
  );
}

export function FreddieAvatar({ animate = true, mono = false, className, title }: FreddieAvatarProps) {
  if (mono) return <FreddieMono className={className} title={title} />;

  const uid = useId().replace(/:/g, '');
  const blinkKf = `freddie-blink-${uid}`;
  const pulseKf = `freddie-pulse-${uid}`;

  const px = (p: Px, extra?: React.CSSProperties, key?: string) => (
    <rect
      key={key ?? `${p.r}-${p.c}`}
      x={p.c}
      y={p.r}
      width={1}
      height={1}
      fill={PALETTE[p.k] ?? '#000'}
      style={extra}
    />
  );

  // Base skin/head/bolts from the grid.
  const base: React.ReactNode[] = [];
  for (let r = 0; r < BASE.length; r++) {
    for (let c = 0; c < BASE[r].length; c++) {
      const key = BASE[r][c];
      if (key === '.') continue;
      base.push(
        <rect
          key={`b-${r}-${c}`}
          x={c}
          y={r}
          width={1}
          height={1}
          fill={PALETTE[key] ?? '#000'}
          style={animate && isBoltCap(r, c) ? { animation: `${pulseKf} 1.4s ease-in-out infinite` } : undefined}
        />
      );
    }
  }

  // Mouth (static grin) always on top of skin.
  const mouth = MOUTH.map((p, i) => px(p, undefined, `m-${i}`));

  // Eyes. Still → just the open layer. Working → open + closed layers cross-
  // faded by the blink keyframe (open is visible ~92% of the cycle; closed
  // flashes briefly). Opposite-phase animations on one keyframe timeline.
  const eyes = animate
    ? [
        ...EYES_OPEN.map((p, i) =>
          px(p, { animation: `${blinkKf}-open 3.2s steps(1,end) infinite` }, `eo-${i}`)
        ),
        ...EYES_CLOSED.map((p, i) =>
          px(p, { animation: `${blinkKf}-closed 3.2s steps(1,end) infinite` }, `ec-${i}`)
        ),
      ]
    : EYES_OPEN.map((p, i) => px(p, undefined, `eo-${i}`));

  return (
    <svg
      viewBox="0 0 24 24"
      className={cn('shrink-0', className ?? 'w-4 h-4')}
      role="img"
      aria-label={title ?? (animate ? 'Freddie is working' : 'Freddie')}
      shapeRendering="crispEdges"
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>{title ?? (animate ? 'Freddie is working' : 'Freddie')}</title>
      {animate && (
        <style>{`
          /* blink: eyes open most of the cycle, a brief closed flash near the end */
          @keyframes ${blinkKf}-open {
            0%, 90% { opacity: 1; }
            93%, 97% { opacity: 0; }
            100% { opacity: 1; }
          }
          @keyframes ${blinkKf}-closed {
            0%, 90% { opacity: 0; }
            93%, 97% { opacity: 1; }
            100% { opacity: 0; }
          }
          @keyframes ${pulseKf} {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
          }
        `}</style>
      )}
      {base}
      {mouth}
      {eyes}
    </svg>
  );
}
