import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { BrandMark } from "@/components/BrandMark";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { getDictionary, hasLocale, localePath } from "@/lib/i18n";
import { localeAlternates, localeOpenGraph } from "@/lib/i18n/metadata";

// Plain link, not Buy Me a Coffee's widget script: the site promises no
// third-party tracking, and the widget would load one on every visit.
const BUY_ME_A_COFFEE_URL = "https://buymeacoffee.com/0x3CE";

type Props = { params: Promise<{ lang: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(lang)) return {};
  const t = getDictionary(lang).meta;
  return {
    title: { absolute: t.title },
    description: t.description,
    alternates: localeAlternates(lang, "/"),
    openGraph: localeOpenGraph(lang, "/"),
  };
}

export default async function LandingPage({ params }: Props) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  const t = getDictionary(lang);
  const editorHref = localePath(lang, "/editor");

  const softwareJsonLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "Glyph",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    inLanguage: lang,
    description: t.meta.softwareDescription,
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: t.meta.priceCurrency,
    },
  };

  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    inLanguage: lang,
    mainEntity: t.faq.items.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a },
    })),
  };

  return (
    <>
      <header className="site-header">
        <Link href={localePath(lang, "/")} className="brand">
          <span className="brand-mark">
            <BrandMark />
          </span>
          <span className="brand-name">Glyph</span>
        </Link>
        <nav className="site-nav">
          <LanguageSwitcher
            locale={lang}
            path="/"
            label={t.switcher.label}
            shortLabel={t.switcher.shortLabel}
            ariaLabel={t.switcher.ariaLabel}
            className="btn btn-ghost lang-switch"
          />
          <a
            href={BUY_ME_A_COFFEE_URL}
            className="btn btn-ghost"
            target="_blank"
            rel="noopener noreferrer"
            aria-label={t.nav.coffeeAria}
          >
            <span aria-hidden="true">☕</span>
            <span className="nav-coffee-label">{t.nav.coffee}</span>
          </a>
          <Link href={editorHref} className="btn btn-accent">
            {t.nav.openEditor}
          </Link>
        </nav>
      </header>

      <section className="hero">
        <span className="hero-eyebrow">{t.hero.eyebrow}</span>
        <h1 className="hero-title">
          {t.hero.titleLine1}
          <br />
          {t.hero.titleLine2Before}
          <span className="hero-accent">{t.hero.titleLine2Accent}</span>
          {t.hero.titleLine2After}
        </h1>
        <p className="hero-subtitle">{t.hero.subtitle}</p>
        <div className="hero-actions">
          <Link href={editorHref} className="btn btn-accent btn-lg">
            {t.nav.openEditor}
          </Link>
          <a href={`#${t.how.anchor}`} className="btn btn-ghost btn-lg">
            {t.hero.howItWorks}
          </a>
        </div>
      </section>

      <section className="section" id={t.problem.anchor}>
        <p className="section-label">{t.problem.label}</p>
        <h2 className="section-title">{t.problem.title}</h2>
        <p className="section-lede">{t.problem.lede}</p>
        <div className="problem-grid">
          <div className="problem-card is-bad">
            <h3>{t.problem.badTitle}</h3>
            <p>{t.problem.badText}</p>
          </div>
          <div className="problem-card is-good">
            <h3>Glyph</h3>
            <p>{t.problem.goodText}</p>
          </div>
        </div>
      </section>

      <section className="section" id={t.how.anchor}>
        <p className="section-label">{t.how.label}</p>
        <h2 className="section-title">{t.how.title}</h2>
        <div className="steps">
          {t.how.steps.map((step) => (
            <div className="step" key={step.title}>
              <p className="step-number" aria-hidden="true" />
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section" id={t.features.anchor}>
        <p className="section-label">{t.features.label}</p>
        <h2 className="section-title">{t.features.title}</h2>
        <div className="features-grid">
          {t.features.items.map((item) => (
            <div className="feature-card" key={item.title}>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section" id="faq">
        <p className="section-label">{t.faq.label}</p>
        <h2 className="section-title">{t.faq.title}</h2>
        <div className="faq-list">
          {t.faq.items.map((item) => (
            <div className="faq-item" key={item.q}>
              <h3>{item.q}</h3>
              <p>{item.a}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section support" id={t.support.anchor}>
        <div className="support-card">
          <div>
            <p className="section-label">{t.support.label}</p>
            <h2 className="support-title">{t.support.title}</h2>
            <p className="support-text">{t.support.text}</p>
          </div>
          <a href={BUY_ME_A_COFFEE_URL} className="btn btn-coffee btn-lg" target="_blank" rel="noopener noreferrer">
            <span aria-hidden="true">☕</span> {t.nav.coffee}
          </a>
        </div>
      </section>

      <section className="cta-band">
        <div className="section">
          <div>
            <h2>{t.cta.title}</h2>
            <p>{t.cta.text}</p>
          </div>
          <Link href={editorHref} className="btn btn-accent btn-lg">
            {t.nav.openEditor}
          </Link>
        </div>
      </section>

      <footer className="site-footer">
        <span>© {new Date().getFullYear()} Glyph</span>
        <span className="footer-links">
          <span>{t.footer.tagline}</span>
          <LanguageSwitcher locale={lang} path="/" label={t.switcher.label} ariaLabel={t.switcher.ariaLabel} />
          <a href={BUY_ME_A_COFFEE_URL} target="_blank" rel="noopener noreferrer">
            Buy me a coffee
          </a>
        </span>
      </footer>

      <script
        type="application/ld+json"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareJsonLd) }}
      />
      <script
        type="application/ld+json"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
    </>
  );
}
