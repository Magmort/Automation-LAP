# Expérience H - Import du modèle minimal depuis les fichiers de tracks UR2D2

- **Statut :** validée avec réserves
- **Ticket :** #11
- **Responsable :** Codex / Jérémie
- **Date de début :** 28 juillet 2026
- **Date de conclusion :** 29 juillet 2026
- **Version du protocole :** 0.1
- **Dépendance :** C-S06 fournit `TrackDefinition` v0.1 comme contrat cible.
- **Expérience sœur :** G explore les sauvegardes `.sav` du Track Editor ; H explore les vrais fichiers de piste utilisés ou exportés par UR2D2.

## 1. Question testée

Pouvons-nous reconstruire automatiquement un `TrackDefinition` minimal validé par l'expérience C à partir des vrais fichiers de tracks d'Ultimate Racing 2D 2, c'est-à-dire les fichiers finis utilisés par le jeu ou produits à l'export final de la piste ?

## 2. Hypothèse

Les fichiers de piste finis peuvent être plus proches du format runtime que les sauvegardes `.sav` de l'éditeur. Ils pourraient donc contenir une représentation déjà normalisée de la géométrie, des objets fonctionnels, des surfaces et du chronométrage.

À l'inverse, ils peuvent aussi perdre des informations d'édition utiles : points de contrôle intermédiaires, noms, objets non utilisés à l'exécution ou métadonnées de construction. H doit donc vérifier si le format final est plus exploitable que le format éditeur, ou seulement complémentaire.

## 3. Relation entre G et H

G et H doivent rester séparées jusqu'à preuve que les formats partagent les mêmes structures.

| Expérience | Source | Risque testé |
|---|---|---|
| G | Sauvegardes `.sav` du Track Editor | Le format d'édition contient-il assez d'information pour reconstruire le contrat ? |
| H | Vrais fichiers de tracks UR2D2 | Le format final/runtime contient-il directement les données nécessaires au contrat ? |

Si les deux chemins sont viables, la décision finale comparera :

- disponibilité des données nécessaires ;
- stabilité du format ;
- quantité de corrections manuelles ;
- facilité de calibration de l'échelle et des axes ;
- robustesse sur plusieurs circuits ;
- contraintes de redistribution ;
- dépendance éventuelle à l'éditeur.

## 4. Contrat cible issu de C

H vise le même contrat que G : `TrackDefinition` v0.1 consolidé par C-S06.

Les champs source minimaux à reconstruire sont :

- identité et version ;
- unités SI ou conversion déterministe ;
- axes, orientation, boucle et sens ;
- surface principale ;
- ligne centrale ordonnée avec largeurs gauche/droite ;
- ligne de départ ;
- checkpoints.

Les données runtime dérivées par C ne doivent pas devenir des champs source importés.

## 5. Hors périmètre

Cette expérience ne cherche pas à :

- redistribuer des pistes officielles ou fichiers protégés ;
- reproduire le rendu exact d'UR2D2 ;
- importer tous les assets décoratifs ;
- remplacer G avant comparaison ;
- figer le format runtime permanent du projet ;
- prouver le contrôleur autonome, déjà traité par C.

## 6. Jeu de données attendu

Le jeu minimal doit contenir au moins :

| Fixture | Source souhaitée | But |
|---|---|---|
| R00 | Piste simple exportée depuis le circuit T02 ou équivalent | Comparer le runtime au `.sav` éditeur |
| R01 | Piste avec départ et checkpoints | Identifier le chronométrage final |
| R02 | Piste avec murs ou limites | Identifier les bords et obstacles |
| R03 | Piste avec surfaces distinctes | Identifier les surfaces et coefficients possibles |
| R04 | Une piste réelle ou exemple fourni par le jeu | Vérifier que l'analyse ne dépend pas uniquement d'un circuit artificiel |

Pour chaque fixture :

- conserver le dossier ou package complet ;
- noter la version d'UR2D2 ;
- noter si la piste vient d'un export, d'un dossier runtime local ou d'un exemple du jeu ;
- conserver les noms originaux des fichiers ;
- ne pas committer de contenu non redistribuable.

