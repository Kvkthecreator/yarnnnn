import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// =============================================================================
// Tool Display Names (ADR-039: Claude Code-style status messages)
// =============================================================================

/**
 * Maps internal tool names to user-facing status messages.
 *
 * Pattern follows Claude Code:
 * - Present participle ("Checking...", "Creating...")
 * - Describes the action, not the tool
 * - Brief and scannable
 */
const TOOL_DISPLAY_NAMES: Record<string, string> = {
  // Communication tools
  respond: "Responding",
  clarify: "Asking for clarification",

  // Work tools
  create_work: "Creating work",
  list_work: "Listing work",
  get_work: "Getting work details",
  update_work: "Updating work",
  delete_work: "Deleting work",

  // Memory tools
  list_memories: "Searching memories",
  create_memory: "Saving to memory",
  update_memory: "Updating memory",
  delete_memory: "Removing memory",

  // Deliverable tools
  list_deliverables: "Listing deliverables",
  get_deliverable: "Getting deliverable",
  create_deliverable: "Creating deliverable",
  update_deliverable: "Updating deliverable",
  run_deliverable: "Running deliverable",

  // Platform operation tools (ADR-039)
  list_integrations: "Checking connected platforms",
  list_platform_resources: "Listing resources",
  sync_platform_resource: "Syncing data",
  get_sync_status: "Checking sync status",

  // Todo tracking
  todo_write: "Updating progress",
};

/**
 * Platform-specific resource messages for list_platform_resources.
 */
const PLATFORM_RESOURCE_MESSAGES: Record<string, string> = {
  slack: "Listing Slack channels",
  gmail: "Listing Gmail labels",
  notion: "Listing Notion pages",
  calendar: "Listing calendars",
};

/**
 * Platform-specific sync messages for sync_platform_resource.
 */
const PLATFORM_SYNC_MESSAGES: Record<string, string> = {
  slack: "Syncing Slack messages",
  gmail: "Syncing emails",
  notion: "Syncing Notion content",
  calendar: "Syncing calendar events",
};

/**
 * Get a human-readable status message for a tool call.
 *
 * @param toolName - The internal tool name
 * @param input - Optional tool input for context-aware messages
 * @returns User-facing status message
 */
export function getToolDisplayMessage(
  toolName: string,
  input?: Record<string, unknown>
): string {
  // Check for platform-specific messages
  if (toolName === "list_platform_resources" && input?.platform) {
    const platform = input.platform as string;
    return PLATFORM_RESOURCE_MESSAGES[platform] || `Listing ${platform} resources`;
  }

  if (toolName === "sync_platform_resource" && input?.platform) {
    const platform = input.platform as string;
    const resourceName = input.resource_name as string;
    if (resourceName) {
      return `Syncing ${resourceName}`;
    }
    return PLATFORM_SYNC_MESSAGES[platform] || `Syncing ${platform} data`;
  }

  if (toolName === "list_integrations") {
    return "Checking connected platforms";
  }

  if (toolName === "get_sync_status" && input?.platform) {
    const platform = input.platform as string;
    return `Checking ${platform} sync status`;
  }

  // Default: look up in mapping or format the tool name
  return TOOL_DISPLAY_NAMES[toolName] || formatToolName(toolName);
}

/**
 * Fallback formatter for unknown tools.
 * Converts snake_case to "Title Case..." format.
 */
function formatToolName(toolName: string): string {
  return toolName
    .split("_")
    .map((word, i) => i === 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word)
    .join(" ");
}
