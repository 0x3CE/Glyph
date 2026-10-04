import { ImageResponse } from "next/og";
import { BRAND_G_PATH, BRAND_G_VIEWBOX, BRAND_INK, BRAND_PAPER } from "@/lib/brand";

// Home-screen icon for iOS (apple-touch-icon): the brand "G" on the site's
// paper background. iOS ignores SVG icons, hence a generated PNG next to
// icon.svg.
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: BRAND_PAPER,
        }}
      >
        <svg viewBox={BRAND_G_VIEWBOX} width="112" height="112">
          <path d={BRAND_G_PATH} fill={BRAND_INK} />
        </svg>
      </div>
    ),
    { ...size },
  );
}
