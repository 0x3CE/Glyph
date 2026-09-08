# Architecture

## Vue d'ensemble

Glyph a deux parties qui ne parlent que par HTTP, chacune remplaçable indépendamment :

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│   Frontend — Next.js         │        │   Backend — FastAPI          │
│                               │        │                               │
│  /            page marketing │  /api  │  documents.py  état en mémoire│
│  /editor      outil (client) │ ─────▶ │  main.py       routes HTTP    │
│                               │ proxy  │  pdf_engine.py moteur PyMuPDF │
│  components/PdfPage.tsx      │        │                               │
│    → rendu pdf.js (canvas)   │        │  Aucun fichier écrit sur      │
│    → overlay cliquable       │        │  disque : tout vit dans la    │
│                               │        │  RAM du process backend       │
└─────────────────────────────┘        └──────────────────────────────┘
```

Le frontend ne parle jamais directement à `localhost:8000` : `next.config.ts` proxifie `/api/*` vers le backend (`rewrites()`), donc dans le navigateur tout part vers `localhost:3000/api/...`. C'est pour ça qu'il n'y a pas de souci CORS en usage normal — CORS ne sert qu'aux tests/scripts qui appellent le backend en direct (`allow_origins` dans `main.py` autorise `localhost:3000`).

## Pourquoi cette séparation frontend/backend

Le rendu (pdf.js, canvas, clic sur un champ) reste 100% client — pas de raison de le faire ailleurs. Mais la vraie édition (supprimer des glyphes d'un flux PDF, choisir une police de remplacement, mesurer du texte) a besoin d'un moteur PDF complet : c'est PyMuPDF, une bibliothèque Python (bindings de MuPDF, en C). Il n'y a pas d'équivalent aussi complet côté JS/navigateur — d'où le split.

## Cycle de vie d'une édition

1. **Upload** — `POST /api/documents` : le PDF part en `multipart/form-data`, le backend le garde en mémoire (`documents.py`), renvoie un `document_id` (uuid). Le fichier n'est jamais écrit sur disque, ni côté client ni côté serveur.
2. **Rendu de page** — le frontend récupère les bytes bruts (`GET /api/documents/{id}/file`) et les rend lui-même avec pdf.js dans un `<canvas>` (`components/PdfPage.tsx`). Le backend n'a aucune notion de rendu visuel.
3. **Structure** — `GET /api/documents/{id}/pages/{n}/structure` : le backend appelle `page.get_text("dict")` (PyMuPDF), qui donne déjà une hiérarchie bloc → ligne → span avec police/taille/couleur/position. `extract_structure()` (`pdf_engine.py`) reclasse ça en unités éditables (voir [`DECISIONS.md`](./DECISIONS.md#regroupement-bloc-vs-ligne) pour pourquoi c'est nécessaire).
4. **Superposition cliquable** — le frontend positionne un `<div>` invisible par bloc, à la bonne position en pixels (coordonnées PDF × échelle de zoom). Clic → `<textarea>` positionnée pile dessus.
5. **Édition** — `POST /api/documents/{id}/pages/{n}/blocks/{blockId}/edit` avec le nouveau texte. `apply_block_edit()` fait le travail réel : redaction (suppression des glyphes d'origine) + choix de police + réinsertion. Le PDF modifié est resauvegardé en mémoire et empilé dans l'historique (`DocumentState.push`).
6. **Undo/redo** — `DocumentState` garde une pile de snapshots complets du PDF (bytes). `undo`/`redo` déplacent juste un curseur dans cette pile — pas de diff, pas de patch, juste "revenir à la version N".
7. **Téléchargement** — `GET /api/documents/{id}/file` renvoie l'état courant (celui pointé par le curseur d'historique).

Comme `structure` et `edit` **recalculent** `extract_structure()` à chaque appel (au lieu de garder un état d'arbre en mémoire), les identifiants de bloc (`b3`, `b12l2`...) ne sont valables que pour la structure qui vient d'être renvoyée. Le frontend refait toujours un `GET .../structure` frais avant de proposer un clic — ne jamais réutiliser un `block_id` d'une réponse précédente.

## Fichiers clés

| Fichier | Rôle |
|---|---|
| `backend/app/pdf_engine.py` | Le moteur : extraction de structure, choix de police, redaction + réinsertion. Toute la logique métier est là — voir [`DECISIONS.md`](./DECISIONS.md) pour le détail de chaque choix non-évident. |
| `backend/app/main.py` | Routes FastAPI, fines — délèguent tout à `pdf_engine.py` et `documents.py`. |
| `backend/app/documents.py` | Store en mémoire + historique undo/redo. Pas de base de données. |
| `components/PdfPage.tsx` | Rendu canvas + overlay cliquable + `<textarea>` d'édition. |
| `components/EditorApp.tsx` | Écran `/editor` complet (upload, navigation de page, undo/redo, téléchargement). |
| `lib/api-client.ts` | Tous les appels `fetch` vers le backend, typés. |
| `app/page.tsx` | Page marketing statique (SSG) — voir la section SEO du README. |

## Ce qui n'est PAS là

Pas de base de données, pas d'auth, pas de queue de jobs. Un process FastAPI unique, état en RAM. Ça veut dire : redémarrer le backend efface tous les documents en cours d'édition, et ça ne scale pas à plusieurs instances (deux workers = deux stores en mémoire différents). Suffisant pour un usage local/mono-utilisateur ; à revoir avant un déploiement multi-instance (il faudrait externaliser `documents.py` vers un store partagé — Redis par exemple).
