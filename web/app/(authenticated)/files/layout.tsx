/**
 * Files layout — pass-through.
 * The Files page has its own Explorer sidebar built in.
 */
export default function FilesLayout({ children }: { children: React.ReactNode }) {
  return <div className="h-full min-h-0">{children}</div>;
}
