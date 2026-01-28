import Link from "next/link";

// TODO: Fetch projects from API
const mockProjects = [
  { id: "1", name: "Q1 Planning", blockCount: 24, ticketCount: 3 },
  { id: "2", name: "Product Research", blockCount: 12, ticketCount: 1 },
];

export default function Dashboard() {
  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold">Projects</h1>
        <button className="px-4 py-2 bg-primary text-primary-foreground rounded-md">
          + New Project
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {mockProjects.map((project) => (
          <Link
            key={project.id}
            href={`/projects/${project.id}`}
            className="block p-6 border border-border rounded-lg hover:border-primary transition-colors"
          >
            <h2 className="text-lg font-semibold mb-2">{project.name}</h2>
            <div className="text-sm text-muted-foreground">
              <span>{project.blockCount} blocks</span>
              <span className="mx-2">·</span>
              <span>{project.ticketCount} tickets</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
