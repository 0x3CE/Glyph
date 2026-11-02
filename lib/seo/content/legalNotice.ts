import { LEGAL_CONTACT_EMAIL, PUBLISHER_NAME, SOURCE_CODE_URL } from "../../site";
import type { LocalizedContent } from "../types";

const email = `[${LEGAL_CONTACT_EMAIL}](mailto:${LEGAL_CONTACT_EMAIL})`;
const domain = "glyph-pdf.com";
const securityTxt = "https://www.glyph-pdf.com/.well-known/security.txt";

// Article 1-1 of the LCEN (loi n° 2004-575 du 21 juin 2004), as amended by
// the SREN law of 21 May 2024: publisher, publication director, host, data
// storage providers. The publisher is a private individual (article 1-1, II).
export const legalNotice: LocalizedContent = {
  fr: {
    nav: "Mentions légales",
    metaTitle: "Mentions légales | Glyph",
    metaDescription:
      "Mentions légales du site Glyph : éditeur, directeur de la publication, hébergeurs, contact et propriété intellectuelle.",
    h1: "Mentions légales",
    intro:
      "Informations prévues par l'article 1-1 de la loi n° 2004-575 du 21 juin 2004 pour la confiance dans l'économie numérique (LCEN).",
    sections: [
      {
        h2: "Éditeur du site",
        blocks: [
          {
            p: PUBLISHER_NAME
              ? `Le site ${domain} (« Glyph ») est édité par **${PUBLISHER_NAME}**, particulier, à titre non professionnel.`
              : `Le site ${domain} (« Glyph ») est édité par un particulier, à titre non professionnel. Conformément à l'article 1-1, II de la LCEN, l'éditeur a choisi de préserver son anonymat : ses éléments d'identification ont été communiqués à l'hébergeur du site, Vercel Inc.`,
          },
          { p: `Contact : ${email}` },
        ],
      },
      {
        h2: "Directeur de la publication",
        blocks: [{ p: PUBLISHER_NAME ?? "L'éditeur du site, joignable à l'adresse ci-dessus." }],
      },
      {
        h2: "Hébergement",
        blocks: [
          {
            list: [
              "**Site web** : Vercel Inc., 440 N Barranca Avenue #4133, Covina, CA 91723, États-Unis. Contact : privacy@vercel.com. [vercel.com](https://vercel.com)",
              "**Traitement des fichiers** (serveur applicatif, prestataire de stockage au sens de l'article 1-1, I, 5° de la LCEN) : Render Services, Inc., 525 Brannan Street, Suite 300, San Francisco, CA 94107, États-Unis. Serveurs situés à Francfort (Allemagne). Contact : support@render.com. [render.com](https://render.com)",
              "**Nom de domaine et DNS** : Cloudflare, Inc., 101 Townsend Street, San Francisco, CA 94107, États-Unis. [cloudflare.com](https://www.cloudflare.com)",
            ],
          },
          {
            p: "Ces prestataires ne publient pas de numéro de téléphone ; ils sont joignables par les adresses indiquées.",
          },
        ],
      },
      {
        h2: "Propriété intellectuelle",
        blocks: [
          {
            p: `Glyph est un logiciel libre : son code source, textes du site compris, est publié sous licence [GNU AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) et disponible sur [GitHub](${SOURCE_CODE_URL}). Les polices de caractères intégrées restent soumises à leurs propres licences (SIL Open Font License, Apache, GPL avec exception de police).`,
          },
          {
            p: "Les documents que vous traitez avec Glyph restent les vôtres : leur envoi ne transfère aucun droit à l'éditeur. Les marques citées sur le site (Adobe Acrobat, Apple, Microsoft Word…) appartiennent à leurs titulaires respectifs, sans lien avec Glyph.",
          },
        ],
      },
      {
        h2: "Données personnelles et cookies",
        blocks: [
          {
            p: "Le traitement de vos données et l'unique cookie déposé par le site sont décrits dans la [politique de confidentialité](@privacy). L'utilisation du service est encadrée par les [conditions d'utilisation](@terms).",
          },
        ],
      },
      {
        h2: "Droit de réponse",
        blocks: [
          {
            p: `Toute personne nommée ou désignée sur le site dispose d'un droit de réponse (article 1-1, III de la LCEN). La demande est à adresser par e-mail à ${email}, dans un délai de trois mois à compter de la mise à disposition du contenu concerné.`,
          },
        ],
      },
      {
        h2: "Signaler un problème",
        blocks: [
          {
            p: `Pour toute question : ${email}. Pour signaler une faille de sécurité, suivez les indications du fichier [security.txt](${securityTxt}).`,
          },
        ],
      },
    ],
    updated: "2026-11-02",
  },
  en: {
    nav: "Legal notice",
    metaTitle: "Legal notice | Glyph",
    metaDescription: "Legal notice for Glyph: publisher, publication director, hosting providers, contact and intellectual property.",
    h1: "Legal notice",
    intro:
      "Information required by article 1-1 of French law no. 2004-575 of 21 June 2004 on confidence in the digital economy (LCEN).",
    sections: [
      {
        h2: "Publisher",
        blocks: [
          {
            p: PUBLISHER_NAME
              ? `The website ${domain} (“Glyph”) is published by **${PUBLISHER_NAME}**, a private individual, on a non-professional basis.`
              : `The website ${domain} (“Glyph”) is published by a private individual, on a non-professional basis. As allowed by article 1-1, II of the LCEN, the publisher has chosen to remain anonymous: their identification details have been provided to the site's host, Vercel Inc.`,
          },
          { p: `Contact: ${email}` },
        ],
      },
      {
        h2: "Publication director",
        blocks: [{ p: PUBLISHER_NAME ?? "The publisher, reachable at the address above." }],
      },
      {
        h2: "Hosting",
        blocks: [
          {
            list: [
              "**Website**: Vercel Inc., 440 N Barranca Avenue #4133, Covina, CA 91723, United States. Contact: privacy@vercel.com. [vercel.com](https://vercel.com)",
              "**File processing** (application server, data storage provider under article 1-1, I, 5° of the LCEN): Render Services, Inc., 525 Brannan Street, Suite 300, San Francisco, CA 94107, United States. Servers located in Frankfurt (Germany). Contact: support@render.com. [render.com](https://render.com)",
              "**Domain name and DNS**: Cloudflare, Inc., 101 Townsend Street, San Francisco, CA 94107, United States. [cloudflare.com](https://www.cloudflare.com)",
            ],
          },
          {
            p: "These providers don't publish a phone number; they can be reached at the addresses given.",
          },
        ],
      },
      {
        h2: "Intellectual property",
        blocks: [
          {
            p: `Glyph is free software: its source code, website texts included, is released under the [GNU AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) license and available on [GitHub](${SOURCE_CODE_URL}). The bundled fonts remain under their own licenses (SIL Open Font License, Apache, GPL with font exception).`,
          },
          {
            p: "The documents you process with Glyph remain yours: sending them transfers no rights to the publisher. Trademarks mentioned on the site (Adobe Acrobat, Apple, Microsoft Word…) belong to their respective owners, with no connection to Glyph.",
          },
        ],
      },
      {
        h2: "Personal data and cookies",
        blocks: [
          {
            p: "How your data is processed, and the single cookie the site sets, are described in the [privacy policy](@privacy). Use of the service is governed by the [terms of use](@terms).",
          },
        ],
      },
      {
        h2: "Right of reply",
        blocks: [
          {
            p: `Anyone named or designated on the site has a right of reply (article 1-1, III of the LCEN). Requests go by email to ${email}, within three months of the content being published.`,
          },
        ],
      },
      {
        h2: "Reporting an issue",
        blocks: [
          {
            p: `For any question: ${email}. To report a security vulnerability, follow the instructions in the [security.txt](${securityTxt}) file.`,
          },
        ],
      },
    ],
    updated: "2026-11-02",
  },
};
