"use client";

/**
 * AppStrip — the "what's in the box" roster, between the problem chapter
 * (Section 2) and the product chapter (Section 3).
 *
 * The shape is the Google Workspace strip: one row of marks with their names
 * under them, answering "what do I actually get" in a glance, before the
 * product chapter takes four of them one at a time.
 *
 * WHY THIS IMPORTS THE PRODUCT'S OWN RESOLVERS, AND DRAWS NOTHING
 * Every other landing component hand-rolls its inline SVG, which is fine for
 * a third-party brand mark but wrong for OUR OWN apps: a hand-drawn copy of
 * the Files folder is a second home for the Files icon, and it goes stale the
 * first time the product re-icons (the ADR-602 D4 fault — Slides wore Palette
 * in one place and Presentation in another). So the mark resolves through
 * `resolveSurfaceIcon` off the same `icon_key` the kernel row declares, and
 * the hue through `resolveSurfaceAccent` off the SLUG (ADR-641). Re-icon the
 * app and this strip moves with it.
 *
 * WHY THE ROSTER IS A LITERAL HERE AND NOT FETCHED
 * This is a static marketing page rendered for a signed-out visitor, who has
 * no workspace and therefore no served roster. The list mirrors the
 * `launcher_tier: "primary"` rows of `api/services/kernel_surfaces.py`, and
 * `web/components/landing/__tests__/app-strip-matches-primary-roster.test.mjs`
 * asserts it against that file in both directions — so a promoted or retired
 * app turns the gate red rather than leaving the strip quietly wrong.
 *
 * Roster-rule note (CANON-LOCK §5): app names are allowed BELOW the fold.
 * This sits under Section 2, well below the hero, with the hero's own copy
 * untouched.
 */

import { resolveSurfaceIcon, resolveSurfaceAccent } from "@/lib/shell/surface-icons";
import { useTranslations } from "next-intl";

/**
 * The hue for a surface with no ADR-641 accent row.
 *
 * `resolveSurfaceAccent` degrades to `text-muted-foreground`, which is correct
 * INSIDE the app (a surface with no declared hue reads neutral) and wrong
 * here: `--muted-foreground` is redefined under `.dark`, next-themes runs
 * `attribute="class"` with `enableSystem`, and this page is hardcoded light
 * (`bg-[#faf8f5]`). A visitor whose OS is dark would get the dark-mode grey
 * (64.9% lightness) on a white tile — legible in the editor, washed out on the
 * live page. The strip therefore names its own neutral in the page's palette
 * rather than borrowing a themed token. Supervisor is the one row this hits
 * today; any app promoted to primary before it earns an accent gets the same.
 */
const STRIP_NEUTRAL = "text-[#1a1a1a]/45";

function stripAccent(slug: string): string {
  const accent = resolveSurfaceAccent(slug);
  return accent === "text-muted-foreground" ? STRIP_NEUTRAL : accent;
}

/** Mirrors the `launcher_tier: "primary"` rows, in launcher declaration order. */
export const STRIP_APPS: { slug: string; label: string; iconKey: string }[] = [
  { slug: "chat", label: "Chat", iconKey: "message-circle" },
  { slug: "slides", label: "Slides", iconKey: "presentation" },
  { slug: "blogger", label: "Blogger", iconKey: "newspaper" },
  { slug: "images", label: "Images", iconKey: "image" },
  { slug: "text", label: "Text", iconKey: "file-text" },
  { slug: "files", label: "Files", iconKey: "folder" },
  { slug: "agents", label: "Agents", iconKey: "bot" },
  { slug: "reach", label: "Reach", iconKey: "arrow-left-right" },
  { slug: "supervisor", label: "Supervisor", iconKey: "compass" },
];

export function AppStrip() {
  const t = useTranslations("marketing.apps");
  return (
    <div className="w-full">
      <p className="text-center text-sm md:text-base text-[#1a1a1a]/45 font-light mb-10">
        {t("includes")}
      </p>

      {/* Wraps rather than scrolls: a horizontal scroller hides half the
          roster on a phone, and the whole point of the strip is that you can
          count what you get without moving anything. */}
      <ul className="flex flex-wrap items-start justify-center gap-x-5 gap-y-8 sm:gap-x-7 lg:gap-x-9">
        {STRIP_APPS.map((app) => {
          const Icon = resolveSurfaceIcon(app.iconKey);
          return (
            <li
              key={app.slug}
              className="flex w-[64px] sm:w-[72px] flex-col items-center gap-3"
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[#1a1a1a]/[0.07] bg-white/70 shadow-[0_1px_2px_rgba(26,26,26,0.04)]">
                <Icon
                  className={`h-[22px] w-[22px] ${stripAccent(app.slug)}`}
                />
              </span>
              <span className="text-xs sm:text-[13px] text-center leading-tight text-[#1a1a1a]/55">
                {app.label}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
