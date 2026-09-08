import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

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

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://glyph.app";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Glyph — l'éditeur PDF qui modifie vraiment le texte",
    template: "%s · Glyph",
  },
  description:
    "Glyph réécrit le contenu d'un PDF au lieu de le recouvrir : le texte d'origine est supprimé, le nouveau réinséré avec la police d'origine. Reflow, recherche et copier-coller intacts.",
  keywords: [
    "éditeur PDF",
    "modifier texte PDF",
    "éditer PDF en ligne",
    "PDF sans overlay",
    "réécrire PDF",
  ],
  openGraph: {
    title: "Glyph — l'éditeur PDF qui modifie vraiment le texte",
    description:
      "Le texte d'origine est supprimé du PDF, pas recouvert. Édition réelle, pas un calque.",
    url: siteUrl,
    siteName: "Glyph",
    locale: "fr_FR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Glyph — l'éditeur PDF qui modifie vraiment le texte",
    description:
      "Le texte d'origine est supprimé du PDF, pas recouvert. Édition réelle, pas un calque.",
  },
};

const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Glyph",
  url: siteUrl,
  description: "Éditeur PDF qui réécrit le contenu du document au lieu de le recouvrir.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body>
        {children}
        <script
          type="application/ld+json"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
        />
      </body>
    </html>
  );
}
