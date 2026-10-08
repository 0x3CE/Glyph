"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { DragEvent } from "react";
import { localePath } from "@/lib/i18n/config";
import type { Locale } from "@/lib/i18n/config";
import { setPendingUpload } from "@/lib/pending-upload";
import type { EditorIntent } from "@/lib/pending-upload";

interface Props {
  locale: Locale;
  intent: EditorIntent;
  title: string;
  or: string;
  choose: string;
  hint: string;
  /** Handle the file here instead of opening the editor with it. */
  onFile?: (file: File) => void;
}

// A drop zone on a content page that opens the editor with the file already
// loaded (and, depending on `intent`, a tool already open).
export function UploadDropzone({ locale, intent, title, or, choose, hint, onFile }: Props) {
  const router = useRouter();
  const [dragging, setDragging] = useState(false);

  const open = (file: File | undefined) => {
    if (!file || file.type !== "application/pdf") return;
    if (onFile) return onFile(file);
    setPendingUpload(file, intent);
    router.push(localePath(locale, "/editor"));
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    open(e.dataTransfer.files?.[0]);
  };

  return (
    <div
      className={`dropzone seo-dropzone ${dragging ? "dropzone-active" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <div className="dropzone-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="28" height="28" fill="none">
          <path
            d="M12 4v11m0-11 4 4m-4-4-4 4M5 16v2a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-2"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <p className="dropzone-title">{title}</p>
      <p className="dropzone-sub">{or}</p>
      <label className="btn btn-accent">
        {choose}
        <input type="file" accept="application/pdf" hidden onChange={(e) => open(e.target.files?.[0])} />
      </label>
      <p className="seo-dropzone-hint">{hint}</p>
    </div>
  );
}
