"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/client";
import { createClient } from "@/lib/supabase/client";
import { Chat } from "@/components/Chat";
import { UserContextPanel } from "@/components/UserContextPanel";
import {
  Loader2,
  Plus,
  X,
  FolderOpen,
  Settings,
  LogOut,
  User,
  Menu,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";

interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  // Sidebar states - mobile uses overlay, desktop uses inline
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const router = useRouter();
  const supabase = createClient();

  // Fetch projects on mount
  useEffect(() => {
    async function fetchProjects() {
      try {
        const data = await api.projects.list();
        setProjects(data);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch projects:", err);
        setError("Failed to load projects");
      } finally {
        setIsLoading(false);
      }
    }
    fetchProjects();
  }, []);

  // Close sidebars when clicking outside on mobile
  const closeSidebars = () => {
    setSidebarOpen(false);
    setRightPanelOpen(false);
  };

  const handleCreateProject = async (name: string, description?: string) => {
    setIsCreating(true);
    try {
      const newProject = await api.projects.create({
        name,
        description,
      });
      setProjects((prev) => [...prev, newProject]);
      setShowProjectModal(false);
    } catch (err) {
      console.error("Failed to create project:", err);
      alert("Failed to create project");
    } finally {
      setIsCreating(false);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.replace("/auth/login");
  };

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Top Header Bar */}
      <header className="h-14 border-b border-border flex items-center justify-between px-3 md:px-4 shrink-0">
        <div className="flex items-center gap-2">
          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-muted rounded-md transition-colors md:hidden"
            aria-label="Toggle projects sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Desktop sidebar toggle */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="hidden md:flex p-2 hover:bg-muted rounded-md transition-colors"
            aria-label={sidebarOpen ? "Hide projects" : "Show projects"}
          >
            {sidebarOpen ? (
              <PanelLeftClose className="w-5 h-5" />
            ) : (
              <PanelLeft className="w-5 h-5" />
            )}
          </button>

          <Link href="/dashboard" className="text-xl font-bold">
            YARNNN
          </Link>
        </div>

        <div className="flex items-center gap-1 md:gap-2">
          {/* About You toggle */}
          <button
            onClick={() => setRightPanelOpen(!rightPanelOpen)}
            className={`p-2 md:px-3 md:py-1.5 text-sm rounded-md transition-colors inline-flex items-center gap-1 ${
              rightPanelOpen
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted"
            }`}
            title="About You"
          >
            <User className="w-5 h-5 md:w-4 md:h-4" />
            <span className="hidden md:inline">About You</span>
          </button>

          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              aria-label="Settings menu"
            >
              <Settings className="w-5 h-5 md:w-4 md:h-4" />
            </button>

            {showUserMenu && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setShowUserMenu(false)}
                />
                <div className="absolute right-0 top-full mt-1 w-48 bg-background border border-border rounded-md shadow-lg z-50">
                  <Link
                    href="/settings"
                    className="flex items-center gap-2 px-4 py-3 md:py-2 text-sm hover:bg-muted"
                    onClick={() => setShowUserMenu(false)}
                  >
                    <Settings className="w-4 h-4" />
                    Settings
                  </Link>
                  <button
                    onClick={handleSignOut}
                    className="flex items-center gap-2 px-4 py-3 md:py-2 text-sm hover:bg-muted w-full text-left text-destructive"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Mobile overlay backdrop */}
        {(sidebarOpen || rightPanelOpen) && (
          <div
            className="fixed inset-0 bg-black/50 z-30 md:hidden"
            onClick={closeSidebars}
          />
        )}

        {/* Left Sidebar - Projects */}
        <aside
          className={`
            fixed md:relative inset-y-0 left-0 z-40 md:z-0
            w-72 md:w-56 lg:w-64
            border-r border-border bg-background md:bg-muted/30
            flex flex-col
            transform transition-transform duration-200 ease-in-out
            ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0 md:hidden"}
            ${sidebarOpen ? "md:flex" : "md:hidden"}
          `}
          style={{ top: "56px" }} // Below header on mobile
        >
          {/* Sidebar Header */}
          <div className="p-3 border-b border-border flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">
              Projects
            </span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-1.5 hover:bg-muted rounded md:hidden"
              aria-label="Close sidebar"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* New Project Button */}
          <div className="p-3">
            <button
              onClick={() => {
                setShowProjectModal(true);
                setSidebarOpen(false); // Close on mobile after action
              }}
              className="w-full px-3 py-2.5 md:py-2 text-sm bg-primary text-primary-foreground rounded-md inline-flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              New Project
            </button>
          </div>

          {/* Projects List */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-2 space-y-1">
              {projects.length === 0 ? (
                <p className="text-xs text-muted-foreground px-2 py-4 text-center">
                  No projects yet
                </p>
              ) : (
                projects.map((project) => (
                  <Link
                    key={project.id}
                    href={`/projects/${project.id}`}
                    className="block px-3 py-2.5 md:py-2 text-sm rounded-md hover:bg-muted transition-colors truncate"
                    title={project.name}
                    onClick={() => setSidebarOpen(false)} // Close on mobile
                  >
                    <FolderOpen className="w-4 h-4 inline-block mr-2 text-muted-foreground" />
                    {project.name}
                  </Link>
                ))
              )}
            </div>
          </div>
        </aside>

        {/* Main Content - Chat */}
        <main className="flex-1 flex flex-col min-w-0">
          {/* Chat Header */}
          <div className="border-b border-border px-4 md:px-6 py-3">
            <h1 className="text-lg font-semibold">What&apos;s on your mind?</h1>
            <p className="text-sm text-muted-foreground">
              Chat with your Thinking Partner
            </p>
          </div>

          {/* Chat Area */}
          <div className="flex-1 px-4 md:px-6 py-4 overflow-hidden">
            {error ? (
              <div className="p-4 bg-destructive/10 text-destructive rounded-lg">
                {error}
              </div>
            ) : (
              <Chat
                includeContext
                heightClass="h-full"
                emptyMessage="Hi! I'm your Thinking Partner. I'm here to help you think through anything - ideas, problems, decisions, or just to chat. As we talk, I'll learn about you and remember what's important. What would you like to explore?"
              />
            )}
          </div>
        </main>

        {/* Right Sidebar - About You */}
        <UserContextPanel
          isOpen={rightPanelOpen}
          onClose={() => setRightPanelOpen(false)}
        />
      </div>

      {/* Modals */}
      {showProjectModal && (
        <CreateProjectModal
          onClose={() => setShowProjectModal(false)}
          onCreate={handleCreateProject}
          isCreating={isCreating}
        />
      )}
    </div>
  );
}

function CreateProjectModal({
  onClose,
  onCreate,
  isCreating,
}: {
  onClose: () => void;
  onCreate: (name: string, description?: string) => void;
  isCreating: boolean;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onCreate(name.trim(), description.trim() || undefined);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-lg p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Create Project</h2>
          <button
            onClick={onClose}
            className="p-1 text-muted-foreground hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              Project Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Project"
              className="w-full px-3 py-2.5 md:py-2 border border-border rounded-md bg-background text-base md:text-sm"
              autoFocus
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              Description (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this project about?"
              rows={3}
              className="w-full px-3 py-2.5 md:py-2 border border-border rounded-md bg-background resize-none text-base md:text-sm"
            />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 md:py-2 border border-border rounded-md text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || isCreating}
              className="px-4 py-2.5 md:py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 inline-flex items-center gap-2 text-sm"
            >
              {isCreating && <Loader2 className="w-4 h-4 animate-spin" />}
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
