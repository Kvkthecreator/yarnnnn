"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Suspense } from "react";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const error = searchParams.get("error");
      const errorDescription = searchParams.get("error_description");
      const next = searchParams.get("next") ?? "/dashboard";

      if (error) {
        router.replace(
          `/auth/login?error=${encodeURIComponent(error)}&message=${encodeURIComponent(errorDescription || "")}`
        );
        return;
      }

      if (code) {
        const { error: exchangeError } =
          await supabase.auth.exchangeCodeForSession(code);

        if (exchangeError) {
          router.replace(
            `/auth/login?error=session_error&message=${encodeURIComponent(exchangeError.message)}`
          );
          return;
        }

        // Successful login
        router.replace(next);
        return;
      }

      // No code provided
      router.replace("/auth/login?error=no_code");
    };

    handleCallback();
  }, [searchParams, router, supabase.auth]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-2">YARNNN</h1>
        <p className="text-gray-600">Completing sign in...</p>
      </div>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-2">YARNNN</h1>
            <p className="text-gray-600">Loading...</p>
          </div>
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
