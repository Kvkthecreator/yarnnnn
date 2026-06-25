"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ShaderBackground } from "@/components/landing/ShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { getSafeNextPath } from "@/lib/auth/redirect";
import { HOME_ROUTE } from "@/lib/routes";
import { AuthForm } from "@/components/auth/AuthForm";
import Link from "next/link";

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
            className="text-3xl font-brand text-[#1a1a1a] hover:opacity-80 transition-opacity"
          >
            yarnnn
          </Link>
        </div>

        <AuthForm
          onPasswordSuccess={() => {
            window.location.href = nextPath;
          }}
          callbackRedirect={callbackRedirect}
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
              <h1 className="text-3xl font-brand text-[#1a1a1a]">yarnnn</h1>
              <p className="mt-2 text-[#1a1a1a]/60">Loading...</p>
            </div>
          </div>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
