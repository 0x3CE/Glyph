import { en } from "./en";
import { fr } from "./fr";
import type { Locale } from "./config";

export type Dictionary = typeof fr;

// Both dictionaries are small and also needed by the editor's client
// components (which can't receive functions like `downloadName` as props
// from a Server Component), so they're plain imports rather than
// server-only lazy loads.
const dictionaries: Record<Locale, Dictionary> = { fr, en };

export function getDictionary(locale: Locale): Dictionary {
  return dictionaries[locale];
}

export * from "./config";
