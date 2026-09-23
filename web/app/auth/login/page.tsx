"use client";

/**
 * Sign-in for the DESKTOP APP (ADR-661 §7p). `page.web.tsx` beside this file
 * is the website's sign-in, and exactly one of the two exists in any build
 * (`pageExtensions` in `next.config.js`).
 *
 * The desktop app does not authenticate — the website does (§7i D5). So this
 * page has no form: one button opens `/auth/desktop` in the member's own
 * browser, where every sign-in method the website has works (password, Google,
 * sign-up, a reset link), and the browser hands the session back over
 * `yarnnn://auth/session`, which `DeepLinkBridge` redeems. This is the shape
 * Notion, Slack and Linear use, and it is why the app never starts an auth
 * flow of its own: an email link or an OAuth return can only complete in the
 * context that began it, and that context is the browser.
 *
 * What this page must still do (§7h): say WHY a hand-off failed. The bridge
 * lands a failure here as `?error=…&message=…`.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { Wordmark } from "@/components/shared/Wordmark";
import { LanguageSwitcher } from "@/components/i18n/LanguageSwitcher";
import { createClient } from "@/lib/supabase/client";
import { getSafeNextPath } from "@/lib/auth/redirect";
import { HOME_ROUTE } from "@/lib/routes";
import { openExternal, webOrigin } from "@/lib/shell/external-navigation";

export default function DesktopSignIn() {
  const t = useTranslations("auth.desktop");
  const router = useRouter();
  const [failure, setFailure] = useState<string | null>(null);
  const [opened, setOpened] = useState(false);

  useEffect(() => {
    // `window.location`, not `useSearchParams`: under a static export the hook
    // demands a Suspense boundary (§7a), and an effect only runs in the app.
    const params = new URLSearchParams(window.location.search);
    const error = params.get("error");
    const message = params.get("message");
    if (error) setFailure(message ? `${error}: ${message}` : error);

    // Already signed in (a session survived, or the hand-off just landed):
    // go where the member was going.
    const next = getSafeNextPath(params.get("next"), HOME_ROUTE);
    void createClient()
      .auth.getSession()
      .then(({ data: { session } }) => {
        if (session) router.replace(next);
      });
  }, [router]);

  const continueInBrowser = () => {
    setFailure(null);
    setOpened(true);
    openExternal(`${webOrigin()}/auth/desktop`);
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-[#faf8f5] px-4">
      <GrainOverlay />
      <ShaderBackground />

      <div className="relative z-10 w-full max-w-md text-center">
        <h1 className="text-[#1a1a1a]">
          <Wordmark className="text-3xl" />
        </h1>
        <p className="mt-6 text-[#1a1a1a]">{t("heading")}</p>
        <p className="mt-2 text-sm text-[#1a1a1a]/60">{t("lead")}</p>

        <button
          type="button"
          onClick={continueInBrowser}
          className="mt-8 w-full rounded-lg bg-[#1a1a1a] px-4 py-3 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          {opened ? t("again") : t("continue")}
        </button>

        {opened && !failure && (
          <p className="mt-4 text-sm text-[#1a1a1a]/60" role="status">
            {t("waiting")}
          </p>
        )}
        {failure && (
          <p className="mt-4 text-sm text-red-700" role="alert">
            {failure}
          </p>
        )}

        <div className="mt-8 flex justify-center">
          <LanguageSwitcher variant="inline" />
        </div>
      </div>
    </div>
  );
}
