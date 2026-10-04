import type { Metadata } from "next";
import { LOCALES, localePath } from "./config";
import type { Locale } from "./config";
import { getDictionary } from "./index";

/** Canonical URL + hreflang links for `path` ("/", "/editor") in `locale`.
 * `x-default` (any language other than ours) points to English, which is
 * what visitors outside France get. */
export function localeAlternates(locale: Locale, path: string): Metadata["alternates"] {
  return {
    canonical: localePath(locale, path),
    languages: {
      ...Object.fromEntries(LOCALES.map((l) => [l, localePath(l, path)])),
      "x-default": localePath("en", path),
    },
  };
}

/** Full Open Graph block for `path` in `locale`. A page's `openGraph`
 * replaces the layout's instead of merging with it, so a page that needs its
 * own `url` must re-send the rest too. */
export function localeOpenGraph(locale: Locale, path: string): Metadata["openGraph"] {
  const t = getDictionary(locale).meta;
  return {
    title: t.title,
    description: t.ogDescription,
    url: localePath(locale, path),
    siteName: "Glyph",
    locale: t.ogLocale,
    alternateLocale: LOCALES.filter((l) => l !== locale).map((l) => getDictionary(l).meta.ogLocale),
    type: "website",
  };
}
