import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { DEFAULT_LOCALE, FRENCH_COUNTRIES, LOCALE_COOKIE, hasLocale, localePath } from "@/lib/i18n/config";
import type { Locale } from "@/lib/i18n/config";

// Locale routing (Next 16 "proxy", formerly middleware):
//
// - `/en/...` is English, served as is: an explicit URL always wins, so a
//   shared or indexed link shows the language it was shared in.
// - `/fr/...` redirects to the same page without the prefix: French URLs are
//   unprefixed, and serving both would be duplicate content for search engines.
// - Any other page URL is French by default and rewritten to `/fr/...`
//   internally, unless the visitor should get English: their saved choice
//   (the switcher's cookie) first, otherwise the country Vercel geolocates
//   their IP to (`x-vercel-ip-country`; no IP is read or stored here).
//   Crawlers are never redirected, so both language versions stay indexable.

const CRAWLER = /bot|crawler|spider|crawling|slurp|facebookexternalhit|embedly|quora link preview|whatsapp|telegram|discord|slack/i;

function preferredLocale(request: NextRequest): Locale {
  const saved = request.cookies.get(LOCALE_COOKIE)?.value;
  if (saved && hasLocale(saved)) return saved;
  if (CRAWLER.test(request.headers.get("user-agent") ?? "")) return DEFAULT_LOCALE;
  const country = request.headers.get("x-vercel-ip-country");
  // No header (local dev, a host other than Vercel): keep the default.
  if (!country) return DEFAULT_LOCALE;
  return FRENCH_COUNTRIES.has(country.toUpperCase()) ? "fr" : "en";
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname === "/en" || pathname.startsWith("/en/")) return NextResponse.next();

  if (pathname === "/fr" || pathname.startsWith("/fr/")) {
    const url = request.nextUrl.clone();
    url.pathname = pathname.slice(3) || "/";
    return NextResponse.redirect(url, 308);
  }

  if (preferredLocale(request) === "en") {
    const url = request.nextUrl.clone();
    url.pathname = localePath("en", pathname);
    // Temporary: the same URL must stay French for other visitors.
    return NextResponse.redirect(url, 307);
  }

  const url = request.nextUrl.clone();
  url.pathname = pathname === "/" ? "/fr" : `/fr${pathname}`;
  return NextResponse.rewrite(url);
}

export const config = {
  // Pages only: not the backend proxy (/api), Next's own assets, Vercel's
  // own endpoints (/_vercel: Speed Insights posts its reports there, with no
  // file extension), files with an extension (icon.svg, robots.txt,
  // sitemap.xml), or generated images with no extension -- the Open Graph
  // images (which already carry their locale in the path) and the
  // apple-touch-icon.
  matcher: ["/((?!api/|_next/|_vercel/|.*\\..*|.*opengraph-image|apple-icon).*)"],
};
