import { LEGAL_CONTACT_EMAIL, PUBLISHER_NAME } from "../../site";
import type { LocalizedContent } from "../types";

const email = `[${LEGAL_CONTACT_EMAIL}](mailto:${LEGAL_CONTACT_EMAIL})`;

// GDPR articles 13 and 14: who processes what, why, on which legal basis,
// for how long, who receives it, transfers, rights. Every statement below
// must match what the code does (backend/app/documents.py, main.py,
// app/[lang]/layout.tsx, components/LanguageSwitcher.tsx): update both
// together.
export const privacy: LocalizedContent = {
  fr: {
    nav: "Confidentialité",
    metaTitle: "Politique de confidentialité | Glyph",
    metaDescription:
      "Quelles données Glyph traite, pourquoi, combien de temps, et vos droits : fichiers traités en mémoire puis supprimés, pas de compte, pas de cookie de suivi.",
    h1: "Politique de confidentialité",
    intro:
      "Cette politique décrit les données traitées lorsque vous utilisez Glyph, conformément au règlement général sur la protection des données (RGPD) et à la loi Informatique et Libertés.",
    sections: [
      {
        h2: "En bref",
        blocks: [
          {
            list: [
              "Pas de compte, pas de publicité, pas de cookie de suivi.",
              "Vos fichiers sont traités **en mémoire uniquement**, jamais écrits sur disque, et supprimés au plus tard 30 minutes après votre dernière action.",
              "Ils ne sont ni consultés, ni analysés à d'autres fins, ni réutilisés, notamment pour entraîner une intelligence artificielle.",
              "La mesure d'audience est anonyme et sans cookie.",
            ],
          },
        ],
      },
      {
        h2: "Responsable du traitement",
        blocks: [
          {
            p: PUBLISHER_NAME
              ? `Le responsable du traitement est **${PUBLISHER_NAME}**, éditeur de Glyph, à titre non professionnel. Contact : ${email}.`
              : `Le responsable du traitement est l'éditeur de Glyph, un particulier agissant à titre non professionnel (voir les [mentions légales](@legalNotice)). Contact : ${email}.`,
          },
          { p: "Glyph n'est pas tenu de désigner un délégué à la protection des données." },
        ],
      },
      {
        h2: "Les données traitées",
        blocks: [
          { p: "**1. Les fichiers que vous envoyez** (PDF, image de signature)." },
          {
            list: [
              "**Finalité** : fournir le service demandé (modification, caviardage, nettoyage, signature, vérification).",
              "**Base légale** : l'exécution du service que vous demandez en acceptant les [conditions d'utilisation](@terms) (article 6.1.b du RGPD).",
              "**Conservation** : en mémoire vive du serveur uniquement, jamais sur disque. Le fichier et ses versions intermédiaires (pour annuler une modification) sont supprimés à la fermeture de l'onglet, ou après 30 minutes d'inactivité. Le vérificateur de PDF caviardé analyse le fichier puis l'oublie immédiatement, sans le conserver.",
              "Vos documents peuvent contenir des données personnelles, les vôtres ou celles d'autres personnes. Vous restez responsable de leur utilisation ; Glyph se contente de les traiter à votre demande.",
            ],
          },
          { p: "**2. Votre adresse IP, pour limiter les abus.**" },
          {
            list: [
              "**Finalité** : limiter chaque visiteur à 10 documents ouverts simultanément, pour garantir la disponibilité du service à tous.",
              "**Base légale** : l'intérêt légitime de l'éditeur à protéger le service contre les abus (article 6.1.f du RGPD).",
              "**Forme et conservation** : Glyph ne conserve pas l'adresse IP elle-même, mais une empreinte non réversible (HMAC-SHA-256), calculée avec une clé aléatoire renouvelée à chaque redémarrage du serveur. Elle reste en mémoire tant que vos documents sont ouverts, soit 30 minutes au plus après votre dernière action.",
            ],
          },
          { p: "**3. Les journaux techniques des hébergeurs.**" },
          {
            list: [
              "**Finalité** : faire fonctionner et sécuriser le site (diagnostic des erreurs, détection des attaques).",
              "**Données** : date et heure, page ou adresse demandée, adresse IP, type de navigateur.",
              "**Base légale** : l'intérêt légitime de l'éditeur à assurer la sécurité du service (article 6.1.f du RGPD).",
              "**Conservation** : durée limitée fixée par les hébergeurs (Vercel, Render). L'éditeur ne les consulte qu'en cas d'incident.",
            ],
          },
          { p: "**4. La mesure d'audience et de performance.**" },
          {
            list: [
              "**Outils** : Vercel Web Analytics et Vercel Speed Insights.",
              "**Finalité** : connaître la fréquentation des pages et leur vitesse de chargement, pour améliorer le site.",
              "**Données** : page visitée, site de provenance, pays, région et ville, système d'exploitation, navigateur, type d'appareil, mesures de vitesse. Les statistiques sont agrégées et anonymes.",
              "**Sans cookie** : un visiteur est reconnu par une empreinte calculée à partir de la requête, valable 24 heures et non conservée au-delà. Elle ne permet pas de vous suivre d'un jour à l'autre, ni d'un site à l'autre.",
              "**Base légale** : l'intérêt légitime de l'éditeur à mesurer l'audience de son site (article 6.1.f du RGPD).",
            ],
          },
          { p: "**5. Les messages que vous nous envoyez.**" },
          {
            list: [
              "**Données** : votre adresse e-mail et le contenu de votre message.",
              "**Finalité** : vous répondre (question, exercice de vos droits, droit de réponse).",
              "**Base légale** : l'intérêt légitime de l'éditeur à traiter vos demandes, et le respect de ses obligations légales pour l'exercice de vos droits (articles 6.1.f et 6.1.c du RGPD).",
              "**Conservation** : le temps de traiter votre demande, puis un an au plus après le dernier échange.",
            ],
          },
        ],
      },
      {
        h2: "Cookies",
        blocks: [
          {
            p: "Glyph dépose **un seul cookie**, « glyph-lang », uniquement si vous utilisez le bouton de changement de langue. Il retient votre choix (« fr » ou « en ») pendant 12 mois. Strictement nécessaire à la fonctionnalité que vous demandez, il est exempté de consentement (article 82 de la loi Informatique et Libertés).",
          },
          {
            p: "Aucun cookie publicitaire, de suivi ou de mesure d'audience n'est utilisé : c'est pourquoi le site n'affiche pas de bandeau de consentement.",
          },
        ],
      },
      {
        h2: "Destinataires et sous-traitants",
        blocks: [
          {
            p: "Vos données ne sont ni vendues, ni louées, ni cédées. Seuls y accèdent, pour le compte de l'éditeur, les prestataires techniques suivants :",
          },
          {
            list: [
              "**Vercel Inc.** (États-Unis) : hébergement du site, relais chiffré des fichiers vers le serveur de traitement, mesure d'audience.",
              "**Render Services, Inc.** (États-Unis) : traitement des fichiers, sur des serveurs situés à **Francfort (Allemagne)**.",
              "**Cloudflare, Inc.** (États-Unis) : nom de domaine et DNS. Cloudflare ne voit pas le contenu de vos fichiers.",
            ],
          },
          {
            p: "Les coordonnées complètes de ces prestataires figurent dans les [mentions légales](@legalNotice).",
          },
        ],
      },
      {
        h2: "Transferts hors de l'Union européenne",
        blocks: [
          {
            p: "Le traitement de vos fichiers a lieu dans l'Union européenne (Francfort). En revanche, les données de navigation traitées par Vercel (journaux techniques, mesure d'audience) et le relais de vos fichiers peuvent transiter par les États-Unis. Vercel et Render sont certifiés au titre du **Data Privacy Framework UE–États-Unis**, reconnu par la décision d'adéquation de la Commission européenne du 10 juillet 2023.",
          },
        ],
      },
      {
        h2: "Sécurité",
        blocks: [
          {
            list: [
              "Échanges chiffrés (HTTPS) entre votre navigateur, Vercel et le serveur de traitement.",
              "Fichiers conservés en mémoire uniquement, jamais écrits sur disque.",
              "Chaque opération sur un PDF s'exécute dans un processus isolé, aux ressources limitées, détruit juste après.",
              "Chaque document n'est accessible que par un identifiant aléatoire de 122 bits, connu de votre seul navigateur.",
            ],
          },
        ],
      },
      {
        h2: "Vos droits",
        blocks: [
          {
            p: "Vous disposez d'un droit d'accès, de rectification, d'effacement, de limitation du traitement, d'opposition et, le cas échéant, de portabilité de vos données (articles 15 à 21 du RGPD), ainsi que du droit de définir des directives relatives à leur sort après votre décès (article 85 de la loi Informatique et Libertés).",
          },
          {
            p: `Pour les exercer, écrivez à ${email}. Une réponse vous sera apportée dans un délai d'un mois. Glyph ne tenant ni compte ni fichier, il est le plus souvent impossible de vous identifier dans les données traitées ; elles sont de toute façon supprimées dans les 30 minutes (article 11 du RGPD).`,
          },
          {
            p: "Si vous estimez que vos droits ne sont pas respectés, vous pouvez adresser une réclamation à la CNIL : [cnil.fr/fr/plaintes](https://www.cnil.fr/fr/plaintes), ou par courrier au 3 place de Fontenoy, TSA 80715, 75334 Paris Cedex 07.",
          },
        ],
      },
      {
        h2: "Liens vers d'autres sites",
        blocks: [
          {
            p: "Le site renvoie vers GitHub (code source, signalements) et Buy Me a Coffee (soutien au projet). Ces services appliquent leur propre politique de confidentialité, sur laquelle Glyph n'a pas de prise.",
          },
        ],
      },
      {
        h2: "Modifications",
        blocks: [
          {
            p: "Cette politique peut évoluer, notamment en cas de changement d'hébergeur. La date de mise à jour figure en haut de la page.",
          },
        ],
      },
    ],
    updated: "2026-11-02",
  },
  en: {
    nav: "Privacy",
    metaTitle: "Privacy policy | Glyph",
    metaDescription:
      "What data Glyph processes, why, for how long, and your rights: files processed in memory then deleted, no account, no tracking cookie.",
    h1: "Privacy policy",
    intro:
      "This policy describes the data processed when you use Glyph, in accordance with the EU General Data Protection Regulation (GDPR) and the French Data Protection Act.",
    sections: [
      {
        h2: "In short",
        blocks: [
          {
            list: [
              "No account, no ads, no tracking cookie.",
              "Your files are processed **in memory only**, never written to disk, and deleted at most 30 minutes after your last action.",
              "They are never viewed, analysed for any other purpose or reused, including to train artificial intelligence.",
              "Audience measurement is anonymous and cookie-free.",
            ],
          },
        ],
      },
      {
        h2: "Data controller",
        blocks: [
          {
            p: PUBLISHER_NAME
              ? `The data controller is **${PUBLISHER_NAME}**, publisher of Glyph, on a non-professional basis. Contact: ${email}.`
              : `The data controller is the publisher of Glyph, a private individual acting on a non-professional basis (see the [legal notice](@legalNotice)). Contact: ${email}.`,
          },
          { p: "Glyph is not required to appoint a data protection officer." },
        ],
      },
      {
        h2: "Data processed",
        blocks: [
          { p: "**1. The files you send** (PDF, signature image)." },
          {
            list: [
              "**Purpose**: providing the service you request (editing, redaction, clean-up, signature, checking).",
              "**Legal basis**: performing the service you request by accepting the [terms of use](@terms) (GDPR article 6.1.b).",
              "**Retention**: in the server's memory only, never on disk. The file and its intermediate versions (to undo a change) are deleted when you close the tab, or after 30 minutes of inactivity. The redacted PDF checker analyses the file then forgets it immediately, without keeping it.",
              "Your documents may contain personal data, yours or other people's. You remain responsible for how you use them; Glyph only processes them at your request.",
            ],
          },
          { p: "**2. Your IP address, to prevent abuse.**" },
          {
            list: [
              "**Purpose**: limiting each visitor to 10 documents open at once, to keep the service available to everyone.",
              "**Legal basis**: the publisher's legitimate interest in protecting the service against abuse (GDPR article 6.1.f).",
              "**Form and retention**: Glyph doesn't keep the IP address itself, but a non-reversible fingerprint (HMAC-SHA-256), computed with a random key renewed every time the server restarts. It stays in memory while your documents are open, at most 30 minutes after your last action.",
            ],
          },
          { p: "**3. The hosting providers' technical logs.**" },
          {
            list: [
              "**Purpose**: running and securing the site (diagnosing errors, detecting attacks).",
              "**Data**: date and time, page or address requested, IP address, browser type.",
              "**Legal basis**: the publisher's legitimate interest in securing the service (GDPR article 6.1.f).",
              "**Retention**: a limited period set by the hosting providers (Vercel, Render). The publisher only looks at them when there is an incident.",
            ],
          },
          { p: "**4. Audience and performance measurement.**" },
          {
            list: [
              "**Tools**: Vercel Web Analytics and Vercel Speed Insights.",
              "**Purpose**: knowing how pages are visited and how fast they load, to improve the site.",
              "**Data**: page visited, referring site, country, region and city, operating system, browser, device type, speed measurements. Statistics are aggregated and anonymous.",
              "**No cookie**: a visitor is recognised by a fingerprint computed from the request, valid for 24 hours and not kept beyond. It can't be used to follow you from one day to the next, or from one site to another.",
              "**Legal basis**: the publisher's legitimate interest in measuring the site's audience (GDPR article 6.1.f).",
            ],
          },
          { p: "**5. The messages you send us.**" },
          {
            list: [
              "**Data**: your email address and the content of your message.",
              "**Purpose**: answering you (questions, exercising your rights, right of reply).",
              "**Legal basis**: the publisher's legitimate interest in handling your requests, and compliance with legal obligations when you exercise your rights (GDPR articles 6.1.f and 6.1.c).",
              "**Retention**: the time needed to handle your request, then at most one year after the last exchange.",
            ],
          },
        ],
      },
      {
        h2: "Cookies",
        blocks: [
          {
            p: "Glyph sets **a single cookie**, “glyph-lang”, only if you use the language switch. It remembers your choice (“fr” or “en”) for 12 months. Strictly necessary for the feature you ask for, it is exempt from consent (article 82 of the French Data Protection Act).",
          },
          {
            p: "No advertising, tracking or audience-measurement cookie is used: that's why the site shows no consent banner.",
          },
        ],
      },
      {
        h2: "Recipients and processors",
        blocks: [
          {
            p: "Your data is never sold, rented or transferred. Only the following technical providers access it, on the publisher's behalf:",
          },
          {
            list: [
              "**Vercel Inc.** (United States): website hosting, encrypted relay of files to the processing server, audience measurement.",
              "**Render Services, Inc.** (United States): file processing, on servers located in **Frankfurt (Germany)**.",
              "**Cloudflare, Inc.** (United States): domain name and DNS. Cloudflare doesn't see the content of your files.",
            ],
          },
          {
            p: "These providers' full details are in the [legal notice](@legalNotice).",
          },
        ],
      },
      {
        h2: "Transfers outside the European Union",
        blocks: [
          {
            p: "Your files are processed in the European Union (Frankfurt). Browsing data processed by Vercel (technical logs, audience measurement) and the relay of your files may however go through the United States. Vercel and Render are certified under the **EU–US Data Privacy Framework**, recognised by the European Commission's adequacy decision of 10 July 2023.",
          },
        ],
      },
      {
        h2: "Security",
        blocks: [
          {
            list: [
              "Encrypted connections (HTTPS) between your browser, Vercel and the processing server.",
              "Files kept in memory only, never written to disk.",
              "Every operation on a PDF runs in an isolated, resource-limited process, destroyed right after.",
              "Each document can only be reached through a random 122-bit identifier, known to your browser alone.",
            ],
          },
        ],
      },
      {
        h2: "Your rights",
        blocks: [
          {
            p: "You have the right to access, rectify and erase your data, to restrict or object to its processing and, where applicable, to data portability (GDPR articles 15 to 21), as well as the right to set instructions about your data after your death (article 85 of the French Data Protection Act).",
          },
          {
            p: `To exercise them, write to ${email}. You will get an answer within one month. As Glyph keeps no account and no file, it is usually impossible to identify you in the data processed; it is deleted within 30 minutes anyway (GDPR article 11).`,
          },
          {
            p: "If you believe your rights are not respected, you can lodge a complaint with your data protection authority, in France the CNIL: [cnil.fr/fr/plaintes](https://www.cnil.fr/fr/plaintes), or by post at 3 place de Fontenoy, TSA 80715, 75334 Paris Cedex 07, France.",
          },
        ],
      },
      {
        h2: "Links to other sites",
        blocks: [
          {
            p: "The site links to GitHub (source code, reports) and Buy Me a Coffee (supporting the project). These services apply their own privacy policies, over which Glyph has no control.",
          },
        ],
      },
      {
        h2: "Changes",
        blocks: [
          {
            p: "This policy may change, in particular if the hosting provider changes. The date of the last update is shown at the top of the page.",
          },
        ],
      },
    ],
    updated: "2026-11-02",
  },
};
