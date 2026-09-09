# Décisions techniques

Ce document explique le *pourquoi* des choix non-évidents du moteur d'édition (`backend/app/pdf_engine.py`). Le code a des commentaires courts sur le *quoi* ; ici c'est le contexte complet — souvent découvert en testant contre de vrais PDF, pas en lisant la doc PyMuPDF. Si tu retouches ce fichier, relis la section correspondante avant de « simplifier » quelque chose : plusieurs de ces détours existent parce que la version évidente produisait un bug silencieux.

## Réécriture réelle vs overlay

**Le problème** : la façon standard de « modifier » un PDF (la plupart des outils en ligne) est de poser un rectangle blanc sur l'ancien texte et d'écrire le nouveau par-dessus. Ça a l'air correct à l'écran mais le texte d'origine reste dans le flux du document — recherche et copier-coller renvoient encore l'ancienne valeur, et un fond coloré ou un tableau se retrouve avec un carré qui jure.

**Ce qu'on fait** : `page.add_redact_annot(rect, fill=None)` + `page.apply_redactions()` supprime réellement les opérateurs de dessin de glyphes qui touchent le rectangle — validé en vérifiant après coup que l'ancien texte n'est plus dans `page.get_text()`. C'est la seule partie du pipeline qui n'a pas de compromis : c'est une vraie suppression, pas un cache.

**Limite acceptée** : la redaction supprime *tout* contenu dans le rectangle, y compris un éventuel remplissage vectoriel (fond de cellule coloré). Non rencontré sur les blocs de texte courants (dates, noms, paragraphes), mais un tableau avec des cellules éditables sur fond coloré perdrait ce fond.

## Regroupement bloc vs ligne

**Le problème** : `page.get_text("dict")` de PyMuPDF renvoie déjà une hiérarchie bloc → ligne → span, mais son algorithme de blocs ne connaît pas la notion de colonne de tableau — il regroupe purement par proximité verticale. Sur un vrai document, une table entière (4 lignes × 8 colonnes) peut atterrir comme **un seul bloc** avec 34 « lignes » à l'intérieur. Éditer ce bloc en entier (comportement initial) effaçait toute la table pour la remplacer par le contenu d'une seule cellule.

**Ce qu'on a vérifié** : à l'inverse, les *lignes* de PyMuPDF à l'intérieur de ce bloc géant correspondent déjà exactement à une cellule chacune (bbox serrée, texte correct) — PyMuPDF sépare bien deux runs de texte dès que l'écart horizontal est significatif (vérifié empiriquement : un écart d'environ une taille de police suffit pour que PyMuPDF démarre une nouvelle « ligne », largement en dessous d'un écart de mise en page volontaire du type `"Nom :          DUPONT"`), seul le regroupement en *blocs* est trop permissif verticalement.

**Ce qu'on fait** (`extract_structure`) : on ignore complètement le regroupement en *blocs* de PyMuPDF et on édite **chaque ligne indépendamment**, tout le temps (`id` du type `b{i}l{j}`) — jamais de fusion multi-lignes. Voir la section suivante pour l'historique de pourquoi une version antérieure tentait de fusionner intelligemment certaines lignes, et pourquoi cette idée a été abandonnée.

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

## Pourquoi la fusion multi-lignes a été abandonnée

**Design initial** : une fonction `_is_coherent_paragraph` essayait de distinguer "ces lignes forment un seul paragraphe qui a wrappé" (à garder fusionné en un bloc, pour permettre le reflow — utile sur une adresse) de "ce sont des cellules de tableau que PyMuPDF a regroupées par erreur" (à éditer ligne par ligne), en se basant sur l'alignement des bords gauche/droit des lignes.

**Pourquoi ça n'a pas tenu, malgré deux itérations de durcissement** :

1. *Bug réel n°1* : sur un avis fiscal réel, deux lignes de titre indépendantes ("IMPOT SUR LES REVENUS DE L'ANNEE 2025" et "AVIS DE SITUATION DÉCLARATIVE ÉTABLI EN 2026", même police, même taille, toutes deux alignées à gauche) étaient fusionnées en un seul bloc — elles partagent le même bord gauche, exactement le signal utilisé pour reconnaître un paragraphe qui a wrappé. Éditer le "2026" éditait donc le bloc entier, effaçant silencieusement le "2025" au-dessus. Correctif : exiger en plus qu'un vrai wrap remplisse chaque ligne (sauf la dernière) jusqu'à une marge commune, un vrai paragraphe reliant deux lignes qui autrement s'arrêteraient chacune où bon leur semble.
2. *Bug réel n°2, découvert immédiatement après* : le même correctif appliqué en miroir à l'alignement à droite laissait passer une colonne de valeurs de tableau (numéro de référence / numéro d'ordre / date), alignées à droite par coïncidence de mise en page plutôt que par justification — éditer une valeur corrompait les trois.

