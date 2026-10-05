import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Inter, JetBrains_Mono } from "next/font/google";
import { SpeedInsights } from "@vercel/speed-insights/next";
import { LOCALES, getDictionary, hasLocale } from "@/lib/i18n";
import { localeOpenGraph } from "@/lib/i18n/metadata";
import { SITE_URL } from "@/lib/site";
import "../globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["400", "500"],
});

type Props = { children: React.ReactNode; params: Promise<{ lang: string }> };

// Every page is prerendered once per locale; proxy.ts routes visitors to the
// right one (French unprefixed, English under /en).
export function generateStaticParams() {
  return LOCALES.map((lang) => ({ lang }));
}

export async function generateMetadata({ params }: Omit<Props, "children">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(lang)) return {};
  const t = getDictionary(lang).meta;
  return {
    metadataBase: new URL(SITE_URL),
    title: { default: t.title, template: "%s · Glyph" },
    description: t.siteDescription,
    keywords: t.keywords,
    openGraph: localeOpenGraph(lang, "/"),
    twitter: {
      card: "summary_large_image",
      title: t.title,
      description: t.ogDescription,
    },
  };
}

export default async function RootLayout({ children, params }: Props) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  const organizationJsonLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "Glyph",
    url: SITE_URL,
    description: getDictionary(lang).meta.organizationDescription,
  };

  return (
    <html lang={lang} className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body>
        {children}
        {/* Vercel Speed Insights: anonymous page-load performance (Web Vitals),
            no cookie, no visitor tracking. Its script and its reports live
            under /_vercel/, which proxy.ts leaves alone. */}
        <SpeedInsights />
        <script
          type="application/ld+json"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
        />
      </body>
    </html>
  );
}
