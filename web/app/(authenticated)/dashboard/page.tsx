"use client";

import { useState, useEffect } from "react";
import { Chat } from "@/components/Chat";
import { UserContextPanel } from "@/components/UserContextPanel";
import { Loader2, Plus, X, User } from "lucide-react";
import { api } from "@/lib/api/client";

export default function Dashboard() {
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  // Listen for "New Project" event from sidebar
  useEffect(() => {
    const handleOpenCreate = () => setShowProjectModal(true);
    window.addEventListener("openCreateProject", handleOpenCreate);
    return () => window.removeEventListener("openCreateProject", handleOpenCreate);
  }, []);

  const handleCreateProject = async (name: string, description?: string) => {
    setIsCreating(true);
    try {
      await api.projects.create({ name, description });
      setShowProjectModal(false);
      // Reload to refresh sidebar projects list
      window.location.reload();
    } catch (err) {
      console.error("Failed to create project:", err);
      alert("Failed to create project");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border px-6 py-4 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-lg font-semibold">What&apos;s on your mind?</h1>
          <p className="text-sm text-muted-foreground">
            Chat with your Thinking Partner
          </p>
        </div>
        <button
          onClick={() => setRightPanelOpen(!rightPanelOpen)}
          className={`p-2 rounded-md transition-colors inline-flex items-center gap-2 text-sm ${
            rightPanelOpen
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted"
          }`}
          title="About You"
        >
          <User className="w-4 h-4" />
          <span className="hidden sm:inline">About You</span>
        </button>
      </div>

      {/* Main content area */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Chat Area */}
        <main className="flex-1 px-6 py-4 overflow-hidden">
          <Chat
            includeContext
            heightClass="h-full"
            emptyMessage="Hi! I'm your Thinking Partner. I'm here to help you think through anything - ideas, problems, decisions, or just to chat. As we talk, I'll learn about you and remember what's important. What would you like to explore?"
          />
        </main>

        {/* Right Sidebar - About You */}
        <UserContextPanel
          isOpen={rightPanelOpen}
          onClose={() => setRightPanelOpen(false)}
        />
      </div>

      {/* Create Project Modal */}
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
