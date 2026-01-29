"use client";

import { useState, useEffect } from "react";
import { Chat } from "@/components/Chat";
import { UserContextPanel } from "@/components/UserContextPanel";
import { Loader2, X, User, MessageSquare, FileText, Briefcase } from "lucide-react";
import { api } from "@/lib/api/client";

type Tab = "chat" | "context" | "work";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("chat");
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
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-border">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-xl font-semibold">Dashboard</h1>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="border-b border-border">
        <div className="container mx-auto px-4">
          <div className="flex gap-1">
            <TabButton
              active={activeTab === "chat"}
              onClick={() => setActiveTab("chat")}
              icon={<MessageSquare className="w-4 h-4" />}
              label="Chat"
            />
            <TabButton
              active={activeTab === "context"}
              onClick={() => setActiveTab("context")}
              icon={<FileText className="w-4 h-4" />}
              label="About You"
            />
          </div>
        </div>
      </nav>

      {/* Tab Content */}
      <div className="flex-1 flex overflow-hidden relative">
        <main className="flex-1 container mx-auto px-4 py-6 overflow-hidden">
          {activeTab === "chat" && (
            <Chat
              includeContext
              heightClass="h-full"
              emptyMessage="Hi! I'm your Thinking Partner. I'm here to help you think through anything - ideas, problems, decisions, or just to chat. As we talk, I'll learn about you and remember what's important. What would you like to explore?"
            />
          )}
          {activeTab === "context" && (
            <UserContextPanel
              isOpen={true}
              onClose={() => setActiveTab("chat")}
              inline
            />
          )}
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
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
        active
          ? "border-primary text-primary"
          : "border-transparent text-muted-foreground hover:text-foreground"
      }`}
    >
      {icon}
      {label}
    </button>
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
