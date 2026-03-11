import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { format } from "date-fns";
import ReactMarkdown from "react-markdown";
import LandingHeader from "@/components/landing/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import { ThemeShaderBackground } from "@/components/landing/ThemeShaderBackground";
import { GrainOverlay } from "@/components/landing/GrainOverlay";
import { getPostBySlug, getPostSlugs, getRelatedPosts, getSeriesPosts } from "@/lib/blog";
import { BRAND } from "@/lib/metadata";

interface BlogPostPageProps {
  params: { slug: string };
}

function getDisplayAuthor(author: string): string {
  return author === "kvk" ? "Kevin Kim" : author;
}

function cleanHeadingText(value: string): string {
  return value
    .replace(/\[(.*?)\]\((.*?)\)/g, "$1")
    .replace(/[`*_#>~]/g, "")
    .trim();
}

function extractSectionHeadings(markdown: string, max = 5): string[] {
  const regex = /^##\s+(.+)$/gm;
  const headings: string[] = [];
  let match: RegExpExecArray | null = regex.exec(markdown);

  while (match && headings.length < max) {
    const cleaned = cleanHeadingText(match[1]);
    if (cleaned) headings.push(cleaned);
    match = regex.exec(markdown);
  }

  return headings;
}

export function generateStaticParams() {
  return getPostSlugs().map((slug) => ({ slug }));
}

export function generateMetadata({ params }: BlogPostPageProps): Metadata {
  const post = getPostBySlug(params.slug);
  if (!post) return {};
  const authorName = getDisplayAuthor(post.author);
  const metadataTitle = post.metaTitle || post.title;

  return {
    title: metadataTitle,
    description: post.metaDescription,
    keywords: post.tags,
    category: post.category === "opinion" ? "Opinion" : "Core",
    authors: [{ name: authorName }],
    robots: {
      index: true,
      follow: true,
    },
    alternates: {
      canonical: post.canonicalUrl,
    },
    openGraph: {
      title: `${metadataTitle} | ${BRAND.name}`,
      description: post.metaDescription,
      type: "article",
      publishedTime: post.date,
      modifiedTime: post.lastModified,
      authors: [authorName],
      tags: post.tags,
      url: post.canonicalUrl,
      images: [
        {
          url: post.imageUrl,
          width: 1200,
          height: 630,
          alt: metadataTitle,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: metadataTitle,
      description: post.metaDescription,
      images: [post.imageUrl],
    },
  };
}

export default function BlogPostPage({ params }: BlogPostPageProps) {
  const post = getPostBySlug(params.slug);
  if (!post) notFound();
  const authorName = getDisplayAuthor(post.author);
  const sectionHeadings = extractSectionHeadings(post.content);
  const relatedPosts = getRelatedPosts(post.slug, 3);
  const seriesPosts = post.series ? getSeriesPosts(post.series) : [];
  const seriesUrl = post.series ? `${BRAND.url}/blog` : undefined;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    description: post.metaDescription || post.description,
    url: post.canonicalUrl,
    datePublished: post.date,
    dateModified: post.lastModified,
    inLanguage: "en-US",
    image: [post.imageUrl],
    keywords: post.tags.join(", "),
    articleSection: post.category === "opinion" ? "Opinion" : "Core",
    about: post.tags.map((tag) => ({
      "@type": "Thing",
      name: tag,
    })),
    wordCount: post.wordCount,
    relatedLink: relatedPosts.map((related) => related.canonicalUrl),
    isPartOf: post.series
      ? {
          "@type": "Blog",
          name: post.series,
          url: seriesUrl,
        }
      : undefined,
    author:
      post.category === "opinion"
        ? {
            "@type": "Person",
            name: authorName,
          }
        : {
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
  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Home",
        item: BRAND.url,
      },
      {
        "@type": "ListItem",
        position: 2,
        name: "Blog",
        item: `${BRAND.url}/blog`,
      },
      {
        "@type": "ListItem",
        position: 3,
        name: post.title,
        item: post.canonicalUrl,
      },
    ],
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-background text-foreground overflow-x-hidden">
      <GrainOverlay />
      <ThemeShaderBackground />

      <div className="relative z-10 flex flex-col min-h-screen">
        <LandingHeader />

        <main className="flex-1">
          <article className="max-w-2xl mx-auto px-6 py-24 md:py-32">
            {/* Back link */}
            <Link
              href="/blog"
              className="text-sm text-muted-foreground/60 hover:text-muted-foreground transition-colors mb-8 inline-block"
            >
              &larr; Back to blog
            </Link>

            {/* Post header */}
            <header className="mb-12">
              <h1 className="text-3xl md:text-4xl lg:text-5xl font-medium tracking-tight leading-[1.1] mb-4">
                {post.title}
              </h1>
              <div className="flex items-center gap-3 text-sm text-muted-foreground/60">
                <time dateTime={post.date}>
                  {format(new Date(post.date), "MMMM d, yyyy")}
                </time>
                <span>&middot;</span>
                <span>{post.readingTime}</span>
                {post.category === "opinion" && (
                  <>
                    <span>&middot;</span>
                    <span>{authorName}</span>
                  </>
                )}
              </div>
            </header>

            <section className="mb-10 rounded-2xl border border-border/50 bg-background/60 p-5 md:p-6">
              <h2 className="text-xs uppercase tracking-wide text-muted-foreground/70 mb-2">
                At a Glance
              </h2>
              <p className="text-base leading-relaxed mb-4">
                <strong>Answer:</strong> {post.metaDescription || post.description}
              </p>
              {sectionHeadings.length > 0 && (
                <div>
                  <p className="text-sm text-muted-foreground/80 mb-2">This article covers:</p>
                  <ul className="list-disc pl-5 space-y-1 text-sm text-muted-foreground/90">
                    {sectionHeadings.map((heading) => (
                      <li key={heading}>{heading}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>

            {/* Post content */}
            <div className="prose prose-neutral dark:prose-invert prose-lg max-w-none">
              <ReactMarkdown>{post.content}</ReactMarkdown>
            </div>

            {seriesPosts.length > 1 && (
              <section className="mt-12 pt-8 border-t border-border/40">
                <h2 className="text-xl font-medium mb-4">Series Navigation</h2>
                <ol className="space-y-2">
                  {seriesPosts.map((seriesPost) => {
                    const isCurrent = seriesPost.slug === post.slug;
                    const partLabel = seriesPost.seriesPart
                      ? `Part ${seriesPost.seriesPart}`
                      : "Article";

                    return (
                      <li key={seriesPost.slug}>
                        {isCurrent ? (
                          <span className="text-sm md:text-base text-muted-foreground">
                            {partLabel}: {seriesPost.title} (current)
                          </span>
                        ) : (
                          <Link
                            href={`/blog/${seriesPost.slug}`}
                            className="text-sm md:text-base text-foreground hover:opacity-70 transition-colors"
                          >
                            {partLabel}: {seriesPost.title}
                          </Link>
                        )}
                      </li>
                    );
                  })}
                </ol>
              </section>
            )}

            {relatedPosts.length > 0 && (
              <section className="mt-12 pt-8 border-t border-border/40">
                <h2 className="text-xl font-medium mb-4">Related Reading</h2>
                <div className="space-y-4">
                  {relatedPosts.map((related) => (
                    <article key={related.slug}>
                      <Link
                        href={`/blog/${related.slug}`}
                        className="text-base md:text-lg font-medium hover:opacity-70 transition-colors"
                      >
                        {related.title}
                      </Link>
                      <p className="text-sm text-muted-foreground mt-1">{related.metaDescription}</p>
                    </article>
                  ))}
                </div>
              </section>
            )}
          </article>
        </main>

        <LandingFooter />
      </div>

      {/* Structured data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbLd) }}
      />
    </div>
  );
}
