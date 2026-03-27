import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ThemeShaderBackground } from "@/components/landing/ThemeShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import BlogPostList from "@/components/blog/BlogPostList";
import { getAllPosts } from "@/lib/blog";
import { BRAND, getMarketingMetadata } from "@/lib/metadata";

export const metadata = getMarketingMetadata({
  title: "Blog",
  description:
    "Practical ideas on AI workforce design, agent intelligence, task automation, context accumulation, and supervised autonomy.",
  path: "/blog",
  keywords: [
    "ai agent blog",
    "autonomous work",
    "context accumulation",
    "yarnnn blog",
    "agent intelligence",
  ],
});

export default function BlogPage() {
  const posts = getAllPosts();
  const listSchema = {
    "@context": "https://schema.org",
    "@type": "Blog",
    name: `${BRAND.name} Blog`,
    description:
      "Practical ideas on AI workforce design, agent intelligence, task automation, context accumulation, and supervised autonomy.",
    url: `${BRAND.url}/blog`,
    blogPost: posts.slice(0, 20).map((post) => ({
      "@type": "BlogPosting",
      headline: post.title,
      description: post.metaDescription,
      url: post.canonicalUrl,
      datePublished: post.date,
      dateModified: post.lastModified,
    })),
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-background text-foreground overflow-x-hidden">
      <GrainOverlay />
      <ThemeShaderBackground />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader />

        <main className="flex-1">
          <section className="max-w-2xl mx-auto px-6 py-24 md:py-32">
            <h1 className="text-4xl md:text-5xl font-medium mb-4 tracking-tight leading-[1.1]">Blog</h1>
            <p className="text-muted-foreground mb-16 max-w-lg">
              Notes on building an AI workforce — agent identity, task design, context accumulation,
              and what it means to supervise instead of execute.
            </p>

            <BlogPostList posts={posts} />
          </section>
        </main>

        <LandingFooter />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(listSchema) }}
      />
    </div>
  );
}