**La leçon tirée** : l'alignement (gauche, droite, ou les deux) est une propriété bien trop commune dans un vrai document — titres, adresses, colonnes de tableau justifiées, numéros alignés à droite — pour, à elle seule, prouver qu'il s'agit d'un paragraphe qui a wrappé plutôt que de plusieurs lignes indépendantes qui partagent juste une mise en page. Chaque durcissement de l'heuristique a corrigé le cas trouvé, mais rien ne garantissait qu'un troisième vrai document n'allait pas trouver un troisième angle mort — et le coût d'un faux positif ici (perte silencieuse de contenu) est bien plus grave que celui d'un faux négatif (un peu plus de clics).

**Ce qu'on fait maintenant** : plus aucune fusion. `extract_structure` édite toujours ligne par ligne (voir section précédente), y compris pour un vrai paragraphe qui wrappe (une adresse se modifie désormais en plusieurs clics, un par ligne). Ce choix élimine toute cette classe de bug par construction, au prix d'un peu de confort en moins sur les champs multi-lignes légitimes — compromis assumé : mieux vaut plus de friction qu'un outil qui peut, sur un document qu'on n'a pas encore rencontré, corrompre silencieusement un champ qu'on n'a pas touché.

**Bonus obtenu gratuitement** : PyMuPDF sépare déjà de lui-même, en *lignes* distinctes, deux runs de texte sur la même ligne visuelle dès que l'écart horizontal dépasse environ une taille de police (vérifié empiriquement : un écart de 1 à 8pt à 10pt de corps reste un seul `line` avec plusieurs `spans`, un écart de 10pt ou plus démarre déjà une nouvelle `line`) — largement en dessous de l'écart d'un vrai champ "Label :          VALEUR". En éditant toujours au niveau ligne, on obtient donc aussi "un grand espace entre deux textes → deux blocs séparés" sans code de détection dédié.

## Un bloc ne doit jamais redacter le territoire d'un voisin

**Bug réel, découvert juste après le précédent** : même une fois les deux lignes de titre correctement séparées en deux blocs indépendants (section précédente), éditer la ligne du BAS ("AVIS DE SITUATION...") effaçait quand même la ligne du HAUT ("IMPOT SUR LES REVENUS..."). Cause : dans le document réel, les bbox des deux lignes se chevauchent physiquement de ~2,9pt (`title.bbox[3]=56.30` > `avis.bbox[1]=53.38`) — un interlignage serré, courant sur un document dense, fait que PyMuPDF mesure le bas du bbox d'une ligne comme débordant légèrement sur le haut du bbox de la suivante. La redaction d'un bloc utilise son propre bbox tel quel comme rectangle ; ce rectangle touchait donc physiquement quelques points du bloc voisin. `page.apply_redactions()` supprime un run de texte **entier** dès qu'il touche ne serait-ce qu'un point du rectangle — pas seulement la portion qui chevauche — d'où la ligne entière du voisin qui disparaît.

**Piège** : le correctif précédent (`_next_block_top`) ne protège que dans un sens (ne pas grandir/redacter vers le bas au-delà du voisin suivant). Il ne protège pas contre le sens inverse : le bloc édité peut avoir un bbox qui déborde déjà, à l'état naturel, sur le voisin du DESSUS — sans qu'aucune croissance ne soit en cause.

**Ce qu'on fait** (`_prev_block_bottom`, symétrique de `_next_block_top`) : avant de poser le rectangle de redaction, on cherche aussi le voisin du dessus qui chevauche horizontalement ce bloc. Si son bord bas dépasse le bord haut naturel du bloc édité, on remonte le bord haut du rectangle de redaction juste après ce chevauchement (`prev_bottom + 0.25`) au lieu d'utiliser le bord haut naturel du bloc. Le nouveau texte est toujours inséré à la baseline d'origine (`first_origin`, indépendante du rectangle de redaction) — seul le rectangle qui *supprime* l'ancien contenu est raboté, jamais la position du texte réinséré.

