import type { LocalizedContent } from "../types";

export const redact: LocalizedContent = {
  fr: {
    nav: "Caviarder un PDF",
    metaTitle: "Caviarder un PDF en ligne, vraiment | Glyph",
    metaDescription:
      "Masque définitivement un nom, un numéro ou une adresse dans un PDF : le contenu sous la zone est supprimé du fichier, pas recouvert. Gratuit, sans compte.",
    eyebrow: "Gratuit · sans compte",
    h1: "Caviarder un PDF, pour de vrai",
    intro:
      "Masque un nom, un numéro de téléphone, un IBAN ou une adresse avant de partager un document. Glyph supprime du fichier tout ce qui se trouve sous la zone, puis la peint en noir : il n'y a plus rien à révéler dessous.",
    widget: "upload",
    intent: "redact",
    sections: [
      {
        h2: "Comment caviarder un PDF",
        blocks: [
          {
            steps: [
              "Dépose ton PDF ci-dessus : l'éditeur s'ouvre directement en mode caviardage.",
              "Touche les lignes à masquer. Pour une partie de ligne, une image ou une signature, passe en mode **Zone** et dessine un rectangle.",
              "Vérifie les zones en noir (le × retire une zone), puis clique sur **Caviarder**.",
              "Recommence sur les autres pages si besoin, puis télécharge le PDF.",
            ],
          },
        ],
      },
      {
        h2: "Pourquoi un rectangle noir ne suffit pas",
        blocks: [
          {
            p: "Dessiner un rectangle noir avec un outil d'annotation, ou surligner en noir, ne retire rien : le texte reste dans le fichier, sous le rectangle. Un copier-coller suffit souvent à le récupérer. C'est la cause de nombreuses fuites de documents censés être caviardés ; l'article [overlay contre vraie édition](@overlayVsReal) raconte comment ça arrive.",
          },
          {
            p: "Glyph fait un caviardage réel : le texte sous la zone est supprimé du contenu de la page, les pixels des images sont effacés, et les formes entièrement contenues dans la zone sont retirées. Le fichier est ensuite entièrement réécrit, pour qu'aucune copie de ce qui a été supprimé n'y subsiste.",
          },
        ],
      },
      {
        h2: "Ce que le caviardage ne fait pas tout seul",
        blocks: [
          {
            list: [
              "**Les métadonnées** : le titre, l'auteur ou les mots-clés du document peuvent contenir un nom. Utilise **Nettoyer les métadonnées** (dans la barre de caviardage), ou passe par [anonymiser un PDF](@anonymize).",
              "**Les autres occurrences** : Glyph ne cherche pas automatiquement le même nom ailleurs dans le document. Parcours chaque page.",
              "**Le nom du fichier** : s'il contient ton nom, renomme-le avant de le partager.",
              "**Les PDF scannés** : le texte y est une image ; le mode Zone fonctionne et efface bien les pixels, mais le mode Lignes n'a rien à sélectionner.",
            ],
          },
          {
            note: "Avant d'envoyer un document sensible, vérifie le résultat avec [le vérificateur de PDF caviardé](@check) : il signale le texte encore caché sous des rectangles et les métadonnées restantes.",
          },
        ],
      },
      {
        h2: "Où va ton fichier ?",
        blocks: [
          {
            p: "Le caviardage n'a pas lieu dans ton navigateur : ton PDF est envoyé en HTTPS au serveur de Glyph, traité **en mémoire uniquement**, jamais écrit sur disque, et supprimé à la fermeture de l'onglet ou après 30 minutes d'inactivité.",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Le texte caviardé peut-il être récupéré ?",
        a: "Non : il est supprimé du fichier, pas recouvert. Ni un copier-coller, ni un éditeur PDF ne peuvent le faire réapparaître.",
      },
      {
        q: "Peut-on annuler un caviardage ?",
        a: "Oui, tant que tu n'as pas téléchargé le fichier : le bouton Annuler revient à la version précédente. Une fois le PDF téléchargé, le caviardage est définitif.",
      },
      {
        q: "Peut-on caviarder une image ou une signature ?",
        a: "Oui, avec le mode Zone : les pixels de l'image situés sous le rectangle sont effacés.",
      },
      {
        q: "Est-ce gratuit ?",
        a: "Oui, sans compte, sans publicité et sans filigrane.",
      },
    ],
    related: ["anonymize", "check", "overlayVsReal"],
  },
  en: {
    nav: "Redact a PDF",
    metaTitle: "Redact a PDF online, for real | Glyph",
    metaDescription:
      "Permanently hide a name, a number or an address in a PDF: the content under the area is deleted from the file, not covered. Free, no account.",
    eyebrow: "Free · no account",
    h1: "Redact a PDF, for real",
    intro:
      "Hide a name, a phone number, a bank account or an address before sharing a document. Glyph deletes everything under the area from the file, then paints it black: there is nothing left to reveal underneath.",
    widget: "upload",
    intent: "redact",
    sections: [
      {
        h2: "How to redact a PDF",
        blocks: [
          {
            steps: [
              "Drop your PDF above: the editor opens straight in redaction mode.",
              "Tap the lines to hide. For part of a line, an image or a signature, switch to **Area** mode and draw a rectangle.",
              "Check the black areas (× removes one), then click **Redact**.",
              "Repeat on other pages if needed, then download the PDF.",
            ],
          },
        ],
      },
      {
        h2: "Why a black box isn't enough",
        blocks: [
          {
            p: "Drawing a black rectangle with an annotation tool, or highlighting in black, removes nothing: the text stays in the file, under the box. A copy-paste is often enough to recover it. It's behind many leaks of documents that were supposed to be redacted; the [overlay vs real editing](@overlayVsReal) article explains how it happens.",
          },
          {
            p: "Glyph does real redaction: the text under the area is deleted from the page content, image pixels are erased, and shapes entirely inside the area are removed. The file is then entirely rewritten, so no copy of what was deleted survives in it.",
          },
        ],
      },
      {
        h2: "What redaction doesn't do on its own",
        blocks: [
          {
            list: [
              "**Metadata**: the document's title, author or keywords can contain a name. Use **Remove metadata** (in the redaction bar), or go through [anonymize a PDF](@anonymize).",
              "**Other occurrences**: Glyph doesn't automatically look for the same name elsewhere in the document. Go through every page.",
              "**The file name**: if it contains your name, rename it before sharing.",
              "**Scanned PDFs**: the text is an image there; Area mode works and does erase the pixels, but Lines mode has nothing to select.",
            ],
          },
          {
            note: "Before sending a sensitive document, check the result with [the redacted PDF checker](@check): it flags text still hidden under boxes and remaining metadata.",
          },
        ],
      },
      {
        h2: "Where does your file go?",
        blocks: [
          {
            p: "Redaction doesn't happen in your browser: your PDF is sent over HTTPS to Glyph's server, processed **in memory only**, never written to disk, and deleted when you close the tab or after 30 minutes of inactivity.",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Can redacted text be recovered?",
        a: "No: it is deleted from the file, not covered. Neither copy-paste nor a PDF editor can bring it back.",
      },
      {
        q: "Can I undo a redaction?",
        a: "Yes, until you download the file: Undo goes back to the previous version. Once the PDF is downloaded, the redaction is permanent.",
      },
      {
        q: "Can I redact an image or a signature?",
        a: "Yes, with Area mode: the image pixels under the rectangle are erased.",
      },
      {
        q: "Is it free?",
        a: "Yes, with no account, no ads and no watermark.",
      },
    ],
    related: ["anonymize", "check", "overlayVsReal"],
  },
};
