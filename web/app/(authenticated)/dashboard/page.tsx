"use client";

/**
 * ADR-013: Conversation + Surfaces
 * Unified conversation interface - the primary authenticated view.
 * Projects are contextual lenses, not separate routes.
 */

import { useState, useEffect } from "react";
import { Chat } from "@/components/Chat";
import { Loader2, X, FolderOpen } from "lucide-react";
import { api } from "@/lib/api/client";
import { useSubscriptionGate } from "@/hooks/useSubscriptionGate";
import { UpgradePrompt } from "@/components/subscription";
import { useProjectContext } from "@/contexts/ProjectContext";

export default function Dashboard() {
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false);

  const { canCreateProject, projects } = useSubscriptionGate();
  const { activeProject, setActiveProject, refreshProjects } = useProjectContext();

  // Listen for "New Project" event from sidebar
  useEffect(() => {
    const handleOpenCreate = () => {
      // Check if user can create more projects
      if (canCreateProject) {
        setShowProjectModal(true);
      } else {
        setShowUpgradePrompt(true);
      }
    };
    window.addEventListener("openCreateProject", handleOpenCreate);
    return () => window.removeEventListener("openCreateProject", handleOpenCreate);
  }, [canCreateProject]);

  const handleCreateProject = async (name: string, description?: string) => {
    setIsCreating(true);
    try {
      const newProject = await api.projects.create({ name, description });
      setShowProjectModal(false);
      // Set the new project as active and refresh list
      setActiveProject({ id: newProject.id, name: newProject.name });
      refreshProjects();
      // Also trigger sidebar refresh
      window.dispatchEvent(new CustomEvent("refreshProjects"));
    } catch (err) {
      console.error("Failed to create project:", err);
      alert("Failed to create project");
    } finally {
      setIsCreating(false);
    }
  };

  // Determine context label
  const contextLabel = activeProject ? activeProject.name : "Dashboard";
  const chatEmptyMessage = activeProject
    ? `Hi! I'm your Thinking Partner. Let's work on "${activeProject.name}" together. I have access to this project's context and can help you analyze, create, or explore. What would you like to do?`
    : "Hi! I'm your Thinking Partner. I'm here to help you think through anything - ideas, problems, decisions, or just to chat. As we talk, I'll learn about you and remember what's important. What would you like to explore?";

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header - shows current context */}
      <header className="border-b border-border">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {activeProject && (
              <FolderOpen className="w-4 h-4 text-muted-foreground" />
            )}
            <h1 className="text-lg font-semibold">{contextLabel}</h1>
          </div>
          {activeProject && (
            <button
              onClick={() => setActiveProject(null)}
              className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded hover:bg-muted transition-colors"
            >
              Exit project
            </button>
          )}
        </div>
      </header>

      {/* Chat - full height conversation interface */}
      <div className="flex-1 flex overflow-hidden">
        <main className="flex-1 container mx-auto px-4 py-4 overflow-hidden">
          <Chat
            projectId={activeProject?.id}
            projectName={activeProject?.name}
            includeContext
            heightClass="h-full"
            emptyMessage={chatEmptyMessage}
          />
        </main>
      </div>

      {/* Create Project Modal */}
      {showProjectModal && (
        <CreateProjectModal
          onClose={() => setShowProjectModal(false)}
          onCreate={handleCreateProject}
          isCreating={isCreating}
        />
      )}

      {/* Upgrade Prompt for Project Limit */}
      {showUpgradePrompt && (
        <UpgradePrompt
          feature="projects"
          currentUsage={projects.current}
          onDismiss={() => setShowUpgradePrompt(false)}
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
              className="w-full px-3 py-2 border border-border rounded-md bg-background text-sm"
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
              className="w-full px-3 py-2 border border-border rounded-md bg-background resize-none text-sm"
            />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-border rounded-md text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || isCreating}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 inline-flex items-center gap-2 text-sm"
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