## 7. Scénarios

### H-S00 - Inventaire des fichiers runtime

1. Localiser les fichiers produits par l'export final ou utilisés par le jeu.
2. Relever noms, tailles, dates, empreintes et signatures.
3. Identifier archives, compression, texte, images et binaires.
4. Extraire les chaînes lisibles et indices de structure.
5. Comparer la composition des packages entre fixtures.
6. Produire une visualisation de couverture.

**Résultat :** H-S00 est validée avec réserves. Une fixture runtime locale `R00_runtime_track_2`, copiée dans le dossier ignoré `fixtures/source`, contient 8 fichiers : `track.data`, `track_info.data`, `track_editor.sav`, 5 PNG de rendu ou surfaces. Aucun conteneur compressé n'est détecté ; `track.data`, `track_info.data` et `track_editor.sav` sont des binaires inconnus avec chaînes lisibles. Le statut d'inventaire est `ready-for-h-s01-comparison`.

### H-S01 - Comparaison avec les sauvegardes G

1. Comparer les chaînes et signatures de R00 avec T02/T05/T07.
2. Rechercher les mêmes coordonnées ou objets fonctionnels dans les deux formats.
3. Déterminer si H peut réutiliser une partie des hypothèses de G.
4. Identifier les informations présentes uniquement dans G ou uniquement dans H.

**Résultat :** H-S01 est validée. `track.data` contient les coordonnées brutes des clés de route G (`1424`, `2480`, `1072`, `1712`) et des points runtime échantillonnés. Les trois premiers records compacts `checkpoint` correspondent exactement aux checkpoints G : `Checkpoint 2`, `Checkpoint 1` et `Finish`, avec rotation runtime égale à la rotation éditeur moins `90°`. `track_info.data` fournit les métadonnées de piste (`First_Track`, `track:2/2796.14`, pays, type, météo/conditions). `track_editor.sav` est présent dans le package runtime mais son hash ne correspond pas aux fixtures G inventoriées, car la piste a été réexportée après corrections.

**Complément H-S01b :** l'inventaire exhaustif du `track_editor.sav` embarqué est validé. Tous les éléments attendus de la piste issue de l'éditeur sont localisés : 4 segments de route, 3 lignes IA, 3 checkpoints, 1 pitlane, 1 entrée de pitlane, 1 sortie de pitlane, 1 mur multi-segment, 1 zone de sable polygonale et 1 zone d'arbres polygonale. H-S01b a montré que `track.data` contient des signaux runtime corrélables, mais H-S02 retient finalement une voie plus simple : utiliser `track_editor.sav` pour les données de simulation, `track_info.data` pour les métadonnées et les PNG comme fonds/couches visuels existants.

### H-S02 - Lecteur brut single-track `.sav` runtime

1. Lire le dossier runtime d'une piste sans régénérer les visuels UR2D2.
2. Extraire `track_info.data` comme source de métadonnées générales.
3. Lire `track_editor.sav` comme source vectorielle brute pour la simulation.
4. Inventorier les calques PNG (`track.png`, `track_preview.png`, `grass.png`, `gravel.png`, `minimap.png`) comme fonds/couches runtime.
5. Produire `UR2D2RuntimeTrackData` v0.1 sérialisable.
6. Marquer explicitement les données encore non interprétées, notamment la route principale.

**Résultat :** H-S02 est validée sur `R00_runtime_track_2`. Le lecteur produit `UR2D2RuntimeTrackData` v0.1 avec `track_editor.sav` comme unique source de données de simulation, `track_info.data` comme source de métadonnées et les PNG comme fonds/couches visuels. Sur R00, la sortie identifie explicitement la piste principale (`0x004d`), les deux voies de pitlane (`0x0997`, `0x0a43`), le mur (`0x06e6`) et les 3 checkpoints. Le statut est `ready-for-h03-route-and-overlay`. H-S02 ne convertit pas encore les unités en mètres et n'aligne pas encore les coordonnées `.sav` sur les pixels des PNG.

