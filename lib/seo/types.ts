import type { Locale } from "../i18n/config";
import type { EditorIntent } from "../pending-upload";
import type { PageId } from "./registry";

// Inline text in paragraphs, list items, notes and FAQ answers supports:
//   **bold**
//   [label](@pageId)    link to another content page (skipped if unpublished)
//   [label](/editor)    internal path, localized automatically
//   [label](https://…)  external link
export type Block = { p: string } | { list: string[] } | { steps: string[] } | { note: string };

export interface Section {
  h2: string;
  blocks: Block[];
}

export interface PageContent {
  /** Short label for links to this page (footer, "related"). */
  nav: string;
  metaTitle: string; // <= 60 characters
  metaDescription: string; // <= 155 characters
  eyebrow?: string;
  h1: string;
  intro: string;
  /** "upload": a drop zone that opens the editor with `intent`; "check": the PDF inspector. */
  widget?: "upload" | "check";
  intent?: EditorIntent;
  sections: Section[];
  faq?: { q: string; a: string }[];
  related?: PageId[];
  /** Shown on articles and guides ("Mis à jour le …"); ISO date. */
  updated?: string;
}

export type LocalizedContent = Record<Locale, PageContent>;
