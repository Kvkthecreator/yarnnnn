'use client';

/**
 * ADR-020: Inline Content Refinement
 *
 * Hook for refining content directly without opening a separate chat.
 * Sends the current content + instruction to TP and returns refined content.
 */

import { useState, useCallback, useRef } from 'react';
import { createClient } from '@/lib/supabase/client';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface UseContentRefinementOptions {
  deliverableId: string;
  deliverableTitle?: string;
  deliverableType?: string;
}

interface UseContentRefinementReturn {
  refineContent: (currentContent: string, instruction: string) => Promise<string | null>;
  isRefining: boolean;
  error: string | null;
}

/**
 * Hook for inline content refinement.
 * Calls TP with the current content and instruction, returns refined content.
 */
export function useContentRefinement({
  deliverableId,
  deliverableTitle,
  deliverableType,
}: UseContentRefinementOptions): UseContentRefinementReturn {
  const [isRefining, setIsRefining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const refineContent = useCallback(
    async (currentContent: string, instruction: string): Promise<string | null> => {
      if (!currentContent.trim() || !instruction.trim()) {
        return null;
      }

      // Cancel any existing request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      setIsRefining(true);
      setError(null);

      try {
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (!session?.access_token) {
          throw new Error('Not authenticated');
        }

        // Build the refinement prompt with context
        const prompt = `I'm reviewing my "${deliverableTitle || 'deliverable'}" (${deliverableType || 'content'}). Here is the current draft:

---
${currentContent}
---

Please refine this content based on the following instruction: ${instruction}

IMPORTANT: Return ONLY the refined content, no explanations or commentary. The output should be ready to replace the current draft directly.`;

        const response = await fetch(`${API_BASE_URL}/api/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            content: prompt,
            include_context: false, // Don't need extra context for refinement
          }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(errorData?.detail || `Request failed: ${response.status}`);
        }

        // Handle SSE stream - collect the full response
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body');
        }

        const decoder = new TextDecoder();
        let refinedContent = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.error) {
                  throw new Error(data.error);
                }

                if (data.content) {
                  refinedContent += data.content;
                }

                if (data.done) {
                  break;
                }
              } catch (parseError) {
                // Ignore parse errors for incomplete chunks
              }
            }
          }
        }

        return refinedContent.trim() || null;
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          return null;
        }

        const errorMessage =
          err instanceof Error ? err.message : 'Failed to refine content';
        setError(errorMessage);
        return null;
      } finally {
        setIsRefining(false);
        abortControllerRef.current = null;
      }
    },
    [deliverableTitle, deliverableType]
  );

  return {
    refineContent,
    isRefining,
    error,
  };
}
