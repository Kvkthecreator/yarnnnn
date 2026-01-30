"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Menu } from "lucide-react";
import Sidebar from "./Sidebar";
import { useSurface } from "@/contexts/SurfaceContext";
import { useMediaQuery } from "@/hooks/useMediaQuery";

interface AuthenticatedLayoutProps {
  children: React.ReactNode;
}

/**
 * ADR-013: Conversation + Surfaces
 * Main authenticated layout with responsive surface support.
 * On desktop, content shrinks when side panel is open.
 */
export default function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  const [userEmail, setUserEmail] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const router = useRouter();
  const supabase = createClient();

  // ADR-013: Surface state for layout adjustment
  const { state: surfaceState } = useSurface();
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const surfaceOpen = surfaceState.isOpen && isDesktop;

  // Mobile detection for initial state
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      // Start with sidebar closed on mobile
      if (mobile) {
        setSidebarOpen(false);
      }
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser();

      if (!user) {
        router.replace("/auth/login");
        return;
      }

      setUserEmail(user.email ?? undefined);
      setLoading(false);
    };

    checkAuth();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
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
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <Sidebar
        userEmail={userEmail}
        open={sidebarOpen}
        onOpenChange={setSidebarOpen}
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header with hamburger menu */}
        {!sidebarOpen && (
          <div className="md:hidden fixed top-0 left-0 right-0 z-30 bg-background/95 backdrop-blur-sm border-b border-border px-4 py-3 flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 -ml-2 rounded-md hover:bg-muted transition-colors"
              aria-label="Open menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <span className="text-lg font-brand">yarnnn</span>
          </div>
        )}

        {/* Desktop expand button when sidebar is closed */}
        {!sidebarOpen && !isMobile && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="fixed top-3 left-3 z-30 p-2 bg-background border border-border rounded-md hover:bg-muted transition-colors shadow-sm"
            aria-label="Open sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* ADR-013: Main content area shrinks when desktop side panel is open */}
        <main
          className={`flex-1 overflow-hidden transition-all duration-300 ${
            !sidebarOpen && isMobile ? "pt-14" : ""
          }`}
          style={{
            marginRight: surfaceOpen ? "480px" : "0",
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
