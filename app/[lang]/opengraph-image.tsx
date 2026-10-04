import { ImageResponse } from "next/og";
import { BRAND_G_PATH, BRAND_G_VIEWBOX, BRAND_INK } from "@/lib/brand";
import { DEFAULT_LOCALE, getDictionary, hasLocale } from "@/lib/i18n";

const size = { width: 1200, height: 630 };
const contentType = "image/png";

// One image per locale, with its alt text (og:image:alt) in that language --
// a plain `export const alt` would be the same string for both.
export async function generateImageMetadata({ params }: { params: { lang: string } }) {
  const { lang } = await params;
  const locale = hasLocale(lang) ? lang : DEFAULT_LOCALE;
  return [{ id: "og", alt: getDictionary(locale).meta.ogImageAlt, size, contentType }];
}

export default async function OpengraphImage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const t = getDictionary(hasLocale(lang) ? lang : DEFAULT_LOCALE).hero;
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          background: "#f4f1ea",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 40 }}>
          <svg viewBox={BRAND_G_VIEWBOX} width="52" height="52">
            <path d={BRAND_G_PATH} fill={BRAND_INK} />
          </svg>
          <span style={{ fontSize: 34, fontWeight: 600, color: "#171717" }}>Glyph</span>
        </div>
        <div style={{ display: "flex", fontSize: 58, fontWeight: 600, color: "#171717", lineHeight: 1.15 }}>
          {t.titleLine1}
        </div>
        <div style={{ display: "flex", fontSize: 58, fontWeight: 600, lineHeight: 1.15 }}>
          {/* trailing space as a non-breaking one, or the image renderer drops it */}
          <span style={{ color: "#171717" }}>{t.titleLine2Before.replace(/ $/, "\u00a0")}</span>
          <span style={{ color: "#3d2fe0", fontStyle: "italic" }}>{t.titleLine2Accent}</span>
          <span style={{ color: "#171717" }}>{t.titleLine2After}</span>
        </div>
      </div>
    ),
    { ...size },
  );
}
