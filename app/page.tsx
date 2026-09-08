import type { Metadata } from "next";
import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";

export const metadata: Metadata = {
  title: "Glyph — l'éditeur PDF qui modifie vraiment le texte",
  description:
    "Modifie le texte d'un PDF pour de vrai : le contenu d'origine est supprimé et réécrit, pas recouvert par un rectangle. Reflow, police d'origine, recherche et copier-coller intacts.",
  alternates: { canonical: "/" },
};

const faqItems = [
  {
    q: "Le texte modifié reste-t-il cherchable et copiable ?",
    a: "Oui. Glyph supprime réellement les anciens caractères du flux du PDF et réinsère le nouveau texte comme du vrai texte — pas une image, pas un calque. Recherche, sélection et copier-coller fonctionnent normalement.",
  },
  {
    q: "Mes fichiers sont-ils stockés quelque part ?",
    a: "Non. Chaque PDF est gardé en mémoire le temps de la session d'édition, jamais écrit sur disque côté serveur, et disparaît à la fermeture.",
  },
  {
    q: "Est-ce que la police d'origine est toujours conservée ?",
    a: "Quand c'est possible, oui — Glyph réutilise la police d'origine du document. Beaucoup de PDF (Word, imprimantes virtuelles) embarquent des polices en sous-ensemble qui ne couvrent pas tous les caractères ; dans ce cas Glyph bascule sur une police système proche et te le signale, plutôt que d'afficher un caractère manquant en silence.",
  },
  {
    q: "Ça marche sur des tableaux ?",
    a: "Oui. Glyph distingue automatiquement une cellule de tableau d'un paragraphe pour ne modifier que le champ cliqué, sans jamais toucher aux cellules voisines.",
  },
  {
    q: "Faut-il un compte pour l'utiliser ?",
    a: "Non, l'éditeur est utilisable directement.",
  },
];

const softwareJsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Glyph",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  description:
    "Éditeur PDF qui réécrit le contenu du document (suppression réelle du texte d'origine, réinsertion avec la police d'origine) au lieu de le recouvrir d'un calque.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "EUR",
  },
};

const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: faqItems.map((item) => ({
    "@type": "Question",
    name: item.q,
    acceptedAnswer: { "@type": "Answer", text: item.a },
  })),
};

