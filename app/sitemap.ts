import type { MetadataRoute } from "next";
import { LOCALES, localePath } from "@/lib/i18n/config";
import { isPublished } from "@/lib/seo/content";
import { PAGE_IDS, pagePath } from "@/lib/seo/registry";
import { absoluteUrl } from "@/lib/site";

// Every language version of the landing page and of each published content
// page, each listing the others as alternates (hreflang). The editor is
// `noindex`, so it isn't listed.
export default function sitemap(): MetadataRoute.Sitemap {
  const entries: MetadataRoute.Sitemap = [];
  const add = (pathFor: (locale: (typeof LOCALES)[number]) => string, priority: number) => {
    const languages = Object.fromEntries(LOCALES.map((l) => [l, absoluteUrl(pathFor(l))]));
    for (const locale of LOCALES) {
      entries.push({
        url: absoluteUrl(pathFor(locale)),
        lastModified: new Date(),
        changeFrequency: "monthly",
        priority,
        alternates: { languages },
      });
    }
  };
  add((l) => localePath(l, "/"), 1);
  for (const id of PAGE_IDS.filter(isPublished)) add((l) => pagePath(id, l), id === "terms" ? 0.3 : 0.8);
  return entries;
}
