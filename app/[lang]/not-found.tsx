import Link from "next/link";
import { lang } from "next/root-params";
import { BrandMark } from "@/components/BrandMark";
import { DEFAULT_LOCALE, getDictionary, hasLocale, localePath } from "@/lib/i18n";

// not-found receives no params; the locale comes from the root segment.
export default async function NotFound() {
  const value = await lang();
  const locale = hasLocale(value) ? value : DEFAULT_LOCALE;
  const t = getDictionary(locale).notFound;
  return (
    <main className="not-found">
      <span className="brand-mark">
        <BrandMark size={32} />
      </span>
      <h1>{t.title}</h1>
      <p>{t.text}</p>
      <Link href={localePath(locale, "/")} className="btn btn-accent">
        {t.back}
      </Link>
    </main>
  );
}
