"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import Link from "next/link";
import { PdfPage } from "@/components/PdfPage";
import type { PendingSignature, RedactRect, RedactTool } from "@/components/PdfPage";
import { ReplaceModal } from "@/components/ReplaceModal";
import { SignatureModal } from "@/components/SignatureModal";
import { MAX_ZOOM, MIN_ZOOM, usePinchZoom } from "@/components/usePinchZoom";
import { BrandMark } from "@/components/BrandMark";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { localePath } from "@/lib/i18n";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { takePendingUpload } from "@/lib/pending-upload";
import type { EditorIntent } from "@/lib/pending-upload";
import {
  deleteDocument,
  documentDownloadUrl,
  redactAreas,
  redo,
  sanitizeDocument,
  undo,
  uploadDocument,
} from "@/lib/api-client";
import type { ReplaceResult } from "@/lib/api-client";

// Multipliers on top of fit-to-width (1 = the page fills the available width).
// The − / + buttons jump between these; a pinch can land anywhere in between.
const ZOOM_STEPS = [MIN_ZOOM, 0.75, 1, 1.5, 2, 3, MAX_ZOOM];
const zoomOutStep = (z: number) => [...ZOOM_STEPS].reverse().find((s) => s < z - 0.01) ?? MIN_ZOOM;
const zoomInStep = (z: number) => ZOOM_STEPS.find((s) => s > z + 0.01) ?? MAX_ZOOM;

