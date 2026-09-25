"use client";

/**
 * AddToChrome — the ONE install action for the yarnnn Chrome extension
 * (ADR-664 Amendments 1 and 2). Reach, the Supervisor's install step, Settings
 * and the marketing site all render this, so the link, its words and the rule
 * for when it exists live in one place.
 *
 * ⚠️ THE SWITCH IS `CHROME_EXTENSION.storeUrl`. Set: "Add to Chrome", to the
 * listing. Null (the Web Store is still reviewing it): "Install" — to Settings →
 * Your browser, where `BrowserSetting` offers the manual-install zip and the
 * three steps. ADR-662 is Accepted, so a member may install it either way; the
 * PUBLIC site still names it only once `EXTENSION_PUBLISHED` (ADR-664 D9), so no
 * stranger is sent to Chrome's developer mode.
 */

import Link from "next/link";
import { useTranslations } from "next-intl";
import { CHROME_EXTENSION } from "@/lib/shell/hands";

/** Where a member installs it by hand while the listing is in review. */
export const INSTALL_BY_HAND = "/settings?settings.pane=browser";

export function AddToChrome({ className }: { className?: string }) {
  const t = useTranslations("extension");
  if (!CHROME_EXTENSION.storeUrl) {
    return (
      <Link href={INSTALL_BY_HAND} className={className}>
        {t("install")}
      </Link>
    );
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
