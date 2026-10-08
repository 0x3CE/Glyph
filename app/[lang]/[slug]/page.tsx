import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SeoPage } from "@/components/SeoPage";
import { LOCALES, hasLocale } from "@/lib/i18n";
import { localeOpenGraph } from "@/lib/i18n/metadata";
import { CONTENT, isPublished } from "@/lib/seo/content";
import { PAGES, PAGE_IDS, pageForSlug, pagePath } from "@/lib/seo/registry";

type Props = { params: Promise<{ lang: string; slug: string }> };

// Content pages (lib/seo): each one prerendered in both languages, under its
// own slug per language. Any other slug is a 404 (dynamicParams = false).
export const dynamicParams = false;

export function generateStaticParams() {
  return PAGE_IDS.filter(isPublished).flatMap((id) => LOCALES.map((lang) => ({ lang, slug: PAGES[id].slug[lang] })));
}

function resolve(lang: string, slug: string) {
  if (!hasLocale(lang)) return null;
  const id = pageForSlug(lang, slug);
  return id && isPublished(id) ? { lang, id } : null;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { lang, slug } = await params;
  const page = resolve(lang, slug);
  if (!page) return {};
  const c = CONTENT[page.id]![page.lang];
  const path = pagePath(page.id, page.lang);
  return {
    title: { absolute: c.metaTitle },
    description: c.metaDescription,
    alternates: {
      canonical: path,
      languages: {
        fr: pagePath(page.id, "fr"),
        en: pagePath(page.id, "en"),
        "x-default": pagePath(page.id, "en"),
      },
    },
    openGraph: {
      ...localeOpenGraph(page.lang, path.replace(/^\/en/, "") || "/"),
      title: c.metaTitle,
      description: c.metaDescription,
      type: PAGES[page.id].kind === "tool" ? "website" : "article",
    },
  };
}

export default async function ContentPage({ params }: Props) {
  const { lang, slug } = await params;
  const page = resolve(lang, slug);
  if (!page) notFound();
  return <SeoPage id={page.id} locale={page.lang} />;
}
