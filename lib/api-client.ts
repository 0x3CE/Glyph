import type { EditResponse, PageStructure, UploadResponse } from "./types";

const BASE = "/api";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/documents`, { method: "POST", body: form });
  return json(res);
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
