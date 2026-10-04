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
