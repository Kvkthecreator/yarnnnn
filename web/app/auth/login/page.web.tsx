"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { authCallbackUrl, getSafeNextPath } from "@/lib/auth/redirect";
import { HOME_ROUTE } from "@/lib/routes";
import { AuthForm } from "@/components/auth/AuthForm";
import Link from "next/link";
import { Wordmark } from "@/components/shared/Wordmark";
import { Working } from '@/components/shared/Working';
import { LanguageSwitcher } from "@/components/i18n/LanguageSwitcher";
import { useTranslations } from "next-intl";

function LoginForm() {
  const t = useTranslations("auth");
  const searchParams = useSearchParams();
  const [initialError, setInitialError] = useState<string | null>(null);
  const nextPath = getSafeNextPath(searchParams.get("next"), HOME_ROUTE);
  const callbackRedirect = authCallbackUrl(nextPath);

  // Show OAuth callback errors
  useEffect(() => {
    const errorParam = searchParams.get("error");
    const messageParam = searchParams.get("message");
    if (errorParam) {
      setInitialError(`${errorParam}${messageParam ? `: ${messageParam}` : ""}`);
    }
  }, [searchParams]);

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-[#faf8f5] px-4">
      <GrainOverlay />
      <ShaderBackground />

      <div className="relative z-10 w-full max-w-md">
        <div className="text-center">
          <Link
            href="/"
            className="inline-block text-[#1a1a1a] hover:opacity-80 transition-opacity"
          >
            <Wordmark className="text-3xl" />
          </Link>
        </div>

        <AuthForm
          onPasswordSuccess={() => {
            // A full load re-enters `middleware.ts`, which must see the new
            // cookie. (Web-only page — the desktop app signs in through the
            // browser, ADR-661 §7p.)
            window.location.href = nextPath;
          }}
          callbackRedirect={callbackRedirect}
          // `?mode=signup` opens in sign-up (2026-09-16). Every conversion CTA
          // on the marketing site — "Start free", "Connect your AI", "Bring the
          // team" — used to land here in SIGN-IN mode, so the first thing a
          // stranger who just decided to try the product saw was a form asking
          // for a password they do not have, with the actual sign-up affordance
          // a small link at the bottom. Observed in a first-time-visitor pass,
          // 2026-09-15. Anything but "signup" stays on sign-in, so an
          // unrecognised value degrades to today's behaviour.
          initialMode={searchParams.get("mode") === "signup" ? "signup" : "login"}
          loginSubheading={t("loginSubheading")}
          signupSubheading={t("signupSubheading")}
          initialError={initialError}
        />

        {/* ADR-660 D2 — signed out, the choice is the device cookie; the first
            signed-in render adopts it into the account. */}
        <div className="mt-6 flex justify-center">
          <LanguageSwitcher variant="inline" />
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  // ADR-660 — the fallback is rendered by THIS component, so the word is bound
  // here; `Working` itself stays locale-free (it is also mounted by routes
  // outside every scope, where a translation hook would throw).
  const t = useTranslations("auth");
  return (
    <Suspense
      fallback={
        <div className="relative min-h-screen flex items-center justify-center bg-[#faf8f5] px-4">
          <div className="relative z-10 w-full max-w-md space-y-8">
            <div className="text-center">
              <h1 className="text-[#1a1a1a]"><Wordmark className="text-3xl" /></h1>
              <div className="mt-2 flex justify-center"><Working label={t('loading')} /></div>
            </div>
          </div>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
