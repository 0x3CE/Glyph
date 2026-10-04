"use client";

import dynamic from "next/dynamic";
import { I18nProvider } from "@/lib/i18n/I18nProvider";
import type { Locale } from "@/lib/i18n";

// PdfPage renders to <canvas> via pdf.js, which touches browser-only APIs --
// this must never be attempted during server rendering.
const EditorApp = dynamic(() => import("@/components/EditorApp").then((m) => m.EditorApp), {
  ssr: false,
});

export function EditorAppLoader({ locale }: { locale: Locale }) {
  return (
    <I18nProvider locale={locale}>
      <EditorApp />
    </I18nProvider>
  );
}
