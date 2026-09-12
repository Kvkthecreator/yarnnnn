import { BRAND, STAGE_NOTICE } from "@/lib/metadata";
import { cn } from "@/lib/utils";

/**
 * Wordmark — the ONE rendering of the yarnnn brand mark (ADR-629 D4).
 *
 * Before this the Pacifico mark was hand-spelled in fourteen files, so there
 * was no single place to say anything ABOUT the brand — such as its release
 * stage. The mark renders here, once, and the stage annotation beside it
 * derives from `BRAND.stage` in lib/metadata.ts: delete that one line and
 * every annotation disappears in the same deploy.
 *
 * Two grains, two shapes (operator ruling 2026-09-12). The APP-grain badge
 * (ADR-629 D1, the Launcher chip) is a DISCRIMINATOR — it means something
 * only by contrast with the bare rows beside it. The PRODUCT-grain stage is a
 * CONSTANT — on every page, every visit, until graduation. The same chip at
 * both grains cancels: a parent wearing BETA makes Blogger's chip read as
 * "beta inside a beta". So this annotation is deliberately QUIET: lowercase,
 * the body sans (never Pacifico — set in the script face it reads as a new
 * name, "yarnnn beta"), at half the mark's ink. Emphasis belongs once, at the
 * sign-up door (AuthForm), not on every page.
 *
 * Presentation only: nothing routes, gates or prices on the stage.
 *
 * A <span>, so it sits inside whatever the site already has — a Link, a
 * button, an <h1>, a <p>. Size and colour come from the caller's className
 * (the mark inherits them); the annotation takes `currentColor` at reduced
 * opacity, so it is legible on every ground the mark appears on — theme-aware
 * chrome, the fixed-light auth pages, the inverted landing header — with no
 * per-site colour prop.
 */

interface StageAnnotationProps {
  className?: string;
}

/**
 * The stage, as a quiet annotation. Renders nothing when there is no stage.
 * Lives inside the Wordmark and, on its own, beside the email in the account
 * menu — the stage's home on phones, where the top bar hides the mark.
 */
export function StageAnnotation({ className }: StageAnnotationProps) {
  if (!BRAND.stage) return null;
  return (
    <span
      className={cn(
        "font-sans text-xs font-normal leading-none tracking-normal opacity-50",
        className,
      )}
      title={STAGE_NOTICE ?? undefined}
    >
      {BRAND.stage}
    </span>
  );
}

interface WordmarkProps {
  /** Size and colour — the mark inherits both (e.g. `text-2xl text-foreground`). */
  className?: string;
  /**
   * Render the mark with no stage annotation. ONE caller: the landing hero,
   * whose sequence CANON-LOCK-2026-07-30 §1 fixes verbatim; the header
   * directly above it already carries the stage.
   */
  bare?: boolean;
}

export function Wordmark({ className, bare = false }: WordmarkProps) {
  return (
    <span className={cn("font-brand inline-flex items-baseline gap-1.5", className)}>
      {BRAND.name}
      {!bare && <StageAnnotation />}
    </span>
  );
}
