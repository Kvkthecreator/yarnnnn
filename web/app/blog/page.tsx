import type { Metadata } from "next";
import Link from "next/link";
import { format } from "date-fns";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { getAllPosts } from "@/lib/blog";

export const metadata: Metadata = {
  title: "Blog",
  description:
    "Ideas on context-powered AI, autonomous work, and why your tools should get smarter the longer you use them.",
  openGraph: {
    title: "Blog | yarnnn",
    description:
      "Ideas on context-powered AI, autonomous work, and why your tools should get smarter the longer you use them.",
  },
};

export default function BlogPage() {
  const posts = getAllPosts();

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          <section className="max-w-2xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl font-medium mb-4 tracking-tight leading-[1.1]">
              Blog
            </h1>
            <p className="text-white/50 mb-16 max-w-lg">
              Ideas on context-powered AI, autonomous work, and why your tools
              should get smarter the longer you use them.
            </p>

            {posts.length === 0 ? (
              <p className="text-white/30">No posts yet. Check back soon.</p>
            ) : (
              <div className="space-y-12">
                {posts.map((post) => (
                  <article key={post.slug}>
                    <Link
                      href={`/blog/${post.slug}`}
                      className="group block"
                    >
                      <div className="flex items-center gap-3 text-sm text-white/30 mb-2">
                        <time dateTime={post.date}>
                          {format(new Date(post.date), "MMMM d, yyyy")}
                        </time>
                        <span>&middot;</span>
                        <span>{post.readingTime}</span>
                      </div>
                      <h2 className="text-xl md:text-2xl font-medium group-hover:text-white/80 transition-colors mb-2">
                        {post.title}
                      </h2>
                      <p className="text-white/50 leading-relaxed">
                        {post.description}
                      </p>
                    </Link>
                  </article>
                ))}
              </div>
            )}
          </section>
        </main>

        <LandingFooter inverted />
      </div>
    </div>
  );
}
