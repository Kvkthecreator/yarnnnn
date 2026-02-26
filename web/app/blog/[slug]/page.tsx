import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { format } from "date-fns";
import ReactMarkdown from "react-markdown";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ShaderBackgroundDark } from "@/components/landing/ShaderBackgroundDark";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { getPostBySlug, getPostSlugs } from "@/lib/blog";
import { BRAND } from "@/lib/metadata";

interface BlogPostPageProps {
  params: { slug: string };
}

export function generateStaticParams() {
  return getPostSlugs().map((slug) => ({ slug }));
}

export function generateMetadata({ params }: BlogPostPageProps): Metadata {
  const post = getPostBySlug(params.slug);
  if (!post) return {};

  return {
    title: post.title,
    description: post.metaDescription,
    keywords: post.tags,
    alternates: {
      canonical: post.canonicalUrl,
    },
    openGraph: {
      title: `${post.title} | ${BRAND.name}`,
      description: post.metaDescription,
      type: "article",
      publishedTime: post.date,
      modifiedTime: post.lastModified,
      authors: [post.author],
      url: post.canonicalUrl,
      images: [
        {
          url: post.imageUrl,
          width: 1200,
          height: 630,
          alt: post.title,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.metaDescription,
      images: [post.imageUrl],
    },
  };
}

export default function BlogPostPage({ params }: BlogPostPageProps) {
  const post = getPostBySlug(params.slug);
  if (!post) notFound();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    description: post.description,
    datePublished: post.date,
    dateModified: post.lastModified,
    image: [post.imageUrl],
    keywords: post.tags.join(", "),
    wordCount: post.wordCount,
    author: {
      "@type": "Organization",
      name: BRAND.name,
      url: BRAND.url,
    },
    publisher: {
      "@type": "Organization",
      name: BRAND.name,
      url: BRAND.url,
      logo: {
        "@type": "ImageObject",
        url: new URL(BRAND.ogImage, BRAND.url).toString(),
      },
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": post.canonicalUrl,
    },
    isAccessibleForFree: true,
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[#0f1419] text-white overflow-x-hidden">
      <GrainOverlay variant="dark" />
      <ShaderBackgroundDark />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader inverted />

        <main className="flex-1">
          <article className="max-w-2xl mx-auto px-6 py-24 md:py-32">
            {/* Back link */}
            <Link
              href="/blog"
              className="text-sm text-white/30 hover:text-white/60 transition-colors mb-8 inline-block"
            >
              &larr; Back to blog
            </Link>

            {/* Post header */}
            <header className="mb-12">
              <h1 className="text-3xl md:text-4xl lg:text-5xl font-medium tracking-tight leading-[1.1] mb-4">
                {post.title}
              </h1>
              <div className="flex items-center gap-3 text-sm text-white/30">
                <time dateTime={post.date}>
                  {format(new Date(post.date), "MMMM d, yyyy")}
                </time>
                <span>&middot;</span>
                <span>{post.readingTime}</span>
              </div>
            </header>

            {/* Post content */}
            <div className="prose prose-invert prose-lg max-w-none">
              <ReactMarkdown>{post.content}</ReactMarkdown>
            </div>
          </article>
        </main>

        <LandingFooter inverted />
      </div>

      {/* Structured data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
    </div>
  );
}
