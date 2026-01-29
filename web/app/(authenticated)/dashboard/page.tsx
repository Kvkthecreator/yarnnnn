"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api/client";
import { Chat } from "@/components/Chat";
import { UserContextPanel } from "@/components/UserContextPanel";
import {
  Loader2,
  Plus,
  X,
  ChevronLeft,
  ChevronRight,
  FolderOpen,
  Upload,
  Settings,
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false);

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

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-screen flex overflow-hidden">
      {/* Left Sidebar - Projects */}
      <aside
        className={`border-r border-border bg-muted/30 flex flex-col transition-all duration-200 ${
          sidebarCollapsed ? "w-12" : "w-64"
        }`}
      >
        {/* Sidebar Header */}
        <div className="p-3 border-b border-border flex items-center justify-between">
          {!sidebarCollapsed && (
            <span className="text-sm font-medium text-muted-foreground">
              Projects
            </span>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1 hover:bg-muted rounded"
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* New Project Button */}
        {!sidebarCollapsed && (
          <div className="p-3">
            <button
              onClick={() => setShowProjectModal(true)}
              className="w-full px-3 py-2 text-sm bg-primary text-primary-foreground rounded-md inline-flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              New Project
            </button>
          </div>
        )}

        {/* Projects List */}
        <div className="flex-1 overflow-y-auto">
          {sidebarCollapsed ? (
            <div className="p-2">
              <button
                onClick={() => setShowProjectModal(true)}
                className="w-full p-2 hover:bg-muted rounded"
                title="New Project"
              >
                <Plus className="w-4 h-4 mx-auto" />
              </button>
            </div>
          ) : (
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
                    className="block px-3 py-2 text-sm rounded-md hover:bg-muted transition-colors truncate"
                    title={project.name}
                  >
                    <FolderOpen className="w-4 h-4 inline-block mr-2 text-muted-foreground" />
                    {project.name}
                  </Link>
                ))
              )}
            </div>
          )}
        </div>
      </aside>

      {/* Main Content - Chat First */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Quick Actions Bar */}
        <div className="border-b border-border px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold">
                What&apos;s on your mind?
              </h1>
              <p className="text-sm text-muted-foreground">
                Chat with your Thinking Partner - no project needed
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowProjectModal(true)}
                className="px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted transition-colors inline-flex items-center gap-1"
              >
                <Plus className="w-4 h-4" />
                New Project
              </button>
              <button
                className="px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted transition-colors inline-flex items-center gap-1"
                title="Coming soon"
                disabled
              >
                <Upload className="w-4 h-4" />
                Import
              </button>
              <Link
                href="/settings"
                className="px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted transition-colors inline-flex items-center gap-1"
              >
                <Settings className="w-4 h-4" />
                Settings
              </Link>
            </div>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 px-6 py-4 overflow-hidden">
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
        collapsed={rightPanelCollapsed}
        onToggleCollapse={() => setRightPanelCollapsed(!rightPanelCollapsed)}
      />

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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background border border-border rounded-lg p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Create Project</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
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
              className="w-full px-3 py-2 border border-border rounded-md bg-background"
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
              className="w-full px-3 py-2 border border-border rounded-md bg-background resize-none"
            />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-border rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || isCreating}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 inline-flex items-center gap-2"
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
