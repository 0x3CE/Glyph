"use client";

import { useEffect, useRef, useState } from "react";
import type React from "react";
import { getDocument } from "pdfjs-dist";
import type { PDFDocumentLoadingTask, PDFDocumentProxy, PDFPageProxy } from "pdfjs-dist";
import "../lib/pdf-setup";
import { addSignature, editBlock, fetchDocumentBytes, getPageStructure } from "../lib/api-client";
import type { Block } from "../lib/types";
import { FLAG_BOLD, FLAG_ITALIC, fontFamilyForFlags } from "../lib/types";
import { SignaturePlacer } from "./SignaturePlacer";
import { useI18n } from "../lib/i18n/I18nProvider";

// Fit-to-width never goes above this (the size the desktop editor always used).
const MAX_FIT_SCALE = 1.5;
// iOS Safari refuses to draw a canvas over ~16.7M pixels (it stays blank); a
// phone's 3x pixel density on a large page gets there quickly. Below this,
// the pixel density is lowered instead.
const MAX_CANVAS_PIXELS = 12_000_000;
// iOS Safari zooms the whole page into any text field under 16px, and stays
// zoomed after the edit.
const MIN_FIELD_FONT_PX = 16;

export type RedactRect = [number, number, number, number]; // PDF points
export type RedactTool = "lines" | "area";

export interface PendingSignature {
  blob: Blob;
  aspectRatio: number;
}

interface PdfPageProps {
  documentId: string;
  pageIndex: number;
  version: number;
  /** Width (CSS px) the page can take: the page is fit to it, then zoomed. */
  availableWidth: number;
  /** 1 = fit to width; higher values zoom in. */
  zoom: number;
  /** Called once a new rendering is on screen (canvas, page box and
   * clickable areas all at the new scale). */
  onRendered?: () => void;
  onEdited: (fontSubstituted: boolean) => void;
  pendingSignature: PendingSignature | null;
  onSignaturePlaced: () => void;
  onCancelSignature: () => void;
  /** Redaction mode: clicks select areas to redact instead of editing. */
  redactMode?: boolean;
  redactTool?: RedactTool;
  redactions?: RedactRect[];
  onAddRedaction?: (rect: RedactRect) => void;
  onRemoveRedaction?: (index: number) => void;
}

interface EditingState {
  block: Block;
  rect: { left: number; top: number; width: number; height: number };
  draft: string;
  saving: boolean;
}

