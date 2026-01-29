"use client";

import { useState, useEffect, useRef } from "react";
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
import { ModeToggle } from "@/components/mode-toggle";

interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

interface SidebarProps {
  userEmail?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export default function Sidebar({
  userEmail,
  open = true,
  onOpenChange,
}: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();

  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Mobile detection
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      const wasMobile = isMobile;
      setIsMobile(mobile);

      // Auto-close sidebar when switching to mobile
      if (mobile && !wasMobile && open) {
        onOpenChange?.(false);
      }
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, [isMobile, open, onOpenChange]);

  // Body scroll lock on mobile when sidebar is open
  useEffect(() => {
    if (!isMobile) return;
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [isMobile, open]);

  // Fetch projects
  const fetchProjects = async () => {
    try {
      const data = await api.projects.list();
      setProjects(data);
    } catch (err) {
      console.error("Failed to fetch projects:", err);
    } finally {
      setIsLoadingProjects(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  // Listen for project refresh events (e.g., when TP creates a project)
  useEffect(() => {
    const handleRefreshProjects = () => {
      fetchProjects();
    };
    window.addEventListener("refreshProjects", handleRefreshProjects);
    return () => window.removeEventListener("refreshProjects", handleRefreshProjects);
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.replace("/auth/login");
  };

  const handleNewProject = () => {
    window.dispatchEvent(new CustomEvent("openCreateProject"));
    if (isMobile) onOpenChange?.(false);
  };

  const handleNavClick = () => {
    if (isMobile) onOpenChange?.(false);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownOpen && dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [dropdownOpen]);

  return (
    <>
      {/* Mobile scrim/overlay */}
      {isMobile && (
        <div
          aria-hidden
          onClick={() => onOpenChange?.(false)}
          className={cn(
            "fixed inset-0 z-40 bg-black/40 transition-opacity md:hidden",
            open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
          )}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "sidebar w-64 border-r border-border flex flex-col h-screen z-50 transition-transform duration-300",
          isMobile
            ? "fixed top-0 left-0 bg-background shadow-xl"
            : "sticky top-0 bg-muted/30",
          open ? "translate-x-0" : "-translate-x-full",
          !open && !isMobile && "hidden"
        )}
      >
        {/* Header */}
        <div className="p-3 border-b border-border flex items-center justify-between">
          <Link
            href="/dashboard"
            className="text-xl font-brand"
            onClick={handleNavClick}
          >
            yarnnn
          </Link>
          <div className="flex items-center gap-1">
            <ModeToggle />
            <button
              onClick={() => onOpenChange?.(false)}
              className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Close sidebar"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Main Navigation */}
        <nav className="p-2">
          <Link
            href="/dashboard"
            onClick={handleNavClick}
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
                    onClick={handleNavClick}
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
        <div className="relative border-t border-border px-4 py-3">
          {userEmail ? (
            <div className="relative w-full" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="text-sm text-muted-foreground hover:text-foreground w-full text-left truncate"
              >
                {userEmail}
              </button>
              {dropdownOpen && (
                <div className="absolute bottom-12 left-0 w-48 rounded-md border border-border bg-background shadow-md z-50 py-1 text-sm">
                  <Link
                    href="/settings"
                    onClick={() => {
                      setDropdownOpen(false);
                      handleNavClick();
                    }}
                    className="flex w-full items-center gap-2 px-4 py-2 hover:bg-muted text-muted-foreground hover:text-foreground"
                  >
                    <Settings className="h-4 w-4" />
                    Settings
                  </Link>
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      handleSignOut();
                    }}
                    className="flex w-full items-center gap-2 px-4 py-2 text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    <LogOut className="h-4 w-4" />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Not signed in</p>
          )}
        </div>
      </aside>
    </>
  );
}
