"use client";

/**
 * AddToChrome — the ONE install action for the yarnnn Chrome extension
 * (ADR-664 Amendment 1). Settings, Reach, the Supervisor's install step and the
 * marketing site all render this, so the link, its words and the rule for when
 * it exists live in one place.
 *
 * ⚠️ THE SWITCH IS `CHROME_EXTENSION.storeUrl` — null until the Web Store
 * listing is published, and held null by ADR-661's tripwire until ADR-662 is
 * Accepted. Without it there is no link: `fallback` renders the one "not yet"
 * line instead (a surface that must say why there is no button), and without
 * `fallback` nothing renders (a surface where the absence says enough).
 */

import { useTranslations } from "next-intl";
import { CHROME_EXTENSION } from "@/lib/shell/hands";

export function AddToChrome({
  className,
  fallback = false,
  fallbackClassName = "text-xs text-muted-foreground",
}: {
  className?: string;
  fallback?: boolean;
  fallbackClassName?: string;
}) {
  const t = useTranslations("extension");
  if (!CHROME_EXTENSION.storeUrl) {
    return fallback ? <span className={fallbackClassName}>{t("notYet")}</span> : null;
  }
  return (
    <a href={CHROME_EXTENSION.storeUrl} target="_blank" rel="noreferrer" className={className}>
      {t("add")}
    </a>
  );
}

/** Whether the extension can be installed from a public listing — the one
 *  predicate the marketing site gates its browser wording on. */
export const EXTENSION_PUBLISHED = CHROME_EXTENSION.storeUrl !== null;
