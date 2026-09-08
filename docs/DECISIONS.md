# Décisions techniques

Ce document explique le *pourquoi* des choix non-évidents du moteur d'édition (`backend/app/pdf_engine.py`). Le code a des commentaires courts sur le *quoi* ; ici c'est le contexte complet — souvent découvert en testant contre de vrais PDF, pas en lisant la doc PyMuPDF. Si tu retouches ce fichier, relis la section correspondante avant de « simplifier » quelque chose : plusieurs de ces détours existent parce que la version évidente produisait un bug silencieux.

## Réécriture réelle vs overlay

**Le problème** : la façon standard de « modifier » un PDF (la plupart des outils en ligne) est de poser un rectangle blanc sur l'ancien texte et d'écrire le nouveau par-dessus. Ça a l'air correct à l'écran mais le texte d'origine reste dans le flux du document — recherche et copier-coller renvoient encore l'ancienne valeur, et un fond coloré ou un tableau se retrouve avec un carré qui jure.

**Ce qu'on fait** : `page.add_redact_annot(rect, fill=None)` + `page.apply_redactions()` supprime réellement les opérateurs de dessin de glyphes qui touchent le rectangle — validé en vérifiant après coup que l'ancien texte n'est plus dans `page.get_text()`. C'est la seule partie du pipeline qui n'a pas de compromis : c'est une vraie suppression, pas un cache.

**Limite acceptée** : la redaction supprime *tout* contenu dans le rectangle, y compris un éventuel remplissage vectoriel (fond de cellule coloré). Non rencontré sur les blocs de texte courants (dates, noms, paragraphes), mais un tableau avec des cellules éditables sur fond coloré perdrait ce fond.

## Regroupement bloc vs ligne

**Le problème** : `page.get_text("dict")` de PyMuPDF renvoie déjà une hiérarchie bloc → ligne → span, mais son algorithme de blocs ne connaît pas la notion de colonne de tableau — il regroupe purement par proximité verticale. Sur un vrai document, une table entière (4 lignes × 8 colonnes) peut atterrir comme **un seul bloc** avec 34 « lignes » à l'intérieur. Éditer ce bloc en entier (comportement initial) effaçait toute la table pour la remplacer par le contenu d'une seule cellule.

**Ce qu'on a vérifié** : à l'inverse, les *lignes* de PyMuPDF à l'intérieur de ce bloc géant correspondent déjà exactement à une cellule chacune (bbox serrée, texte correct) — PyMuPDF sépare bien deux runs de texte dès que l'écart horizontal est significatif, seul le regroupement en *blocs* est trop permissif verticalement.

**Ce qu'on fait** (`_is_coherent_paragraph`) : après extraction, on regarde si les lignes d'un bloc ont leur bord gauche (ou droit, pour du texte justifié/aligné à droite) à peu près au même x. Si oui → vrai paragraphe multi-lignes, on garde le bloc entier (permet le reflow sur une adresse ou un paragraphe qui wrap). Si non → probablement des cellules de tableau fusionnées par erreur, on édite chaque ligne indépendamment (`id` du type `b{i}l{j}`).

**Piège à ne pas réintroduire** : ne pas se fier à l'ordre des blocs dans `raw["blocks"]` pour deviner l'ordre de lecture — on a vu un bloc situé visuellement en haut de page apparaître après un bloc du milieu de page dans le tableau retourné par PyMuPDF.

## Pourquoi pas juste réutiliser la police d'origine

**Hypothèse de départ, invalidée par un test** : `doc.extract_font(xref)` renvoie les bytes de la police embarquée dans le PDF ; l'idée naturelle est de la redonner telle quelle à `insert_text(fontfile=...)`. Testé sur ce document réel → glyphes complètement illisibles (des carrés), pour n'importe quel texte nouveau.

**Pourquoi** : la plupart des PDF générés par Word/imprimante virtuelle embarquent leurs polices en sous-ensemble **Identity-H** (CID-keyed) — le sous-ensemble ne contient que les glyphes déjà utilisés dans le document, et surtout n'a **pas de table `cmap`** exploitable (vérifié avec `fontTools` : `post` format 3.0, aucun nom de glyphe, aucune table `cmap`). Sans cmap, impossible de savoir quel code correspond à quelle lettre pour du texte *nouveau* — MuPDF interprète alors les codes de caractères comme des index de glyphe bruts, d'où le résultat illisible. C'est un phénomène général à ce type de police, pas un bug ponctuel : dans le PDF de test, 5 polices sur 8 étaient dans ce cas.

**Ce qu'on fait** (`_font_covers_text`) : avant de réutiliser une police embarquée, on vérifie via `fontTools` qu'elle a un `cmap` couvrant tous les caractères du nouveau texte. Si non → on ne l'utilise jamais, on passe directement au repli. C'est un garde-fou générique, pas un cas spécial pour Identity-H — n'importe quelle police sans cmap exploitable est exclue de la même façon.

