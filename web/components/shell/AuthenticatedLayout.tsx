"use client";

/**
 * ADR-014: Top Bar with Minimal Chrome
 * Simplified layout with top bar instead of sidebar.
 * On desktop, content shrinks when side panel is open.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { TopBar } from "./TopBar";
import { useSurface } from "@/contexts/SurfaceContext";
import { useMediaQuery } from "@/hooks/useMediaQuery";

interface AuthenticatedLayoutProps {
  children: React.ReactNode;
}

export default function AuthenticatedLayout({
  children,
}: AuthenticatedLayoutProps) {
  const [userEmail, setUserEmail] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const supabase = createClient();

  // ADR-013: Surface state for layout adjustment
  const { state: surfaceState } = useSurface();
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const surfaceOpen = surfaceState.isOpen && isDesktop;

  useEffect(() => {
    const checkAuth = async () => {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        router.replace("/auth/login");
        return;
      }

      setUserEmail(user.email ?? undefined);
      setLoading(false);
    };

    checkAuth();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT" || !session) {
        router.replace("/auth/login");
      }
    });

    return () => subscription.unsubscribe();
  }, [router, supabase.auth]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-brand mb-2">yarnnn</h1>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-background">
      {/* Top Bar */}
      <TopBar email={userEmail} />

      {/* Main content area */}
      <main
        className="flex-1 overflow-hidden transition-all duration-300"
        style={{
          marginRight: surfaceOpen ? "480px" : "0",
        }}
      >
        {children}
      </main>
    </div>
  );
}
