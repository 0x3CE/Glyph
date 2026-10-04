import { BRAND_G_PATH, BRAND_G_VIEWBOX } from "@/lib/brand";

// The brand "G" (see lib/brand.ts). Drawn in `currentColor`, so it follows
// the surrounding text color (`.brand-mark` sets the ink color).
export function BrandMark({ size = 20 }: { size?: number }) {
  return (
    <svg viewBox={BRAND_G_VIEWBOX} width={size} height={size} aria-hidden="true">
      <path d={BRAND_G_PATH} fill="currentColor" />
    </svg>
  );
}
