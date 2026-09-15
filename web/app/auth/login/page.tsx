"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { getSafeNextPath } from "@/lib/auth/redirect";
import { HOME_ROUTE } from "@/lib/routes";
import { AuthForm } from "@/components/auth/AuthForm";
import Link from "next/link";
import { Wordmark } from "@/components/shared/Wordmark";
import { Working } from '@/components/shared/Working';

function LoginForm() {
  const searchParams = useSearchParams();
  const [initialError, setInitialError] = useState<string | null>(null);
  const nextPath = getSafeNextPath(searchParams.get("next"), HOME_ROUTE);
  const callbackRedirect =
    typeof window === "undefined"
      ? ""
      : `${window.location.origin}/auth/callback?next=${encodeURIComponent(nextPath)}`;

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
          loginSubheading="Sign in to your account"
          signupSubheading="Create your account"
          initialError={initialError}
        />
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="relative min-h-screen flex items-center justify-center bg-[#faf8f5] px-4">
          <div className="relative z-10 w-full max-w-md space-y-8">
            <div className="text-center">
              <h1 className="text-[#1a1a1a]"><Wordmark className="text-3xl" /></h1>
              <div className="mt-2 flex justify-center"><Working label="Loading…" /></div>
            </div>
          </div>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
