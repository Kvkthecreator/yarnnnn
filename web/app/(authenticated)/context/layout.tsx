import { Suspense } from 'react';
import { ContextSidebar } from '@/components/context/ContextSidebar';

export default function ContextLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <div className="flex-1 flex overflow-hidden">
        <Suspense fallback={<div className="w-48 flex-shrink-0 border-r border-border bg-muted/50" />}>
          <ContextSidebar />
        </Suspense>
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </div>
    </div>
  );
}
