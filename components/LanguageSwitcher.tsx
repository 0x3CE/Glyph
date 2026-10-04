"use client";

import { LOCALE_COOKIE, LOCALE_COOKIE_MAX_AGE, localePath } from "@/lib/i18n/config";
import type { Locale } from "@/lib/i18n/config";

interface LanguageSwitcherProps {
  /** Language of the page being shown. */
  locale: Locale;
  /** The page's path without a locale prefix ("/", "/editor"). */
  path: string;
  label: string;
  /** Shown instead of `label` on narrow screens. */
  shortLabel?: string;
  ariaLabel: string;
  className?: string;
}

// A plain link to the same page in the other language. Clicking it also saves
// the choice, which then beats the country-based guess in proxy.ts on every
// later visit (otherwise a French visitor clicking "English" would be sent
// back to French the next time they open `/`).
export function LanguageSwitcher({ locale, path, label, shortLabel, ariaLabel, className }: LanguageSwitcherProps) {
  const target: Locale = locale === "fr" ? "en" : "fr";
  return (
    <a
      href={localePath(target, path)}
      hrefLang={target}
      lang={target}
      aria-label={ariaLabel}
      className={className}
      onClick={() => {
        document.cookie = `${LOCALE_COOKIE}=${target}; path=/; max-age=${LOCALE_COOKIE_MAX_AGE}; samesite=lax`;
      }}
    >
      {shortLabel ? (
        <>
          <span className="lang-long">{label}</span>
          <span className="lang-short">{shortLabel}</span>
        </>
      ) : (
        label
      )}
    </a>
  );
}
