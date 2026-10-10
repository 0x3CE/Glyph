# Référence API backend

Base : `http://localhost:8000` en local (le frontend y accède via le proxy Next.js sous `/api/*`, voir [`ARCHITECTURE.md`](./ARCHITECTURE.md)). Doc interactive auto-générée par FastAPI : `http://localhost:8000/docs`, seulement si le backend est lancé avec `ENABLE_API_DOCS=1` (désactivée par défaut, donc en production).

Aucune authentification. Les documents sont identifiés par un `document_id` opaque (uuid hex) obtenu à l'upload — le connaître suffit à lire/modifier/supprimer le document (pas de contrôle d'accès, cohérent avec l'absence de comptes utilisateurs).

---

### `POST /api/documents`

Upload un PDF. Corps : **les octets bruts du fichier** (`Content-Type: application/pdf`), pas du `multipart/form-data` : le backend les lit en flux, en mémoire uniquement, et coupe dès que la limite est dépassée (voir [`DECISIONS.md`](./DECISIONS.md#uploads-en-corps-brut-pas-en-multipart)).

```json
// 200
{ "document_id": "34ca6796213f49efb648acc326c472d0", "page_count": 3 }
```

`400` si le fichier n'est pas un PDF valide (échec d'ouverture, protégé par mot de passe, ou parsing tué par la sandbox — timeout/mémoire/CPU, voir [`DECISIONS.md`](./DECISIONS.md#isoler-le-parsing-pdf-dans-un-sous-processus)). `413` si le fichier dépasse `MAX_UPLOAD_MB` (20 Mo par défaut). `429` si ce visiteur (même IP) a déjà `MAX_DOCUMENTS_PER_OWNER` documents ouverts (10 par défaut) : il doit en fermer un ou attendre qu'il expire. `503` si le serveur est à pleine capacité (mémoire ou sandbox, voir [`DECISIONS.md`](./DECISIONS.md#borner-la-mémoire-et-la-concurrence)) : réessayer plus tard.

Les envois (upload, vérificateur, signature) sont traités `MAX_CONCURRENT_UPLOADS` (4) à la fois, car chaque corps est gardé en mémoire ; au-delà de 10 s d'attente, `503`. Toutes les routes ci-dessous peuvent aussi répondre `503` pour la même raison, et `404` pour un document expiré (30 minutes sans activité par défaut, `DOCUMENT_TTL_MINUTES`).

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
      "id": "b9l0",                // valable UNIQUEMENT pour cette réponse (voir plus bas) -- une ligne PyMuPDF = un bloc, toujours
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

`404` si le document ou la page n'existe pas. `422` si le traitement échoue dans la sandbox (timeout/mémoire/CPU, voir [`DECISIONS.md`](./DECISIONS.md#isoler-le-parsing-pdf-dans-un-sous-processus)).

---

### `POST /api/documents/{document_id}/pages/{page_index}/blocks/{block_id}/edit`

```json
// requête
{ "text": "Lille, le 05/09/2026" }  // 5000 caractères max
```

Un `\n` dans `text` crée une ligne supplémentaire (utile pour un bloc multi-lignes comme une adresse). Le backend :
1. Redécoupe la structure de la page à la volée pour retrouver le bloc correspondant à `block_id` (`404` si introuvable — typiquement parce que l'id vient d'une structure périmée).
2. Supprime réellement les glyphes d'origine du bloc et réinsère le nouveau texte (voir [`DECISIONS.md`](./DECISIONS.md) pour le détail du moteur) — dans le sous-processus isolé, comme toute opération touchant le PDF.
3. Empile le nouvel état du document dans l'historique (undo devient possible, redo est vidé).

```json
// 200
{
  "font_substituted": true,               // la police d'origine n'a pas pu être réutilisée
  "new_bbox": [311.8, 224.1, 406.5, 244.9] // zone réellement occupée après édition
}
```

`422` si `text` dépasse 5000 caractères, ou si le traitement échoue dans la sandbox (timeout/mémoire/CPU). `404` si la page ou le bloc n'existe pas.

---

### `POST /api/documents/{document_id}/pages/{page_index}/signature`

Place une signature sur la page. Corps : les octets bruts du fichier (PDF, PNG ou JPEG — le type est détecté à partir des octets du fichier, pas de son nom ni du `Content-Type` déclaré). Le rectangle cible passe en paramètres de requête `?x0=&y0=&x1=&y1=` (en points PDF, origine en haut à gauche — mêmes conventions que `bbox` ailleurs dans cette API).

Un PDF source est incrusté en vectoriel (`page.show_pdf_page`, sa première page uniquement) ; une image PNG/JPEG est insérée telle quelle (`page.insert_image`). Dans les deux cas, la signature est étirée pour remplir exactement le rectangle donné — pas de préservation automatique du ratio d'origine, à gérer côté client si besoin (voir [`DECISIONS.md`](./DECISIONS.md)).

```json
// 200
{ "bbox": [100.0, 400.0, 300.0, 460.0] }
```

`400` si le fichier n'est ni un PDF, ni une PNG, ni une JPEG reconnaissable, ou si c'est un PDF protégé par mot de passe / sans page. `413` si le fichier dépasse `MAX_SIGNATURE_MB` (5 Mo par défaut). `422` si le rectangle est invalide : coordonnée NaN, infinie ou au-delà de 100 000 points, ou rectangle vide ou inversé. `404` si le document ou la page n'existe pas. `422` si le traitement échoue dans la sandbox (timeout/mémoire/CPU).

---

### `POST /api/documents/{document_id}/undo` / `POST /api/documents/{document_id}/redo`

Aucun corps. Déplace le curseur dans la pile d'historique du document (clampé aux bornes — un undo au tout début ou un redo à la fin est un no-op silencieux).

```json
{ "cursor": 0, "can_undo": false, "can_redo": true }
```

---

### `DELETE /api/documents/{document_id}`

Libère le document de la mémoire. `{ "ok": true }` même si l'id n'existait pas déjà (idempotent). Le frontend l'appelle quand l'onglet se ferme (`pagehide`, avec `keepalive`) et quand un autre PDF remplace le document courant ; sinon le document expire après `DOCUMENT_TTL_MINUTES` d'inactivité.

---

### `POST /api/documents/{document_id}/pages/{page_index}/redact`

Caviardage réel. Corps JSON : `{"rects": [[x0, y0, x1, y1], …]}` (points PDF, 1 à 200 zones, coordonnées finies). Tout ce qui se trouve sous chaque zone est supprimé du fichier (texte, pixels d'image, tracés entièrement couverts), puis la zone est peinte en noir. Les zones sont rognées à la page ; celles de moins d'un point sont ignorées.

```json
// 200
{ "redacted": 2 }
```

`404` si le document ou la page n'existe pas. `422` (validation) pour une coordonnée NaN ou infinie.

---

### `POST /api/documents/{document_id}/sanitize`

Aucun corps. Retire les métadonnées (dictionnaire d'informations et XMP), les pièces jointes, le JavaScript, le texte invisible, les vignettes, applique les caviardages marqués mais jamais appliqués, puis réécrit entièrement le fichier (sans ses anciennes versions). Les liens et les champs de formulaire remplis sont conservés. `removed` liste ce qui a été trouvé, en clés stables que le frontend traduit.

```json
// 200
{ "removed": ["metadata.author", "metadata.keywords", "xmp"] }
```

---

### `POST /api/documents/{document_id}/replace`

Rechercher-remplacer dans tout le document. Corps JSON :

```json
{ "find": "Dupont", "replace": "Martin", "match_case": false, "whole_word": false }
```

`find` : 1 à 200 caractères, `replace` : 0 à 200, sans retour à la ligne. La recherche ignore les ligatures et les espaces spéciaux (normalisation NFKC). Chaque ligne trouvée est éditée comme une édition manuelle. Une exécution sandbox cherche les pages concernées, puis une exécution par page fait les éditions (20 pages, 60 lignes par page et 300 lignes au plus par requête). L'ensemble forme **une seule** étape d'historique.

```json
// 200
{ "replaced": 3, "lines": 2, "pages": [1, 4], "truncated": false, "font_substituted": true }
```

`pages` est en base 1. `truncated` indique que la limite a été atteinte et qu'il reste des occurrences. Sans occurrence, la réponse a `replaced: 0`, et rien n'est ajouté à l'historique.

---

### `POST /api/inspect`

Vérificateur de PDF caviardé. Corps : les octets bruts du PDF. Le fichier est analysé dans la sandbox, **ni modifié ni conservé** : pas de `document_id`.

```json
// 200
{
  "page_count": 2,
  "pages_inspected": 2,
  "hidden_text": [{ "page": 1, "text": "Salarié : Jean Dupont" }],
  "unapplied_redactions": 0,
  "invisible_text_chars": 0,
  "invisible_text_samples": [],
  "metadata": { "author": "Jean Dupont" },
  "has_xmp": false,
  "versions": 1,
  "attachments": [],
  "annotations": {}
}
```

`hidden_text` : texte couvert à 60 % au moins par une forme opaque ou une image sans transparence dessinée après lui, ou par une annotation remplie. Le texte sous une image de la taille de la page (un scan) compte comme invisible, pas comme caché. 300 pages analysées au plus, 50 résultats par liste. `400` si le PDF est illisible ou protégé par mot de passe, `413` au-delà de `MAX_UPLOAD_MB`, `503` si la sandbox est saturée.
