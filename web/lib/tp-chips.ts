/**
 * ADR-023: Supervisor Desk Architecture
 * TP chip configuration based on current surface
 */

import { DeskSurface, Chip } from '@/types/desk';

/**
 * Get contextual chips based on current desk surface
 */
export function getChipsForSurface(surface: DeskSurface): Chip[] {
  switch (surface.type) {
    case 'deliverable-review':
      return [
        { label: 'Shorter', prompt: 'Make this more concise' },
        { label: 'More detail', prompt: 'Add more detail to this' },
        { label: 'More formal', prompt: 'Make the tone more formal' },
        { label: 'Simpler', prompt: 'Use simpler language' },
      ];

    case 'deliverable-detail':
      return [
        { label: 'Run now', prompt: 'Generate a new version now' },
        { label: 'History', prompt: 'Show me the version history' },
        { label: 'Settings', prompt: 'I want to change the settings' },
      ];

    case 'context-browser':
      return [
        { label: 'Add memory', prompt: 'I want to tell you something to remember' },
        { label: 'What do you know?', prompt: 'Summarize what you know about me' },
      ];

    case 'context-editor':
      return [
        { label: 'Update this', prompt: 'I want to update this memory' },
        { label: 'Delete this', prompt: 'Please delete this memory' },
      ];

    case 'work-output':
      return [
        { label: 'Summarize', prompt: 'Give me the key points from this' },
        { label: 'Save insight', prompt: 'Remember the key findings from this work' },
        { label: 'Run again', prompt: 'Run this work again with the same parameters' },
      ];

    case 'work-list':
      return [
        { label: 'New research', prompt: 'I need you to research something' },
        { label: 'New content', prompt: 'I need you to write something' },
      ];

    case 'document-viewer':
      return [
        { label: 'Summarize', prompt: 'Summarize this document' },
        { label: 'Key points', prompt: 'What are the key points from this document?' },
      ];

    case 'document-list':
      return [
        { label: 'Upload', prompt: 'I want to upload a document' },
      ];

    case 'project-detail':
      return [
        { label: 'Rename', prompt: 'I want to rename this project' },
        { label: 'Context', prompt: 'Show me the context for this project' },
      ];

    case 'project-list':
      return [
        { label: 'New project', prompt: 'Create a new project' },
      ];

    case 'idle':
    default:
      return [
        { label: 'Weekly report', prompt: 'I need to send weekly status reports' },
        { label: 'Research', prompt: 'I need you to research something' },
        { label: 'My context', prompt: 'Show me what you know about me' },
      ];
  }
}

/**
 * Get surface context description for TP
 */
export function getSurfaceContextDescription(surface: DeskSurface): string {
  switch (surface.type) {
    case 'deliverable-review':
      return `User is reviewing a deliverable draft (version ${surface.versionId})`;
    case 'deliverable-detail':
      return `User is viewing deliverable details (${surface.deliverableId})`;
    case 'context-browser':
      return `User is browsing ${surface.scope} context`;
    case 'context-editor':
      return `User is editing a memory`;
    case 'work-output':
      return `User is viewing work output`;
    case 'work-list':
      return `User is viewing their work list`;
    case 'document-viewer':
      return `User is viewing a document`;
    case 'document-list':
      return `User is viewing their documents`;
    case 'project-detail':
      return `User is viewing a project`;
    case 'project-list':
      return `User is viewing their projects`;
    case 'idle':
    default:
      return `User is on the home screen`;
  }
}
