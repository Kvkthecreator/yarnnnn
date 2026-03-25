/**
 * Context layout — pass-through (ADR-139).
 * The context page has its own Explorer sidebar built in.
 * Legacy ContextSidebar removed.
 */
export default function ContextLayout({ children }: { children: React.ReactNode }) {
  return <div className="h-full min-h-0">{children}</div>;
}
