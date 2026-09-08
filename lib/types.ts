export interface Span {
  text: string;
  bbox: [number, number, number, number];
  font: string;
  size: number;
  color: number;
  flags: number;
}

export interface Line {
  bbox: [number, number, number, number];
  spans: Span[];
}

export interface Block {
  id: string;
  bbox: [number, number, number, number];
  lines: Line[];
  text: string;
}

export interface PageStructure {
  page_index: number;
  width: number;
  height: number;
  blocks: Block[];
}

export interface UploadResponse {
  document_id: string;
  page_count: number;
}

export interface EditResponse {
  font_substituted: boolean;
  new_bbox: [number, number, number, number];
}

export const FLAG_ITALIC = 1 << 1;
export const FLAG_SERIF = 1 << 2;
export const FLAG_MONOSPACE = 1 << 3;
export const FLAG_BOLD = 1 << 4;

export function colorIntToCss(color: number): string {
  const r = (color >> 16) & 255;
  const g = (color >> 8) & 255;
  const b = color & 255;
  return `rgb(${r}, ${g}, ${b})`;
}

export function fontFamilyForFlags(flags: number): string {
  if (flags & FLAG_MONOSPACE) return "'Courier New', monospace";
  if (flags & FLAG_SERIF) return "Georgia, 'Times New Roman', serif";
  return "Arial, Helvetica, sans-serif";
}
