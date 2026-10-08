import Link from "next/link";
import { PdfChecker } from "@/components/PdfChecker";
import { RichText } from "@/components/RichText";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { UploadDropzone } from "@/components/UploadDropzone";
import { getDictionary, localePath } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n";
import { CONTENT, isPublished } from "@/lib/seo/content";
import { PAGES, pagePath } from "@/lib/seo/registry";
import type { PageId } from "@/lib/seo/registry";
import type { Block } from "@/lib/seo/types";
import { absoluteUrl } from "@/lib/site";

function BlockView({ block, locale }: { block: Block; locale: Locale }) {
  if ("p" in block) return <p><RichText text={block.p} locale={locale} /></p>;
  if ("note" in block) return <p className="seo-note"><RichText text={block.note} locale={locale} /></p>;
  const Tag = "steps" in block ? "ol" : "ul";
  const items = "steps" in block ? block.steps : block.list;
  return (
    <Tag className={"steps" in block ? "seo-steps" : undefined}>
      {items.map((item) => (
        <li key={item}>
          <RichText text={item} locale={locale} />
        </li>
      ))}
    </Tag>
  );
}

function formatDate(iso: string, locale: Locale) {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString(locale === "fr" ? "fr-FR" : "en-US", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function SeoPage({ id, locale }: { id: PageId; locale: Locale }) {
  const c = CONTENT[id]![locale];
  const t = getDictionary(locale);
  const other: Locale = locale === "fr" ? "en" : "fr";
  const otherHref = pagePath(id, other);
  const kind = PAGES[id].kind;
  const related = (c.related ?? []).filter(isPublished);

  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: t.seo.home, item: absoluteUrl(localePath(locale, "/")) },
      { "@type": "ListItem", position: 2, name: c.nav, item: absoluteUrl(pagePath(id, locale)) },
    ],
  };
  const faqJsonLd = c.faq && {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    inLanguage: locale,
    mainEntity: c.faq.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a.replace(/\*\*|\[([^\]]+)\]\([^)]+\)/g, "$1") },
    })),
  };
  const articleJsonLd = (kind === "article" || kind === "guide") && {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: c.h1,
    description: c.metaDescription,
    inLanguage: locale,
    dateModified: c.updated,
    mainEntityOfPage: absoluteUrl(pagePath(id, locale)),
    publisher: { "@type": "Organization", name: "Glyph" },
  };

  return (
    <>
      <SiteHeader locale={locale} otherHref={otherHref} />

      <nav className="seo-breadcrumb" aria-label="breadcrumb">
        <Link href={localePath(locale, "/")}>{t.seo.home}</Link>
        <span aria-hidden="true"> / </span>
        <span>{c.nav}</span>
      </nav>

      <section className={`seo-hero ${c.widget ? "" : "seo-hero-text"}`}>
        {c.eyebrow && <span className="hero-eyebrow">{c.eyebrow}</span>}
        <h1 className="seo-title">{c.h1}</h1>
        <p className="seo-intro">
          <RichText text={c.intro} locale={locale} />
        </p>
        {c.widget === "upload" && (
          <UploadDropzone
            locale={locale}
            intent={c.intent ?? "edit"}
            title={t.editor.dropTitle}
            or={t.editor.dropOr}
            choose={t.editor.chooseFile}
            hint={t.seo.uploadHint}
          />
        )}
        {c.widget === "check" && <PdfChecker locale={locale} />}
        {c.widget && (
          <p className="seo-terms-notice">
            {t.seo.termsNotice} <Link href={pagePath("terms", locale)}>{t.seo.termsLink}</Link>.
          </p>
        )}
      </section>

      <article className="seo-article">
        {c.updated && (kind !== "tool") && (
          <p className="seo-updated">
            {t.seo.updated} {formatDate(c.updated, locale)}
          </p>
        )}
        {c.sections.map((section) => (
          <section key={section.h2}>
            <h2>{section.h2}</h2>
            {section.blocks.map((block, i) => (
              <BlockView key={i} block={block} locale={locale} />
            ))}
          </section>
        ))}

        {c.faq && (
          <section className="seo-faq">
            <h2>{t.seo.faq}</h2>
            {c.faq.map((item) => (
              <div key={item.q} className="faq-item">
                <h3>{item.q}</h3>
                <p>
                  <RichText text={item.a} locale={locale} />
                </p>
              </div>
            ))}
          </section>
        )}

        {related.length > 0 && (
          <section className="seo-related">
            <h2>{t.seo.related}</h2>
            <ul>
              {related.map((rid) => (
                <li key={rid}>
                  <Link href={pagePath(rid, locale)}>{CONTENT[rid]![locale].nav}</Link>
                </li>
              ))}
            </ul>
          </section>
        )}
      </article>

      <SiteFooter locale={locale} otherHref={otherHref} />

      {[breadcrumbJsonLd, faqJsonLd, articleJsonLd].filter(Boolean).map((data, i) => (
        <script
          key={i}
          type="application/ld+json"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
        />
      ))}
    </>
  );
}
