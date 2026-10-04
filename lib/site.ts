// The site's public origin, used for canonical URLs, hreflang links, Open
// Graph images, the sitemap and robots.txt. Never a guess: a wrong origin
// tells search engines the "real" page lives somewhere else (this used to
// fall back to a placeholder domain nobody owned, so every canonical URL on
// the live site pointed to a dead host).
//
// 1. NEXT_PUBLIC_SITE_URL, set once a custom domain is attached;
// 2. otherwise the production URL Vercel exposes at build time
//    (VERCEL_PROJECT_PRODUCTION_URL, the project's main domain, no scheme);
// 3. otherwise local dev.
function resolveSiteUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_SITE_URL;
  if (explicit) return explicit.replace(/\/+$/, "");
  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  if (vercel) return `https://${vercel}`;
  return "http://localhost:3000";
}

export const SITE_URL = resolveSiteUrl();

/** Absolute URL of a public path. The root is written without a trailing
 * slash, exactly like Next renders canonical URLs, so the sitemap and the
 * page's own tags agree. */
export function absoluteUrl(path: string): string {
  return path === "/" ? SITE_URL : `${SITE_URL}${path}`;
}
