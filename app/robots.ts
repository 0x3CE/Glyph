import type { MetadataRoute } from "next";
import { absoluteUrl } from "@/lib/site";

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
    sitemap: absoluteUrl("/sitemap.xml"),
  };
}