### H-S03 - Extraction de la route principale

1. Sélectionner ou reconstruire la route principale depuis les blocs vectoriels du `.sav`.
2. Déterminer boucle, sens, départ et checkpoints.
3. Identifier les lignes IA utiles comme données d'aide éventuelles.
4. Produire une représentation brute de simulation sans redessiner les éléments visuels.

**Résultat :** H-S03 est validée avec réserves. La piste principale lue à l'offset `0x004d` est convertie vers un `TrackDefinition` v0.1 en coordonnées métriques, avec l'échelle `12,8` unités éditeur par mètre reprise de la calibration G, une largeur source de `10,000 m`, et une orientation de simulation `clockwise`. Le tracé vectoriel est échantillonné à 16 points par segment, soit 64 points de centerline. La validation C-S01 passe sans erreur : longueur `275,352 m`, largeur minimale `10,000 m`, courbure maximale `0,241360 1/m`. Les deux voies de pitlane et le mur sont également convertis en géométrie métrique hors contrat C.

### H-S04 - Superposition sur fond runtime

Superposer, lorsque possible, les données de simulation sur les PNG existants :

- fond de carte `track.png` ou `track_preview.png` ;
- ligne centrale ;
- points et segments décodés ;
- départ et checkpoints ;
- sens de circulation.

**Résultat :** H-S04 est validée visuellement. La géométrie issue du `.sav` est superposée au fond runtime `track_preview.png`, embarqué directement dans le SVG. Le mapping utilise les coordonnées éditeur écran en Y descendant, avec `track.png` `4096 x 2048 px` vers `track_preview.png` `768 x 384 px`, soit une échelle uniforme `0,1875`. La largeur de piste source `10,000 m` correspond à `24,000 px` sur la preview, et la largeur pitlane `5,000 m` à `12,000 px`. Les contrôles passent : fond présent, ratio identique, échelle uniforme, géométrie dans le canvas, piste, pitlane, mur, checkpoints et TrackDefinition H-S03 valides.

### H-S05 - Paquet d'import simulation

1. Consolider le `TrackDefinition` v0.1 produit en H-S03.
2. Ajouter les données hors contrat nécessaires à la simulation : voies de pitlane, murs et points de checkpoints.
3. Ajouter le mapping runtime validé en H-S04 : fond PNG préféré, transformation coordonnées éditeur vers pixels et politique de rendu.
4. Documenter la provenance des fichiers (`track_editor.sav`, `track_info.data`, PNG) et l'absence de dépendance à `track.data`.
5. Produire un paquet JSON déterministe et un résumé de validation.

**Résultat :** H-S05 produit un paquet `UR2D2ImportedTrackPackage` prêt pour H-S06. Le statut est `import-package-ready-for-h-s06` et tous les contrôles passent : `trackDefinitionValid`, `overlayValidated`, `trackDataNotRequired`, `pitlaneIncluded`, `wallsIncluded`, `backgroundIncluded` et `uniformPixelMapping`. Le paquet contient une piste de 64 points, `275,352 m` de longueur, `10,000 m` de largeur minimale, 2 voies de pitlane, 1 mur, 3 checkpoints, le fond préféré `track_preview.png` et la provenance complète. Les assets PNG sont référencés par chemin local et ne sont pas redistribués.

### H-S06 - Validation fonctionnelle et comparaison G/H

1. Charger le `TrackDefinition` converti depuis H.
2. Exécuter le contrôleur issu de C.
3. Afficher la voiture sur le fond de carte runtime.
4. Comparer le résultat avec le même circuit importé ou approximé depuis G.
5. Décider si le chemin runtime H remplace, complète ou invalide le chemin éditeur G.