**Limite acceptée** : cette troncature peut, en théorie, laisser un minuscule fragment de l'ancien glyphe non supprimé dans la zone de chevauchement (quelques points en haut du bloc édité). En pratique le nouveau texte est redessiné au même endroit et le recouvre presque toujours. C'est un compromis délibéré, dans la même logique que le reste du fichier : accepter une imperfection cosmétique mineure sur le bloc qu'on édite plutôt que de risquer d'effacer un bloc qu'on n'édite pas.

**Test de non-régression** : les trois blocs du cas réel (titre, sous-titre, "pour justifier") ont chacun été édités individuellement, en vérifiant à chaque fois que les deux AUTRES survivent intacts — dans les deux sens (bloc du dessus édité, bloc du dessous édité) — en plus du paragraphe adresse qui doit toujours pouvoir grandir vers le bas sans se faire lui-même bloquer par ce garde-fou.

**Généralisation à l'horizontal** : le même risque existe entre deux cellules de tableau côte à côte dont les bbox se touchent (colonnes serrées) — pas seulement entre lignes empilées. `_next_block_top`/`_prev_block_bottom` ont été fusionnées en une seule fonction générique `_sibling_bound(block, all_blocks, edge)` paramétrée par bord (`"top"`/`"bottom"`/`"left"`/`"right"`), utilisée pour les 4 côtés du rectangle de redaction — y compris pour la largeur utilisée par la réduction de police (`safe_width`), pas seulement pour la redaction, afin que le nouveau texte ne chevauche pas non plus visuellement un voisin proche même quand rien n'a été effacé de son côté. Couvert par `backend/tests/test_pdf_engine.py`.

**Suite de tests** : ces garanties (et celles de la section précédente) sont maintenant figées dans `backend/tests/test_pdf_engine.py` (`unittest`, zéro nouvelle dépendance — lancer avec `.venv/bin/python -m unittest discover -s tests -v` depuis `backend/`). Avant leur ajout, chaque itération de ce fichier de décisions avait été validée à la main, une fois, dans le terminal — aucune garantie qu'un futur changement ne les recasse pas silencieusement.

## "Chevauchement perpendiculaire" ne suffit pas à définir un voisin

**Bug réel, introduit par la généralisation horizontale ci-dessus** : dans une colonne de valeurs à 3 lignes serrées ("310 12 47 5907959789 3" / "2" / "28/04/2026", le même cas que la section "Alignement à gauche..."), éditer la date ("2026" → "2099") laissait l'ancien dernier caractère ("6") non supprimé, visiblement plus grand que le nouveau texte à côté.

**Cause** : `_sibling_bound` considérait tout bloc qui chevauche perpendiculairement (même ligne pour un test horizontal, même colonne pour un test vertical) comme un "voisin" légitime sur ce bord, sans vérifier la taille du chevauchement. Or le "2", à interligne serré, chevauche verticalement ET la ligne du dessus ET celle du dessous — exactement le pattern déjà identifié plus haut. Utilisé comme signal de "voisin horizontal" pour la ligne "date" (dont il chevauche aussi la portion perpendiculaire), le "2" a été détecté comme "voisin à droite" de la date alors que son bbox est presque entièrement **imbriqué à l'intérieur** de celui de la date (x0="2" = 229.0, alors que la date s'étend de 188.96 à 233.996) — pas à côté. Le rectangle de redaction de la date a donc été raboté juste avant son propre dernier caractère.

**Ce qu'on fait** : un candidat ne compte comme "le prochain bloc sur ce bord" que si le chevauchement (le cas échéant) reste petit par rapport à la taille des deux blocs sur cet axe — au plus la moitié de l'étendue du plus petit des deux (`_sibling_bound._not_too_nested`). Un vrai espacement positif (un blanc normal avant le bloc suivant) est toujours accepté, quelle que soit sa taille ; seul un chevauchement *important* (imbrication, pas un simple contact de bord) est rejeté. Validé sur les coordonnées exactes du cas réel : le "2" n'est plus jamais considéré comme voisin horizontal de la date, tout en restant correctement identifié comme voisin vertical du bloc au-dessus (le "310 12 47...").

