"use client";

import { useEffect, useRef, useState } from "react";
import { getDocument } from "pdfjs-dist";
import type { PDFPageProxy } from "pdfjs-dist";
import "../lib/pdf-setup";
import { editBlock, fetchDocumentBytes, getPageStructure } from "../lib/api-client";
import type { Block } from "../lib/types";
import { FLAG_BOLD, FLAG_ITALIC, fontFamilyForFlags } from "../lib/types";

interface PdfPageProps {
  documentId: string;
  pageIndex: number;
  version: number;
  scale: number;
  onEdited: (fontSubstituted: boolean) => void;
}

interface EditingState {
  block: Block;
  rect: { left: number; top: number; width: number; height: number };
  draft: string;
  saving: boolean;
}

export function PdfPage({ documentId, pageIndex, version, scale, onEdited }: PdfPageProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [pageSize, setPageSize] = useState<{ width: number; height: number } | null>(null);
  const [editing, setEditing] = useState<EditingState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setEditing(null);

    async function run() {
      setLoading(true);
      const [bytes, structure] = await Promise.all([
        fetchDocumentBytes(documentId),
        getPageStructure(documentId, pageIndex),
      ]);
      if (cancelled) return;

      const pdf = await getDocument({ data: bytes }).promise;
      if (cancelled) return;
      const page: PDFPageProxy = await pdf.getPage(pageIndex + 1);
      if (cancelled) return;

      const viewport = page.getViewport({ scale });
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;

      const outputScale = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * outputScale);
      canvas.height = Math.floor(viewport.height * outputScale);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      container.style.width = `${viewport.width}px`;
      container.style.height = `${viewport.height}px`;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : undefined;
      const renderTask = page.render({ canvas, viewport, transform });
      try {
        await renderTask.promise;
      } catch (err) {
        const name = err && typeof err === "object" && "name" in err ? (err as { name?: string }).name : undefined;
        if (name !== "RenderingCancelledException") throw err;
      }
      if (cancelled) return;

      setPageSize({ width: structure.width, height: structure.height });
      setBlocks(structure.blocks);
      setLoading(false);
    }

    run().catch(console.error);
    return () => {
      cancelled = true;
    };
  }, [documentId, pageIndex, version, scale]);

  const startEdit = (block: Block) => {
    if (!pageSize) return;
    const [x0, y0, x1, y1] = block.bbox;
    setEditing({
      block,
      rect: {
        left: x0 * scale,
        top: y0 * scale,
        width: (x1 - x0) * scale,
        height: (y1 - y0) * scale,
      },
      draft: block.text,
      saving: false,
    });
  };

  const cancelEdit = () => setEditing(null);

  const commitEdit = async () => {
    if (!editing) return;
    if (editing.draft === editing.block.text) {
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
      <div className="block-overlay">
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
                onClick={() => startEdit(block)}
              />
            );
          })}
      </div>
      {editing &&
        (() => {
          const span = dominantSpan(editing.block);
          return (
            <div className="block-editor" style={{ left: editing.rect.left - 4, top: editing.rect.top - 4 }}>
              <textarea
                autoFocus
                className="block-editor-textarea"
                style={{
                  width: Math.max(editing.rect.width, 140) + 8,
                  height: Math.max(editing.rect.height, 24) + 8,
                  fontSize: span.size * scale,
                  lineHeight: `${(span.size * scale * 1.25).toFixed(1)}px`,
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
                disabled={editing.saving}
                onChange={(e) => setEditing((prev) => (prev ? { ...prev, draft: e.target.value } : prev))}
                onKeyDown={(e) => {
                  if (e.key === "Escape") cancelEdit();
                }}
              />
              <div className="block-editor-controls">
                <button className="btn btn-accent" onClick={commitEdit} disabled={editing.saving}>
                  {editing.saving ? "Enregistrement…" : "Enregistrer"}
                </button>
                <button className="btn btn-ghost" onClick={cancelEdit} disabled={editing.saving}>
                  Annuler
                </button>
              </div>
            </div>
          );
        })()}
    </div>
  );
}
