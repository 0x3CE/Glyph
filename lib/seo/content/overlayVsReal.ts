import type { LocalizedContent } from "../types";

export const overlayVsReal: LocalizedContent = {
  fr: {
    nav: "Overlay contre vraie édition",
    metaTitle: "Modifier un PDF : overlay ou vraie édition ? | Glyph",
    metaDescription:
      "Pourquoi un rectangle blanc ne modifie pas vraiment un PDF, ce qu'il laisse dans le fichier, et comment vérifier qu'un texte a bien été supprimé.",
    eyebrow: "Article",
    h1: "Overlay ou vraie édition : ce qui se passe vraiment quand on « modifie » un PDF",
    intro:
      "Deux PDF peuvent s'afficher exactement pareil et contenir des choses très différentes. L'un a vraiment été modifié ; l'autre cache simplement l'ancien texte sous un rectangle. La différence ne se voit pas à l'écran, mais elle compte dès qu'on copie, cherche, partage ou caviarde.",
    sections: [
      {
        h2: "Comment un PDF stocke son texte",
        blocks: [
          {
            p: "Un PDF n'est pas un document de traitement de texte. Chaque page est une suite d'instructions de dessin : « place-toi ici, utilise cette police, dessine ces caractères », « trace ce rectangle », « affiche cette image ». Le texte que tu vois est le résultat de ces instructions, dessinées les unes après les autres, dans l'ordre.",
          },
          {
            p: "Conséquence directe : ce qui est dessiné **en dernier** recouvre ce qui est dessiné avant. Un rectangle blanc placé après une ligne de texte la fait disparaître à l'écran… sans la retirer de la liste des instructions.",
          },
        ],
      },
      {
        h2: "Méthode 1 : l'overlay, ou le rectangle blanc",
        blocks: [
          {
            p: "C'est la méthode de la plupart des éditeurs PDF en ligne et des annotations : on ajoute un rectangle de la couleur du fond par-dessus l'ancien texte, puis le nouveau texte par-dessus le rectangle. Rien n'est supprimé, tout est ajouté.",
          },
          {
            p: "Dans le fichier, on trouve donc trois couches empilées : l'ancien texte, le rectangle, le nouveau texte. Et chacune reste exploitable :",
          },
          {
            list: [
              "**la recherche et le copier-coller** renvoient l'ancien texte, parfois mélangé au nouveau ;",
              "**les lecteurs d'écran** (accessibilité) lisent souvent les deux versions ;",
              "**n'importe quel éditeur PDF** permet de déplacer ou supprimer le rectangle et de révéler l'ancien texte ;",
              "**sur un fond coloré**, une photo ou un tableau, le rectangle se voit.",
            ],
          },
          {
            p: "C'est exactement le mécanisme des caviardages ratés qui font régulièrement l'actualité : des documents publiés avec des passages « noircis » par un rectangle noir, dont le texte se récupère par un simple copier-coller. En janvier 2019, une pièce déposée par les avocats de Paul Manafort devant un tribunal américain a ainsi révélé des informations censées être masquées ([source](https://www.abajournal.com/news/article/paul-manaforts-attorneys-failed-at-redacting-learn-how-to-do-it-right)).",
          },
        ],
      },
      {
        h2: "Méthode 2 : la vraie édition",
        blocks: [
          {
            p: "Modifier vraiment un PDF, c'est retirer de la page les instructions qui dessinent l'ancien texte, puis ajouter celles qui dessinent le nouveau. Après l'opération, l'ancien texte n'existe plus dans le fichier : il n'y a rien à révéler, et une recherche renvoie la nouvelle valeur.",
          },
          {
            p: "C'est plus difficile qu'il n'y paraît, et c'est pour ça que peu d'outils le font :",
          },
          {
            list: [
              "**les polices sont souvent incomplètes** : un PDF n'embarque généralement que les lettres qu'il utilise. Pour écrire un mot nouveau, il faut parfois trouver une police de remplacement aux mêmes largeurs de lettres, sinon la ligne déborde ou se décale ;",
              "**une ligne peut mélanger plusieurs styles** : un mot en gras au milieu d'une phrase doit le rester si on modifie le reste ;",
              "**il ne faut rien effacer chez les voisins** : dans un tableau serré, les zones des lignes se chevauchent souvent de quelques points ;",
              "**certains PDF ne permettent pas de relire leur texte** : les caractères affichés ne correspondent pas à ceux enregistrés, et il faut alors retaper la ligne.",
            ],
          },
          {
            p: "Glyph applique cette méthode : il supprime les caractères d'origine (par une opération de « redaction », qui retire réellement le contenu sous une zone), puis réinsère le nouveau texte à la position exacte de l'ancien, dans la police d'origine ou la plus proche possible. Le fichier final est entièrement réécrit : l'ancien texte ne subsiste pas non plus dans ses données internes.",
          },
        ],
      },
      {
        h2: "Comment vérifier un PDF soi-même",
        blocks: [
          {
            steps: [
              "Ouvre le PDF et sélectionne le texte autour de la zone modifiée ou noircie, puis colle-le dans un éditeur de texte. Si l'ancien texte apparaît, il est toujours dans le fichier.",
              "Utilise la recherche (Ctrl+F ou Cmd+F) avec un mot de l'ancien texte.",
              "Ouvre le fichier dans un éditeur PDF et essaie de déplacer les rectangles : un overlay se déplace, une vraie suppression ne laisse rien derrière.",
              "Regarde les propriétés du document : le titre, l'auteur ou les mots-clés contiennent parfois des informations qu'on croyait retirées.",
            ],
          },
          {
            note: "Un PDF peut aussi garder d'anciennes versions de lui-même quand il a été modifié « par ajout » (enregistrement incrémental). Les supprimer demande de réécrire entièrement le fichier, ce que fait Glyph. Pour tout vérifier d'un coup, [le vérificateur de PDF caviardé](@check) analyse ces points à ta place.",
          },
        ],
      },
      {
        h2: "En résumé",
        blocks: [
          {
            list: [
              "un overlay **cache** : l'ancien texte reste dans le fichier, récupérable par n'importe qui ;",
              "une vraie édition **remplace** : l'ancien texte disparaît du fichier ;",
              "pour caviarder un document avant de le partager, seule la vraie suppression protège réellement l'information.",
            ],
          },
          {
            p: "Pour modifier un PDF de cette façon : [modifier le texte d'un PDF](@editText). Pour masquer définitivement une information : [caviarder un PDF](@redact).",
          },
        ],
      },
    ],
    related: ["editText", "redact", "check"],
    updated: "2026-10-08",
  },
  en: {
    nav: "Overlay vs real editing",
    metaTitle: "Editing a PDF: overlay or real editing? | Glyph",
    metaDescription:
      "Why a white box doesn't really edit a PDF, what it leaves in the file, and how to check that text was actually removed.",
    eyebrow: "Article",
    h1: "Overlay or real editing: what actually happens when you “edit” a PDF",
    intro:
      "Two PDFs can look exactly the same and contain very different things. One was really edited; the other just hides the old text under a box. The difference doesn't show on screen, but it matters as soon as you copy, search, share or redact.",
    sections: [
      {
        h2: "How a PDF stores its text",
        blocks: [
          {
            p: "A PDF isn't a word-processing document. Each page is a list of drawing instructions: “move here, use this font, draw these characters”, “draw this rectangle”, “show this image”. The text you see is the result of those instructions, drawn one after another, in order.",
          },
          {
            p: "The direct consequence: whatever is drawn **last** covers whatever was drawn before. A white rectangle placed after a line of text hides it on screen… without removing it from the list of instructions.",
          },
        ],
      },
      {
        h2: "Method 1: the overlay, or the white box",
        blocks: [
          {
            p: "This is how most online PDF editors and annotations work: a box the color of the background is added over the old text, then the new text on top of the box. Nothing is removed; everything is added.",
          },
          {
            p: "So the file holds three stacked layers: the old text, the box, the new text. And each of them stays usable:",
          },
          {
            list: [
              "**search and copy-paste** return the old text, sometimes mixed with the new one;",
              "**screen readers** (accessibility) often read both versions;",
              "**any PDF editor** can move or delete the box and reveal the old text;",
              "**on a colored background**, a photo or a table, the box shows.",
            ],
          },
          {
            p: "It's exactly the mechanism behind the failed redactions that regularly make the news: documents published with passages “blacked out” by a black rectangle, whose text can be recovered with a simple copy-paste. In January 2019, a court filing by Paul Manafort's lawyers revealed information that was supposed to be hidden this way ([source](https://www.abajournal.com/news/article/paul-manaforts-attorneys-failed-at-redacting-learn-how-to-do-it-right)).",
          },
        ],
      },
      {
        h2: "Method 2: real editing",
        blocks: [
          {
            p: "Really editing a PDF means removing the instructions that draw the old text from the page, then adding the ones that draw the new text. Afterwards, the old text no longer exists in the file: there is nothing to reveal, and a search returns the new value.",
          },
          {
            p: "It's harder than it sounds, which is why few tools do it:",
          },
          {
            list: [
              "**fonts are often incomplete**: a PDF usually embeds only the letters it uses. Writing a new word sometimes needs a replacement font with the same letter widths, or the line overflows or shifts;",
              "**a line can mix several styles**: a bold word in the middle of a sentence must stay bold when the rest is edited;",
              "**nothing may be erased next door**: in a tight table, the areas of neighbouring lines often overlap by a few points;",
              "**some PDFs don't let their text be read back**: the characters displayed don't match the ones stored, and the line then has to be retyped.",
            ],
          },
          {
            p: "Glyph uses this method: it removes the original characters (with a “redaction” operation, which actually deletes the content under an area), then reinserts the new text at the exact position of the old one, in the original font or the closest one. The final file is entirely rewritten: the old text doesn't survive in its internal data either.",
          },
        ],
      },
      {
        h2: "How to check a PDF yourself",
        blocks: [
          {
            steps: [
              "Open the PDF, select the text around the edited or blacked-out area, and paste it into a text editor. If the old text shows up, it's still in the file.",
              "Use search (Ctrl+F or Cmd+F) with a word from the old text.",
              "Open the file in a PDF editor and try moving the boxes: an overlay moves, a real deletion leaves nothing behind.",
              "Look at the document properties: the title, author or keywords sometimes hold information you thought was removed.",
            ],
          },
          {
            note: "A PDF can also keep older versions of itself when it was edited “by appending” (incremental save). Removing them requires rewriting the whole file, which Glyph does. To check everything at once, [the redacted PDF checker](@check) analyses these points for you.",
          },
        ],
      },
      {
        h2: "In short",
        blocks: [
          {
            list: [
              "an overlay **hides**: the old text stays in the file, recoverable by anyone;",
              "real editing **replaces**: the old text disappears from the file;",
              "to redact a document before sharing it, only real deletion actually protects the information.",
            ],
          },
          {
            p: "To edit a PDF this way: [edit the text in a PDF](@editText). To hide information for good: [redact a PDF](@redact).",
          },
        ],
      },
    ],
    related: ["editText", "redact", "check"],
    updated: "2026-10-08",
  },
};
