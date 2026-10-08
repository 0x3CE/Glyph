// Every content page beyond the landing: its public URL in each language and
// what kind of page it is. The single list proxy.ts, the sitemap, internal
// links and the [slug] route all read, so a page exists everywhere at once.
//
// French slugs are served unprefixed (/modifier-texte-pdf), English ones under
// /en (/en/edit-pdf-text), like the rest of the site (lib/i18n/config.ts).

import type { Locale } from "../i18n/config";

export type PageKind = "tool" | "article" | "guide" | "legal";

export interface PageEntry {
  kind: PageKind;
  slug: Record<Locale, string>;
}

// Every planned page has its final URLs here; only the ones with content
// (lib/seo/content/index.ts) are published -- routed, in the sitemap, linked.
export const PAGES = {
  editText: { kind: "tool", slug: { fr: "modifier-texte-pdf", en: "edit-pdf-text" } },
  overlayVsReal: { kind: "article", slug: { fr: "overlay-vs-vraie-edition-pdf", en: "overlay-vs-real-pdf-editing" } },
  redact: { kind: "tool", slug: { fr: "caviarder-pdf", en: "redact-pdf" } },
  anonymize: { kind: "tool", slug: { fr: "anonymiser-pdf", en: "anonymize-pdf" } },
  check: { kind: "tool", slug: { fr: "verifier-pdf-caviarde", en: "check-redacted-pdf" } },
  findReplace: { kind: "tool", slug: { fr: "remplacer-mot-pdf", en: "find-replace-pdf" } },
  sign: { kind: "tool", slug: { fr: "signer-pdf", en: "sign-pdf" } },
  guideFixTypo: { kind: "guide", slug: { fr: "corriger-faute-pdf", en: "fix-typo-in-pdf" } },
  guideWithoutAcrobat: { kind: "guide", slug: { fr: "modifier-pdf-sans-acrobat", en: "edit-pdf-without-acrobat" } },
  guideMac: { kind: "guide", slug: { fr: "modifier-pdf-sur-mac", en: "edit-pdf-on-mac" } },
  terms: { kind: "legal", slug: { fr: "conditions-utilisation", en: "terms" } },
} as const satisfies Record<string, PageEntry>;

export type PageId = keyof typeof PAGES;

export const PAGE_IDS = Object.keys(PAGES) as PageId[];

export function isPageId(value: string): value is PageId {
  return value in PAGES;
}

/** The page whose slug in `locale` is `slug`, if any. */
export function pageForSlug(locale: Locale, slug: string): PageId | undefined {
  return PAGE_IDS.find((id) => PAGES[id].slug[locale] === slug);
}

/** Public path of a page ("/modifier-texte-pdf", "/en/edit-pdf-text"). */
export function pagePath(id: PageId, locale: Locale): string {
  const slug = `/${PAGES[id].slug[locale]}`;
  return locale === "fr" ? slug : `/${locale}${slug}`;
}

/** The same page in `to`, for an unprefixed (French) path; null if it isn't one
 * of these pages. Used to redirect a visitor to the right English URL. */
export function translateFrenchPath(path: string, to: Locale): string | null {
  const id = pageForSlug("fr", path.replace(/^\//, ""));
  return id ? pagePath(id, to) : null;
}
