import { Suspense } from "react";
import { ProjectProvider } from "@/contexts/ProjectContext";
import { WorkStatusProvider } from "@/contexts/WorkStatusContext";
import { SurfaceProvider } from "@/contexts/SurfaceContext";
import { TabProvider } from "@/contexts/TabContext";
import { SurfaceRouter } from "@/components/surfaces";

/**
 * ADR-022: Chat-First Tab Architecture
 *
 * Layout for authenticated routes:
 * - Chat tab is home (always present)
 * - Output tabs open for deliverables, versions, etc.
 * - Drawer available within tabs for TP chat
 */
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <WorkStatusProvider>
        <SurfaceProvider>
          <TabProvider>
            <Suspense fallback={<LayoutFallback />}>
              {children}
              <SurfaceRouter />
            </Suspense>
          </TabProvider>
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
