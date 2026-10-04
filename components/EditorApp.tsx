"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import Link from "next/link";
import { PdfPage } from "@/components/PdfPage";
import type { PendingSignature } from "@/components/PdfPage";
import { SignatureModal } from "@/components/SignatureModal";
import { BrandMark } from "@/components/BrandMark";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { localePath } from "@/lib/i18n";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { deleteDocument, documentDownloadUrl, redo, undo, uploadDocument } from "@/lib/api-client";

const SCALE = 1.5;

export function EditorApp() {
  const { locale, t } = useI18n();
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
  const [showSignatureModal, setShowSignatureModal] = useState(false);
  const [pendingSignature, setPendingSignature] = useState<PendingSignature | null>(null);

  // The server keeps each document in memory until it expires: free it as
  // soon as it's no longer reachable from this tab (another PDF opened, tab
  // closed). Not done in an effect cleanup, which React's StrictMode runs
  // on mount in dev and would delete the document being edited.
  const documentIdRef = useRef<string | null>(null);
  useEffect(() => {
    const onPageHide = (event: PageTransitionEvent) => {
      // A page kept in the back/forward cache may come back: keep its document.
      if (!event.persisted && documentIdRef.current) deleteDocument(documentIdRef.current);
    };
    window.addEventListener("pagehide", onPageHide);
    return () => window.removeEventListener("pagehide", onPageHide);
  }, []);

  const loadFile = useCallback(async (file: File) => {
    setError(null);
    setLoading(true);
    try {
      const res = await uploadDocument(file);
      if (documentIdRef.current) deleteDocument(documentIdRef.current);
      documentIdRef.current = res.document_id;
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
      setError(t.editor.loadError);
    } finally {
      setLoading(false);
    }
  }, [t]);

  const handleEdited = (fontSubstituted: boolean) => {
    setEditCount((n) => n + 1);
    setCanUndo(true);
    setCanRedo(false);
    setSubstitutionNotice(fontSubstituted);
    setVersion((v) => v + 1);
  };

  const handleSignaturePlaced = () => {
    setPendingSignature(null);
    setEditCount((n) => n + 1);
    setCanUndo(true);
    setCanRedo(false);
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
        <Link href={localePath(locale, "/")} className="brand">
          <span className="brand-mark">
            <BrandMark />
          </span>
          <span className="brand-name">Glyph</span>
        </Link>

        <div className="topbar-actions">
          {/* Only before a document is open: switching reloads the page,
              which would drop the document being edited. */}
          {!documentId && (
            <LanguageSwitcher
              locale={locale}
              path="/editor"
              label={t.switcher.label}
              shortLabel={t.switcher.shortLabel}
              ariaLabel={t.switcher.ariaLabel}
              className="btn btn-ghost lang-switch"
            />
          )}
          <label className="btn btn-ghost">
            {fileName ? t.editor.changeFile : t.editor.openPdf}
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
              <button className="btn btn-icon" onClick={handleUndo} disabled={!canUndo} title={t.editor.undo}>
                ↶
              </button>
              <button className="btn btn-icon" onClick={handleRedo} disabled={!canRedo} title={t.editor.redo}>
                ↷
              </button>
              <button
                className="btn btn-ghost"
                onClick={() => setShowSignatureModal(true)}
                disabled={!!pendingSignature}
              >
                {t.editor.signature}
              </button>
              <a
                className="btn btn-accent"
                href={documentDownloadUrl(documentId)}
                download={fileName ? t.editor.downloadName(fileName) : t.editor.defaultDownloadName}
              >
                {t.editor.download}
                {editCount ? <span className="btn-badge">{editCount}</span> : null}
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
            {t.editor.substitutionNotice}
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
              <p className="dropzone-title">{t.editor.dropTitle}</p>
              <p className="dropzone-sub">{t.editor.dropOr}</p>
              <label className="btn btn-accent">
                {t.editor.chooseFile}
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
            <p className="empty-hint">{t.editor.emptyHint}</p>
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
                title={t.editor.previousPage}
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
                title={t.editor.nextPage}
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
                pendingSignature={pendingSignature}
                onSignaturePlaced={handleSignaturePlaced}
                onCancelSignature={() => setPendingSignature(null)}
              />
            </div>
          </div>
        )}

        {isDragging && documentId && (
          <div className="drop-overlay">
            <p>{t.editor.dropToReplace}</p>
          </div>
        )}
      </main>

      {showSignatureModal && (
        <SignatureModal
          onClose={() => setShowSignatureModal(false)}
          onConfirm={(blob, aspectRatio) => {
            setPendingSignature({ blob, aspectRatio });
            setShowSignatureModal(false);
          }}
        />
      )}
    </div>
  );
}
