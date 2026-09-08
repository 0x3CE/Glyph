# Glyph

Édition de texte réelle dans un PDF : le contenu cliqué est réécrit dans le flux du document (redaction PyMuPDF), pas recouvert par un calque. Le texte d'origine est supprimé, pas juste masqué.

Frontend Next.js (App Router) : page marketing statique optimisée SEO sur `/`, éditeur interactif sur `/editor`.

**Documentation technique** : [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) (comment les deux moitiés du projet s'articulent), [`docs/API.md`](./docs/API.md) (référence des routes backend), [`docs/DECISIONS.md`](./docs/DECISIONS.md) (pourquoi le moteur d'édition est fait comme il est fait — les bugs réels rencontrés et pourquoi chaque détour existe).

## Démarrer

Backend (Python/FastAPI/PyMuPDF) :

```bash
cd backend
python3 -m venv .venv        # une seule fois
.venv/bin/pip install -r requirements.txt   # une seule fois
.venv/bin/uvicorn app.main:app --port 8000 --reload
```

Frontend (Next.js, proxy `/api` vers le backend via `next.config.ts`) :

```bash
npm install
npm run dev
```

Ouvre http://localhost:3000 (page d'accueil) ou http://localhost:3000/editor (outil directement).

## Fonctionnement

1. Ouvre un PDF (envoyé au backend, gardé en mémoire process, jamais écrit sur disque).
2. Clique sur un paragraphe ou une cellule : un éditeur apparaît à sa place exacte.
3. Modifie le texte, Enregistrer.
4. Le backend supprime réellement les glyphes d'origine (redaction PyMuPDF, pas un rectangle de couverture) et réinsère le nouveau texte avec la police d'origine si elle couvre tous les caractères nécessaires, sinon une police système proche avec compensation métrique (bandeau d'avertissement affiché dans ce cas).
5. Annuler/Rétablir naviguent dans l'historique de versions du document (côté serveur).
6. Télécharge le PDF à tout moment.

## SEO

- `/` est un composant serveur statique (SSG) : HTML complet dès la première réponse, `/editor` (l'outil) est en `noindex, follow` pour ne pas concurrencer la page d'accueil dans les résultats de recherche.
- Métadonnées : Open Graph + Twitter Card, image OG générée (`app/opengraph-image.tsx`), JSON-LD `Organization` (layout), `SoftwareApplication` + `FAQPage` (page d'accueil).
- `app/sitemap.ts` et `app/robots.ts` génèrent `/sitemap.xml` et `/robots.txt`.
- `NEXT_PUBLIC_SITE_URL` (variable d'environnement) fixe l'URL canonique une fois un vrai domaine en place — sans elle, un placeholder (`https://glyph.app`) est utilisé.
- Polices auto-hébergées via `next/font/google` (pas de requête bloquante vers Google Fonts).

## Structure

```
app/            # routes Next.js (page d'accueil, /editor, sitemap, robots, OG image)
components/     # PdfPage (rendu + édition), EditorApp (écran outil), BrandMark
lib/            # client API, types partagés, config pdf.js
backend/        # FastAPI + PyMuPDF (moteur d'édition, inchangé)
```

## Limites connues de ce premier jalon

- **Réutilisation de la police d'origine** : ne fonctionne que si elle expose un cmap Unicode exploitable. La plupart des PDF générés par Word/imprimante virtuelle embarquent leurs polices en sous-ensembles Identity-H sans cmap — dans ce cas (très fréquent), Glyph tente une police système du même nom (ex. Arial Narrow), sinon une police système générique proche, avec compensation métrique pour garder la même largeur visuelle.
- **Débordement de bloc** : un paragraphe multi-lignes peut s'agrandir vers le bas si le nouveau texte est plus long ; une cellule de tableau (une seule ligne) ne grandit jamais — la police est réduite si besoin pour ne jamais empiéter sur la ligne ou la colonne voisine.
- **Fonds colorés** : la redaction retire tout contenu (y compris un éventuel remplissage vectoriel) dans la zone éditée — un bloc de texte sur fond coloré perdrait ce fond. Non rencontré sur les blocs de texte courants (dates, noms, paragraphes), mais à garder en tête pour des tableaux avec cellules éditables colorées.
- Pas de shaping HarfBuzz avancé, pas de RTL/CJK, pas de rotation de page — hors périmètre de ce premier jalon (édition de texte). Signatures, formes, formulaires et OCR ne sont pas encore implémentés.
