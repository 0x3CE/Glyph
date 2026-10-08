import type { LocalizedContent } from "../types";

export const guideFixTypo: LocalizedContent = {
  fr: {
    nav: "Corriger une faute dans un PDF",
    metaTitle: "Corriger une faute d'orthographe dans un PDF | Glyph",
    metaDescription:
      "Une coquille dans un CV, un devis ou un mémoire déjà exporté en PDF ? Comment la corriger proprement, avec ou sans le fichier d'origine.",
    eyebrow: "Guide",
    h1: "Corriger une faute dans un PDF déjà envoyé… ou presque",
    intro:
      "Tu relis ton CV, ton devis ou ton mémoire une dernière fois, et la faute saute aux yeux. Voici comment la corriger sans tout refaire, et sans que l'ancienne version reste cachée dans le fichier.",
    widget: "upload",
    intent: "edit",
    sections: [
      {
        h2: "Si tu as encore le fichier d'origine",
        blocks: [
          {
            p: "C'est la meilleure solution : corrige dans Word, Google Docs, Pages ou LibreOffice, puis exporte à nouveau en PDF. La mise en page sera parfaite, et la correction s'appliquera aussi aux prochaines versions.",
          },
        ],
      },
      {
        h2: "Si tu n'as que le PDF",
        blocks: [
          {
            steps: [
              "Dépose le PDF ci-dessus.",
              "Clique sur la ligne qui contient la faute, corrige-la, puis enregistre.",
              "Si la même faute revient plusieurs fois, utilise plutôt [remplacer un mot dans tout le PDF](@findReplace).",
              "Zoome sur la ligne corrigée pour vérifier le rendu, puis télécharge le PDF.",
            ],
          },
          {
            p: "Glyph supprime le mot fautif du fichier et réécrit la ligne, dans la police d'origine quand c'est possible. Si un message t'indique qu'une police de remplacement a été utilisée, compare la ligne avec ses voisines : la différence est en général invisible sur un mot, plus visible sur un titre en grande taille.",
          },
        ],
      },
      {
        h2: "Ce qu'il vaut mieux éviter",
        blocks: [
          {
            list: [
              "**Coller un rectangle blanc et retaper par-dessus** : la faute reste dans le fichier, et réapparaît au copier-coller ou à la recherche. Un recruteur qui copie ton nom ou ton e-mail depuis le CV peut récupérer l'ancien texte. Voir [overlay contre vraie édition](@overlayVsReal).",
              "**Convertir le PDF en Word puis le réexporter** : la conversion déplace souvent les éléments, change les polices et casse les tableaux. À réserver aux documents simples.",
              "**Imprimer, corriger au stylo, scanner** : le texte devient une image, impossible à rechercher ou à copier.",
            ],
          },
        ],
      },
      {
        h2: "Quand ça ne marche pas",
        blocks: [
          {
            list: [
              "**La ligne n'est pas cliquable** : la page est probablement un scan (une image). Glyph ne fait pas de reconnaissance de caractères.",
              "**Le champ d'édition affiche des caractères bizarres** : le PDF a une couche de texte illisible. Tu peux quand même corriger, mais il faut retaper toute la ligne.",
              "**Le texte corrigé est sur un fond coloré** : le fond est effacé derrière la ligne modifiée.",
            ],
          },
        ],
      },
    ],
    faq: [
      {
        q: "La correction se verra-t-elle ?",
        a: "En général non, quand la police d'origine peut être réutilisée. Avec une police de remplacement, la différence peut se voir sur un titre en grande taille. Vérifie toujours en zoomant.",
      },
      {
        q: "Peut-on corriger un PDF sur téléphone ?",
        a: "Oui : Glyph fonctionne dans le navigateur du téléphone, la ligne se modifie au toucher.",
      },
    ],
    related: ["editText", "findReplace", "overlayVsReal"],
    updated: "2026-10-08",
  },
  en: {
    nav: "Fix a typo in a PDF",
    metaTitle: "Fix a typo in a PDF | Glyph",
    metaDescription:
      "A typo in a résumé, a quote or a thesis already exported to PDF? How to fix it cleanly, with or without the original file.",
    eyebrow: "Guide",
    h1: "Fix a typo in a PDF you've almost sent",
    intro:
      "You read your résumé, quote or thesis one last time, and the typo jumps out. Here's how to fix it without redoing everything, and without the old version staying hidden in the file.",
    widget: "upload",
    intent: "edit",
    sections: [
      {
        h2: "If you still have the original file",
        blocks: [
          {
            p: "That's the best option: fix it in Word, Google Docs, Pages or LibreOffice, then export to PDF again. The layout will be perfect, and the fix will carry over to future versions.",
          },
        ],
      },
      {
        h2: "If you only have the PDF",
        blocks: [
          {
            steps: [
              "Drop the PDF above.",
              "Click the line with the typo, fix it, then save.",
              "If the same typo appears several times, use [replace a word in the whole PDF](@findReplace) instead.",
              "Zoom in on the fixed line to check it, then download the PDF.",
            ],
          },
          {
            p: "Glyph deletes the misspelled word from the file and rewrites the line, in the original font when possible. If a message says a replacement font was used, compare the line with its neighbours: the difference is usually invisible on a word, more visible on a large heading.",
          },
        ],
      },
      {
        h2: "What to avoid",
        blocks: [
          {
            list: [
              "**Pasting a white box and typing over it**: the typo stays in the file, and comes back on copy-paste or search. A recruiter copying your name or email from the résumé can get the old text. See [overlay vs real editing](@overlayVsReal).",
              "**Converting the PDF to Word and exporting it again**: the conversion often moves things around, changes fonts and breaks tables. Keep it for simple documents.",
              "**Printing, fixing with a pen, scanning**: the text becomes an image that can't be searched or copied.",
            ],
          },
        ],
      },
      {
        h2: "When it doesn't work",
        blocks: [
          {
            list: [
              "**The line isn't clickable**: the page is probably a scan (an image). Glyph doesn't do character recognition.",
              "**The edit field shows odd characters**: the PDF has an unreadable text layer. You can still fix it, but you have to retype the whole line.",
              "**The fixed text sits on a colored background**: the background is erased behind the changed line.",
            ],
          },
        ],
      },
    ],
    faq: [
      {
        q: "Will the fix show?",
        a: "Usually not, when the original font can be reused. With a replacement font, the difference can show on a large heading. Always check by zooming in.",
      },
      {
        q: "Can I fix a PDF on my phone?",
        a: "Yes: Glyph works in the phone's browser, and you edit a line by tapping it.",
      },
    ],
    related: ["editText", "findReplace", "overlayVsReal"],
    updated: "2026-10-08",
  },
};

