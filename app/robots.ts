import type { MetadataRoute } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://glyph.app";

export default function robots(): MetadataRoute.Robots {
  return {
    // /editor is kept crawlable (not disallowed here) so a `noindex` meta
    // tag on that page itself is what search engines actually see and obey
    // -- disallowing it here instead would block the crawl entirely, which
    // means Google could still list the bare URL (no snippet) if it's ever
    // linked from elsewhere, since it could never see the noindex directive.
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
