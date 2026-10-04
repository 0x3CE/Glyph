import type { MetadataRoute } from "next";
import { LOCALES, localePath } from "@/lib/i18n/config";
import { absoluteUrl } from "@/lib/site";

// One entry per language version of the landing page, each listing the other
// as an alternate (hreflang). The editor is `noindex`, so it isn't listed.
export default function sitemap(): MetadataRoute.Sitemap {
  const languages = Object.fromEntries(LOCALES.map((l) => [l, absoluteUrl(localePath(l, "/"))]));
  return LOCALES.map((locale) => ({
    url: absoluteUrl(localePath(locale, "/")),
    lastModified: new Date(),
    changeFrequency: "monthly",
    priority: 1,
    alternates: { languages },
  }));
}
