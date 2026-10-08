import Link from "next/link";
import type { ReactNode } from "react";
import { localePath } from "@/lib/i18n";
import type { Locale } from "@/lib/i18n";
import { isPublished } from "@/lib/seo/content";
import { isPageId, pagePath } from "@/lib/seo/registry";

// The small inline syntax of lib/seo/types.ts: **bold**, [label](@pageId),
// [label](/path) and [label](https://…). A link to a page that isn't
// published yet renders as its plain label, never as a dead link.
const TOKEN = /\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)]+)\)/g;

export function RichText({ text, locale }: { text: string; locale: Locale }) {
  const out: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(TOKEN)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const key = m.index;
    if (m[1] !== undefined) {
      out.push(<strong key={key}>{m[1]}</strong>);
    } else {
      const [label, target] = [m[2], m[3]];
      if (target.startsWith("@")) {
        const id = target.slice(1);
        out.push(
          isPageId(id) && isPublished(id) ? (
            <Link key={key} href={pagePath(id, locale)}>
              {label}
            </Link>
          ) : (
            label
          ),
        );
      } else if (target.startsWith("/")) {
        out.push(
          <Link key={key} href={localePath(locale, target)}>
            {label}
          </Link>,
        );
      } else {
        out.push(
          <a key={key} href={target} target="_blank" rel="noopener noreferrer">
            {label}
          </a>,
        );
      }
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return <>{out}</>;
}