## Police de repli : polices système plutôt que Base-14

**Ce qu'on a essayé d'abord** : les polices Base-14 intégrées à PyMuPDF (`helv`, `tiro`, `cour`...). Ça marche, mais deux problèmes découverts en testant : (1) elles ne couvrent pas le symbole `€` (rendu en `?` ou en glyphe manquant selon le point d'entrée utilisé — vérifié aussi bien avec `insert_text` qu'`insert_textbox`) ; (2) elles n'ont aucun rapport visuel avec la police d'origine (Helvetica à la place d'un Arial Narrow condensé → texte visiblement plus large, signalé par l'utilisateur en test réel).

**Ce qu'on fait** (`_SYSTEM_FAMILIES`, `_FAMILY_ALIASES`) : on utilise les vraies polices système présentes sur macOS (`/System/Library/Fonts/Supplemental/*.ttf` — Arial, Arial Narrow, Times New Roman, Courier New, Georgia, Verdana, Tahoma), qui couvrent un jeu de caractères bien plus large (testé : `€`, accents, guillemets `«»`, `£`, `°` tous présents). On essaie d'abord de faire correspondre le **nom** de la police d'origine (ex. `"ArialNarrow"` détecté dans le nom PDF → vraie `Arial Narrow.ttf`, pas juste une police sans-serif générique) ; sinon on choisit une famille générique par catégorie (`_generic_family_for_flags` : sans-serif/serif/monospace selon les `flags`).

**Non portable** : ces chemins sont spécifiques à macOS. Sur un système sans ces fichiers, `_system_font_path` renvoie `None` et le code retombe sur Base-14 (dernier recours, toujours disponible). À traiter avant un déploiement sur un serveur Linux : soit embarquer des polices libres équivalentes (Liberation Sans/Serif/Mono, licence compatible), soit détecter l'OS et adapter `_SYSTEM_FONT_DIR`.

## Compensation métrique (`_metric_match_scale`)

**Le problème, remonté par l'utilisateur en test réel** : même avec une police de repli raisonnable, Helvetica est plus large qu'Arial Narrow — un champ édité avait l'air « élargi » par rapport à l'original.

**Ce qu'on fait** : on mesure la largeur qu'occuperait le texte **d'origine** (pas le nouveau texte — la police et le texte d'origine, comme référence indépendante de ce que l'utilisateur va taper) avec la police de repli choisie, et on compare à sa largeur réelle dans le PDF (`span.bbox`). Le ratio donne un facteur d'échelle horizontale (`pymupdf.Matrix(scale_x, 1)` passé en `morph`), borné à `[0.6, 1.4]` pour ne jamais compresser/étirer au point de devenir illisible.

## Une seule cellule = jamais de croissance verticale