// Toasts close by themselves after this long (or on click).
const TOAST_MS = 3000;

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
  const [zoom, setZoom] = useState(1);
  const [notice, setNotice] = useState<string | null>(null);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showReplaceModal, setShowReplaceModal] = useState(false);
  // Redaction mode: areas picked on the current page, applied together.
  const [redactMode, setRedactMode] = useState(false);
  const [redactTool, setRedactTool] = useState<RedactTool>("lines");
  const [redactions, setRedactions] = useState<RedactRect[]>([]);

  // Width the page can take inside the scrollable area, so it fits a phone
  // screen instead of being drawn at a fixed desktop size. Small changes
  // (a scrollbar appearing) are ignored so they can't trigger re-renders in
  // a loop.
  const [availableWidth, setAvailableWidth] = useState(0);
  const canvasAreaRef = useRef<HTMLDivElement | null>(null);
  const observerRef = useRef<ResizeObserver | null>(null);
  const measureCanvasArea = useCallback((node: HTMLDivElement | null) => {
    observerRef.current?.disconnect();
    canvasAreaRef.current = node;
    if (!node) return;
    const update = () => {
      const style = getComputedStyle(node);
      const width = node.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
      setAvailableWidth((prev) => (Math.abs(prev - width) > 16 ? width : prev));
    };
    update();
    observerRef.current = new ResizeObserver(update);
    observerRef.current.observe(node);
  }, []);
  const { afterRender } = usePinchZoom(canvasAreaRef, zoom, setZoom, !!documentId);

  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => setError(null), TOAST_MS);
    return () => clearTimeout(timer);
  }, [error]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), TOAST_MS);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    if (!substitutionNotice) return;
    const timer = setTimeout(() => setSubstitutionNotice(false), TOAST_MS);
    return () => clearTimeout(timer);
  }, [substitutionNotice, version]);

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

  const loadFile = useCallback(async (file: File): Promise<boolean> => {
    setError(null);
    setNotice(null);
    setRedactMode(false);
    setRedactions([]);
    setLoading(true);
    try {
      const res = await uploadDocument(file);
      if (documentIdRef.current) deleteDocument(documentIdRef.current);
      documentIdRef.current = res.document_id;
      setDocumentId(res.document_id);
      setPageCount(res.page_count);
      setPageNumber(1);
      setZoom(1);
      setVersion((v) => v + 1);
      setEditCount(0);
      setCanUndo(false);
      setCanRedo(false);
      setFileName(file.name);
      return true;
    } catch (e) {
      console.error(e);
      setError(t.editor.loadError);
      return false;
    } finally {
      setLoading(false);
    }
  }, [t]);

  // What a content page asked for, once its file is open (/caviarder-pdf
  // opens redaction mode, /signer-pdf the signature dialog…).
  const applyIntent = useCallback((intent: EditorIntent) => {
    if (intent === "redact" || intent === "anonymize") setRedactMode(true);
    if (intent === "sign") setShowSignatureModal(true);
    if (intent === "replace") setShowReplaceModal(true);
  }, []);

  // A file picked on a content page (/modifier-texte-pdf…) opens right away.
  useEffect(() => {
    const pending = takePendingUpload();
    if (pending) void loadFile(pending.file).then((ok) => ok && applyIntent(pending.intent));
  }, [loadFile, applyIntent]);

  // Any change that produced a new version of the document.
  const recordChange = () => {
    setEditCount((n) => n + 1);
    setCanUndo(true);
    setCanRedo(false);
    setVersion((v) => v + 1);
  };

  const handleApplyRedactions = async () => {
    if (!documentId || redactions.length === 0) return;
    setBusy(true);
    try {
      const res = await redactAreas(documentId, pageNumber - 1, redactions);
      setRedactions([]);
      recordChange();
      setNotice(t.tools.redactDone(res.redacted));
    } catch (e) {
      console.error(e);
      setError(t.tools.actionError);
    } finally {
      setBusy(false);
    }
  };

  const handleSanitize = async () => {
    if (!documentId) return;
    setToolsOpen(false);
    setBusy(true);
    try {
      const res = await sanitizeDocument(documentId);
      recordChange();
      const labels = res.removed.map((key) => t.tools.removedLabels[key] ?? key);
      setNotice(labels.length ? t.tools.sanitizeDone(labels.join(", ")) : t.tools.sanitizeNothing);
    } catch (e) {
      console.error(e);
      setError(t.tools.actionError);
    } finally {
      setBusy(false);
    }
  };

  const handleReplaced = (result: ReplaceResult) => {
    setShowReplaceModal(false);
    recordChange();
    setSubstitutionNotice(result.font_substituted);
    setNotice(t.replace.done(result.replaced, result.pages) + (result.truncated ? ` ${t.replace.truncated}` : ""));
    // Show a page that changed if the current one didn't.
    if (!result.pages.includes(pageNumber)) changePage(result.pages[0]);
  };

  const changePage = (n: number) => {
    setRedactions([]); // areas are per page
    setPageNumber(n);
  };

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
          <span className="brand-name only-wide">Glyph</span>
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
            <span className="only-wide">{fileName ? t.editor.changeFile : t.editor.openPdf}</span>
            <span className="only-narrow">{t.editor.openShort}</span>
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
                disabled={!!pendingSignature || redactMode}
              >
                <span className="only-wide">{t.editor.signature}</span>
                <span className="only-narrow">{t.editor.signatureShort}</span>
              </button>
              <div className="tools-menu">
                <button
                  className="btn btn-ghost tools-trigger"
                  aria-haspopup="menu"
                  aria-expanded={toolsOpen}
                  aria-label={t.tools.menu}
                  onClick={() => setToolsOpen((o) => !o)}
                  disabled={busy}
                >
                  <span className="only-wide">{t.tools.menu}</span>
                  <span className="only-narrow" aria-hidden="true">
                    ⋯
                  </span>
                </button>
                {toolsOpen && (
                  <div className="tools-popover" role="menu">
                    <button
                      role="menuitem"
                      onClick={() => {
                        setToolsOpen(false);
                        setRedactMode(true);
                      }}
                    >
                      {t.tools.redact}
                    </button>
                    <button
                      role="menuitem"
                      onClick={() => {
                        setToolsOpen(false);
                        setShowReplaceModal(true);
                      }}
                    >
                      {t.replace.menu}
                    </button>
                    <button role="menuitem" onClick={handleSanitize}>
                      {t.tools.sanitize}
                    </button>
                  </div>
                )}
              </div>
              <a
                className="btn btn-accent"
                href={documentDownloadUrl(documentId)}
                download={fileName ? t.editor.downloadName(fileName) : t.editor.defaultDownloadName}
                aria-label={t.editor.download}
              >
                <span className="only-wide">{t.editor.download}</span>
                <span className="only-narrow" aria-hidden="true">
                  ↓
                </span>
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
        {notice && (
          <div className="toast toast-info" onClick={() => setNotice(null)}>
            {notice}
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
                onClick={() => changePage(pageNumber - 1)}
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
                onClick={() => changePage(pageNumber + 1)}
                title={t.editor.nextPage}
              >
                →
              </button>
              <span className="page-toolbar-sep" aria-hidden="true" />
              <button
                className="btn btn-icon"
                disabled={zoom <= MIN_ZOOM}
                onClick={() => setZoom(zoomOutStep)}
                title={t.editor.zoomOut}
                aria-label={t.editor.zoomOut}
              >
                −
              </button>
              <span className="page-indicator">{Math.round(zoom * 100)} %</span>
              <button
                className="btn btn-icon"
                disabled={zoom >= MAX_ZOOM}
                onClick={() => setZoom(zoomInStep)}
                title={t.editor.zoomIn}
                aria-label={t.editor.zoomIn}
              >
                +
              </button>
            </div>

            {redactMode && (
              <div className="redact-bar">
                <p className="redact-hint">{t.tools.redactHint}</p>
                <div className="redact-actions">
                  <div className="segmented" role="group">
                    {(["lines", "area"] as const).map((tool) => (
                      <button
                        key={tool}
                        className={redactTool === tool ? "is-active" : undefined}
                        aria-pressed={redactTool === tool}
                        onClick={() => setRedactTool(tool)}
                      >
                        {tool === "lines" ? t.tools.redactLines : t.tools.redactArea}
                      </button>
                    ))}
                  </div>
                  <button className="btn btn-ghost" onClick={handleSanitize} disabled={busy}>
                    {t.tools.sanitize}
                  </button>
                  <button
                    className="btn btn-accent"
                    onClick={handleApplyRedactions}
                    disabled={busy || redactions.length === 0}
                  >
                    {t.tools.redactApply(redactions.length)}
                  </button>
                  <button
                    className="btn btn-ghost"
                    onClick={() => {
                      setRedactMode(false);
                      setRedactions([]);
                    }}
                  >
                    {t.tools.redactClose}
                  </button>
                </div>
              </div>
            )}

            <div className="page-canvas" ref={measureCanvasArea}>
              <PdfPage
                documentId={documentId}
                pageIndex={pageNumber - 1}
                version={version}
                availableWidth={availableWidth}
                zoom={zoom}
                onRendered={afterRender}
                onEdited={handleEdited}
                pendingSignature={pendingSignature}
                onSignaturePlaced={handleSignaturePlaced}
                onCancelSignature={() => setPendingSignature(null)}
                redactMode={redactMode}
                redactTool={redactTool}
                redactions={redactions}
                onAddRedaction={(rect) => setRedactions((list) => [...list, rect])}
                onRemoveRedaction={(index) => setRedactions((list) => list.filter((_, i) => i !== index))}
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

      {showReplaceModal && documentId && (
        <ReplaceModal
          documentId={documentId}
          onReplaced={handleReplaced}
          onClose={() => setShowReplaceModal(false)}
        />
      )}

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
