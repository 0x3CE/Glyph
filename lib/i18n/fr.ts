// French copy. Its shape is the `Dictionary` type every other locale must
// match (lib/i18n/index.ts), so a key missing from a translation fails the
// typecheck instead of rendering blank.

export const fr = {
  meta: {
    title: "Glyph — l'éditeur PDF qui modifie vraiment le texte",
    description:
      "Modifie le texte d'un PDF pour de vrai : l'ancien texte est supprimé, pas caché sous un rectangle. Police d'origine, recherche et copier-coller intacts.",
    siteDescription:
      "Glyph réécrit le contenu d'un PDF au lieu de le recouvrir : l'ancien texte est supprimé, le nouveau réinséré avec la police d'origine.",
    keywords: ["éditeur PDF", "modifier texte PDF", "éditer PDF en ligne", "PDF sans overlay", "réécrire PDF"],
    ogDescription: "Le texte d'origine est supprimé du PDF, pas recouvert. Édition réelle, pas un calque.",
    ogLocale: "fr_FR",
    ogImageAlt: "Glyph : modifie le texte d'un PDF, pour de vrai.",
    organizationDescription: "Éditeur PDF qui réécrit le contenu du document au lieu de le recouvrir.",
    softwareDescription:
      "Éditeur PDF qui réécrit le contenu du document (suppression réelle du texte d'origine, réinsertion avec la police d'origine) au lieu de le recouvrir d'un calque.",
    priceCurrency: "EUR",
    editorTitle: "Éditeur",
    editorDescription: "Ouvre un PDF et modifie son texte directement.",
  },
  nav: {
    openEditor: "Ouvrir l'éditeur",
    coffee: "Offrir un café",
    coffeeAria: "Offrir un café (Buy Me a Coffee)",
  },
  switcher: {
    // Label of the link to the OTHER language, written in that language.
    label: "English",
    shortLabel: "EN",
    ariaLabel: "Switch to English",
  },
  hero: {
    eyebrow: "Édition PDF sans overlay",
    titleLine1: "Modifie le texte d'un PDF.",
    titleLine2Before: "Pour de ",
    titleLine2Accent: "vrai",
    titleLine2After: ".",
    subtitle:
      "Glyph réécrit le contenu du PDF au lieu de le recouvrir : le texte d'origine est supprimé, le nouveau est réinséré avec la police d'origine quand c'est possible — recherche et copier-coller inclus.",
    howItWorks: "Comment ça marche",
  },
  problem: {
    anchor: "le-probleme",
    label: "Le problème",
    title: "Les autres éditeurs PDF ne modifient pas le texte — ils le cachent",
    lede: "La méthode classique : recouvrir l'ancien texte d'un rectangle blanc et écrire le nouveau par-dessus. Ça a l'air correct à l'écran, mais le document reste cassé.",
    badTitle: "Overlay (la méthode classique)",
    badText:
      "Le texte d'origine reste présent sous le cache : recherche et copier-coller renvoient encore l'ancienne valeur, et n'importe qui peut la retrouver en retirant le cache.",
    goodText:
      "Les glyphes d'origine sont supprimés du flux du document et remplacés par du vrai texte, à la bonne position, avec la bonne police quand c'est possible. Rien à cacher : il n'y a plus rien en dessous.",
  },
  how: {
    anchor: "comment-ca-marche",
    label: "Comment ça marche",
    title: "Quatre étapes, aucune trace de l'ancien texte",
    steps: [
      { title: "Dépose ton PDF", text: "Traitement en mémoire, rien n'est écrit sur disque côté serveur." },
      { title: "Clique sur une ligne", text: "Chaque ligne s'édite à part : ses voisines ne sont jamais touchées." },
      {
        title: "Le contenu est réécrit",
        text: "Suppression réelle des anciens glyphes, réinsertion avec la police d'origine si possible.",
      },
      { title: "Télécharge", text: "Un PDF où le texte modifié est du vrai texte — cherchable, copiable, imprimable." },
    ],
  },
  features: {
    anchor: "fonctionnalites",
    label: "Fonctionnalités",
    title: "Pensé pour la fidélité, pas pour l'apparence",
    items: [
      {
        title: "Suppression réelle du contenu",
        text: "Aucun rectangle de couverture — les anciens caractères sont retirés du document.",
      },
      {
        title: "Police d'origine préservée",
        text: "Réutilisée quand c'est possible, sinon la même famille parmi 240 polices libres. Tu es prévenu quand ce n'est pas l'originale.",
      },
      {
        title: "Formatage conservé",
        text: "Un mot en gras ou en italique garde son style quand tu modifies le reste de la ligne.",
      },
      {
        title: "Tableaux respectés",
        text: "Chaque cellule est éditée indépendamment, sans jamais déborder sur ses voisines.",
      },
      {
        title: "Signature",
        text: "Dessine-la ou importe-la (PDF, PNG, JPG), puis place-la où tu veux. Une signature PDF reste vectorielle.",
      },
      { title: "Annuler / rétablir", text: "Annule ou rétablis tes modifications pendant toute la session d'édition." },
    ],
  },
  faq: {
    label: "FAQ",
    title: "Questions fréquentes",
    items: [
      {
        q: "Le texte modifié reste-t-il cherchable et copiable ?",
        a: "Oui. Glyph supprime réellement les anciens caractères du flux du PDF et réinsère le nouveau texte comme du vrai texte — pas une image, pas un calque. Recherche, sélection et copier-coller fonctionnent normalement.",
      },
      {
        q: "Mes fichiers sont-ils stockés quelque part ?",
        a: "Non. Chaque PDF est gardé en mémoire le temps de la session d'édition, jamais écrit sur disque côté serveur, et supprimé dès que tu fermes l'onglet (ou après 30 minutes d'inactivité).",
      },
      {
        q: "Est-ce que la police d'origine est toujours conservée ?",
        a: "Quand c'est possible, oui — Glyph réutilise la police d'origine du document. Beaucoup de PDF (Word, imprimantes virtuelles) embarquent des polices en sous-ensemble qui ne couvrent pas tous les caractères ; dans ce cas Glyph réutilise la même famille depuis son catalogue d'environ 240 polices libres (Roboto, Montserrat, Lato…), ou un équivalent aux mêmes métriques pour les polices propriétaires (Calibri, Arial, Times…), et te prévient quand le résultat n'est pas exactement la police d'origine.",
      },
      {
        q: "Ça marche sur des tableaux ?",
        a: "Oui. Chaque ligne est éditée séparément, cellules de tableau comprises : seul le texte cliqué change, et Glyph n'efface jamais rien dans les cellules voisines, même quand elles se touchent.",
      },
      {
        q: "Y a-t-il des limites ?",
        a: "Quelques-unes. Les PDF jusqu'à 20 Mo, sans mot de passe. L'édition se fait ligne par ligne : une adresse sur trois lignes se modifie en trois clics. Et un fond coloré derrière le texte modifié est effacé avec lui.",
      },
      { q: "Faut-il un compte pour l'utiliser ?", a: "Non, l'éditeur est utilisable directement." },
    ],
  },
  support: {
    anchor: "soutenir",
    label: "Soutenir le projet",
    title: "Gratuit, open source, sans pub ni traçage",
    text: "Glyph est développé sur mon temps libre. S'il t'a évité une galère avec un PDF, tu peux m'offrir un café : ça aide à payer l'hébergement et à continuer de l'améliorer.",
  },
  cta: {
    title: "Prêt à modifier un PDF pour de vrai ?",
    text: "Aucune inscription nécessaire.",
  },
  footer: {
    tagline: "Édition PDF réelle — pas un calque.",
  },
  notFound: {
    title: "Page introuvable",
    text: "Cette page n'existe pas ou plus.",
    back: "Retour à l'accueil",
  },
  editor: {
    openPdf: "Ouvrir un PDF",
    changeFile: "Changer de fichier",
    // Short labels for narrow screens.
    openShort: "Ouvrir",
    signatureShort: "Signer",
    zoomIn: "Zoomer",
    zoomOut: "Dézoomer",
    undo: "Annuler",
    redo: "Rétablir",
    signature: "Signature",
    download: "Télécharger",
    downloadName: (fileName: string) => `modifie-${fileName}`,
    defaultDownloadName: "document-modifie.pdf",
    loadError: "Impossible de charger ce PDF. Le fichier est peut-être corrompu ou protégé.",
    substitutionNotice: "Police d'origine indisponible pour ce texte — une police de remplacement a été utilisée.",
    dropTitle: "Glisse un PDF ici",
    dropOr: "ou",
    chooseFile: "Choisir un fichier",
    emptyHint: "Rien n'est stocké : le fichier est traité en mémoire le temps de la session.",
    previousPage: "Page précédente",
    nextPage: "Page suivante",
    dropToReplace: "Déposer pour remplacer le document",
    save: "Enregistrer",
    saving: "Enregistrement…",
    cancel: "Annuler",
    confirm: "Valider",
    signatureAlt: "Signature",
  },
  signatureModal: {
    title: "Ajouter une signature",
    close: "Fermer",
    draw: "Dessiner",
    upload: "Importer un fichier",
    clear: "Effacer",
    useDrawing: "Utiliser cette signature",
    chooseFile: "Choisir un fichier (PDF, PNG, JPG)",
    useFile: "Utiliser ce fichier",
    unsupportedFile: "Format non supporté — PDF, PNG ou JPG uniquement.",
  },
};
