import type { LocalizedContent } from "../types";

export const terms: LocalizedContent = {
  fr: {
    nav: "Conditions d'utilisation",
    metaTitle: "Conditions d'utilisation | Glyph",
    metaDescription:
      "Les règles d'utilisation de Glyph : modifier uniquement des documents que tu as le droit de modifier, et ce qu'il advient de tes fichiers.",
    h1: "Conditions d'utilisation",
    intro:
      "Glyph est un projet open source, gratuit et sans compte. En l'utilisant, tu acceptes les règles ci-dessous. Elles sont courtes : lis-les.",
    sections: [
      {
        h2: "Ce que tu peux faire",
        blocks: [
          {
            p: "Modifier, caviarder, signer ou nettoyer des PDF **que tu as le droit de modifier** : tes propres documents, ou ceux pour lesquels tu as l'accord de leur auteur.",
          },
        ],
      },
      {
        h2: "Ce qui est interdit",
        blocks: [
          {
            list: [
              "fabriquer ou altérer un document pour tromper quelqu'un : fiche de paie, facture, relevé bancaire, diplôme, pièce d'identité, acte officiel, contrat signé par d'autres. C'est un faux, puni par la loi (en France, article 441-1 du Code pénal) ;",
              "utiliser Glyph pour une fraude, une usurpation d'identité ou tout autre usage illégal ;",
              "chercher à perturber le service ou à accéder aux documents d'autres utilisateurs.",
            ],
          },
        ],
      },
      {
        h2: "Ce qu'il advient de tes fichiers",
        blocks: [
          {
            p: "Le traitement n'a pas lieu dans ton navigateur : ton PDF est envoyé en HTTPS au serveur de Glyph (hébergé chez Render), traité **en mémoire uniquement**, jamais écrit sur disque, et supprimé à la fermeture de l'onglet ou après 30 minutes d'inactivité. Il n'est ni conservé, ni analysé, ni réutilisé.",
          },
          {
            p: "Le site (hébergé chez Vercel) mesure de façon anonyme la vitesse de chargement des pages (Vercel Speed Insights), sans cookie ni suivi des visiteurs. Ton choix de langue est retenu dans un cookie de préférence.",
          },
        ],
      },
      {
        h2: "Sans garantie",
        blocks: [
          {
            p: "Glyph est fourni tel quel, gratuitement. Vérifie toujours le document obtenu avant de l'utiliser : le rendu peut différer légèrement de l'original (police de remplacement, fond coloré effacé). Tu restes responsable des documents que tu modifies et de leur usage.",
          },
          {
            p: "Pour une question ou un problème : [le dépôt GitHub du projet](https://github.com/0x3CE/Glyph).",
          },
        ],
      },
    ],
    updated: "2026-10-08",
  },
  en: {
    nav: "Terms of use",
    metaTitle: "Terms of use | Glyph",
    metaDescription:
      "The rules for using Glyph: only edit documents you have the right to edit, and what happens to your files.",
    h1: "Terms of use",
    intro:
      "Glyph is an open-source project, free and with no account. By using it, you accept the rules below. They're short: read them.",
    sections: [
      {
        h2: "What you can do",
        blocks: [
          {
            p: "Edit, redact, sign or clean up PDFs **that you have the right to change**: your own documents, or ones whose author agreed.",
          },
        ],
      },
      {
        h2: "What is forbidden",
        blocks: [
          {
            list: [
              "creating or altering a document to deceive someone: a payslip, an invoice, a bank statement, a diploma, an ID, an official record, a contract signed by others. That is forgery, and illegal;",
              "using Glyph for fraud, identity theft or any other illegal purpose;",
              "trying to disrupt the service or to access other users' documents.",
            ],
          },
        ],
      },
      {
        h2: "What happens to your files",
        blocks: [
          {
            p: "Processing doesn't happen in your browser: your PDF is sent over HTTPS to Glyph's server (hosted by Render), processed **in memory only**, never written to disk, and deleted when you close the tab or after 30 minutes of inactivity. It is not kept, analysed or reused.",
          },
          {
            p: "The website (hosted by Vercel) anonymously measures page-load speed (Vercel Speed Insights), with no cookie and no visitor tracking. Your language choice is remembered in a preference cookie.",
          },
        ],
      },
      {
        h2: "No warranty",
        blocks: [
          {
            p: "Glyph is provided as is, for free. Always check the resulting document before using it: it may differ slightly from the original (replacement font, erased colored background). You remain responsible for the documents you edit and how you use them.",
          },
          {
            p: "For questions or issues: [the project's GitHub repository](https://github.com/0x3CE/Glyph).",
          },
        ],
      },
    ],
    updated: "2026-10-08",
  },
};
