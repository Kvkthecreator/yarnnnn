import { Suspense } from 'react';
import { ContextSidebar } from '@/components/context/ContextSidebar';

export default function ContextLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-full bg-background min-h-0">
      <div className="h-full min-h-0 flex">
        <aside className="hidden md:block md:w-56 lg:w-64 shrink-0 h-full min-h-0">
          <Suspense fallback={<div className="h-full border-r border-border bg-muted/50" />}>
            <ContextSidebar />
          </Suspense>
        </aside>
        <div className="flex-1 min-h-0 overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
}
