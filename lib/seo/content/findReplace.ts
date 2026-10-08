import type { LocalizedContent } from "../types";

export const findReplace: LocalizedContent = {
  fr: {
    nav: "Remplacer un mot dans un PDF",
    metaTitle: "Remplacer un mot dans tout un PDF | Glyph",
    metaDescription:
      "Remplace un nom, une date ou une coquille dans toutes les pages d'un PDF en une fois. L'ancien texte est supprimé du fichier, pas recouvert. Gratuit, sans compte.",
    eyebrow: "Gratuit · sans compte",
    h1: "Remplacer un mot dans tout un PDF",
    intro:
      "Un nom de client à changer dans un devis type, une coquille répétée sur dix pages, une année à mettre à jour : Glyph trouve chaque occurrence et la réécrit, page après page, en supprimant l'ancien texte du fichier.",
    widget: "upload",
    intent: "replace",
    sections: [
      {
        h2: "Comment remplacer un mot dans un PDF",
        blocks: [
          {
            steps: [
              "Dépose ton PDF ci-dessus : l'éditeur s'ouvre avec la fenêtre **Rechercher et remplacer**.",
              "Tape le texte à chercher et son remplaçant. Coche **Mot entier** pour ne pas toucher « Jeanne » en remplaçant « Jean », et **Respecter la casse** si les majuscules comptent.",
              "Clique sur **Tout remplacer** : Glyph indique combien d'occurrences ont été remplacées, et sur quelles pages.",
              "Vérifie le résultat, puis télécharge le PDF. Un seul **Annuler** défait tout le remplacement.",
            ],
          },
          {
            p: "La fenêtre reste accessible ensuite depuis le menu **Outils** de l'éditeur.",
          },
        ],
      },
      {
        h2: "Un vrai remplacement, pas un collage",
        blocks: [
          {
            p: "Chaque ligne concernée est modifiée comme si tu l'avais retapée : les caractères d'origine sont supprimés du contenu de la page, et la nouvelle ligne est écrite dans la police d'origine quand c'est possible, ou dans la plus proche sinon. Le reste de la ligne garde sa mise en forme. Après coup, une recherche dans le PDF ne trouve plus l'ancien mot. Le principe est expliqué dans [overlay contre vraie édition](@overlayVsReal).",
          },
          {
            p: "La recherche ignore les ligatures typographiques (« ﬁ » est trouvé quand tu cherches « fi ») et les espaces insécables, fréquents dans les PDF.",
          },
        ],
      },
      {
        h2: "Les limites",
        blocks: [
          {
            list: [
              "**Ligne par ligne** : une expression coupée par un retour à la ligne n'est pas trouvée. Modifie ces lignes à la main.",
              "**Texte plus long** : la ligne s'étend vers la droite jusqu'au prochain élément, puis le texte est légèrement réduit pour tenir. Vérifie les pages indiquées.",
              "**PDF au texte illisible** : les lignes dont le texte ne peut pas être relu (certains logiciels de paie, par exemple) sont ignorées.",
              "**PDF scannés** : pas de texte, donc rien à remplacer (pas d'OCR).",
              "**Volume** : 300 lignes modifiées par opération, sur les 300 premières pages. Au-delà, relance l'opération.",
              "**Fond coloré** : il est effacé derrière chaque ligne modifiée.",
            ],
          },
        ],
      },
      {
        h2: "Où va ton fichier ?",
        blocks: [
          {
            p: "Ton PDF est envoyé en HTTPS au serveur de Glyph, traité **en mémoire uniquement**, jamais écrit sur disque, et supprimé à la fermeture de l'onglet ou après 30 minutes d'inactivité.",
          },
          {
            p: "Glyph sert à mettre à jour tes propres documents. Modifier un document pour tromper quelqu'un est un faux, puni par la loi : voir les [conditions d'utilisation](@terms).",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Peut-on supprimer un mot partout ?",
        a: "Oui : laisse le champ « Remplacer par » vide. Pour qu'un mot disparaisse sans laisser de trou visible dans la mise en page, le [caviardage](@redact) est parfois plus adapté.",
      },
      {
        q: "Les majuscules et les accents comptent-ils ?",
        a: "Les majuscules, seulement si tu coches « Respecter la casse ». Les accents, toujours : « cafe » ne trouve pas « café ».",
      },
      {
        q: "Est-ce gratuit ?",
        a: "Oui, sans compte, sans publicité et sans filigrane.",
      },
    ],
    related: ["editText", "overlayVsReal", "redact"],
  },
  en: {
    nav: "Replace a word in a PDF",
    metaTitle: "Find and replace a word in a whole PDF | Glyph",
    metaDescription:
      "Replace a name, a date or a typo on every page of a PDF at once. The old text is deleted from the file, not covered. Free, no account.",
    eyebrow: "Free · no account",
    h1: "Find and replace a word in a whole PDF",
    intro:
      "A client name to change in a quote template, a typo repeated over ten pages, a year to update: Glyph finds every occurrence and rewrites it, page after page, deleting the old text from the file.",
    widget: "upload",
    intent: "replace",
    sections: [
      {
        h2: "How to replace a word in a PDF",
        blocks: [
          {
            steps: [
              "Drop your PDF above: the editor opens with the **Find and replace** window.",
              "Type the text to find and its replacement. Tick **Whole word** to leave “Joanna” alone when replacing “Joan”, and **Match case** if capitals matter.",
              "Click **Replace all**: Glyph tells you how many occurrences were replaced, and on which pages.",
              "Check the result, then download the PDF. A single **Undo** reverts the whole replacement.",
            ],
          },
          {
            p: "The window stays available afterwards from the editor's **Tools** menu.",
          },
        ],
      },
      {
        h2: "A real replacement, not a patch",
        blocks: [
          {
            p: "Each affected line is changed as if you had retyped it: the original characters are deleted from the page content, and the new line is written in the original font when possible, or the closest one otherwise. The rest of the line keeps its formatting. Afterwards, searching the PDF no longer finds the old word. The principle is explained in [overlay vs real editing](@overlayVsReal).",
          },
          {
            p: "The search sees through typographic ligatures (“ﬁ” is found when you search for “fi”) and non-breaking spaces, both common in PDFs.",
          },
        ],
      },
      {
        h2: "The limits",
        blocks: [
          {
            list: [
              "**Line by line**: a phrase broken across two lines isn't found. Edit those lines by hand.",
              "**Longer text**: the line extends to the right up to the next element, then the text is made slightly smaller to fit. Check the pages listed.",
              "**Unreadable text layer**: lines whose text can't be read back (some payroll software, for instance) are skipped.",
              "**Scanned PDFs**: no text, so nothing to replace (no OCR).",
              "**Volume**: 300 lines changed per run, over the first 300 pages. Beyond that, run it again.",
              "**Colored background**: it is erased behind each changed line.",
            ],
          },
        ],
      },
      {
        h2: "Where does your file go?",
        blocks: [
          {
            p: "Your PDF is sent over HTTPS to Glyph's server, processed **in memory only**, never written to disk, and deleted when you close the tab or after 30 minutes of inactivity.",
          },
          {
            p: "Glyph is for updating your own documents. Changing a document to deceive someone is forgery, and illegal: see the [terms of use](@terms).",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Can I delete a word everywhere?",
        a: "Yes: leave “Replace with” empty. To make a word disappear without leaving a visible gap in the layout, [redaction](@redact) is sometimes a better fit.",
      },
      {
        q: "Do capitals and accents matter?",
        a: "Capitals, only if you tick “Match case”. Accents, always: “cafe” doesn't find “café”.",
      },
      {
        q: "Is it free?",
        a: "Yes, with no account, no ads and no watermark.",
      },
    ],
    related: ["editText", "overlayVsReal", "redact"],
  },
};
