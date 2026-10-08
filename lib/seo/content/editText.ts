import type { LocalizedContent } from "../types";

export const editText: LocalizedContent = {
  fr: {
    nav: "Modifier le texte d'un PDF",
    metaTitle: "Modifier le texte d'un PDF en ligne, gratuitement | Glyph",
    metaDescription:
      "Change un mot, une date ou un montant dans un PDF : l'ancien texte est supprimé du fichier et réécrit, pas caché sous un rectangle blanc. Gratuit, sans compte.",
    eyebrow: "Gratuit · sans compte",
    h1: "Modifier le texte d'un PDF, pour de vrai",
    intro:
      "Change un mot, une date, un montant ou une ligne entière dans un PDF. Glyph supprime le texte d'origine du fichier et écrit le nouveau à sa place, dans la même police quand c'est possible. Rien n'est caché sous un rectangle blanc.",
    widget: "upload",
    intent: "edit",
    sections: [
      {
        h2: "Comment modifier le texte d'un PDF",
        blocks: [
          {
            steps: [
              "Dépose ton PDF dans la zone ci-dessus, ou choisis-le sur ton appareil.",
              "Clique (ou touche) la ligne à modifier : un champ s'ouvre exactement à sa place.",
              "Tape le nouveau texte, puis enregistre. La page est redessinée avec la modification.",
              "Télécharge le PDF modifié. Annuler et rétablir restent possibles jusqu'au téléchargement.",
            ],
          },
          {
            p: "L'édition se fait **ligne par ligne** : une adresse sur trois lignes se modifie en trois fois. C'est volontaire : deviner qu'un groupe de lignes forme un paragraphe se trompait trop souvent et pouvait effacer une ligne voisine.",
          },
        ],
      },
      {
        h2: "Ce que « modifier pour de vrai » veut dire",
        blocks: [
          {
            p: "La plupart des éditeurs PDF en ligne ne modifient pas le texte : ils posent un rectangle blanc par-dessus et écrivent le nouveau texte au-dessus. À l'écran, ça a l'air juste. Dans le fichier, l'ancien texte est toujours là.",
          },
          {
            list: [
              "une recherche ou un copier-coller renvoie encore l'ancienne valeur ;",
              "n'importe qui peut retrouver l'ancien texte en retirant le rectangle ;",
              "sur un fond coloré ou dans un tableau, le rectangle blanc se voit.",
            ],
          },
          {
            p: "Glyph supprime réellement les caractères d'origine du contenu de la page, puis insère le nouveau texte comme du vrai texte. Le fichier téléchargé ne contient plus l'ancienne version, même dans ses données internes. Le détail technique est expliqué dans [overlay contre vraie édition](@overlayVsReal).",
          },
        ],
      },
      {
        h2: "La police d'origine, ou la plus proche possible",
        blocks: [
          {
            p: "Quand la police embarquée dans le PDF contient tous les caractères dont tu as besoin, Glyph la réutilise : le résultat est identique au reste du document.",
          },
          {
            p: "Beaucoup de PDF (issus de Word ou d'une imprimante virtuelle) n'embarquent qu'une partie de leur police, inutilisable pour écrire un mot nouveau. Glyph prend alors la même famille dans son catalogue d'environ 240 polices libres (Roboto, Montserrat, Lato…), ou un équivalent aux mêmes largeurs de lettres pour les polices propriétaires (Calibri, Arial, Times, Courier…). Il ajuste la largeur pour que la ligne garde sa place, et te prévient quand la police n'est pas exactement l'originale.",
          },
          {
            p: "Un mot en gras ou en italique au milieu de la ligne garde son style si tu modifies le reste de la phrase.",
          },
        ],
      },
      {
        h2: "Ce que Glyph sait faire, et ses limites",
        blocks: [
          {
            list: [
              "**PDF scannés** : une page scannée est une image, sans texte à modifier. Glyph ne fait pas de reconnaissance de caractères (OCR).",
              "**PDF au texte illisible** : certains logiciels (de paie, notamment) produisent des PDF dont le texte ne peut pas être relu par un programme. Glyph le détecte : tu peux modifier la ligne, mais il faut la retaper en entier.",
              "**Fond coloré** : le fond derrière le texte modifié est effacé avec lui.",
              "**PDF protégés par mot de passe** : refusés à l'ouverture.",
              "**Taille** : 20 Mo maximum par fichier.",
              "**Écritures** : pas d'arabe, d'hébreu, ni de chinois, japonais ou coréen pour l'instant.",
            ],
          },
        ],
      },
      {
        h2: "Où va ton fichier ?",
        blocks: [
          {
            p: "La modification n'a pas lieu dans ton navigateur : ton PDF est envoyé, de façon chiffrée (HTTPS), au serveur de Glyph. Il y est traité **en mémoire uniquement**, jamais écrit sur disque, et supprimé dès que tu fermes l'onglet, ou après 30 minutes d'inactivité. Il n'y a pas de compte, et le fichier n'est ni conservé, ni analysé, ni réutilisé.",
          },
        ],
      },
      {
        h2: "Usage responsable",
        blocks: [
          {
            p: "Glyph sert à corriger tes propres documents : une coquille dans un devis avant envoi, une adresse qui a changé, une date à mettre à jour. Modifier un document pour tromper quelqu'un (une fiche de paie, une facture, un diplôme, un acte officiel) est un faux, puni par la loi. Voir les [conditions d'utilisation](@terms).",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Le texte modifié reste-t-il sélectionnable et cherchable ?",
        a: "Oui. Le nouveau texte est inséré comme du vrai texte, pas comme une image : sélection, recherche et copier-coller fonctionnent normalement, et renvoient la nouvelle valeur.",
      },
      {
        q: "Peut-on modifier le texte d'un PDF sans Adobe Acrobat ?",
        a: "Oui. Glyph fonctionne dans le navigateur, sur ordinateur comme sur téléphone, sans logiciel à installer ni compte à créer.",
      },
      {
        q: "Peut-on modifier un PDF scanné ?",
        a: "Pas encore : une page scannée ne contient qu'une image, sans texte. Il faudrait d'abord une reconnaissance de caractères (OCR), que Glyph ne propose pas pour l'instant.",
      },
      {
        q: "Glyph est-il gratuit ?",
        a: "Oui, entièrement, sans publicité ni filigrane. Le projet est open source.",
      },
      {
        q: "Mon fichier est-il conservé ?",
        a: "Non. Il est traité en mémoire sur le serveur de Glyph, jamais écrit sur disque, et supprimé à la fermeture de l'onglet ou après 30 minutes d'inactivité.",
      },
    ],
    related: ["overlayVsReal", "redact", "findReplace"],
  },
  en: {
    nav: "Edit PDF text",
    metaTitle: "Edit PDF text online for free | Glyph",
    metaDescription:
      "Change a word, a date or an amount in a PDF: the old text is removed from the file and rewritten, not hidden under a white box. Free, no account.",
    eyebrow: "Free · no account",
    h1: "Edit the text in a PDF, for real",
    intro:
      "Change a word, a date, an amount or a whole line in a PDF. Glyph removes the original text from the file and writes the new text in its place, in the same font whenever possible. Nothing is hidden under a white box.",
    widget: "upload",
    intent: "edit",
    sections: [
      {
        h2: "How to edit the text in a PDF",
        blocks: [
          {
            steps: [
              "Drop your PDF in the area above, or pick it from your device.",
              "Click (or tap) the line to change: a field opens exactly where it is.",
              "Type the new text and save. The page is redrawn with your change.",
              "Download the edited PDF. Undo and redo stay available until then.",
            ],
          },
          {
            p: "Editing works **line by line**: a three-line address takes three edits. That's on purpose: guessing that several lines form one paragraph was wrong too often, and could erase a neighbouring line.",
          },
        ],
      },
      {
        h2: "What editing “for real” means",
        blocks: [
          {
            p: "Most online PDF editors don't change the text: they put a white box over it and type the new text on top. It looks right on screen, but the old text is still in the file.",
          },
          {
            list: [
              "search and copy-paste still return the old value;",
              "anyone can recover the old text by removing the box;",
              "on a colored background or in a table, the white box shows.",
            ],
          },
          {
            p: "Glyph actually removes the original characters from the page's content, then inserts the new text as real text. The downloaded file no longer contains the old version, not even in its internal data. The technical side is explained in [overlay vs real editing](@overlayVsReal).",
          },
        ],
      },
      {
        h2: "The original font, or the closest one",
        blocks: [
          {
            p: "When the font embedded in the PDF has every character you need, Glyph reuses it: the result matches the rest of the document exactly.",
          },
          {
            p: "Many PDFs (from Word or a virtual printer) embed only part of their font, which can't be used to write a new word. Glyph then uses the same family from its catalog of about 240 free fonts (Roboto, Montserrat, Lato…), or a metric-compatible equivalent for proprietary fonts (Calibri, Arial, Times, Courier…). It adjusts the width so the line keeps its place, and tells you when the font isn't exactly the original.",
          },
          {
            p: "A bold or italic word in the middle of the line keeps its style when you edit the rest of the sentence.",
          },
        ],
      },
      {
        h2: "What Glyph can do, and its limits",
        blocks: [
          {
            list: [
              "**Scanned PDFs**: a scanned page is an image, with no text to edit. Glyph doesn't do character recognition (OCR).",
              "**PDFs with unreadable text**: some software (payroll, notably) produces PDFs whose text can't be read back by a program. Glyph detects it: you can still edit the line, but you have to retype it in full.",
              "**Colored backgrounds**: the background behind the edited text is erased along with it.",
              "**Password-protected PDFs**: refused when opened.",
              "**Size**: 20 MB per file at most.",
              "**Scripts**: no Arabic, Hebrew, Chinese, Japanese or Korean for now.",
            ],
          },
        ],
      },
      {
        h2: "Where does your file go?",
        blocks: [
          {
            p: "Editing doesn't happen in your browser: your PDF is sent, encrypted (HTTPS), to Glyph's server. It is processed **in memory only**, never written to disk, and deleted as soon as you close the tab, or after 30 minutes of inactivity. There's no account, and the file is not kept, analysed or reused.",
          },
        ],
      },
      {
        h2: "Responsible use",
        blocks: [
          {
            p: "Glyph is for fixing your own documents: a typo in a quote before sending it, an address that changed, a date to update. Altering a document to deceive someone (a payslip, an invoice, a diploma, an official record) is forgery, and illegal. See the [terms of use](@terms).",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Is the edited text still selectable and searchable?",
        a: "Yes. The new text is inserted as real text, not as an image: selection, search and copy-paste work normally, and return the new value.",
      },
      {
        q: "Can I edit the text in a PDF without Adobe Acrobat?",
        a: "Yes. Glyph runs in the browser, on a computer or a phone, with nothing to install and no account to create.",
      },
      {
        q: "Can I edit a scanned PDF?",
        a: "Not yet: a scanned page only contains an image, with no text. It would first need character recognition (OCR), which Glyph doesn't offer for now.",
      },
      {
        q: "Is Glyph free?",
        a: "Yes, completely, with no ads and no watermark. The project is open source.",
      },
      {
        q: "Is my file kept?",
        a: "No. It is processed in memory on Glyph's server, never written to disk, and deleted when you close the tab or after 30 minutes of inactivity.",
      },
    ],
    related: ["overlayVsReal", "redact", "findReplace"],
  },
};
