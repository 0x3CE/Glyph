import { LEGAL_CONTACT_EMAIL, SOURCE_CODE_URL } from "../../site";
import type { LocalizedContent } from "../types";

const email = `[${LEGAL_CONTACT_EMAIL}](mailto:${LEGAL_CONTACT_EMAIL})`;

export const terms: LocalizedContent = {
  fr: {
    nav: "Conditions d'utilisation",
    metaTitle: "Conditions d'utilisation | Glyph",
    metaDescription:
      "Les conditions d'utilisation de Glyph : usages autorisés et interdits, traitement des fichiers, limites du service gratuit, responsabilité et droit applicable.",
    h1: "Conditions d'utilisation",
    intro:
      "Glyph est un service gratuit, sans compte, publié sous licence libre [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). En l'utilisant, vous acceptez les conditions ci-dessous.",
    sections: [
      {
        h2: "Objet",
        blocks: [
          {
            p: "Glyph permet de modifier le texte d'un PDF, de le caviarder, d'en retirer les métadonnées, de le signer et de vérifier qu'un PDF caviardé ne cache plus rien. Ces conditions encadrent l'utilisation du site et de ces outils. L'éditeur est identifié dans les [mentions légales](@legalNotice).",
          },
        ],
      },
      {
        h2: "Usages autorisés",
        blocks: [
          {
            p: "Vous pouvez modifier, caviarder, signer ou nettoyer des documents **que vous avez le droit de modifier** : vos propres documents, ou ceux pour lesquels vous disposez de l'accord de leur auteur ou de leur titulaire.",
          },
        ],
      },
      {
        h2: "Usages interdits",
        blocks: [
          {
            list: [
              "fabriquer ou altérer un document pour tromper autrui : fiche de paie, facture, relevé bancaire, diplôme, pièce d'identité, acte officiel, contrat signé par d'autres. Il s'agit d'un faux, puni par la loi (en France, article 441-1 du Code pénal) ;",
              "apposer la signature d'une autre personne ;",
              "utiliser Glyph pour une fraude, une usurpation d'identité ou toute autre activité illégale ;",
              "traiter des documents en violation des droits de tiers (droit d'auteur, vie privée, secret des correspondances) ;",
              "chercher à perturber le service, à contourner ses limites ou à accéder aux documents d'autres utilisateurs.",
            ],
          },
        ],
      },
      {
        h2: "Vos fichiers",
        blocks: [
          {
            p: "Vos fichiers sont traités sur le serveur de Glyph, **en mémoire uniquement**, jamais écrits sur disque, et supprimés à la fermeture de l'onglet ou après 30 minutes d'inactivité. Ils ne sont ni consultés, ni conservés, ni réutilisés. Le détail figure dans la [politique de confidentialité](@privacy).",
          },
          {
            p: "Vos documents restent les vôtres : leur envoi ne confère aucun droit à l'éditeur.",
          },
        ],
      },
      {
        h2: "Disponibilité et limites",
        blocks: [
          {
            p: "Le service est fourni gratuitement, sans engagement de disponibilité. Il peut être interrompu, notamment pour maintenance, et évoluer à tout moment. Pour le garder disponible pour tous, certaines limites s'appliquent :",
          },
          {
            list: [
              "fichiers de 20 Mo au plus, non protégés par mot de passe ;",
              "10 documents ouverts simultanément au plus par visiteur ;",
              "documents supprimés après 30 minutes d'inactivité, ou au redémarrage du serveur : téléchargez votre résultat avant de quitter la page.",
            ],
          },
        ],
      },
      {
        h2: "Responsabilité",
        blocks: [
          {
            p: "Glyph est fourni « en l'état », sans garantie. Vérifiez toujours le document obtenu avant de l'utiliser : le rendu peut différer légèrement de l'original (police de remplacement, fond coloré effacé), et une vérification automatique ne remplace pas une relecture. Vous restez seul responsable des documents que vous traitez et de leur usage.",
          },
          {
            p: "Dans les limites permises par la loi, l'éditeur ne saurait être tenu responsable d'un dommage résultant de l'utilisation du service, de son indisponibilité ou de la perte d'un document non téléchargé.",
          },
        ],
      },
      {
        h2: "Propriété intellectuelle",
        blocks: [
          {
            p: `Le code source de Glyph est publié sous licence [GNU AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) et disponible sur [GitHub](${SOURCE_CODE_URL}) : vous pouvez l'utiliser, l'étudier, le modifier et le redistribuer dans le respect de cette licence.`,
          },
        ],
      },
      {
        h2: "Modification des conditions",
        blocks: [
          {
            p: "Ces conditions peuvent être modifiées à tout moment. La version applicable est celle publiée sur cette page au moment de votre utilisation ; sa date de mise à jour figure en haut de la page.",
          },
        ],
      },
      {
        h2: "Droit applicable",
        blocks: [
          {
            p: "Ces conditions sont régies par le droit français. En cas de litige, une solution amiable sera recherchée en priorité ; à défaut, les tribunaux français seront compétents, sous réserve des règles impératives protégeant les consommateurs.",
          },
        ],
      },
      {
        h2: "Contact",
        blocks: [
          {
            p: `Pour toute question sur ces conditions : ${email}.`,
          },
        ],
      },
    ],
    updated: "2026-11-02",
  },
  en: {
    nav: "Terms of use",
    metaTitle: "Terms of use | Glyph",
    metaDescription:
      "Glyph's terms of use: permitted and forbidden uses, file handling, limits of the free service, liability and governing law.",
    h1: "Terms of use",
    intro:
      "Glyph is a free service, with no account, released under the [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) open-source license. By using it, you accept the terms below.",
    sections: [
      {
        h2: "Purpose",
        blocks: [
          {
            p: "Glyph lets you edit the text of a PDF, redact it, remove its metadata, sign it, and check that a redacted PDF no longer hides anything. These terms govern the use of the site and these tools. The publisher is identified in the [legal notice](@legalNotice).",
          },
        ],
      },
      {
        h2: "Permitted use",
        blocks: [
          {
            p: "You may edit, redact, sign or clean up documents **that you have the right to change**: your own documents, or ones whose author or owner has agreed.",
          },
        ],
      },
      {
        h2: "Forbidden use",
        blocks: [
          {
            list: [
              "creating or altering a document to deceive others: a payslip, an invoice, a bank statement, a diploma, an ID, an official record, a contract signed by others. That is forgery, and illegal;",
              "placing someone else's signature;",
              "using Glyph for fraud, identity theft or any other illegal activity;",
              "processing documents in breach of third parties' rights (copyright, privacy, confidentiality of correspondence);",
              "trying to disrupt the service, get around its limits, or access other users' documents.",
            ],
          },
        ],
      },
      {
        h2: "Your files",
        blocks: [
          {
            p: "Your files are processed on Glyph's server, **in memory only**, never written to disk, and deleted when you close the tab or after 30 minutes of inactivity. They are never viewed, kept or reused. Details are in the [privacy policy](@privacy).",
          },
          {
            p: "Your documents remain yours: sending them gives the publisher no rights over them.",
          },
        ],
      },
      {
        h2: "Availability and limits",
        blocks: [
          {
            p: "The service is provided free of charge, with no availability commitment. It may be interrupted, for maintenance in particular, and change at any time. To keep it available to everyone, some limits apply:",
          },
          {
            list: [
              "files of 20 MB at most, not password-protected;",
              "at most 10 documents open at once per visitor;",
              "documents are deleted after 30 minutes of inactivity, or when the server restarts: download your result before leaving the page.",
            ],
          },
        ],
      },
      {
        h2: "Liability",
        blocks: [
          {
            p: "Glyph is provided “as is”, without warranty. Always check the resulting document before using it: it may differ slightly from the original (replacement font, erased colored background), and an automatic check doesn't replace reading it again. You alone remain responsible for the documents you process and how you use them.",
          },
          {
            p: "To the extent permitted by law, the publisher can't be held liable for damage resulting from the use of the service, its unavailability, or the loss of a document that wasn't downloaded.",
          },
        ],
      },
      {
        h2: "Intellectual property",
        blocks: [
          {
            p: `Glyph's source code is released under the [GNU AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) license and available on [GitHub](${SOURCE_CODE_URL}): you may use, study, modify and redistribute it under that license.`,
          },
        ],
      },
      {
        h2: "Changes to these terms",
        blocks: [
          {
            p: "These terms may change at any time. The applicable version is the one published on this page when you use the service; its update date is shown at the top of the page.",
          },
        ],
      },
      {
        h2: "Governing law",
        blocks: [
          {
            p: "These terms are governed by French law. In case of dispute, an amicable solution will be sought first; failing that, the French courts will have jurisdiction, subject to mandatory rules protecting consumers.",
          },
        ],
      },
      {
        h2: "Contact",
        blocks: [
          {
            p: `For any question about these terms: ${email}.`,
          },
        ],
      },
    ],
    updated: "2026-11-02",
  },
};