**Leçon** : généraliser un correctif géométrique par symétrie (vertical → horizontal) sans revalider les vrais cas limites du domaine a introduit un nouveau bug d'un coup. Toute nouvelle géométrie de garde-fou doit être testée contre TOUS les cas déjà connus, pas seulement le cas qui l'a motivée — d'où la suite de tests de la section précédente, étendue avec ce cas précis.

## Isoler le parsing PDF dans un sous-processus

**Le problème** : PyMuPDF est un binding Python autour de MuPDF, une bibliothèque C. Ouvrir/traiter un PDF qu'on n'a pas produit soi-même (upload utilisateur) avec une bibliothèque C a un historique de bugs mémoire (MuPDF a son lot de CVEs sur des fichiers malformés). Un PDF pathologique qui fait planter, boucler à l'infini, ou exploser la mémoire de MuPDF ferait planter tout le process FastAPI — donc toutes les requêtes en cours d'autres utilisateurs, sur un déploiement partagé (Render).

**Ce qu'on fait** (`backend/app/isolation.py`) : toute opération qui touche des bytes PDF non produits par ce process (`worker_validate_pdf`, `worker_extract_structure`, `worker_apply_edit` dans `pdf_engine.py`) tourne dans un sous-processus jetable (`multiprocessing`, contexte `spawn`), avec :

- une limite mémoire (`RLIMIT_AS`) et CPU (`RLIMIT_CPU`) posées dans l'enfant avant d'exécuter quoi que ce soit,
- un timeout mur (`TIMEOUT_SECONDS`) côté parent — si l'enfant ne répond pas à temps, il est `terminate()`/`kill()`.

Le pire qu'un PDF hostile peut faire est donc de gâcher un sous-processus de courte durée ; le process API n'est jamais impacté. Configurable via `SANDBOX_MAX_MEMORY_MB`, `SANDBOX_MAX_CPU_SECONDS`, `SANDBOX_TIMEOUT_SECONDS` (env vars, defaults 512/8/15).

**Pourquoi `spawn` et pas `fork`** : `fork` copierait les descripteurs de fichiers et l'état déjà chargé des extensions C du process parent (uvicorn, threads inclus) — dangereux à combiner avec des threads, et ça viderait une partie de l'intérêt de l'isolation. `spawn` redémarre un interpréteur propre à chaque appel : plus lent (~quelques dizaines à centaines de ms de coût d'import par appel), mais chaque appel part d'un état vierge.

**Limite connue, acceptée** : `RLIMIT_AS` n'est pas fiable sur macOS (utilisé en dev local) — `_set_limits()` avale l'erreur silencieusement dans ce cas et retombe uniquement sur le timeout. Sur Linux (Render, la cible de déploiement), les deux limites s'appliquent normalement.

## PDF protégés par mot de passe : rejeter tôt, avec un message clair

**Le problème** : PyMuPDF ouvre sans broncher un PDF chiffré/protégé par mot de passe et répond même correctement à `doc.page_count` — mais toute opération réelle dessus (`get_text`, redaction...) échoue ensuite avec une erreur opaque MuPDF ("document closed or encrypted"). Sans garde-fou, l'upload aurait semblé réussir, et l'échec ne serait apparu qu'au premier clic sur un champ, avec un message incompréhensible pour l'utilisateur.

**Ce qu'on fait** (`worker_validate_pdf`) : on vérifie `doc.needs_pass` juste après l'ouverture, avant même de renvoyer `page_count`, et on rejette l'upload immédiatement avec un message explicite ("password-protected PDFs are not supported"). Le problème est signalé au bon moment (à l'upload), pas plus tard au premier clic.

## Tests qui ont vraiment servi

Aucun test automatisé n'est committé dans le repo (`backend/smoke_test.py` est un script de vérification manuelle, pas une suite CI). Ce qui a permis de trouver chacun des bugs ci-dessus :

- Toujours tester sur un **vrai** document (celui de l'utilisateur, `interialeortheses.pdf`), jamais seulement un PDF de test synthétique à une ligne — plusieurs bugs (tableau fusionné, collision de ressource police après plusieurs éditions) ne se manifestent que sur un document réel avec plusieurs polices et plusieurs éditions séquentielles.
- Après chaque édition, vérifier `page.get_text()` sur le résultat — pas seulement un rendu visuel — pour confirmer que l'ancien texte a bien disparu et que le nouveau est exactement celui tapé (caractère par caractère), pas une approximation qui a l'air correcte à l'œil.
