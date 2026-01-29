"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api/client";
import {
  LayoutDashboard,
  Settings,
  LogOut,
  FolderOpen,
  Plus,
  ChevronLeft,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

interface SidebarProps {
  userEmail?: string;
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function Sidebar({
  userEmail,
  collapsed = false,
  onCollapsedChange,
}: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();

  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);

  // Fetch projects
  useEffect(() => {
    async function fetchProjects() {
      try {
        const data = await api.projects.list();
        setProjects(data);
      } catch (err) {
        console.error("Failed to fetch projects:", err);
      } finally {
        setIsLoadingProjects(false);
      }
    }
    fetchProjects();
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.replace("/auth/login");
  };

  const handleNewProject = () => {
    // Emit event for dashboard to open create modal
    window.dispatchEvent(new CustomEvent("openCreateProject"));
  };

  if (collapsed) {
    return null;
  }

  return (
    <aside className="w-64 border-r border-border bg-muted/30 flex flex-col h-screen sticky top-0">
      {/* Header with collapse toggle */}
      <div className="p-3 border-b border-border flex items-center justify-between">
        <Link href="/dashboard" className="text-xl font-bold">
          YARNNN
        </Link>
        <button
          onClick={() => onCollapsedChange?.(true)}
          className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Collapse sidebar"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* Main Navigation */}
      <nav className="p-2">
        <Link
          href="/dashboard"
          className={cn(
            "flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors",
            pathname === "/dashboard"
              ? "bg-primary/10 text-primary font-medium"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <LayoutDashboard className="h-4 w-4" />
          Dashboard
        </Link>
      </nav>

      {/* Projects Section */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="px-3 py-2 flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Projects
          </span>
          <button
            onClick={handleNewProject}
            className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors"
            title="New Project"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2">
          {isLoadingProjects ? (
            <div className="flex justify-center py-4">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          ) : projects.length === 0 ? (
            <p className="text-xs text-muted-foreground px-3 py-2">
              No projects yet
            </p>
          ) : (
            <div className="space-y-0.5">
              {projects.map((project) => (
                <Link
                  key={project.id}
                  href={`/projects/${project.id}`}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors truncate",
                    pathname === `/projects/${project.id}`
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                  title={project.name}
                >
                  <FolderOpen className="w-4 h-4 shrink-0" />
                  <span className="truncate">{project.name}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border p-2 space-y-0.5">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors",
            pathname === "/settings"
              ? "bg-primary/10 text-primary font-medium"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <Settings className="h-4 w-4" />
          Settings
        </Link>

        {userEmail && (
          <p className="text-xs text-muted-foreground truncate px-3 py-1">
            {userEmail}
          </p>
        )}

        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground rounded-md transition-colors w-full"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
