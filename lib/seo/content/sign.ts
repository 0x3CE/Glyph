import type { LocalizedContent } from "../types";

export const sign: LocalizedContent = {
  fr: {
    nav: "Signer un PDF",
    metaTitle: "Signer un PDF en ligne, gratuitement | Glyph",
    metaDescription:
      "Ajoute ta signature manuscrite à un PDF : dessine-la au doigt ou à la souris, ou importe-la, puis place-la où tu veux. Gratuit, sans compte.",
    eyebrow: "Gratuit · sans compte",
    h1: "Signer un PDF",
    intro:
      "Dessine ta signature au doigt ou à la souris, ou importe-la, puis place-la sur la page. Pratique pour un bon pour accord, une attestation ou un formulaire à renvoyer signé.",
    widget: "upload",
    intent: "sign",
    sections: [
      {
        h2: "Comment signer un PDF",
        blocks: [
          {
            steps: [
              "Dépose ton PDF ci-dessus : l'éditeur s'ouvre directement sur la fenêtre de signature.",
              "Dessine ta signature, ou importe-la (PDF, PNG ou JPG).",
              "Fais-la glisser à sa place sur la page, ajuste sa taille par le coin, puis valide.",
              "Télécharge le PDF signé.",
            ],
          },
          {
            p: "Une signature importée en PDF reste vectorielle : nette à n'importe quel zoom et à l'impression. Une image PNG avec fond transparent s'intègre mieux qu'une photo sur fond blanc.",
          },
        ],
      },
      {
        h2: "Ce n'est pas une signature électronique certifiée",
        blocks: [
          {
            p: "Glyph appose **l'image de ta signature manuscrite** sur la page, comme si tu imprimais, signais et scannais le document. C'est ce qu'on attend d'un bon pour accord ou d'un formulaire courant.",
          },
          {
            p: "Ce n'est **pas** une signature électronique au sens du règlement européen eIDAS : il n'y a ni vérification de ton identité, ni certificat, ni scellement du document contre les modifications. Pour un acte qui l'exige (certains contrats, actes notariés, marchés publics), passe par un prestataire de signature électronique qualifié.",
          },
        ],
      },
      {
        h2: "Où va ton fichier ?",
        blocks: [
          {
            p: "Ton PDF et ta signature sont envoyés en HTTPS au serveur de Glyph, traités **en mémoire uniquement**, jamais écrits sur disque, et supprimés à la fermeture de l'onglet ou après 30 minutes d'inactivité. Ta signature n'est pas enregistrée pour la fois suivante.",
          },
          {
            p: "Ne signe que des documents qui te concernent, et seulement avec ta propre signature : apposer celle de quelqu'un d'autre est un faux. Voir les [conditions d'utilisation](@terms).",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Une signature ajoutée avec Glyph a-t-elle une valeur légale ?",
        a: "Celle d'une signature manuscrite scannée : souvent suffisante pour un accord courant, mais pas pour les actes qui exigent une signature électronique avancée ou qualifiée (eIDAS).",
      },
      {
        q: "Peut-on signer sur téléphone ?",
        a: "Oui : la signature se dessine au doigt, et se place et se redimensionne au toucher.",
      },
      {
        q: "Peut-on signer plusieurs pages ?",
        a: "Oui : place la signature sur une page, passe à la suivante, et recommence.",
      },
      {
        q: "Est-ce gratuit ?",
        a: "Oui, sans compte, sans publicité et sans filigrane.",
      },
    ],
    related: ["editText", "findReplace", "redact"],
  },
  en: {
    nav: "Sign a PDF",
    metaTitle: "Sign a PDF online for free | Glyph",
    metaDescription:
      "Add your handwritten signature to a PDF: draw it with a finger or a mouse, or upload it, then place it wherever you want. Free, no account.",
    eyebrow: "Free · no account",
    h1: "Sign a PDF",
    intro:
      "Draw your signature with a finger or a mouse, or upload it, then place it on the page. Handy for an approval, a certificate or a form to send back signed.",
    widget: "upload",
    intent: "sign",
    sections: [
      {
        h2: "How to sign a PDF",
        blocks: [
          {
            steps: [
              "Drop your PDF above: the editor opens straight on the signature window.",
              "Draw your signature, or upload it (PDF, PNG or JPG).",
              "Drag it into place on the page, resize it from the corner, then confirm.",
              "Download the signed PDF.",
            ],
          },
          {
            p: "A signature uploaded as a PDF stays vector: sharp at any zoom and in print. A PNG with a transparent background blends in better than a photo on white paper.",
          },
        ],
      },
      {
        h2: "This isn't a certified electronic signature",
        blocks: [
          {
            p: "Glyph places **the image of your handwritten signature** on the page, as if you printed, signed and scanned the document. That's what an approval or an everyday form expects.",
          },
          {
            p: "It is **not** an electronic signature in the sense of the EU eIDAS regulation: there is no identity verification, no certificate, and no seal protecting the document against changes. For a document that requires one (some contracts, notarial deeds, public tenders), use a qualified electronic signature provider.",
          },
        ],
      },
      {
        h2: "Where does your file go?",
        blocks: [
          {
            p: "Your PDF and your signature are sent over HTTPS to Glyph's server, processed **in memory only**, never written to disk, and deleted when you close the tab or after 30 minutes of inactivity. Your signature isn't saved for next time.",
          },
          {
            p: "Only sign documents that concern you, and only with your own signature: placing someone else's is forgery. See the [terms of use](@terms).",
          },
        ],
      },
    ],
    faq: [
      {
        q: "Is a signature added with Glyph legally valid?",
        a: "As valid as a scanned handwritten signature: often enough for an everyday agreement, but not for documents that require an advanced or qualified electronic signature (eIDAS).",
      },
      {
        q: "Can I sign on my phone?",
        a: "Yes: you draw the signature with a finger, and place and resize it by touch.",
      },
      {
        q: "Can I sign several pages?",
        a: "Yes: place the signature on one page, go to the next, and do it again.",
      },
      {
        q: "Is it free?",
        a: "Yes, with no account, no ads and no watermark.",
      },
    ],
    related: ["editText", "findReplace", "redact"],
  },
};
