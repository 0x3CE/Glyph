"use client";

import dynamic from "next/dynamic";

// PdfPage renders to <canvas> via pdf.js, which touches browser-only APIs --
// this must never be attempted during server rendering.
const EditorApp = dynamic(() => import("@/components/EditorApp").then((m) => m.EditorApp), {
  ssr: false,
});

export function EditorAppLoader() {
  return <EditorApp />;
}
