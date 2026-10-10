import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { getDictionary, localePath } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n";
import { CONTENT, isPublished } from "@/lib/seo/content";
import { PAGE_IDS, PAGES, pagePath } from "@/lib/seo/registry";
import type { PageId } from "@/lib/seo/registry";
import { SOURCE_CODE_URL } from "@/lib/site";

// Plain link, not Buy Me a Coffee's widget script: the site promises no
// third-party tracking, and the widget would load one on every visit.
export const BUY_ME_A_COFFEE_URL = "https://buymeacoffee.com/0x3CE";

interface ChromeProps {
  locale: Locale;
  /** This page's path without locale prefix ("/"), for the language switch... */
  path?: string;
  /** ...or the other language's URL directly, when the slug differs. */
  otherHref?: string;
}

export function SiteHeader({ locale, path = "/", otherHref }: ChromeProps) {
  const t = getDictionary(locale);
  return (
    <header className="site-header">
      <Link href={localePath(locale, "/")} className="brand">
        <span className="brand-mark">
          <BrandMark />
        </span>
        <span className="brand-name">Glyph</span>
      </Link>
      <nav className="site-nav">
        <LanguageSwitcher
          locale={locale}
          path={path}
          href={otherHref}
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
        <Link href={localePath(locale, "/editor")} className="btn btn-accent">
          {t.nav.openEditor}
        </Link>
      </nav>
    </header>
  );
}

interface FooterLink {
  id: string;
  href: string;
  label: string;
  external?: boolean;
}

function linksOfKind(locale: Locale, kinds: string[]): FooterLink[] {
  return PAGE_IDS.filter((id) => isPublished(id) && kinds.includes(PAGES[id].kind)).map((id) => ({
    id,
    href: pagePath(id, locale),
    label: CONTENT[id]![locale].nav,
  }));
}

export function SiteFooter({ locale, path = "/", otherHref }: ChromeProps) {
  const t = getDictionary(locale);
  const groups = [
    { title: t.footer.tools, links: linksOfKind(locale, ["tool"]) },
    { title: t.footer.guides, links: linksOfKind(locale, ["article", "guide"]) },
    {
      title: t.footer.about,
      links: [
        ...linksOfKind(locale, ["legal"]),
        { id: "source", href: SOURCE_CODE_URL, label: t.footer.sourceCode, external: true },
      ],
    },
  ].filter((g) => g.links.length > 0);
  return (
    <footer className="site-footer-wrap">
      {groups.length > 0 && (
        <nav className="footer-nav" aria-label={t.footer.tools}>
          {groups.map((group) => (
            <div key={group.title} className="footer-nav-group">
              <p className="footer-nav-title">{group.title}</p>
              <ul>
                {group.links.map((link) => (
                  <li key={link.id}>
                    {link.external ? (
                      <a href={link.href} target="_blank" rel="noopener noreferrer">
                        {link.label}
                      </a>
                    ) : (
                      <Link href={link.href}>{link.label}</Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      )}
      <div className="site-footer">
        <span>© {new Date().getFullYear()} Glyph</span>
        <span className="footer-links">
          <span>{t.footer.tagline}</span>
          <LanguageSwitcher
            locale={locale}
            path={path}
            href={otherHref}
            label={t.switcher.label}
            ariaLabel={t.switcher.ariaLabel}
          />
          <a href={BUY_ME_A_COFFEE_URL} target="_blank" rel="noopener noreferrer">
            Buy me a coffee
          </a>
        </span>
      </div>
    </footer>
  );
}
