import type { LocalizedContent } from "../types";

export const anonymize: LocalizedContent = {
  fr: {
    nav: "Anonymiser un PDF",
    metaTitle: "Anonymiser un PDF : contenu et métadonnées | Glyph",
    metaDescription:
      "Retire d'un PDF les noms et numéros visibles, mais aussi ce qui ne se voit pas : auteur, mots-clés, métadonnées XMP, pièces jointes, texte invisible.",
    eyebrow: "Gratuit · sans compte",
    h1: "Anonymiser un PDF, y compris ce qui ne se voit pas",
    intro:
      "Un PDF contient souvent plus que ce qu'il affiche : le nom de son auteur, le logiciel qui l'a produit, des mots-clés, d'anciennes versions, parfois du texte invisible. Glyph caviarde ce qui se voit et nettoie ce qui ne se voit pas.",
    widget: "upload",
    intent: "anonymize",
    sections: [
      {
        h2: "Comment anonymiser un PDF",
        blocks: [
          {
            steps: [
              "Dépose ton PDF ci-dessus : l'éditeur s'ouvre en mode caviardage.",
              "Masque les noms, numéros et adresses visibles : touche les lignes, ou dessine des zones.",
              "Clique sur **Nettoyer les métadonnées** : Glyph indique ce qu'il a trouvé et retiré.",
              "Télécharge le PDF, puis renomme le fichier s'il contient ton nom.",
            ],
          },
        ],
      },
      {
        h2: "Ce qu'un PDF cache sans qu'on le voie",
        blocks: [
          {
            list: [
              "**Les métadonnées** : titre, auteur, sujet, mots-clés, logiciel d'origine, dates. Certains logiciels y mettent le nom ou le matricule de la personne concernée.",
              "**Les métadonnées XMP** : une seconde copie, plus détaillée, de ces informations.",
              "**Les pièces jointes** : des fichiers embarqués dans le PDF.",
              "**Le texte invisible** : du texte présent mais non affiché (couche de reconnaissance de caractères d'un scan, par exemple).",
              "**Les anciennes versions** : un PDF modifié « par ajout » garde ses versions précédentes à l'intérieur du fichier.",
              "**Du texte caché sous des rectangles** : le cas des faux caviardages.",
            ],
          },
          {
            p: "C'est un cas réel : un bulletin de paie « anonymisé » avec des rectangles noirs gardait le nom et le matricule du salarié dans ses mots-clés, invisibles à l'écran.",
          },
        ],
      },
      {
        h2: "Ce que fait le nettoyage",
        blocks: [
          {
            p: "**Nettoyer les métadonnées** efface le dictionnaire d'informations et les métadonnées XMP, retire les pièces jointes, le JavaScript, le texte invisible et les vignettes, et applique les caviardages marqués par un autre logiciel mais jamais appliqués (le texte dessous est supprimé). Le fichier est ensuite entièrement réécrit, ce qui élimine aussi ses anciennes versions et les objets orphelins.",
          },
          {
            p: "Il ne touche ni au texte visible, ni aux liens, ni aux champs de formulaire que tu as remplis.",
          },
        ],
      },
      {
        h2: "Les limites",
        blocks: [
          {
            list: [
              "**Le contenu visible** reste ton travail : Glyph ne détecte pas tout seul les noms ou numéros à masquer.",
              "**Les images** : le visage ou le nom sur une photo de pièce d'identité doit être masqué avec le mode Zone.",
              "**Le nom du fichier** n'est pas modifié par Glyph : renomme-le.",
              "**Le style d'écriture et le contexte** d'un document peuvent suffire à identifier quelqu'un : aucun outil ne règle ça.",
            ],
          },
          {
            note: "Pour contrôler le résultat, passe le fichier final dans [le vérificateur de PDF caviardé](@check).",
          },
        ],
      },
      {
        h2: "Où va ton fichier ?",
        blocks: [
          {
            p: "Ton PDF est envoyé en HTTPS au serveur de Glyph, traité **en mémoire uniquement**, jamais écrit sur disque, et supprimé à la fermeture de l'onglet ou après 30 minutes d'inactivité.",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Comment voir les métadonnées d'un PDF ?",
        a: "Dans la plupart des lecteurs PDF : Fichier, puis Propriétés (ou Outils, puis Afficher l'inspecteur dans Aperçu sur Mac). Le vérificateur de Glyph les liste aussi.",
      },
      {
        q: "Le nettoyage modifie-t-il l'apparence du document ?",
        a: "Non : seuls le texte invisible et les données cachées sont retirés. Ce qui s'affiche reste identique.",
      },
      {
        q: "Est-ce gratuit ?",
        a: "Oui, sans compte, sans publicité et sans filigrane.",
      },
    ],
    related: ["redact", "check", "overlayVsReal"],
  },
  en: {
    nav: "Anonymize a PDF",
    metaTitle: "Anonymize a PDF: content and metadata | Glyph",
    metaDescription:
      "Remove the visible names and numbers from a PDF, and what doesn't show: author, keywords, XMP metadata, attachments, invisible text.",
    eyebrow: "Free · no account",
    h1: "Anonymize a PDF, including what doesn't show",
    intro:
      "A PDF often holds more than it displays: its author's name, the software that produced it, keywords, older versions, sometimes invisible text. Glyph redacts what shows and cleans up what doesn't.",
    widget: "upload",
    intent: "anonymize",
    sections: [
      {
        h2: "How to anonymize a PDF",
        blocks: [
          {
            steps: [
              "Drop your PDF above: the editor opens in redaction mode.",
              "Hide the visible names, numbers and addresses: tap lines, or draw areas.",
              "Click **Remove metadata**: Glyph shows what it found and removed.",
              "Download the PDF, then rename the file if it contains your name.",
            ],
          },
        ],
      },
      {
        h2: "What a PDF hides without showing it",
        blocks: [
          {
            list: [
              "**Metadata**: title, author, subject, keywords, creating software, dates. Some software puts the name or employee number of the person concerned there.",
              "**XMP metadata**: a second, more detailed copy of that information.",
              "**Attachments**: files embedded in the PDF.",
              "**Invisible text**: text that is there but not displayed (a scan's character-recognition layer, for instance).",
              "**Older versions**: a PDF edited “by appending” keeps its previous versions inside the file.",
              "**Text hidden under boxes**: the case of fake redactions.",
            ],
          },
          {
            p: "A real case: a payslip “anonymized” with black boxes still had the employee's name and number in its keywords, invisible on screen.",
          },
        ],
      },
      {
        h2: "What the clean-up does",
        blocks: [
          {
            p: "**Remove metadata** erases the information dictionary and the XMP metadata, removes attachments, JavaScript, invisible text and thumbnails, and applies redactions that another program marked but never applied (the text under them is deleted). The file is then entirely rewritten, which also gets rid of its older versions and orphaned objects.",
          },
          {
            p: "It doesn't touch the visible text, links, or the form fields you filled in.",
          },
        ],
      },
      {
        h2: "The limits",
        blocks: [
          {
            list: [
              "**Visible content** is up to you: Glyph doesn't detect the names or numbers to hide on its own.",
              "**Images**: the face or name on a photo of an ID has to be hidden with Area mode.",
              "**The file name** isn't changed by Glyph: rename it.",
              "**Writing style and context** can be enough to identify someone: no tool fixes that.",
            ],
          },
          {
            note: "To check the result, run the final file through [the redacted PDF checker](@check).",
          },
        ],
      },
      {
        h2: "Where does your file go?",
        blocks: [
          {
            p: "Your PDF is sent over HTTPS to Glyph's server, processed **in memory only**, never written to disk, and deleted when you close the tab or after 30 minutes of inactivity.",
          },
        ],
      },
    ],
    faq: [
      {
        q: "How do I see a PDF's metadata?",
        a: "In most PDF readers: File, then Properties (or Tools, then Show Inspector in Preview on a Mac). Glyph's checker lists them too.",
      },
      {
        q: "Does the clean-up change how the document looks?",
        a: "No: only invisible text and hidden data are removed. What displays stays the same.",
      },
      {
        q: "Is it free?",
        a: "Yes, with no account, no ads and no watermark.",
      },
    ],
    related: ["redact", "check", "overlayVsReal"],
  },
};
