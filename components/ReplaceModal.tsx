"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { replaceText } from "@/lib/api-client";
import type { ReplaceResult } from "@/lib/api-client";
import { useI18n } from "@/lib/i18n/I18nProvider";

interface ReplaceModalProps {
  documentId: string;
  onReplaced: (result: ReplaceResult) => void;
  onClose: () => void;
}

export function ReplaceModal({ documentId, onReplaced, onClose }: ReplaceModalProps) {
  const { t } = useI18n();
  const [find, setFind] = useState("");
  const [replacement, setReplacement] = useState("");
  const [matchCase, setMatchCase] = useState(false);
  const [wholeWord, setWholeWord] = useState(false);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!find || working) return;
    setWorking(true);
    setMessage(null);
    try {
      const result = await replaceText(documentId, find, replacement, { matchCase, wholeWord });
      if (result.replaced === 0) setMessage(t.replace.none);
      else onReplaced(result);
    } catch (err) {
      console.error(err);
      setMessage(t.tools.actionError);
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={working ? undefined : onClose}>
      <form className="modal replace-modal" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <div className="modal-header">
          <h2>{t.replace.title}</h2>
          <button type="button" className="btn btn-icon" onClick={onClose} title={t.replace.close} disabled={working}>
            ✕
          </button>
        </div>
        <label className="field">
          <span>{t.replace.find}</span>
          <input
            autoFocus
            value={find}
            maxLength={200}
            onChange={(e) => {
              setFind(e.target.value);
              setMessage(null);
            }}
          />
        </label>
        <label className="field">
          <span>{t.replace.replaceWith}</span>
          <input value={replacement} maxLength={200} onChange={(e) => setReplacement(e.target.value)} />
        </label>
        <div className="replace-options">
          <label>
            <input type="checkbox" checked={matchCase} onChange={(e) => setMatchCase(e.target.checked)} />
            {t.replace.matchCase}
          </label>
          <label>
            <input type="checkbox" checked={wholeWord} onChange={(e) => setWholeWord(e.target.checked)} />
            {t.replace.wholeWord}
          </label>
        </div>
        <p className="replace-hint">{t.replace.hint}</p>
        {message && (
          <p className="replace-message" role="status">
            {message}
          </p>
        )}
        <div className="modal-actions">
          <button type="submit" className="btn btn-accent" disabled={!find || working}>
            {working ? t.replace.working : t.replace.submit}
          </button>
        </div>
      </form>
    </div>
  );
}
