import type { EditResponse, PageStructure, SignatureResponse, UploadResponse } from "./types";

const BASE = "/api";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// Files go up as the raw request body, not multipart: the backend reads it
// straight into memory with a size cap, instead of a multipart parser that
// spools large parts to a temporary file on disk.
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const res = await fetch(`${BASE}/documents`, {
    method: "POST",
    headers: { "Content-Type": "application/pdf" },
    body: file,
  });
  return json(res);
}

// Frees the server-side copy right away instead of waiting for it to expire.
// `keepalive` lets the request outlive the page when called from `pagehide`.
export function deleteDocument(documentId: string): void {
  fetch(`${BASE}/documents/${documentId}`, { method: "DELETE", keepalive: true }).catch(() => {});
}

export async function getPageStructure(documentId: string, pageIndex: number): Promise<PageStructure> {
  const res = await fetch(`${BASE}/documents/${documentId}/pages/${pageIndex}/structure`);
  return json(res);
}

export async function editBlock(
  documentId: string,
  pageIndex: number,
  blockId: string,
  text: string,
): Promise<EditResponse> {
  const res = await fetch(`${BASE}/documents/${documentId}/pages/${pageIndex}/blocks/${blockId}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return json(res);
}

export async function addSignature(
  documentId: string,
  pageIndex: number,
  file: Blob,
  bbox: [number, number, number, number],
): Promise<SignatureResponse> {
  const [x0, y0, x1, y1] = bbox;
  const query = new URLSearchParams({ x0: String(x0), y0: String(y0), x1: String(x1), y1: String(y1) });
  const res = await fetch(`${BASE}/documents/${documentId}/pages/${pageIndex}/signature?${query}`, {
    method: "POST",
    headers: { "Content-Type": file.type || "application/octet-stream" },
    body: file,
  });
  return json(res);
}

export async function fetchDocumentBytes(documentId: string): Promise<Uint8Array> {
  const res = await fetch(`${BASE}/documents/${documentId}/file`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return new Uint8Array(await res.arrayBuffer());
}

export function documentDownloadUrl(documentId: string): string {
  return `${BASE}/documents/${documentId}/file`;
}

export async function undo(documentId: string): Promise<{ can_undo: boolean; can_redo: boolean }> {
  const res = await fetch(`${BASE}/documents/${documentId}/undo`, { method: "POST" });
  return json(res);
}

export async function redo(documentId: string): Promise<{ can_undo: boolean; can_redo: boolean }> {
  const res = await fetch(`${BASE}/documents/${documentId}/redo`, { method: "POST" });
  return json(res);
}

/** Real redaction: everything under `rects` (PDF points) is deleted from the
 * file, then painted black. */
export async function redactAreas(
  documentId: string,
  pageIndex: number,
  rects: [number, number, number, number][],
): Promise<{ redacted: number }> {
  const res = await fetch(`${BASE}/documents/${documentId}/pages/${pageIndex}/redact`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rects }),
  });
  return json(res);
}

/** Strips metadata, XMP, attachments, invisible text… from the whole document.
 * `removed` lists what was found (keys like "metadata.author", "xmp"). */
export async function sanitizeDocument(documentId: string): Promise<{ removed: string[] }> {
  const res = await fetch(`${BASE}/documents/${documentId}/sanitize`, { method: "POST" });
  return json(res);
}

export interface ReplaceResult {
  replaced: number;
  lines: number;
  pages: number[];
  truncated: boolean;
  font_substituted: boolean;
}

/** Find & replace across the whole document, as one undo step. */
export async function replaceText(
  documentId: string,
  find: string,
  replace: string,
  options: { matchCase: boolean; wholeWord: boolean },
): Promise<ReplaceResult> {
  const res = await fetch(`${BASE}/documents/${documentId}/replace`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ find, replace, match_case: options.matchCase, whole_word: options.wholeWord }),
  });
  return json(res);
}

export interface InspectReport {
  page_count: number;
  pages_inspected: number;
  hidden_text: { page: number; text: string }[];
  unapplied_redactions: number;
  invisible_text_chars: number;
  invisible_text_samples: { page: number; text: string }[];
  metadata: Record<string, string>;
  has_xmp: boolean;
  versions: number;
  attachments: string[];
  annotations: Record<string, number>;
}

/** Read-only check of what a PDF hides; the file is not kept. */
export async function inspectPdf(file: File): Promise<InspectReport> {
  const res = await fetch(`${BASE}/inspect`, {
    method: "POST",
    headers: { "Content-Type": "application/pdf" },
    body: file,
  });
  return json(res);
}
