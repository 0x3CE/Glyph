"use client";

import { useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";

interface SignatureModalProps {
  onConfirm: (blob: Blob, aspectRatio: number) => void;
  onClose: () => void;
}

type Tab = "draw" | "upload";

const CANVAS_WIDTH = 480;
const CANVAS_HEIGHT = 180;
const ACCEPTED_TYPES = ["application/pdf", "image/png", "image/jpeg"];

export function SignatureModal({ onConfirm, onClose }: SignatureModalProps) {
  const [tab, setTab] = useState<Tab>("draw");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const [hasDrawn, setHasDrawn] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const pointerPos = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((e.clientX - rect.left) / rect.width) * canvas.width,
      y: ((e.clientY - rect.top) / rect.height) * canvas.height,
    };
  };

  const startDraw = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    drawing.current = true;
    const { x, y } = pointerPos(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
    canvasRef.current?.setPointerCapture(e.pointerId);
  };

  const moveDraw = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) return;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    const { x, y } = pointerPos(e);
    ctx.strokeStyle = "#171717";
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasDrawn(true);
  };

  const endDraw = () => {
    drawing.current = false;
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasDrawn(false);
  };

  const confirmDrawing = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    // A transparent background (canvas is never filled) rather than white:
    // stamped onto the page via `insert_image`, a white rectangle would
    // cover whatever's underneath instead of just adding ink.
    canvas.toBlob((blob) => {
      if (blob) onConfirm(blob, canvas.width / canvas.height);
    }, "image/png");
  };

  const pickFile = (f: File) => {
    if (!ACCEPTED_TYPES.includes(f.type)) {
      setFileError("Format non supporté — PDF, PNG ou JPG uniquement.");
      return;
    }
    setFileError(null);
    setFile(f);
  };

  const confirmFile = () => {
    if (!file) return;
    if (file.type === "application/pdf") {
      // No cheap way to read a PDF's own page aspect ratio from the
      // browser without parsing it -- a common signature-strip ratio is a
      // fine default since the placement box is freely resizable next.
      onConfirm(file, 3);
      return;
    }
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      onConfirm(file, img.naturalWidth / img.naturalHeight || 3);
      URL.revokeObjectURL(url);
    };
    img.onerror = () => {
      onConfirm(file, 3);
      URL.revokeObjectURL(url);
    };
    img.src = url;
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal signature-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Ajouter une signature</h2>
          <button className="btn btn-icon" onClick={onClose} title="Fermer">
            ✕
          </button>
        </div>

        <div className="tab-row">
          <button className={`tab ${tab === "draw" ? "tab-active" : ""}`} onClick={() => setTab("draw")}>
            Dessiner
          </button>
          <button className={`tab ${tab === "upload" ? "tab-active" : ""}`} onClick={() => setTab("upload")}>
            Importer un fichier
          </button>
        </div>

        {tab === "draw" && (
          <div className="signature-tab-panel">
            <canvas
              ref={canvasRef}
              width={CANVAS_WIDTH}
              height={CANVAS_HEIGHT}
              className="signature-canvas"
              onPointerDown={startDraw}
              onPointerMove={moveDraw}
              onPointerUp={endDraw}
              onPointerLeave={endDraw}
            />
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={clearCanvas} disabled={!hasDrawn}>
                Effacer
              </button>
              <button className="btn btn-accent" onClick={confirmDrawing} disabled={!hasDrawn}>
                Utiliser cette signature
              </button>
            </div>
          </div>
        )}

        {tab === "upload" && (
          <div className="signature-tab-panel">
            <label className="btn btn-ghost">
              Choisir un fichier (PDF, PNG, JPG)
              <input
                type="file"
                accept="application/pdf,image/png,image/jpeg"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) pickFile(f);
                }}
              />
            </label>
            {file && <p className="signature-file-name">{file.name}</p>}
            {fileError && <p className="signature-file-error">{fileError}</p>}
            <div className="modal-actions">
              <button className="btn btn-accent" onClick={confirmFile} disabled={!file}>
                Utiliser ce fichier
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
