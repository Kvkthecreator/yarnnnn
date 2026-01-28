import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-4">YARNNN</h1>
      <p className="text-muted-foreground mb-8">
        Context-aware AI work platform
      </p>
      <div className="flex gap-4">
        <Link
          href="/auth/login"
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md"
        >
          Login
        </Link>
        <Link
          href="/dashboard"
          className="px-4 py-2 border border-border rounded-md"
        >
          Dashboard
        </Link>
      </div>
    </main>
  );
}