export default function LandingPage() {
  return (
    <>
      <header className="site-header">
        <Link href="/" className="brand">
          <span className="brand-mark">
            <BrandMark />
          </span>
          <span className="brand-name">Glyph</span>
        </Link>
        <nav className="site-nav">
          <Link href="/editor" className="btn btn-accent">
            Ouvrir l&apos;éditeur
          </Link>
        </nav>
      </header>

      <section className="hero">
        <span className="hero-eyebrow">Édition PDF sans overlay</span>
        <h1 className="hero-title">
          Modifie le texte d&apos;un PDF.
          <br />
          Pour de <span className="hero-accent">vrai</span>.
        </h1>
        <p className="hero-subtitle">
          Glyph réécrit le contenu du PDF au lieu de le recouvrir : le texte d&apos;origine est supprimé,
          le nouveau est réinséré avec la police d&apos;origine quand c&apos;est possible — reflow, recherche
          et copier-coller inclus.
        </p>
        <div className="hero-actions">
          <Link href="/editor" className="btn btn-accent btn-lg">
            Ouvrir l&apos;éditeur
          </Link>
          <a href="#comment-ca-marche" className="btn btn-ghost btn-lg">
            Comment ça marche
          </a>
        </div>
      </section>

      <section className="section" id="le-probleme">
        <p className="section-label">Le problème</p>
        <h2 className="section-title">Les autres éditeurs PDF ne modifient pas le texte — ils le cachent</h2>
        <p className="section-lede">
          La méthode classique : recouvrir l&apos;ancien texte d&apos;un rectangle blanc et écrire le nouveau
          par-dessus. Ça a l&apos;air correct à l&apos;écran, mais le document reste cassé.
        </p>
        <div className="problem-grid">
          <div className="problem-card is-bad">
            <h3>Overlay (la méthode classique)</h3>
            <p>
              Le texte d&apos;origine reste présent sous le cache : recherche et copier-coller renvoient encore
              l&apos;ancienne valeur. Un fond coloré ou un tableau se retrouve avec un carré blanc qui jure.
            </p>
          </div>
          <div className="problem-card is-good">
            <h3>Glyph</h3>
            <p>
              Les glyphes d&apos;origine sont supprimés du flux du document et remplacés par du vrai texte, à la
              bonne position, avec la bonne police quand c&apos;est possible. Rien à cacher : il n&apos;y a plus rien
              en dessous.
            </p>
          </div>
        </div>
      </section>

      <section className="section" id="comment-ca-marche">
        <p className="section-label">Comment ça marche</p>
        <h2 className="section-title">Quatre étapes, aucune trace de l&apos;ancien texte</h2>
        <div className="steps">
          <div className="step">
            <p className="step-number" aria-hidden="true" />
            <h3>Dépose ton PDF</h3>
            <p>Traitement en mémoire, rien n&apos;est écrit sur disque côté serveur.</p>
          </div>
          <div className="step">
            <p className="step-number" aria-hidden="true" />
            <h3>Clique sur un champ</h3>
            <p>Glyph distingue automatiquement un paragraphe d&apos;une cellule de tableau.</p>
          </div>
          <div className="step">
            <p className="step-number" aria-hidden="true" />
            <h3>Le contenu est réécrit</h3>
            <p>Suppression réelle des anciens glyphes, réinsertion avec la police d&apos;origine si possible.</p>
          </div>
          <div className="step">
            <p className="step-number" aria-hidden="true" />
            <h3>Télécharge</h3>
            <p>Un PDF où le texte modifié est du vrai texte — cherchable, copiable, imprimable.</p>
          </div>
        </div>
      </section>

      <section className="section" id="fonctionnalites">
        <p className="section-label">Fonctionnalités</p>
        <h2 className="section-title">Pensé pour la fidélité, pas pour l&apos;apparence</h2>
        <div className="features-grid">
          <div className="feature-card">
            <h3>Suppression réelle du contenu</h3>
            <p>Aucun rectangle de couverture — les anciens caractères sont retirés du document.</p>
          </div>
          <div className="feature-card">
            <h3>Police d&apos;origine préservée</h3>
            <p>Réutilisée quand elle couvre les caractères nécessaires ; repli signalé sinon.</p>
          </div>
          <div className="feature-card">
            <h3>Tableaux respectés</h3>
            <p>Chaque cellule est éditée indépendamment, sans jamais déborder sur ses voisines.</p>
          </div>
          <div className="feature-card">
            <h3>Annuler / rétablir</h3>
            <p>Historique complet des modifications sur le document en cours d&apos;édition.</p>
          </div>
        </div>
      </section>

      <section className="section" id="faq">
        <p className="section-label">FAQ</p>
        <h2 className="section-title">Questions fréquentes</h2>
        <div className="faq-list">
          {faqItems.map((item) => (
            <div className="faq-item" key={item.q}>
              <h3>{item.q}</h3>
              <p>{item.a}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="cta-band">
        <div className="section">
          <div>
            <h2>Prêt à modifier un PDF pour de vrai ?</h2>
            <p>Aucune inscription nécessaire.</p>
          </div>
          <Link href="/editor" className="btn btn-accent btn-lg">
            Ouvrir l&apos;éditeur
          </Link>
        </div>
      </section>

      <footer className="site-footer">
        <span>© {new Date().getFullYear()} Glyph</span>
        <span>Édition PDF réelle — pas un calque.</span>
      </footer>

      <script
        type="application/ld+json"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareJsonLd) }}
      />
      <script
        type="application/ld+json"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
    </>
  );
}
