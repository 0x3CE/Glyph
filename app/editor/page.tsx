import type { Metadata } from "next";
import { EditorAppLoader } from "@/components/EditorAppLoader";

export const metadata: Metadata = {
  title: "Éditeur",
  description: "Ouvre un PDF et modifie son texte directement.",
  robots: { index: false, follow: true },
};

export default function EditorPage() {
  return <EditorAppLoader />;
}
