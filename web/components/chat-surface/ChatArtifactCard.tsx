'use client';

import type { ReactNode } from 'react';

interface ChatArtifactCardProps {
  children: ReactNode;
}

export function ChatArtifactCard({ children }: ChatArtifactCardProps) {
  return (
    <section className="mx-auto max-h-[38vh] w-full max-w-4xl overflow-y-auto">
      {children}
    </section>
  );
}
