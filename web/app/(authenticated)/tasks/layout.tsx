/**
 * Tasks layout — pass-through.
 * The task surface handles its own three-panel layout.
 */
export default function TasksLayout({ children }: { children: React.ReactNode }) {
  return <div className="h-full min-h-0">{children}</div>;
}
