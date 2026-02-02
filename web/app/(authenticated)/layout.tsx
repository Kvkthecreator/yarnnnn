import { Suspense } from "react";
import { ProjectProvider } from "@/contexts/ProjectContext";
import { WorkStatusProvider } from "@/contexts/WorkStatusContext";
import { SurfaceProvider } from "@/contexts/SurfaceContext";
import { TabProvider } from "@/contexts/TabContext";

/**
 * ADR-022: Tab-Based Supervision Architecture
 * ADR-016: Work status awareness in top bar
 *
 * Root layout for authenticated routes with tab-based supervision UI.
 * TP is always present at the bottom, tabs provide content navigation.
 *
 * Note: SurfaceProvider is kept temporarily for backwards compatibility
 * with WorkStatus component. Will be removed in future cleanup.
 */
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <WorkStatusProvider>
        <SurfaceProvider>
          <Suspense fallback={<TabProviderFallback />}>
            <TabProvider>
              {children}
            </TabProvider>
          </Suspense>
        </SurfaceProvider>
      </WorkStatusProvider>
    </ProjectProvider>
  );
}

function TabProviderFallback() {
  return (
    <div className="h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <h1 className="text-xl font-brand mb-2">yarnnn</h1>
        <p className="text-muted-foreground text-sm">Loading...</p>
      </div>
    </div>
  );
}
