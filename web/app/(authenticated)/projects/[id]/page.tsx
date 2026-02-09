"use client";

/**
 * ADR-013: Conversation + Surfaces
 * ADR-034: Context v2 - Domain-based scoping
 *
 * Legacy project route - redirects to dashboard.
 *
 * Projects are now organizational containers, context/memory
 * is scoped by domains (which emerge from deliverable sources).
 * This redirect maintains backwards compatibility for bookmarks and links.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

export default function ProjectRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    // Simply redirect to dashboard - projects are now browsed via surfaces
    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground mx-auto mb-4" />
        <p className="text-muted-foreground">Redirecting...</p>
      </div>
    </div>
  );
}
