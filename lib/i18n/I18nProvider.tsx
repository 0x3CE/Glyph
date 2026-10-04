"use client";

import { createContext, useContext } from "react";
import type { ReactNode } from "react";
import { getDictionary } from "./index";
import type { Dictionary, Locale } from "./index";

const I18nContext = createContext<{ locale: Locale; t: Dictionary } | null>(null);

// Only the locale crosses the server -> client boundary; the dictionary is
// looked up here, so it can keep functions (e.g. `editor.downloadName`).
export function I18nProvider({ locale, children }: { locale: Locale; children: ReactNode }) {
  return <I18nContext.Provider value={{ locale, t: getDictionary(locale) }}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useI18n must be used inside <I18nProvider>");
  return value;
}
