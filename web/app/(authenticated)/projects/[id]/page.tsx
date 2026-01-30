"use client";

/**
 * ADR-013: Conversation + Surfaces
 * Legacy project route - redirects to dashboard with project context set.
 *
 * Projects are now contextual lenses on the dashboard, not separate routes.
 * This redirect maintains backwards compatibility for bookmarks and links.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api/client";
import { useProjectContext } from "@/contexts/ProjectContext";

export default function ProjectRedirectPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { setActiveProject } = useProjectContext();

  useEffect(() => {
    async function redirectToProject() {
      try {
        // Fetch project to get the name for context
        const project = await api.projects.get(params.id);

        // Set as active project
        setActiveProject({ id: project.id, name: project.name });

        // Redirect to dashboard
        router.replace("/dashboard");
      } catch (err) {
        console.error("Failed to load project:", err);
        // Still redirect to dashboard on error
        router.replace("/dashboard");
      }
    }

    redirectToProject();
  }, [params.id, setActiveProject, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground mx-auto mb-4" />
        <p className="text-muted-foreground">Loading project...</p>
      </div>
    </div>
  );
}
