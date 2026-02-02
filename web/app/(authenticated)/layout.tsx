import { Suspense } from "react";
import { ProjectProvider } from "@/contexts/ProjectContext";
import { WorkStatusProvider } from "@/contexts/WorkStatusContext";
import { SurfaceProvider } from "@/contexts/SurfaceContext";
import { SurfaceRouter } from "@/components/surfaces";

/**
 * ADR-022: Chat-First Architecture with Drawer Views
 *
 * Layout for authenticated routes:
 * - Chat is the primary surface (main view)
 * - Drawers open for detailed content (deliverables, reviews)
 * - SurfaceRouter handles drawer rendering
 */
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <WorkStatusProvider>
        <SurfaceProvider>
          <Suspense fallback={<LayoutFallback />}>
            {children}
            <SurfaceRouter />
          </Suspense>
        </SurfaceProvider>
      </WorkStatusProvider>
    </ProjectProvider>
  );
}

function LayoutFallback() {
  return (
    <div className="h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <h1 className="text-xl font-brand mb-2">yarnnn</h1>
        <p className="text-muted-foreground text-sm">Loading...</p>
      </div>
    </div>
  );
}
