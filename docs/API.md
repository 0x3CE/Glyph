# Référence API backend

Base : `http://localhost:8000` en local (le frontend y accède via le proxy Next.js sous `/api/*`, voir [`ARCHITECTURE.md`](./ARCHITECTURE.md)). Doc interactive auto-générée par FastAPI : `http://localhost:8000/docs`.

Aucune authentification. Les documents sont identifiés par un `document_id` opaque (uuid hex) obtenu à l'upload — le connaître suffit à lire/modifier/supprimer le document (pas de contrôle d'accès, cohérent avec l'absence de comptes utilisateurs).

---

### `POST /api/documents`

Upload un PDF. Corps : `multipart/form-data`, champ `file`.

```json
// 200
{ "document_id": "34ca6796213f49efb648acc326c472d0", "page_count": 3 }
```

`400` si le fichier n'est pas un PDF valide (PyMuPDF n'a pas pu l'ouvrir).

---

### `GET /api/documents/{document_id}/file`

Renvoie les bytes du PDF **courant** (celui pointé par le curseur d'historique — reflète les édits déjà appliqués et les éventuels undo/redo). `Content-Type: application/pdf`. `404` si l'id est inconnu.

---

### `GET /api/documents/{document_id}/pages/{page_index}/structure`

`page_index` commence à 0. Renvoie la liste des blocs éditables de la page, recalculée à chaque appel à partir de l'état courant du document.

```jsonc
{
  "page_index": 0,
  "width": 595.27,   // en points PDF, pas en pixels écran
  "height": 841.89,
  "blocks": [
    {
      "id": "b9",                 // valable UNIQUEMENT pour cette réponse (voir plus bas)
      "bbox": [311.8, 224.1, 387.5, 239.4],  // [x0, y0, x1, y1], origine en haut à gauche
      "text": "Lille, le 22/06/2026",
      "lines": [
        {
          "bbox": [311.8, 224.1, 387.5, 239.4],
          "spans": [
            {
              "text": "Lille, le 22/06/2026",
              "bbox": [311.8, 224.1, 387.5, 239.4],
              "font": "ArialNarrow",
              "size": 11.0,
              "color": 0,          // entier 0xRRGGBB
              "flags": 0           // bits : voir table plus bas
            }
          ]
        }
      ]
    }
  ]
}
```

**`flags`** (bitmask, cf. `FLAG_*` dans `pdf_engine.py`) :

| Bit | Constante | Sens |
|---|---|---|
| `1 << 1` | `FLAG_ITALIC` | Italique |
| `1 << 2` | `FLAG_SERIF` | Police à empattements |
| `1 << 3` | `FLAG_MONOSPACE` | Police à chasse fixe |
| `1 << 4` | `FLAG_BOLD` | Gras |

**⚠️ Les `id` de bloc ne sont pas stables entre deux appels.** Ils sont recalculés à chaque `GET .../structure` à partir de la position des blocs dans le document à cet instant (`b{index-de-bloc}` ou `b{index}l{index-de-ligne}` pour une ligne éclatée d'un bloc non-cohérent, voir [`DECISIONS.md`](./DECISIONS.md#regroupement-bloc-vs-ligne)). Toute édition qui précède change potentiellement la numérotation. **Toujours refaire un `GET .../structure` juste avant d'utiliser un `block_id`.**

`404` si le document ou la page n'existe pas.

---

### `POST /api/documents/{document_id}/pages/{page_index}/blocks/{block_id}/edit`

```json
// requête
{ "text": "Lille, le 05/09/2026" }
```

Un `\n` dans `text` crée une ligne supplémentaire (utile pour un bloc multi-lignes comme une adresse). Le backend :
1. Redécoupe la structure de la page à la volée pour retrouver le bloc correspondant à `block_id` (`404` si introuvable — typiquement parce que l'id vient d'une structure périmée).
2. Supprime réellement les glyphes d'origine du bloc et réinsère le nouveau texte (voir [`DECISIONS.md`](./DECISIONS.md) pour le détail du moteur).
3. Empile le nouvel état du document dans l'historique (undo devient possible, redo est vidé).

```json
// 200
{
  "font_substituted": true,               // la police d'origine n'a pas pu être réutilisée
  "new_bbox": [311.8, 224.1, 406.5, 244.9] // zone réellement occupée après édition
}
```

---

### `POST /api/documents/{document_id}/undo` / `POST /api/documents/{document_id}/redo`

Aucun corps. Déplace le curseur dans la pile d'historique du document (clampé aux bornes — un undo au tout début ou un redo à la fin est un no-op silencieux).

```json
{ "cursor": 0, "can_undo": false, "can_redo": true }
```

---

### `DELETE /api/documents/{document_id}`

Libère le document de la mémoire. `{ "ok": true }` même si l'id n'existait pas déjà (idempotent). Le frontend actuel ne l'appelle pas — les documents restent en mémoire jusqu'au redémarrage du process (voir la limite décrite dans [`ARCHITECTURE.md`](./ARCHITECTURE.md#ce-qui-nest-pas-là)).