export const guideWithoutAcrobat: LocalizedContent = {
  fr: {
    nav: "Modifier un PDF sans Acrobat",
    metaTitle: "Modifier un PDF sans Adobe Acrobat : les options | Glyph",
    metaDescription:
      "Acrobat Reader ne modifie pas le texte d'un PDF. Les alternatives gratuites, ce que chacune fait vraiment, et laquelle choisir selon ton document.",
    eyebrow: "Guide",
    h1: "Modifier un PDF sans Adobe Acrobat",
    intro:
      "Acrobat Reader, gratuit, permet de lire, annoter et signer un PDF, mais pas d'en modifier le texte : il faut pour ça un abonnement payant. Voici les alternatives, et ce que chacune fait vraiment au fichier.",
    widget: "upload",
    intent: "edit",
    sections: [
      {
        h2: "La question à se poser d'abord",
        blocks: [
          {
            p: "Veux-tu **modifier le texte existant**, ou **ajouter quelque chose par-dessus** (une note, une signature, une case cochée) ? Pour ajouter, presque tous les outils gratuits suffisent, y compris Acrobat Reader et l'Aperçu du Mac. Pour modifier, les choses se compliquent.",
          },
        ],
      },
      {
        h2: "Les options pour modifier le texte",
        blocks: [
          {
            list: [
              "**Le fichier d'origine** (Word, Google Docs…) : si tu l'as, c'est toujours la meilleure solution. Corrige, puis réexporte en PDF.",
              "**Word** sait ouvrir un PDF en le convertissant en document modifiable. Pratique pour un texte simple ; sur une mise en page complexe (colonnes, tableaux, formulaires), le résultat s'éloigne souvent de l'original.",
              "**LibreOffice Draw** (gratuit) ouvre un PDF et transforme chaque ligne en zone de texte modifiable. La mise en page est mieux conservée qu'avec Word, mais les polices non installées sur ton ordinateur sont remplacées.",
              "**Les éditeurs PDF en ligne** : beaucoup posent un rectangle blanc sur l'ancien texte et écrivent par-dessus. Le rendu est correct à l'écran, mais l'ancien texte reste dans le fichier. Voir [overlay contre vraie édition](@overlayVsReal).",
              "**Glyph** modifie le texte en place, ligne par ligne : l'ancien texte est supprimé du fichier, le nouveau est écrit dans la police d'origine ou la plus proche. Gratuit, sans compte, dans le navigateur.",
            ],
          },
        ],
      },
      {
        h2: "Laquelle choisir ?",
        blocks: [
          {
            list: [
              "**Quelques mots ou chiffres à changer** dans un document fini : [modifier le texte du PDF](@editText) directement.",
              "**Le même mot sur plusieurs pages** : [remplacer un mot dans tout le PDF](@findReplace).",
              "**Des paragraphes entiers à réécrire** : repars du fichier d'origine, ou convertis en document modifiable (Word, LibreOffice). Glyph n'est pas fait pour réécrire un texte long : il modifie ligne par ligne.",
              "**Des informations à masquer** avant de partager : [caviarder le PDF](@redact), pas un rectangle noir.",
            ],
          },
        ],
      },
      {
        h2: "Les limites de Glyph",
        blocks: [
          {
            p: "Pas de PDF scannés (pas d'OCR), pas de PDF protégés par mot de passe, 20 Mo maximum, et pas encore d'arabe, d'hébreu, de chinois, japonais ou coréen. Le fichier est traité en mémoire sur le serveur de Glyph, puis supprimé.",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Acrobat Reader peut-il modifier un PDF ?",
        a: "Il peut ajouter des commentaires, du texte par-dessus, remplir des formulaires et signer. Modifier le texte existant demande une version payante d'Acrobat.",
      },
      {
        q: "Existe-t-il un éditeur PDF vraiment gratuit ?",
        a: "Oui : LibreOffice Draw sur ordinateur, et Glyph dans le navigateur, tous deux gratuits et open source, sans filigrane.",
      },
    ],
    related: ["editText", "guideMac", "overlayVsReal"],
    updated: "2026-10-08",
  },
  en: {
    nav: "Edit a PDF without Acrobat",
    metaTitle: "Edit a PDF without Adobe Acrobat: your options | Glyph",
    metaDescription:
      "Acrobat Reader doesn't edit a PDF's text. The free alternatives, what each one really does, and which to pick for your document.",
    eyebrow: "Guide",
    h1: "Edit a PDF without Adobe Acrobat",
    intro:
      "Acrobat Reader, the free one, lets you read, annotate and sign a PDF, but not edit its text: that takes a paid subscription. Here are the alternatives, and what each one really does to the file.",
    widget: "upload",
    intent: "edit",
    sections: [
      {
        h2: "The question to ask first",
        blocks: [
          {
            p: "Do you want to **change the existing text**, or **add something on top** (a note, a signature, a ticked box)? To add, almost every free tool will do, Acrobat Reader and the Mac's Preview included. To change, it gets trickier.",
          },
        ],
      },
      {
        h2: "Options for changing the text",
        blocks: [
          {
            list: [
              "**The original file** (Word, Google Docs…): if you have it, it's always the best option. Fix it, then export to PDF again.",
              "**Word** can open a PDF by converting it to an editable document. Handy for plain text; on a complex layout (columns, tables, forms), the result often drifts from the original.",
              "**LibreOffice Draw** (free) opens a PDF and turns each line into an editable text box. The layout survives better than with Word, but fonts not installed on your computer are replaced.",
              "**Online PDF editors**: many put a white box over the old text and write on top. It looks right on screen, but the old text stays in the file. See [overlay vs real editing](@overlayVsReal).",
              "**Glyph** edits the text in place, line by line: the old text is deleted from the file, and the new text is written in the original font or the closest one. Free, no account, in the browser.",
            ],
          },
        ],
      },
      {
        h2: "Which one to pick?",
        blocks: [
          {
            list: [
              "**A few words or figures to change** in a finished document: [edit the PDF's text](@editText) directly.",
              "**The same word on several pages**: [replace a word in the whole PDF](@findReplace).",
              "**Whole paragraphs to rewrite**: go back to the original file, or convert to an editable document (Word, LibreOffice). Glyph isn't made for rewriting long text: it edits line by line.",
              "**Information to hide** before sharing: [redact the PDF](@redact), not a black box.",
            ],
          },
        ],
      },
      {
        h2: "Glyph's limits",
        blocks: [
          {
            p: "No scanned PDFs (no OCR), no password-protected PDFs, 20 MB maximum, and no Arabic, Hebrew, Chinese, Japanese or Korean yet. The file is processed in memory on Glyph's server, then deleted.",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Can Acrobat Reader edit a PDF?",
        a: "It can add comments and text on top, fill in forms and sign. Changing the existing text takes a paid version of Acrobat.",
      },
      {
        q: "Is there a truly free PDF editor?",
        a: "Yes: LibreOffice Draw on the desktop, and Glyph in the browser, both free and open source, with no watermark.",
      },
    ],
    related: ["editText", "guideMac", "overlayVsReal"],
    updated: "2026-10-08",
  },
};

export const guideMac: LocalizedContent = {
  fr: {
    nav: "Modifier un PDF sur Mac",
    metaTitle: "Modifier le texte d'un PDF sur Mac | Glyph",
    metaDescription:
      "Aperçu, l'app PDF du Mac, annote mais ne modifie pas le texte existant. Comment changer réellement un mot dans un PDF sur Mac, sans rien installer.",
    eyebrow: "Guide",
    h1: "Modifier le texte d'un PDF sur Mac",
    intro:
      "Aperçu, livré avec chaque Mac, fait beaucoup de choses avec un PDF, mais il ne modifie pas le texte qui s'y trouve déjà. Voici ce qu'il sait faire, ce qu'il ne sait pas faire, et comment changer réellement un mot.",
    widget: "upload",
    intent: "edit",
    sections: [
      {
        h2: "Ce qu'Aperçu sait faire",
        blocks: [
          {
            list: [
              "ajouter une zone de texte, une forme, une note (menu **Outils**, puis **Annoter**) ;",
              "ajouter ta signature, capturée avec le trackpad ou la caméra ;",
              "remplir un formulaire, réorganiser, supprimer ou fusionner des pages ;",
              "afficher les métadonnées du document (**Outils**, puis **Afficher l'inspecteur**).",
            ],
          },
        ],
      },
      {
        h2: "Ce qu'il ne fait pas",
        blocks: [
          {
            p: "Aperçu ne permet pas de cliquer dans une phrase du PDF pour la corriger. La méthode souvent conseillée, une forme blanche sur l'ancien mot puis une zone de texte par-dessus, est un **overlay** : l'ancien texte reste dans le fichier, sous la forme. Il réapparaît au copier-coller, à la recherche, ou si quelqu'un déplace la forme. Le détail est dans [overlay contre vraie édition](@overlayVsReal).",
          },
          {
            p: "Même chose pour masquer une information : un rectangle noir dessiné dans Aperçu cache le texte à l'écran sans le retirer du fichier. Utilise un vrai [caviardage](@redact).",
          },
        ],
      },
      {
        h2: "Modifier réellement le texte, sans rien installer",
        blocks: [
          {
            steps: [
              "Ouvre cette page dans Safari, Chrome ou Firefox, et dépose ton PDF ci-dessus.",
              "Clique sur la ligne à modifier, tape le nouveau texte, enregistre.",
              "Télécharge le PDF : il arrive dans le dossier **Téléchargements**, et s'ouvre normalement dans Aperçu.",
            ],
          },
          {
            p: "Le zoom au trackpad (pincer avec deux doigts) fonctionne dans l'éditeur, pour vérifier le rendu de près.",
          },
        ],
      },
      {
        h2: "Bon à savoir",
        blocks: [
          {
            list: [
              "**Après Glyph, évite de réenregistrer dans Aperçu** si tu n'as rien d'autre à changer : chaque enregistrement réécrit le fichier à sa façon, sans bénéfice.",
              "**Pour ajouter du texte libre** (une date à côté de la signature), Aperçu reste pratique : une zone de texte ajoutée là où il n'y avait rien ne cache rien.",
              "Glyph traite le fichier en mémoire sur son serveur, puis le supprime : rien n'est installé ni stocké sur ton Mac à part le PDF téléchargé.",
            ],
          },
        ],
      },
    ],
    faq: [
      {
        q: "Peut-on modifier le texte d'un PDF avec Pages ?",
        a: "Non : Pages exporte en PDF, mais n'ouvre pas les PDF pour les modifier.",
      },
      {
        q: "Glyph fonctionne-t-il sur iPhone et iPad ?",
        a: "Oui, dans Safari : la ligne se modifie au toucher, et la page se zoome en pinçant.",
      },
    ],
    related: ["editText", "guideWithoutAcrobat", "redact"],
    updated: "2026-10-08",
  },
  en: {
    nav: "Edit a PDF on a Mac",
    metaTitle: "Edit the text of a PDF on a Mac | Glyph",
    metaDescription:
      "Preview, the Mac's PDF app, annotates but doesn't change the existing text. How to really change a word in a PDF on a Mac, without installing anything.",
    eyebrow: "Guide",
    h1: "Edit the text of a PDF on a Mac",
    intro:
      "Preview, which ships with every Mac, does a lot with a PDF, but it doesn't change the text already in it. Here's what it can do, what it can't, and how to really change a word.",
    widget: "upload",
    intent: "edit",
    sections: [
      {
        h2: "What Preview can do",
        blocks: [
          {
            list: [
              "add a text box, a shape, a note (**Tools** menu, then **Annotate**);",
              "add your signature, captured with the trackpad or the camera;",
              "fill in a form, reorder, delete or merge pages;",
              "show the document's metadata (**Tools**, then **Show Inspector**).",
            ],
          },
        ],
      },
      {
        h2: "What it doesn't do",
        blocks: [
          {
            p: "Preview doesn't let you click into a sentence of the PDF to fix it. The method often suggested, a white shape over the old word and a text box on top, is an **overlay**: the old text stays in the file, under the shape. It comes back on copy-paste, on search, or if someone moves the shape. Details in [overlay vs real editing](@overlayVsReal).",
          },
          {
            p: "Same for hiding information: a black box drawn in Preview hides the text on screen without removing it from the file. Use real [redaction](@redact).",
          },
        ],
      },
      {
        h2: "Really change the text, without installing anything",
        blocks: [
          {
            steps: [
              "Open this page in Safari, Chrome or Firefox, and drop your PDF above.",
              "Click the line to change, type the new text, save.",
              "Download the PDF: it lands in your **Downloads** folder, and opens normally in Preview.",
            ],
          },
          {
            p: "Trackpad zoom (pinch with two fingers) works in the editor, to check the result up close.",
          },
        ],
      },
      {
        h2: "Good to know",
        blocks: [
          {
            list: [
              "**After Glyph, avoid re-saving in Preview** if you have nothing else to change: each save rewrites the file its own way, for no benefit.",
              "**To add free text** (a date next to the signature), Preview is still handy: a text box added where there was nothing hides nothing.",
              "Glyph processes the file in memory on its server, then deletes it: nothing is installed or stored on your Mac apart from the downloaded PDF.",
            ],
          },
        ],
      },
    ],
    faq: [
      {
        q: "Can I edit a PDF's text with Pages?",
        a: "No: Pages exports to PDF, but doesn't open PDFs for editing.",
      },
      {
        q: "Does Glyph work on iPhone and iPad?",
        a: "Yes, in Safari: you edit a line by tapping it, and pinch to zoom the page.",
      },
    ],
    related: ["editText", "guideWithoutAcrobat", "redact"],
    updated: "2026-10-08",
  },
};