**Résultat :** H-S06 est validée visuellement. Le paquet H-S05 est consommé directement par le contrôleur C-S03 avec la QFC55 issue de A9. Les deux pas de temps testés (`1/60 s` et `1/120 s`) sont stables. La référence `1/120 s` boucle 3 tours en `62,658 s`, avec des tours de `20,89 s`, `20,88 s` et `20,87 s`, une vitesse moyenne de `46,09 km/h`, une vitesse maximale de `80,72 km/h`, une erreur latérale moyenne de `0,927 m`, une erreur latérale maximale de `3,042 m` et aucune sortie de piste. Le rendu `H_S06_FUNCTIONAL_REPLAY_VISUALIZATION.svg` superpose la trajectoire colorée par vitesse, la piste, la pitlane, le mur et les checkpoints sur `track_preview.png`.

**Réserve :** H-S06 valide le chemin d'import et l'intégration avec le contrôleur autonome actuel. Les murs et la pitlane sont disponibles comme données et rendus visuellement, mais ils ne sont pas encore imposés comme contraintes de conduite.

## 8. Métriques

| Métrique | Unité | Attente |
|---|---|---|
| Champs obligatoires reconstruits | % | 100 % ou limitation explicitement acceptable |
| Fichiers nécessaires par piste | nombre | Aussi faible que possible |
| Archives ou compression détectées | type | Documentées et reproductibles |
| Intervention manuelle | opérations par circuit | Aussi proche de zéro que possible |
| Écart face à G | champs / offsets / géométrie | Mesuré quand une piste comparable existe |
| Résultat du validateur C | succès / erreurs | Succès sans correction cachée |
| Déterminisme | empreinte de sortie | Identique pour entrées identiques |
| Versions testées | nombre | Au moins la version installée de référence |

## 9. Critères de réussite

- [x] au moins un vrai fichier de track est inventorié ;
- [x] les fichiers nécessaires à une piste sont identifiés ;
- [x] un circuit simple est converti sans édition point par point ;
- [x] la sortie respecte `TrackDefinition` v0.1 ;
- [x] la boucle, le sens, le départ et les checkpoints sont corrects ou les limites sont explicites ;
- [x] les transformations de coordonnées et d'échelle sont documentées ;
- [x] l'import est déterministe ;
- [x] les écarts avec G sont décrits ;
- [x] la piste convertie est utilisable par le contrôleur C.

## 10. Conditions de révision ou d'échec

L'hypothèse doit être révisée si :

- le format final ne contient pas la géométrie nécessaire ;
- la piste runtime référence des données externes difficiles à localiser ;
- l'extraction impose une redistribution non autorisée ;
- les exports finaux changent trop selon la version ;
- les fichiers runtime perdent des informations indispensables présentes dans les `.sav`.

Un échec de H ne remet pas en cause G. Il indique seulement que les fichiers finaux ne sont pas une meilleure source que les sauvegardes éditeur.

## 11. Conclusions possibles

- **Validée :** les vrais fichiers de tracks suffisent pour alimenter `TrackDefinition`.
- **Validée avec réserves :** le chemin runtime est viable avec calibration ou complément limité.
- **À modifier :** le chemin runtime doit être combiné avec G ou un outil assisté.
- **Non viable :** les vrais fichiers de tracks ne sont pas retenus comme source.

## 12. Livrables

- rapport complété dans ce document ;
- inventaire des fichiers runtime ;
- comparaison G/H ;
- schéma provisoire `UR2D2RuntimeTrackData` ;
- lecteur ou importeur expérimental ;
- visualiseur ;
- exemple de sortie `TrackDefinition` ;
- décision sur le meilleur chemin d'import UR2D2.

## 13. Conclusion

H est validée avec réserves. Les vrais dossiers de tracks UR2D2 fournissent une chaîne exploitable : `track_editor.sav` pour la géométrie de simulation, `track_info.data` pour les métadonnées, et les PNG runtime pour l'affichage. `track.data` n'est pas requis pour le chemin critique.

Cette validation confirme que le projet dispose d'un chemin complet : données véhicule Automation, modèle dynamique candidat, contrôleur autonome, trafic, replay, performance et import de circuit UR2D2 fonctionnel. Les réserves restantes portent sur la robustesse multi-circuits, la calibration physique finale, et l'intégration production.
