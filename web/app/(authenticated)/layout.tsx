import AuthenticatedLayout from "@/components/shell/AuthenticatedLayout";
import { SurfaceProvider } from "@/contexts/SurfaceContext";
import { ProjectProvider } from "@/contexts/ProjectContext";
import { WorkStatusProvider } from "@/contexts/WorkStatusContext";
import { FloatingChatProvider } from "@/contexts/FloatingChatContext";
import { SurfaceRouter } from "@/components/surfaces";
import { FloatingChatPanel } from "@/components/FloatingChatPanel";
import { FloatingChatTrigger } from "@/components/FloatingChatTrigger";

/**
 * ADR-013: Conversation + Surfaces
 * ADR-016: Work status awareness in top bar
 * ADR-020: Floating contextual chat
 * Root layout for authenticated routes with surface/drawer system
 */
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <WorkStatusProvider>
        <SurfaceProvider>
          <FloatingChatProvider>
            <AuthenticatedLayout>
              {children}
              <SurfaceRouter />
              <FloatingChatPanel />
              <FloatingChatTrigger />
            </AuthenticatedLayout>
          </FloatingChatProvider>
        </SurfaceProvider>
      </WorkStatusProvider>
    </ProjectProvider>
  );
}
