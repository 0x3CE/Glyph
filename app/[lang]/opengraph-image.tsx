import { ImageResponse } from "next/og";
import { DEFAULT_LOCALE, getDictionary, hasLocale } from "@/lib/i18n";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

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
          <svg viewBox="0 0 48 48" width="52" height="52">
            <path
              d="M24 10a14 14 0 1 0 12.12 21"
              stroke="#171717"
              strokeWidth="4.5"
              fill="none"
              strokeLinecap="round"
            />
            <path
              d="M24 24h11v4a11 11 0 0 1-6 3.5"
              stroke="#3d2fe0"
              strokeWidth="4.5"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
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
