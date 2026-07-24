// The skin-variable parse (DESIGN-SYSTEMS.md §5/§6) — ONE parse, two readers.
// The Design tab reads the artifact's marked element (what THIS artifact
// wears); the manage panel reads the resolved skin_element (what the SYSTEM
// is). Both surface the kernel-consumed vocabulary first — those are the
// tokens that actually theme the chrome (§5 Move 1).

/** The kernel-consumed slot vocabulary (STUDIO_KERNEL_CSS v9, §5 Move 1).
 *  Categories, never a vendor's instances (ADR-222): the ink ramp steps the
 *  chrome reads, the radius + type scales, the semantic trio. */
export const KERNEL_CONSUMED_VARS = new Set([
  'ink', 'ink-06', 'ink-10', 'paper', 'muted', 'accent', 'deck-stage',
  'radius-sm', 'radius-md', 'radius-lg', 'radius-pill',
  'text-xs', 'text-sm', 'text-base', 'text-lg', 'text-xl',
  'text-2xl', 'text-3xl', 'text-4xl', 'text-5xl', 'fresh', 'danger', 'warn',
]);

export type SkinVar = { name: string; value: string };

/** Parse the custom properties a skin's CSS defines, kernel-consumed first.
 *  Collection is capped at 40 (a real export defines ~119; the tail is
 *  scaffolding); `limit` caps what the caller shows. */
export function parseSkinVars(css: string, limit = 12): SkinVar[] {
  const out: SkinVar[] = [];
  const rx = /--([a-z0-9-]+)\s*:\s*([^;}]+)[;}]/gi;
  let m;
  while ((m = rx.exec(css)) && out.length < 40) {
    out.push({ name: m[1], value: m[2].trim() });
  }
  return out
    .sort(
      (a, b) =>
        Number(KERNEL_CONSUMED_VARS.has(b.name)) -
        Number(KERNEL_CONSUMED_VARS.has(a.name)),
    )
    .slice(0, limit);
}

/** A value the theme row can show as a color swatch. */
export function isColorValue(value: string): boolean {
  return /^(#|rgb|hsl)/i.test(value);
}
