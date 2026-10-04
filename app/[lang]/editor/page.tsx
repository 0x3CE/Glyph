import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { EditorAppLoader } from "@/components/EditorAppLoader";
import { getDictionary, hasLocale } from "@/lib/i18n";
import { localeAlternates } from "@/lib/i18n/metadata";

type Props = { params: Promise<{ lang: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(lang)) return {};
  const t = getDictionary(lang).meta;
  return {
    title: t.editorTitle,
    description: t.editorDescription,
    alternates: localeAlternates(lang, "/editor"),
    robots: { index: false, follow: true },
  };
}

export default async function EditorPage({ params }: Props) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();
  return <EditorAppLoader locale={lang} />;
}
