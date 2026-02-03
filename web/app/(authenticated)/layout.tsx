import { Suspense } from 'react';
import AuthenticatedLayout from '@/components/shell/AuthenticatedLayout';

/**
 * ADR-023: Supervisor Desk Architecture
 *
 * Layout for authenticated routes:
 * - Single desk view (one surface at a time)
 * - TP always present at bottom
 * - Domain browser as escape hatch
 */
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<LayoutFallback />}>
      <AuthenticatedLayout>{children}</AuthenticatedLayout>
    </Suspense>
  );
}

function LayoutFallback() {
  return (
    <div className="h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <h1 className="text-xl font-brand mb-2">yarnnn</h1>
        <p className="text-muted-foreground text-sm">Loading...</p>
      </div>
    </div>
  );
}
