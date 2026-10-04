import type { Dictionary } from "./index";

export const en: Dictionary = {
  meta: {
    title: "Glyph — the PDF editor that actually edits the text",
    description:
      "Edit the text of a PDF for real: the old text is removed, not hidden under a white box. Original font, search and copy-paste stay intact.",
    siteDescription:
      "Glyph rewrites a PDF's content instead of covering it up: the old text is removed, the new text inserted with the original font.",
    keywords: ["PDF editor", "edit PDF text", "edit PDF online", "PDF editor without overlay", "rewrite PDF text"],
    ogDescription: "The original text is removed from the PDF, not covered up. Real editing, not an overlay.",
    ogLocale: "en_US",
    ogImageAlt: "Glyph: edit the text in a PDF, for real.",
    organizationDescription: "A PDF editor that rewrites the document's content instead of covering it up.",
    softwareDescription:
      "A PDF editor that rewrites the document's content (the original text is truly removed, then reinserted with the original font) instead of covering it with an overlay.",
    priceCurrency: "USD",
    editorTitle: "Editor",
    editorDescription: "Open a PDF and edit its text directly.",
  },
  nav: {
    openEditor: "Open the editor",
    coffee: "Buy me a coffee",
    coffeeAria: "Buy me a coffee (Buy Me a Coffee)",
  },
  switcher: {
    label: "Français",
    shortLabel: "FR",
    ariaLabel: "Passer en français",
  },
  hero: {
    eyebrow: "PDF editing without overlays",
    titleLine1: "Edit the text in a PDF.",
    titleLine2Before: "For ",
    titleLine2Accent: "real",
    titleLine2After: ".",
    subtitle:
      "Glyph rewrites the PDF's content instead of covering it: the original text is removed and the new text goes in with the original font whenever possible — search and copy-paste included.",
    howItWorks: "How it works",
  },
  problem: {
    anchor: "the-problem",
    label: "The problem",
    title: "Other PDF editors don't edit the text — they hide it",
    lede: "The usual trick: cover the old text with a white box and type the new text on top. It looks fine on screen, but the document is still broken.",
    badTitle: "Overlay (the usual trick)",
    badText:
      "The original text is still there under the box: search and copy-paste still return the old value, and anyone can recover it by removing the box.",
    goodText:
      "The original glyphs are removed from the document and replaced with real text, in the right place, with the right font whenever possible. Nothing to hide: there's nothing left underneath.",
  },
  how: {
    anchor: "how-it-works",
    label: "How it works",
    title: "Four steps, no trace of the old text",
    steps: [
      { title: "Drop your PDF", text: "Processed in memory, nothing is written to disk on the server." },
      { title: "Click a line", text: "Each line is edited on its own: the lines around it are never touched." },
      {
        title: "The content is rewritten",
        text: "The old glyphs are truly removed, and the new text goes in with the original font when possible.",
      },
      { title: "Download", text: "A PDF where the edited text is real text — searchable, copyable, printable." },
    ],
  },
  features: {
    anchor: "features",
    label: "Features",
    title: "Built for fidelity, not just looks",
    items: [
      {
        title: "Content truly removed",
        text: "No cover-up boxes — the old characters are taken out of the document.",
      },
      {
        title: "Original font kept",
        text: "Reused when possible, otherwise the same family from 240 free fonts. You're told when it isn't the original.",
      },
      {
        title: "Formatting kept",
        text: "A bold or italic word keeps its style when you edit the rest of the line.",
      },
      {
        title: "Tables stay intact",
        text: "Each cell is edited on its own, without ever spilling into the cells next to it.",
      },
      {
        title: "Signature",
        text: "Draw it or upload one (PDF, PNG, JPG), then drag it into place. A PDF signature stays vector-sharp.",
      },
      { title: "Undo / redo", text: "Step back or forward through your edits for the whole editing session." },
    ],
  },
  faq: {
    label: "FAQ",
    title: "Frequently asked questions",
    items: [
      {
        q: "Is the edited text still searchable and copyable?",
        a: "Yes. Glyph truly removes the old characters from the PDF and inserts the new text as real text — not an image, not an overlay. Search, selection and copy-paste work as usual.",
      },
      {
        q: "Are my files stored anywhere?",
        a: "No. Each PDF is kept in memory only while you edit it, never written to disk on the server, and deleted as soon as you close the tab (or after 30 minutes of inactivity).",
      },
      {
        q: "Is the original font always kept?",
        a: "Whenever possible — Glyph reuses the document's own font. Many PDFs (from Word or virtual printers) embed font subsets that don't cover every character; in that case Glyph uses the same family from its catalog of about 240 free fonts (Roboto, Montserrat, Lato…), or a metric-compatible equivalent for proprietary fonts (Calibri, Arial, Times…), and tells you when the result isn't exactly the original font.",
      },
      {
        q: "Does it work on tables?",
        a: "Yes. Every line is edited on its own, table cells included: only the text you clicked changes, and Glyph never erases anything in the cells next to it, even when they touch.",
      },
      {
        q: "Are there any limits?",
        a: "A few. PDFs up to 20 MB, without a password. Editing works line by line: a three-line address takes three clicks. And a colored background behind the edited text is erased along with it.",
      },
      { q: "Do I need an account?", a: "No, you can use the editor right away." },
    ],
  },
  support: {
    anchor: "support",
    label: "Support the project",
    title: "Free, open source, no ads, no tracking",
    text: "I build Glyph in my spare time. If it saved you a headache with a PDF, you can buy me a coffee: it helps pay for hosting and keeps it improving.",
  },
  cta: {
    title: "Ready to edit a PDF for real?",
    text: "No sign-up needed.",
  },
  footer: {
    tagline: "Real PDF editing — not an overlay.",
  },
  notFound: {
    title: "Page not found",
    text: "This page doesn't exist, or no longer does.",
    back: "Back to the home page",
  },
  editor: {
    openPdf: "Open a PDF",
    changeFile: "Change file",
    undo: "Undo",
    redo: "Redo",
    signature: "Signature",
    download: "Download",
    downloadName: (fileName: string) => `edited-${fileName}`,
    defaultDownloadName: "edited-document.pdf",
    loadError: "Couldn't open this PDF. The file may be corrupted or password-protected.",
    substitutionNotice: "The original font isn't available for this text — a replacement font was used.",
    dropTitle: "Drop a PDF here",
    dropOr: "or",
    chooseFile: "Choose a file",
    emptyHint: "Nothing is stored: the file is processed in memory for the length of your session.",
    previousPage: "Previous page",
    nextPage: "Next page",
    dropToReplace: "Drop to replace the document",
    save: "Save",
    saving: "Saving…",
    cancel: "Cancel",
    confirm: "Confirm",
    signatureAlt: "Signature",
  },
  signatureModal: {
    title: "Add a signature",
    close: "Close",
    draw: "Draw",
    upload: "Upload a file",
    clear: "Clear",
    useDrawing: "Use this signature",
    chooseFile: "Choose a file (PDF, PNG, JPG)",
    useFile: "Use this file",
    unsupportedFile: "Unsupported format — PDF, PNG or JPG only.",
  },
};