**Bug réel rencontré** : la première version faisait grandir la boîte (largeur *et* hauteur) quand le texte ne rentrait pas, en boucle jusqu'à ce que `insert_textbox` réussisse. Sur une cellule de tableau, `insert_textbox` demandait systématiquement bien plus de hauteur que la ligne d'origine (constaté empiriquement : besoin d'environ 3× la hauteur de ligne pour qu'un texte d'une ligne soit accepté) — la boîte grandissait donc vers le bas, et la redaction qui l'accompagne effaçait une partie de la ligne du tableau juste en dessous.

**Ce qu'on fait** (`apply_block_edit`) : pour un bloc d'une seule ligne (donc très probablement un champ court, cellule de tableau ou équivalent), on ne fait jamais grandir la boîte. Si le texte ne rentre pas en largeur, on réduit la taille de police par paliers de 10 % (jusqu'à 50 % de la taille d'origine) plutôt que d'agrandir quoi que ce soit — ça ne peut jamais mordre sur une ligne ou une colonne voisine. Les blocs multi-lignes (vrais paragraphes) gardent le droit de grandir vers le bas : c'est le comportement de reflow demandé, et un paragraphe n'est en général pas collé à un voisin comme l'est une ligne de tableau.

## Position verticale : la vraie ligne de base, pas une estimation

**Bug réel, remonté par l'utilisateur** : la première version plaçait le texte à `y0 + fontsize * 0.8` (estimation de la ligne de base à partir du haut de la bbox). Résultat : le texte édité « remontait » visiblement par rapport aux lignes non éditées du même tableau — décalage de quelques points, mais très visible sur une colonne de dates.

**Ce qu'on fait** : PyMuPDF donne directement la ligne de base exacte de chaque span d'origine (`span["origin"]`, capturé dans `Span.origin`). On l'utilise telle quelle comme point d'insertion, et l'espacement entre lignes d'un bloc multi-lignes est mesuré ligne de base à ligne de base sur les lignes d'origine (pas bbox-haut à bbox-haut, qui varie avec la hauteur des ascendantes) — alignement pixel-parfait avec l'original, plus besoin de deviner.

## `insert_text` ligne par ligne plutôt que le wrap de `insert_textbox`

**Bug réel** : `insert_textbox` fait son propre retour à la ligne automatique, et pour ça marque en interne ses points de coupure potentiels en remplaçant l'espace normal par une espace insécable (U+00A0) et le trait d'union par un trait d'union conditionnel (U+00AD) — **même quand ce point n'est finalement pas utilisé comme coupure**. Résultat vérifié : un nom du type « DURAND-LEFEBVRE » ressortait de l'extraction comme `DURAND\xadLEFEBVRE`, cassant une recherche/copie sur le texte exact tapé par l'utilisateur.

**Ce qu'on fait** : puisque l'utilisateur tape déjà ses propres retours à la ligne (`\n`) pour un bloc multi-lignes, on n'a pas besoin que MuPDF redécide où couper — `new_text.split("\n")` puis un appel `page.insert_text(...)` par ligne, à une position explicite (voir section ligne de base ci-dessus). Zéro logique de wrap interne déclenchée, zéro substitution de caractère.

## `set_simple=1` : correct pour l'espace/tiret, dangereux pour `€`

**Suite du bug précédent** : même avec `insert_text` (pas de wrap), le simple fait d'utiliser une police *embarquée fraîchement* (`fontfile=...`) déclenchait la même substitution espace→U+00A0 et tiret→U+00AD à l'extraction — indépendamment de tout wrap. Testé et confirmé : le paramètre `set_simple=1` d'`insert_text` corrige ça (encodage « simple » plutôt qu'un CID généré à la volée pour l'embarquement).

**Mais** : `set_simple=1` limite l'encodage à Latin-1 (code point ≤ 255). Testé caractère par caractère : `€`, tiret cadratin `—`, guillemets typographiques `'` `"` (tous des code points > 255) redeviennent illisibles (`·`) sous `set_simple=1`, alors que `£`, `°`, `«»`, les lettres accentuées (`é`, `ñ`...) restent corrects (ils sont dans Latin-1).

**Ce qu'on fait** : `set_simple=1` seulement quand tous les caractères du texte à insérer sont `ord(c) <= 255` ; sinon encodage par défaut (`set_simple=0`), qui gère `€` et les guillemets correctement au prix de la substitution espace/tiret dans l'extraction pour *cette* édition précise. Compromis choisi consciemment : mieux vaut un espace normal qui devient un caractère invisible équivalent visuellement, que perdre carrément le symbole monétaire.

## Un nom de ressource police unique par édition

**Bug réel, le plus retors de la série** : le `€` fonctionnait en isolation, recommençait à casser (`?`) uniquement après plusieurs éditions successives sur le même document, avec des polices de repli différentes. Cause : le nom de ressource passé à `fontname=` (ex. `"sys-arial_narrow"`) est réutilisé tel quel par PyMuPDF comme identifiant interne de ressource dans le PDF — si un **précédent** appel avait déjà enregistré ce même nom en `set_simple=1` (encodage restreint), un appel ultérieur avec le même nom mais `set_simple=0` réutilisait silencieusement la ressource déjà posée, encodage restreint compris, malgré la demande explicite.

**Ce qu'on fait** : chaque appel à `pick_font` génère un tag aléatoire (`uuid.uuid4().hex[:8]`) et l'utilise comme nom de ressource (`f{unique}`), garantissant qu'aucune édition ne peut jamais entrer en collision avec une ressource posée par une édition précédente — même quand les deux tombent sur la même police physique. Coût : le PDF final embarque plusieurs copies de la même police (une par édition qui l'utilise) au lieu d'une seule partagée. Négligeable en taille pour un usage d'édition ponctuelle ; à revisiter (cache par `(chemin, set_simple)`) si la taille de fichier devient un problème sur un document avec beaucoup d'éditions.

## Tests qui ont vraiment servi

Aucun test automatisé n'est committé dans le repo (`backend/smoke_test.py` est un script de vérification manuelle, pas une suite CI). Ce qui a permis de trouver chacun des bugs ci-dessus :
- Toujours tester sur un **vrai** document (celui de l'utilisateur, `interialeortheses.pdf`), jamais seulement un PDF de test synthétique à une ligne — plusieurs bugs (tableau fusionné, collision de ressource police après plusieurs éditions) ne se manifestent que sur un document réel avec plusieurs polices et plusieurs éditions séquentielles.
- Après chaque édition, vérifier `page.get_text()` sur le résultat — pas seulement un rendu visuel — pour confirmer que l'ancien texte a bien disparu et que le nouveau est exactement celui tapé (caractère par caractère), pas une approximation qui a l'air correcte à l'œil.
