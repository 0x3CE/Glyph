"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { UploadDropzone } from "@/components/UploadDropzone";
import { inspectPdf } from "@/lib/api-client";
import type { InspectReport } from "@/lib/api-client";
import { getDictionary, localePath } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n";
import { setPendingUpload } from "@/lib/pending-upload";

// Metadata that names a person or a document; creator, producer and dates
// are listed too but are present in almost every PDF.
const IDENTIFYING_METADATA = ["title", "author", "subject", "keywords"];

type State =
  | { step: "idle" }
  | { step: "checking" }
  | { step: "error"; message: string }
  | { step: "done"; file: File; report: InspectReport };

// "D:20261004153000+02'00'" -> "2026-10-04 15:30"
function formatPdfDate(value: string) {
  const m = /^D:(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?/.exec(value);
  if (!m) return value;
  return `${m[1]}-${m[2]}-${m[3]}${m[4] ? ` ${m[4]}:${m[5] ?? "00"}` : ""}`;
}

function Samples({ items, label }: { items: { page: number; text: string }[]; label: (n: number) => string }) {
  return (
    <ul className="check-samples">
      {items.map((item, i) => (
        <li key={i}>
          <span className="check-page">{label(item.page)}</span> {item.text}
        </li>
      ))}
    </ul>
  );
}

/** The redacted-PDF checker: uploads the file for a read-only inspection
 * and explains what it still hides. */
export function PdfChecker({ locale }: { locale: Locale }) {
  const t = getDictionary(locale);
  const c = t.check;
  const router = useRouter();
  const [state, setState] = useState<State>({ step: "idle" });

  const check = async (file: File) => {
    setState({ step: "checking" });
    try {
      setState({ step: "done", file, report: await inspectPdf(file) });
    } catch (e) {
      const status = Number.parseInt(String((e as Error).message), 10);
      const message = status === 413 ? c.errorTooLarge : status === 503 ? c.errorBusy : c.errorInvalid;
      setState({ step: "error", message });
    }
  };

  if (state.step !== "done") {
    return (
      <div className="check-start">
        {state.step === "checking" ? (
          <div className="dropzone seo-dropzone check-busy" role="status">
            <span className="spinner" aria-hidden="true" />
            <p className="dropzone-title">{c.checking}</p>
          </div>
        ) : (
          <UploadDropzone
            locale={locale}
            intent="anonymize"
            title={t.editor.dropTitle}
            or={t.editor.dropOr}
            choose={t.editor.chooseFile}
            hint={t.seo.uploadHint}
            onFile={check}
          />
        )}
        {state.step === "error" && <p className="check-error" role="alert">{state.message}</p>}
      </div>
    );
  }

  const { file, report } = state;
  const metadata = Object.entries(report.metadata);
  const hidden = report.hidden_text.length > 0 || report.unapplied_redactions > 0;
  const warn =
    report.invisible_text_chars > 0 ||
    report.versions > 1 ||
    report.attachments.length > 0 ||
    metadata.some(([key]) => IDENTIFYING_METADATA.includes(key));
  const verdict = hidden ? "hidden" : warn ? "warn" : "clean";

  const fix = () => {
    setPendingUpload(file, "anonymize");
    router.push(localePath(locale, "/editor"));
  };

  return (
    <div className="check-report" aria-live="polite">
      <p className={`check-verdict check-${verdict}`}>
        {verdict === "hidden" ? c.verdictHidden : verdict === "warn" ? c.verdictWarn : c.verdictClean}
        <span className="check-file">{file.name}</span>
      </p>

      {verdict === "clean" && <p>{c.cleanText}</p>}

      {report.hidden_text.length > 0 && (
        <section className="check-item check-item-danger">
          <h3>{c.hiddenTitle(report.hidden_text.length)}</h3>
          <p>{c.hiddenText}</p>
          <Samples items={report.hidden_text} label={c.page} />
        </section>
      )}
      {report.unapplied_redactions > 0 && (
        <section className="check-item check-item-danger">
          <p>{c.unapplied(report.unapplied_redactions)}</p>
        </section>
      )}
      {report.invisible_text_chars > 0 && (
        <section className="check-item">
          <h3>{c.invisibleTitle(report.invisible_text_chars)}</h3>
          <p>{c.invisibleText}</p>
          <Samples items={report.invisible_text_samples} label={c.page} />
        </section>
      )}
      {report.versions > 1 && (
        <section className="check-item">
          <p>{c.versions(report.versions)}</p>
        </section>
      )}
      {report.attachments.length > 0 && (
        <section className="check-item">
          <h3>{c.attachmentsTitle}</h3>
          <ul className="check-samples">
            {report.attachments.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </section>
      )}
      {(metadata.length > 0 || report.has_xmp) && (
        <section className="check-item">
          <h3>{c.metadataTitle}</h3>
          <p>{c.metadataText}</p>
          {metadata.length > 0 && (
            <dl className="check-meta">
              {metadata.map(([key, value]) => (
                <div key={key}>
                  <dt>{t.tools.removedLabels[`metadata.${key}`] ?? key}</dt>
                  <dd>{key.endsWith("Date") ? formatPdfDate(value) : value}</dd>
                </div>
              ))}
            </dl>
          )}
          {report.has_xmp && <p>{c.xmp}</p>}
        </section>
      )}

      {report.pages_inspected < report.page_count && (
        <p className="check-caveat">{c.partial(report.pages_inspected, report.page_count)}</p>
      )}
      <p className="check-caveat">{c.scanCaveat}</p>

      <div className="check-actions">
        {verdict !== "clean" && (
          <button type="button" className="btn btn-accent" onClick={fix}>
            {c.fix}
          </button>
        )}
        <button type="button" className="btn btn-ghost" onClick={() => setState({ step: "idle" })}>
          {c.again}
        </button>
      </div>
    </div>
  );
}
