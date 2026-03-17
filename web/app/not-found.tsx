import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Page not found",
  robots: {
    index: false,
    follow: false,
  },
};

export default function NotFound() {
  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center px-6">
      <div className="max-w-xl text-center">
        <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground/70 mb-4">
          404
        </p>
        <h1 className="text-3xl md:text-4xl font-medium tracking-tight mb-4">
          This page doesn&apos;t exist anymore.
        </h1>
        <p className="text-base md:text-lg text-muted-foreground/80 mb-8 leading-relaxed">
          The URL may be outdated, removed, or replaced during the product transition.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-full border border-border px-5 py-2.5 text-sm font-medium hover:bg-muted/50 transition-colors"
          >
            Go home
          </Link>
          <Link
            href="/blog"
            className="inline-flex items-center justify-center rounded-full border border-border px-5 py-2.5 text-sm font-medium hover:bg-muted/50 transition-colors"
          >
            Read the blog
          </Link>
          <Link
            href="/auth/login"
            className="inline-flex items-center justify-center rounded-full border border-border px-5 py-2.5 text-sm font-medium hover:bg-muted/50 transition-colors"
          >
            Open yarnnn
          </Link>
        </div>
      </div>
    </main>
  );
}
