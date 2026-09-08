"use client";

import { useCallback, useState } from "react";
import type { DragEvent } from "react";
import Link from "next/link";
import { PdfPage } from "@/components/PdfPage";
import { BrandMark } from "@/components/BrandMark";
import { documentDownloadUrl, redo, undo, uploadDocument } from "@/lib/api-client";

const SCALE = 1.5;

export function EditorApp() {
  const [fileName, setFileName] = useState<string | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [pageCount, setPageCount] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [version, setVersion] = useState(0);
  const [editCount, setEditCount] = useState(0);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const [substitutionNotice, setSubstitutionNotice] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const loadFile = useCallback(async (file: File) => {
    setError(null);
    setLoading(true);
    try {
      const res = await uploadDocument(file);
      setDocumentId(res.document_id);
      setPageCount(res.page_count);
      setPageNumber(1);
      setVersion((v) => v + 1);
      setEditCount(0);
      setCanUndo(false);
      setCanRedo(false);
      setFileName(file.name);
    } catch (e) {
      console.error(e);
      setError("Impossible de charger ce PDF. Le fichier est peut-être corrompu ou protégé.");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleEdited = (fontSubstituted: boolean) => {
    setEditCount((n) => n + 1);
    setCanUndo(true);
    setCanRedo(false);
    setSubstitutionNotice(fontSubstituted);
    setVersion((v) => v + 1);
  };

  const handleUndo = async () => {
    if (!documentId) return;
    const res = await undo(documentId);
    setCanUndo(res.can_undo);
    setCanRedo(res.can_redo);
    setVersion((v) => v + 1);
  };

  const handleRedo = async () => {
    if (!documentId) return;
    const res = await redo(documentId);
    setCanUndo(res.can_undo);
    setCanRedo(res.can_redo);
    setVersion((v) => v + 1);
  };

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const onDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type === "application/pdf") loadFile(file);
  };

  return (
    <div className="editor-shell">
      <header className="topbar">
        <Link href="/" className="brand">
          <span className="brand-mark">
            <BrandMark />
          </span>
          <span className="brand-name">Glyph</span>
        </Link>

        <div className="topbar-actions">
          <label className="btn btn-ghost">
            {fileName ? "Changer de fichier" : "Ouvrir un PDF"}
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) loadFile(file);
              }}
              hidden
            />
          </label>
          {documentId && (
            <>
              <button className="btn btn-icon" onClick={handleUndo} disabled={!canUndo} title="Annuler">
                ↶
              </button>
              <button className="btn btn-icon" onClick={handleRedo} disabled={!canRedo} title="Rétablir">
                ↷
              </button>
              <a
                className="btn btn-accent"
                href={documentDownloadUrl(documentId)}
                download={fileName ? `modifie-${fileName}` : "document-modifie.pdf"}
              >
                Télécharger{editCount ? <span className="btn-badge">{editCount}</span> : null}
              </a>
            </>
          )}
        </div>
      </header>

      <div className="toast-stack">
        {error && (
          <div className="toast toast-error" onClick={() => setError(null)}>
            {error}
          </div>
        )}
        {substitutionNotice && (
          <div className="toast toast-notice" onClick={() => setSubstitutionNotice(false)}>
            Police d&apos;origine indisponible pour ce texte — une police de remplacement a été utilisée.
          </div>
        )}
      </div>

      <main className="workspace" onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
        {!documentId && !loading && (
          <div className="empty-state">
            <div className={`dropzone ${isDragging ? "dropzone-active" : ""}`}>
              <div className="dropzone-icon">
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
              <p className="dropzone-title">Glisse un PDF ici</p>
              <p className="dropzone-sub">ou</p>
              <label className="btn btn-accent">
                Choisir un fichier
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) loadFile(file);
                  }}
                  hidden
                />
              </label>
            </div>
            <p className="empty-hint">
              Rien n&apos;est stocké : le fichier est traité en mémoire le temps de la session.
            </p>
          </div>
        )}

        {loading && (
          <div className="empty-state">
            <div className="spinner" />
          </div>
        )}

        {documentId && (
          <div className="viewer">
            <div className="page-toolbar">
              <button
                className="btn btn-icon"
                disabled={pageNumber <= 1}
                onClick={() => setPageNumber((n) => n - 1)}
                title="Page précédente"
              >
                ←
              </button>
              <span className="page-indicator">
                {pageNumber} / {pageCount}
              </span>
              <button
                className="btn btn-icon"
                disabled={pageNumber >= pageCount}
                onClick={() => setPageNumber((n) => n + 1)}
                title="Page suivante"
              >
                →
              </button>
            </div>

            <div className="page-canvas">
              <PdfPage
                documentId={documentId}
                pageIndex={pageNumber - 1}
                version={version}
                scale={SCALE}
                onEdited={handleEdited}
              />
            </div>
          </div>
        )}

        {isDragging && documentId && (
          <div className="drop-overlay">
            <p>Déposer pour remplacer le document</p>
          </div>
        )}
      </main>
    </div>
  );
}
