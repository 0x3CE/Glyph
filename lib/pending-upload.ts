"use client";

// Hands a file picked on a content page (e.g. /modifier-texte-pdf) to the
// editor, which then opens it right away. Module state survives Next's
// client-side navigation; it is consumed once and never persisted.

export type EditorIntent = "edit" | "redact" | "anonymize" | "replace" | "sign";

let pending: { file: File; intent: EditorIntent } | null = null;

export function setPendingUpload(file: File, intent: EditorIntent): void {
  pending = { file, intent };
}

export function takePendingUpload(): { file: File; intent: EditorIntent } | null {
  const value = pending;
  pending = null;
  return value;
}