export function PdfPage({
  documentId,
  pageIndex,
  version,
  availableWidth,
  zoom,
  onRendered,
  onEdited,
  pendingSignature,
  onSignaturePlaced,
  onCancelSignature,
  redactMode = false,
  redactTool = "lines",
  redactions = [],
  onAddRedaction,
  onRemoveRedaction,
}: PdfPageProps) {
  const { t } = useI18n();
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [pageSize, setPageSize] = useState<{ width: number; height: number } | null>(null);
  const [editing, setEditing] = useState<EditingState | null>(null);
  const [loading, setLoading] = useState(true);
  const [signatureSaving, setSignatureSaving] = useState(false);
  // CSS px per PDF point of the page as last rendered: positions the
  // clickable areas, the edit field and the signature box over the canvas.
  const [scale, setScale] = useState(1);

  // The PDF itself only changes with `version` (an edit, undo/redo, a
  // signature): turning the page reuses the document already downloaded and
  // parsed by pdf.js, instead of fetching and parsing the whole file again.
  type CachedPdf = { key: string; doc: Promise<PDFDocumentProxy>; loading: { task: PDFDocumentLoadingTask | null } };
  const pdfRef = useRef<CachedPdf | null>(null);
  const release = (cached: CachedPdf | null) => {
    // pdf.js 6 frees a document through its loading task.
    cached?.doc.then(() => cached.loading.task?.destroy()).catch(() => {});
  };
  const loadPdf = (key: string): Promise<PDFDocumentProxy> => {
    if (pdfRef.current?.key !== key) {
      const previous = pdfRef.current;
      const loading: CachedPdf["loading"] = { task: null };
      const doc = fetchDocumentBytes(documentId)
        .then((bytes) => {
          loading.task = getDocument({ data: bytes });
          return loading.task.promise;
        })
        .catch((err) => {
          if (pdfRef.current?.doc === doc) pdfRef.current = null; // let the next attempt retry
          throw err;
        });
      pdfRef.current = { key, doc, loading };
      release(previous);
    }
    return pdfRef.current.doc;
  };
  useEffect(
    () => () => {
      release(pdfRef.current);
      pdfRef.current = null;
    },
    [],
  );

  useEffect(() => {
    let cancelled = false;
    setEditing(null);

    async function run() {
      setLoading(true);
      const [pdf, structure] = await Promise.all([
        loadPdf(`${documentId}:${version}`),
        getPageStructure(documentId, pageIndex),
      ]);
      if (cancelled) return;
      const page: PDFPageProxy = await pdf.getPage(pageIndex + 1);
      if (cancelled) return;

      const natural = page.getViewport({ scale: 1 });
      const fit = availableWidth > 0 ? Math.min(MAX_FIT_SCALE, availableWidth / natural.width) : MAX_FIT_SCALE;
      const renderScale = fit * zoom;
      const viewport = page.getViewport({ scale: renderScale });
      const outputScale = Math.min(
        window.devicePixelRatio || 1,
        Math.sqrt(MAX_CANVAS_PIXELS / (viewport.width * viewport.height)),
      );

      // Render off screen, then swap it in at once: the page on screen keeps
      // its previous rendering (and size) until the new one is complete --
      // no blank flash while it draws, and a pinch-zoom preview (a CSS
      // transform on the page) is replaced in a single frame.
      const offscreen = document.createElement("canvas");
      offscreen.width = Math.floor(viewport.width * outputScale);
      offscreen.height = Math.floor(viewport.height * outputScale);
      const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : undefined;
      const renderTask = page.render({ canvas: offscreen, viewport, transform });
      try {
        await renderTask.promise;
      } catch (err) {
        const name = err && typeof err === "object" && "name" in err ? (err as { name?: string }).name : undefined;
        if (name !== "RenderingCancelledException") throw err;
        return;
      }
      if (cancelled) return;

      const canvas = canvasRef.current;
      const container = containerRef.current;
      const ctx = canvas?.getContext("2d");
      if (!canvas || !container || !ctx) return;
      canvas.width = offscreen.width;
      canvas.height = offscreen.height;
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      container.style.width = `${viewport.width}px`;
      container.style.height = `${viewport.height}px`;
      ctx.drawImage(offscreen, 0, 0);
      onRendered?.();

      setScale(renderScale);
      setPageSize({ width: structure.width, height: structure.height });
      setBlocks(structure.blocks);
      setLoading(false);
    }

    run().catch(console.error);
    return () => {
      cancelled = true;
    };
  }, [documentId, pageIndex, version, availableWidth, zoom]);

  // Area tool: a rectangle drawn with the pointer, in PDF points.
  const [drawing, setDrawing] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
  const toPdfPoint = (e: React.PointerEvent) => {
    const r = containerRef.current!.getBoundingClientRect();
    return { x: (e.clientX - r.left) / scale, y: (e.clientY - r.top) / scale };
  };
  const finishDrawing = () => {
    if (drawing) {
      const rect: RedactRect = [
        Math.min(drawing.x0, drawing.x1),
        Math.min(drawing.y0, drawing.y1),
        Math.max(drawing.x0, drawing.x1),
        Math.max(drawing.y0, drawing.y1),
      ];
      if (rect[2] - rect[0] > 3 && rect[3] - rect[1] > 3) onAddRedaction?.(rect);
    }
    setDrawing(null);
  };

  const onBlockClick = (block: Block) => {
    if (redactMode) {
      // A little margin, so accents and descenders are inside the area.
      const [x0, y0, x1, y1] = block.bbox;
      onAddRedaction?.([x0 - 1, y0 - 1, x1 + 1, y1 + 1]);
      return;
    }
    startEdit(block);
  };

  const startEdit = (block: Block) => {
    if (!pageSize || pendingSignature || redactMode) return;
    const [x0, y0, x1, y1] = block.bbox;
    setEditing({
      block,
      rect: {
        left: x0 * scale,
        top: y0 * scale,
        width: (x1 - x0) * scale,
        height: (y1 - y0) * scale,
      },
      // An unreadable text layer would put garbage in the field (and the
      // user would edit around it): start empty instead, see text_reliable.
      draft: block.text_reliable !== false ? block.text : "",
      saving: false,
    });
  };

  const cancelEdit = () => setEditing(null);

  const commitEdit = async () => {
    if (!editing) return;
    // Nothing changed -- or an unreadable line left empty, which would just
    // erase it.
    if (editing.draft === editing.block.text || (editing.block.text_reliable === false && !editing.draft.trim())) {
      setEditing(null);
      return;
    }
    setEditing((prev) => (prev ? { ...prev, saving: true } : prev));
    try {
      const result = await editBlock(documentId, pageIndex, editing.block.id, editing.draft);
      setEditing(null);
      onEdited(result.font_substituted);
    } catch (err) {
      console.error(err);
      setEditing((prev) => (prev ? { ...prev, saving: false } : prev));
    }
  };

  const confirmSignature = async (bbox: [number, number, number, number]) => {
    if (!pendingSignature) return;
    setSignatureSaving(true);
    try {
      await addSignature(documentId, pageIndex, pendingSignature.blob, bbox);
      onSignaturePlaced();
    } catch (err) {
      console.error(err);
      setSignatureSaving(false);
    }
  };

  const dominantSpan = (block: Block) => {
    let best = block.lines[0]?.spans[0];
    let bestLen = 0;
    for (const line of block.lines) {
      for (const span of line.spans) {
        if (span.text.length > bestLen) {
          best = span;
          bestLen = span.text.length;
        }
      }
    }
    return best;
  };

  return (
    <div className="pdf-page" ref={containerRef}>
      <canvas ref={canvasRef} className="pdf-base-canvas" />
      <div className="block-overlay" style={pendingSignature ? { pointerEvents: "none" } : undefined}>
        {!loading &&
          blocks.map((block) => {
            const [x0, y0, x1, y1] = block.bbox;
            if (block.text.trim().length === 0) return null;
            return (
              <div
                key={block.id}
                className="block-hit-area"
                style={{
                  left: x0 * scale,
                  top: y0 * scale,
                  width: (x1 - x0) * scale,
                  height: (y1 - y0) * scale,
                }}
                onClick={() => onBlockClick(block)}
              />
            );
          })}
      </div>
      {redactMode && redactTool === "area" && (
        <div
          className="redact-draw-layer"
          onPointerDown={(e) => {
            e.currentTarget.setPointerCapture(e.pointerId);
            const p = toPdfPoint(e);
            setDrawing({ x0: p.x, y0: p.y, x1: p.x, y1: p.y });
          }}
          onPointerMove={(e) => {
            if (!drawing) return;
            const p = toPdfPoint(e);
            setDrawing({ ...drawing, x1: p.x, y1: p.y });
          }}
          onPointerUp={finishDrawing}
          onPointerCancel={() => setDrawing(null)}
        />
      )}
      {redactMode &&
        redactions.map(([x0, y0, x1, y1], i) => (
          <div
            key={`${i}-${x0}-${y0}`}
            className="redact-pending"
            style={{ left: x0 * scale, top: y0 * scale, width: (x1 - x0) * scale, height: (y1 - y0) * scale }}
          >
            <button
              type="button"
              className="redact-remove"
              aria-label={t.tools.redactRemove}
              title={t.tools.redactRemove}
              onPointerDown={(e) => e.stopPropagation()}
              onClick={() => onRemoveRedaction?.(i)}
            >
              ×
            </button>
          </div>
        ))}
      {drawing && (
        <div
          className="redact-pending redact-drawing"
          style={{
            left: Math.min(drawing.x0, drawing.x1) * scale,
            top: Math.min(drawing.y0, drawing.y1) * scale,
            width: Math.abs(drawing.x1 - drawing.x0) * scale,
            height: Math.abs(drawing.y1 - drawing.y0) * scale,
          }}
        />
      )}
      {editing &&
        (() => {
          const span = dominantSpan(editing.block);
          return (
            <div className="block-editor" style={{ left: editing.rect.left - 4, top: editing.rect.top - 4 }}>
              {(() => {
                // Under MIN_FIELD_FONT_PX, the field is laid out at that size
                // and shrunk back visually with a transform: same look, but
                // iOS no longer zooms in when it gets focus.
                const fontPx = span.size * scale;
                const k = Math.min(1, fontPx / MIN_FIELD_FONT_PX);
                const boxWidth = Math.max(editing.rect.width, 140) + 8;
                const boxHeight = Math.max(editing.rect.height, 24) + 8;
                return (
                  <>
                    {editing.block.text_reliable === false && <p className="block-editor-hint">{t.editor.unreadableText}</p>}
                    <div className="block-editor-field" style={{ width: boxWidth, height: boxHeight }}>
                      <textarea
                        autoFocus
                        className="block-editor-textarea"
                        style={{
                          width: boxWidth / k,
                          height: boxHeight / k,
                          fontSize: fontPx / k,
                          lineHeight: `${((fontPx * 1.25) / k).toFixed(1)}px`,
                          padding: 3 / k,
                          borderWidth: 1.5 / k,
                          transform: k < 1 ? `scale(${k})` : undefined,
                          transformOrigin: "top left",
                          fontFamily: fontFamilyForFlags(span.flags),
                          fontWeight: span.flags & FLAG_BOLD ? "bold" : "normal",
                          fontStyle: span.flags & FLAG_ITALIC ? "italic" : "normal",
                          // Always readable in the editor regardless of the
                          // original text color (e.g. white text on a colored PDF
                          // background would be invisible on the textarea's white
                          // background otherwise) -- purely a UI choice, the
                          // backend still reinserts the ORIGINAL color untouched.
                          color: "#111111",
                        }}
                        value={editing.draft}
                        placeholder={editing.block.text_reliable === false ? t.editor.unreadablePlaceholder : undefined}
                        disabled={editing.saving}
                        onChange={(e) => setEditing((prev) => (prev ? { ...prev, draft: e.target.value } : prev))}
                        onKeyDown={(e) => {
                          if (e.key === "Escape") cancelEdit();
                        }}
                      />
                    </div>
                  </>
                );
              })()}
              <div className="block-editor-controls">
                <button className="btn btn-accent" onClick={commitEdit} disabled={editing.saving}>
                  {editing.saving ? t.editor.saving : t.editor.save}
                </button>
                <button className="btn btn-ghost" onClick={cancelEdit} disabled={editing.saving}>
                  {t.editor.cancel}
                </button>
              </div>
            </div>
          );
        })()}
      {pendingSignature && pageSize && (
        <SignaturePlacer
          // Its box lives in screen pixels: start over if the zoom changes.
          key={scale}
          blob={pendingSignature.blob}
          pageWidth={pageSize.width}
          pageHeight={pageSize.height}
          scale={scale}
          aspectRatio={pendingSignature.aspectRatio}
          saving={signatureSaving}
          onConfirm={confirmSignature}
          onCancel={onCancelSignature}
        />
      )}
    </div>
  );
}
