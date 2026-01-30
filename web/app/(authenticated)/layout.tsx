import AuthenticatedLayout from "@/components/shell/AuthenticatedLayout";
import { SurfaceProvider } from "@/contexts/SurfaceContext";
import { ProjectProvider } from "@/contexts/ProjectContext";
import { SurfaceRouter } from "@/components/surfaces";

/**
 * ADR-013: Conversation + Surfaces
 * Root layout for authenticated routes with surface/drawer system
 */
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <SurfaceProvider>
        <AuthenticatedLayout>
          {children}
          <SurfaceRouter />
        </AuthenticatedLayout>
      </SurfaceProvider>
    </ProjectProvider>
  );
}
