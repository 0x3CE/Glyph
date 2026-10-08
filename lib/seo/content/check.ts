import type { LocalizedContent } from "../types";

export const check: LocalizedContent = {
  fr: {
    nav: "Vérifier un PDF caviardé",
    metaTitle: "Vérifier qu'un PDF caviardé ne cache plus rien | Glyph",
    metaDescription:
      "Avant d'envoyer un PDF caviardé, vérifie qu'aucun texte ne reste sous les rectangles noirs, et quelles métadonnées il contient encore. Gratuit, sans compte.",
    eyebrow: "Gratuit · sans compte",
    h1: "Vérifier qu'un PDF caviardé ne cache plus rien",
    intro:
      "Un rectangle noir peut masquer un nom à l'écran tout en le laissant dans le fichier. Dépose ton PDF : Glyph cherche le texte encore présent sous des formes, les caviardages jamais appliqués, le texte invisible et les métadonnées.",
    widget: "check",
    sections: [
      {
        h2: "Ce que le vérificateur cherche",
        blocks: [
          {
            list: [
              "**Du texte recouvert** par un rectangle ou une image posés par-dessus : un faux caviardage, ou une ancienne valeur cachée sous un rectangle blanc.",
              "**Des caviardages marqués mais jamais appliqués** : certains logiciels marquent d'abord les zones, puis demandent de les appliquer ; tant que ce n'est pas fait, le texte est toujours là.",
              "**Du texte invisible** : présent dans le fichier mais pas affiché, comme la couche de reconnaissance de caractères d'un scan.",
              "**Les métadonnées** : titre, auteur, sujet, mots-clés, logiciels, dates, et métadonnées XMP.",
              "**Les anciennes versions** : un PDF modifié « par ajout » garde ses versions précédentes, avec leur texte.",
              "**Les pièces jointes** embarquées dans le PDF.",
            ],
          },
        ],
      },
      {
        h2: "Ce qu'il ne voit pas",
        blocks: [
          {
            p: "Une vérification automatique aide, mais ne remplace pas une relecture. Le vérificateur ne détecte pas :",
          },
          {
            list: [
              "**un rectangle posé sur un scan** : le texte d'un scan est une image, et les pixels sous le rectangle peuvent subsister ;",
              "**du texte de la même couleur que le fond**, blanc sur blanc par exemple ;",
              "**du texte placé en dehors de la zone visible de la page** ;",
              "**un caviardage incomplet** : le nom masqué en page 1 mais oublié en page 4, ou dans le nom du fichier.",
            ],
          },
          {
            p: "Les PDF protégés par mot de passe ne peuvent pas être vérifiés, et seules les 300 premières pages sont analysées.",
          },
        ],
      },
      {
        h2: "Si un problème est trouvé",
        blocks: [
          {
            steps: [
              "Clique sur **Corriger dans l'éditeur** : le fichier s'ouvre en mode caviardage.",
              "Caviarde à nouveau les zones concernées : cette fois le texte dessous est supprimé du fichier. Voir [caviarder un PDF](@redact).",
              "Clique sur **Nettoyer les métadonnées**, puis télécharge le PDF.",
              "Repasse le nouveau fichier dans le vérificateur.",
            ],
          },
        ],
      },
      {
        h2: "Où va ton fichier ?",
        blocks: [
          {
            p: "La vérification n'a pas lieu dans ton navigateur : ton PDF est envoyé en HTTPS au serveur de Glyph, analysé **en mémoire uniquement**, sans être modifié ni conservé, pas même le temps d'une session. Seul le rapport t'est renvoyé.",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Comment savoir si un caviardage est réel ?",
        a: "Essaie de sélectionner le texte sous le rectangle et de le copier-coller : si du texte apparaît, il n'est pas caviardé. Le vérificateur fait ce test sur toutes les pages, et regarde aussi les métadonnées et les anciennes versions.",
      },
      {
        q: "Le vérificateur modifie-t-il mon fichier ?",
        a: "Non. Il le lit, envoie un rapport, et l'oublie. Pour corriger, il faut passer par l'éditeur.",
      },
      {
        q: "Est-ce gratuit ?",
        a: "Oui, sans compte, sans publicité, sans limite d'utilisation raisonnable.",
      },
    ],
    related: ["redact", "anonymize", "overlayVsReal"],
  },
  en: {
    nav: "Check a redacted PDF",
    metaTitle: "Check that a redacted PDF hides nothing | Glyph",
    metaDescription:
      "Before sending a redacted PDF, check that no text remains under the black boxes, and which metadata it still holds. Free, no account.",
    eyebrow: "Free · no account",
    h1: "Check that a redacted PDF hides nothing",
    intro:
      "A black box can hide a name on screen while leaving it in the file. Drop your PDF: Glyph looks for text still present under shapes, redactions never applied, invisible text and metadata.",
    widget: "check",
    sections: [
      {
        h2: "What the checker looks for",
        blocks: [
          {
            list: [
              "**Covered text** under a box or an image placed on top: a fake redaction, or an old value hidden under a white box.",
              "**Redactions marked but never applied**: some software marks areas first, then asks you to apply them; until you do, the text is still there.",
              "**Invisible text**: in the file but not displayed, like a scan's character-recognition layer.",
              "**Metadata**: title, author, subject, keywords, software, dates, and XMP metadata.",
              "**Older versions**: a PDF edited “by appending” keeps its previous versions, with their text.",
              "**Attachments** embedded in the PDF.",
            ],
          },
        ],
      },
      {
        h2: "What it doesn't see",
        blocks: [
          {
            p: "An automatic check helps, but doesn't replace reading the document again. The checker doesn't detect:",
          },
          {
            list: [
              "**a box placed on a scan**: a scan's text is an image, and the pixels under the box may survive;",
              "**text the same color as the background**, white on white for instance;",
              "**text placed outside the visible area of the page**;",
              "**an incomplete redaction**: the name hidden on page 1 but forgotten on page 4, or in the file name.",
            ],
          },
          {
            p: "Password-protected PDFs can't be checked, and only the first 300 pages are analysed.",
          },
        ],
      },
      {
        h2: "If a problem is found",
        blocks: [
          {
            steps: [
              "Click **Fix it in the editor**: the file opens in redaction mode.",
              "Redact the areas again: this time the text underneath is deleted from the file. See [redact a PDF](@redact).",
              "Click **Remove metadata**, then download the PDF.",
              "Run the new file through the checker again.",
            ],
          },
        ],
      },
      {
        h2: "Where does your file go?",
        blocks: [
          {
            p: "The check doesn't happen in your browser: your PDF is sent over HTTPS to Glyph's server, analysed **in memory only**, without being changed or kept, not even for a session. Only the report comes back to you.",
          },
        ],
      },
    ],
    faq: [
      {
        q: "How can I tell whether a redaction is real?",
        a: "Try selecting the text under the box and copy-pasting it: if text appears, it isn't redacted. The checker runs that test on every page, and also looks at metadata and older versions.",
      },
      {
        q: "Does the checker change my file?",
        a: "No. It reads it, sends back a report, and forgets it. To fix it, go through the editor.",
      },
      {
        q: "Is it free?",
        a: "Yes, with no account, no ads, and no limit for reasonable use.",
      },
    ],
    related: ["redact", "anonymize", "overlayVsReal"],
  },
};
