import AuthenticatedLayout from "@/components/shell/AuthenticatedLayout";
import { SurfaceProvider } from "@/contexts/SurfaceContext";
import { ProjectProvider } from "@/contexts/ProjectContext";
import { WorkStatusProvider } from "@/contexts/WorkStatusContext";
import { SurfaceRouter } from "@/components/surfaces";

/**
 * ADR-013: Conversation + Surfaces
 * ADR-016: Work status awareness in top bar
 * Root layout for authenticated routes with surface/drawer system
 */
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <WorkStatusProvider>
        <SurfaceProvider>
          <AuthenticatedLayout>
            {children}
            <SurfaceRouter />
          </AuthenticatedLayout>
        </SurfaceProvider>
      </WorkStatusProvider>
    </ProjectProvider>
  );
}
