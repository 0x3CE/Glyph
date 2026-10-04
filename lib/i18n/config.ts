// Locale routing rules, shared by proxy.ts (server edge) and the pages.
//
// French is the default and lives at the root (`/`, `/editor`); English
// lives under `/en` (`/en`, `/en/editor`). Internally every page sits under
// `app/[lang]`: proxy.ts rewrites the unprefixed French URLs to `/fr/...`.

export const LOCALES = ["fr", "en"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "fr";

export const hasLocale = (value: string): value is Locale => (LOCALES as readonly string[]).includes(value);

// Set when a visitor picks a language with the switcher; it wins over the
// country guess on every later visit. A preference cookie, not a tracker.
export const LOCALE_COOKIE = "glyph-lang";
export const LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

// Visitors from these countries get French on their first visit, everyone
// else English. ISO 3166-1 codes as sent by Vercel in `x-vercel-ip-country`:
// metropolitan France, its overseas regions and collectivities (each has its
// own country code), and Monaco.
export const FRENCH_COUNTRIES = new Set([
  "FR", // France
  "GP", // Guadeloupe
  "MQ", // Martinique
  "GF", // Guyane
  "RE", // La Réunion
  "YT", // Mayotte
  "PM", // Saint-Pierre-et-Miquelon
  "BL", // Saint-Barthélemy
  "MF", // Saint-Martin
  "WF", // Wallis-et-Futuna
  "PF", // Polynésie française
  "NC", // Nouvelle-Calédonie
  "TF", // Terres australes et antarctiques françaises
  "MC", // Monaco
]);

/** Public URL of `path` ("/", "/editor") in `locale`. */
export function localePath(locale: Locale, path: string): string {
  if (locale === DEFAULT_LOCALE) return path;
  return path === "/" ? `/${locale}` : `/${locale}${path}`;
}

/** `pathname` (a public URL) with its locale prefix removed. */
export function stripLocale(pathname: string): string {
  for (const locale of LOCALES) {
    if (pathname === `/${locale}`) return "/";
    if (pathname.startsWith(`/${locale}/`)) return pathname.slice(locale.length + 1);
  }
  return pathname;
}
