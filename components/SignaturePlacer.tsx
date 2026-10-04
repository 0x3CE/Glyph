"use client";

import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { useI18n } from "@/lib/i18n/I18nProvider";

interface SignaturePlacerProps {
  blob: Blob;
  pageWidth: number; // PDF points
  pageHeight: number; // PDF points
  scale: number;
  aspectRatio: number;
  saving: boolean;
  onConfirm: (bbox: [number, number, number, number]) => void;
  onCancel: () => void;
}

interface ScreenRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

type DragMode = "move" | "resize";

interface DragState {
  mode: DragMode;
  startX: number;
  startY: number;
  startRect: ScreenRect;
}

const MIN_SIZE = 24;

export function SignaturePlacer({
  blob,
  pageWidth,
  pageHeight,
  scale,
  aspectRatio,
  saving,
  onConfirm,
  onCancel,
}: SignaturePlacerProps) {
  const { t } = useI18n();
  const pageBoxWidth = pageWidth * scale;
  const pageBoxHeight = pageHeight * scale;

  const [rect, setRect] = useState<ScreenRect>(() => {
    const width = Math.min(220, pageBoxWidth * 0.6);
    const height = width / aspectRatio;
    return {
      left: (pageBoxWidth - width) / 2,
      top: (pageBoxHeight - height) / 2,
      width,
      height,
    };
  });
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const dragRef = useRef<DragState | null>(null);

  useEffect(() => {
    if (!blob.type.startsWith("image/")) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(blob);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [blob]);

  const clamp = (r: ScreenRect): ScreenRect => {
    const width = Math.min(Math.max(r.width, MIN_SIZE), pageBoxWidth);
    const height = Math.min(Math.max(r.height, MIN_SIZE), pageBoxHeight);
    const left = Math.min(Math.max(r.left, 0), Math.max(pageBoxWidth - width, 0));
    const top = Math.min(Math.max(r.top, 0), Math.max(pageBoxHeight - height, 0));
    return { left, top, width, height };
  };

  const beginDrag = (mode: DragMode) => (e: ReactPointerEvent) => {
    if (saving) return;
    e.preventDefault();
    e.stopPropagation();
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
    dragRef.current = { mode, startX: e.clientX, startY: e.clientY, startRect: rect };
  };

  const onPointerMove = (e: ReactPointerEvent) => {
    const drag = dragRef.current;
    if (!drag) return;
    const dx = e.clientX - drag.startX;
    const dy = e.clientY - drag.startY;
    if (drag.mode === "move") {
      setRect(clamp({ ...drag.startRect, left: drag.startRect.left + dx, top: drag.startRect.top + dy }));
    } else {
      setRect(clamp({ ...drag.startRect, width: drag.startRect.width + dx, height: drag.startRect.height + dy }));
    }
  };

  const endDrag = () => {
    dragRef.current = null;
  };

  const confirm = () => {
    onConfirm([rect.left / scale, rect.top / scale, (rect.left + rect.width) / scale, (rect.top + rect.height) / scale]);
  };

  return (
    <div
      className="signature-placer"
      style={{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }}
      onPointerDown={beginDrag("move")}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
    >
      {previewUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={previewUrl} alt={t.editor.signatureAlt} className="signature-preview" draggable={false} />
      ) : (
        <div className="signature-preview signature-preview-file">PDF</div>
      )}
      <div className="signature-placer-handle" onPointerDown={beginDrag("resize")} />
      <div className="signature-placer-controls" onPointerDown={(e) => e.stopPropagation()}>
        <button className="btn btn-accent" onClick={confirm} disabled={saving}>
          {saving ? t.editor.saving : t.editor.confirm}
        </button>
        <button className="btn btn-ghost" onClick={onCancel} disabled={saving}>
          {t.editor.cancel}
        </button>
      </div>
    </div>
  );
}
