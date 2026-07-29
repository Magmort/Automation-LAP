# Expérience C — Tour autonome et modèle minimal de circuit

- **Statut :** validée avec réserves
- **Ticket :** #5
- **Responsable :** à renseigner
- **Date de début :** 2026-07-27
- **Date de conclusion :** 2026-07-27
- **Version du protocole :** 0.1
- **Dépendance d'entrée :** expérience B validée avec réserves, pas candidat `1/60 s`, référence `1/120 s`
- **Dépendance produite :** `TrackDefinition` minimal pour l'expérience G

## 1. Question testée

Une IA de conduite peut-elle suivre une trajectoire, adapter sa vitesse et récupérer une perturbation à partir d'un modèle de circuit minimal indépendant de tout format tiers, sans script par virage ?

## 2. Hypothèse

L'expérience B fournit un état dynamique 2D suffisant pour tester un tour autonome simple : vitesse, position, cap et commandes throttle/frein/direction.

L'hypothèse est qu'un prototype peut :

- définir un `TrackDefinition` minimal à partir des besoins du contrôleur ;
- valider automatiquement une piste canonique créée directement dans ce format ;
- prétraiter la géométrie en distance curviligne, tangente, normale, largeur et courbure ;
- exécuter un contrôleur qui suit une trajectoire de référence sans script spécifique par virage ;
- mesurer l'erreur latérale, la progression, les tours et la récupération après perturbation.

## 3. Hors périmètre

- import UR2D2, traité par G ;
- Unity, rendu, caméra ou interface ;
- trafic, dépassement et collisions entre voitures ;
- optimisation de trajectoire de production ;
- stands, secteurs multiples, dénivelé, dévers et surfaces décoratives ;
- modèle pneu/suspension détaillé.

## 4. Environnement

| Élément | Version ou valeur |
|---|---|
| Système d'exploitation | Windows, machine locale |
| Matériel pertinent | non significatif pour C-S01 à C-S06 |
| Runtime / SDK | Python embarqué Codex pour prototype hors Unity |
| Version du prototype | `prototypes/autonomous-lap/` |
| Entrées utilisées | `prototypes/autonomous-lap/fixtures/canonical_track.json`, export A9 QFC55 |
| Graine aléatoire | aucune pour les scénarios déterministes initiaux |

## 5. Protocole reproductible

1. Charger la piste canonique `TrackDefinition` v0.1.
2. Valider le contrat minimal : identité, unités SI, boucle fermée, points, largeurs, départ et checkpoints.
3. Prétraiter la ligne centrale : segments, distances cumulées, longueur, tangentes, normales et courbure.
4. Exécuter les scénarios C-S01 à C-S06 avec `1/60 s` comme pas candidat et `1/120 s` comme référence.
5. Mesurer stabilité, erreur latérale, sorties de piste, temps au tour et récupération.
6. Archiver les résultats dans `prototypes/autonomous-lap/results/`.

Les champs calculables ne doivent pas être stockés comme vérité source si le prototype peut les reconstruire de manière déterministe.

## 6. Scénarios

| Identifiant | Description | Entrées | Répétitions |
|---|---|---|---:|
| C-S01 | Contrat `TrackDefinition` et prétraitement piste canonique | piste canonique | 1, validée |
| C-S02 | Suivi de trajectoire à vitesse contrainte | piste canonique, modèle B | 3 tours, validée |
| C-S03 | Adaptation de vitesse par courbure | piste canonique, QFC55 A9 | 3 tours, validée avec réserves |
| C-S04 | Récupération après perturbation latérale | piste canonique, QFC55 A9 | 3 perturbations, validée avec réserves |
| C-S05 | Différences de compétence pilote | piste canonique, QFC55 A9, profils de contrôle | 3 profils, validée avec réserves |
| C-S06 | Contrat minimal final pour G | résultats C-S01 à C-S05 | 1 consolidation, validée avec réserves |

## 7. Métriques

| Métrique | Unité | Méthode de collecte | Seuil ou attente |
|---|---|---|---|
| Erreurs de contrat | nombre | validateur C-S01 | 0 |
| Longueur de boucle | m | somme des segments | finie, > 100 m |
| Écart de fermeture | m | dernier point vers premier point implicite | segment de fermeture valide |
| Largeur roulable minimale | m | largeur gauche + droite | > 4 m |
| Courbure maximale | 1/m | prétraitement | finie, documentée |
| Tours terminés | nombre | simulation C-S02+ | au moins 3 consécutifs |
| Sorties de piste | nombre | distance latérale > largeur disponible | 0 ou réserve explicite |
| Erreur latérale moyenne | m | projection sur ligne centrale | mesurée |
| Variation des temps au tour | % | trois tours consécutifs | faible et documentée |
| Récupération perturbation | booléen | C-S04 | retour dans la largeur de piste |
| Écart entre profils pilote | s | C-S05 | ordre et amplitude documentés |
| Saturation du grip | % ticks, ratio | C-S05 témoin négatif | saturation détectée et trajectoire dégradée |
| Champs source du contrat | liste | C-S06 | champs strictement nécessaires documentés |

## 8. Critères de réussite et d'échec

### Réussite

- [x] le `TrackDefinition` minimal ne dépend ni de Unity ni d'un éditeur externe ;
- [x] une piste canonique peut être validée et prétraitée automatiquement ;
- [x] plusieurs tours sont effectués sans sortie systématique ;
- [x] l'erreur latérale et la variation des temps sont mesurées ;
- [x] une perturbation modérée peut être récupérée ;
- [x] compétence et marge de risque produisent des comportements différents ;
- [x] les champs strictement nécessaires au contrôleur sont identifiés ;
- [x] le contrat permet de tester ultérieurement un importeur externe.

### Échec ou révision obligatoire

- [ ] le contrat minimal ne permet pas de projeter une voiture sur la piste ;
- [ ] les limites nécessaires au contrôle sont absentes ou ambiguës ;
- [ ] le contrôleur nécessite des scripts par virage ;
- [ ] la piste canonique ne peut pas être validée de manière déterministe ;
- [ ] le format devient dépendant d'un outil externe avant G.

## 9. Résultats

### Données brutes

Premiers résultats disponibles :

- `prototypes/autonomous-lap/results/C_S01_TRACK_CONTRACT_RESULT.md`
- `prototypes/autonomous-lap/results/c_s01_track_contract_summary.json`
- `prototypes/autonomous-lap/results/C_S02_PATH_FOLLOWING_RESULT.md`
- `prototypes/autonomous-lap/results/c_s02_path_following_summary.json`
- `prototypes/autonomous-lap/results/C_S03_CURVATURE_SPEED_RESULT.md`
- `prototypes/autonomous-lap/results/c_s03_curvature_speed_summary.json`
- `prototypes/autonomous-lap/results/C_S03_CURVATURE_SPEED_VISUALIZATION.svg`
- `prototypes/autonomous-lap/results/C_S04_LATERAL_RECOVERY_RESULT.md`
- `prototypes/autonomous-lap/results/c_s04_lateral_recovery_summary.json`
- `prototypes/autonomous-lap/results/C_S04_LATERAL_RECOVERY_VISUALIZATION.svg`
- `prototypes/autonomous-lap/results/C_S05_DRIVER_PROFILES_RESULT.md`
- `prototypes/autonomous-lap/results/c_s05_driver_profiles_summary.json`
- `prototypes/autonomous-lap/results/C_S05_DRIVER_PROFILES_VISUALIZATION.svg`
- `prototypes/autonomous-lap/results/C_S06_CONTRACT_CONSOLIDATION_RESULT.md`
- `prototypes/autonomous-lap/results/c_s06_contract_consolidation_summary.json`

### Synthèse

| Scénario | Résultat | Variance | Observation |
|---|---:|---:|---|
| C-S01 | 1 piste valide / 1 | aucune | contrat minimal chargeable, boucle prétraitée |
| C-S02 | 3 tours terminés / 3 | `1/60 s` et `1/120 s` | suivi de ligne validé sans sortie de piste |
| C-S03 | 3 tours terminés / 3 | `1/60 s` et `1/120 s` | adaptation de vitesse par courbure validée avec QFC55, réserve sur le proxy de grip latéral |
| C-S04 | 3 perturbations récupérées / 3 | `1/60 s` et `1/120 s` | offsets latéraux jusqu'à 3,25 m, récupérés sans sortie |
| C-S05 | 3 profils terminés / 3 | `1/60 s` et `1/120 s` | profils prudent, équilibré et agressif différenciés sur temps, vitesse et erreur |
| C-S06 | contrat consolidé | aucune | `TrackDefinition` v0.1 validé comme contrat d'entrée de G |

## 10. Analyse

C-S01 définit un premier contrat `TrackDefinition` v0.1 centré sur ce dont le contrôleur aura besoin :

- une ligne centrale fermée ordonnée ;
- des largeurs gauche/droite par point ;
- des conventions SI explicites ;
- un sens de circulation ;
- une ligne de départ et des checkpoints ;
- une surface principale et une adhérence indicative ;
- des valeurs dérivées calculables : longueur, distance curviligne, tangente, normale et courbure.

Ce contrat est suffisamment petit pour être reconstruit par G depuis un importeur, tout en évitant de dépendre d'UR2D2 dans C.

C-S02 valide un premier contrôleur de suivi de trajectoire à vitesse contrainte. Le contrôleur utilise :

- projection de la position sur la ligne centrale ;
- cible lookahead à 14 m ;
- loi pure pursuit ;
- vitesse constante contrainte à 45 km/h ;
- intégration cinématique au pas `1/60 s` et `1/120 s`.

Les deux pas de temps terminent trois tours sans sortie de piste. Au pas de référence `1/120 s`, l'erreur latérale moyenne est de 0,173 m, l'erreur latérale maximale de 0,693 m, et les trois tours durent environ 30,45 s chacun. Ce résultat confirme que le contrat C-S01 suffit pour projeter une voiture, mesurer sa progression, compter les tours et suivre une cible sans script par virage.

C-S03 remplace la vitesse constante par une cible calculée depuis la courbure anticipée de la piste. Le scénario utilise la QFC55 exportée en A9 (`0.1.13-a9-steering-raw-graphs`) :

- accélération par pente de `AccelerationToTopSpeed.Speed/Time` ;
- freinage par pente de `Braking.Speed/Time` ;
- vitesse maximale par la courbe `AccelerationToTopSpeed.Speed` ;
- limite latérale provisoire par proxy `FrontGripG + RearGripG`, avec facteur de sécurité de 0,85.

Les deux pas de temps terminent trois tours sans sortie de piste. Au pas de référence `1/120 s`, la durée totale est de 83,33 s, la vitesse moyenne de 49,31 km/h, la vitesse maximale de 62,79 km/h, l'erreur latérale moyenne de 0,231 m et l'erreur latérale maximale de 0,807 m. Le modèle atteint 0,446 g latéral contre une limite provisoire de 1,008 g. C-S03 valide donc l'adaptation de vitesse par courbure, avec réserve explicite sur la calibration latérale issue de B-S04.

C-S04 conserve exactement la logique C-S03 et applique trois perturbations latérales instantanées à progression fixe. La perturbation déplace la voiture suivant la normale locale de la ligne centrale, sans modifier sa vitesse ni son cap :

- `p1-left-entry` : `+2,75 m` à `0,55` tour ;
- `p2-right-mid` : `-3,25 m` à `1,35` tour ;
- `p3-left-late` : `+3,00 m` à `2,15` tours.

La récupération est validée quand l'erreur latérale absolue repasse sous `0,75 m` en moins de `7 s`, sans sortie de piste. Au pas de référence `1/120 s`, les trois perturbations sont récupérées en `1,433 s`, `1,800 s` et `2,467 s`. Les trois tours restent terminés en 83,33 s, sans sortie, avec une erreur latérale moyenne de 0,348 m et une erreur latérale maximale égale à l'offset maximal de 3,25 m. C-S04 valide donc la capacité du contrôleur à revenir vers la trajectoire après un écart modéré, avec la même réserve latérale que C-S03.

C-S05 conserve la QFC55, la piste canonique et le contrôleur C-S03, puis fait varier uniquement les paramètres de contrôle :

- marge de vitesse et d'adhérence ;
- distance de lookahead ;
- usage de l'accélération et du freinage ;
- temps de réponse longitudinal ;
- gain et limite de direction.

Trois profils sont testés : prudent, équilibré et agressif. Au pas de référence `1/120 s`, ils terminent trois tours sans sortie de piste. Le profil prudent réalise 115,28 s avec 35,67 km/h de moyenne, le profil équilibré 83,33 s avec 49,31 km/h, et le profil agressif 56,84 s avec 72,64 km/h. L'écart entre profils extrêmes est de 58,44 s sur trois tours, bien supérieur au seuil de 8 s. Les erreurs latérales moyennes suivent aussi l'intention des profils : `0,126 m` pour le prudent, `0,231 m` pour l'équilibré et `0,302 m` pour l'agressif, qui monte jusqu'à `1,002 g` latéral.

C-S05 ajoute désormais un témoin négatif de sur-vitesse. Ce cas demande plus de yaw que le grip véhicule ne permet ; au pas de référence `1/120 s`, il sature le grip sur `84,11 %` des ticks, atteint un ratio de saturation maximal de `5,87x`, produit `24,197 m` d'erreur latérale maximale et sort de piste. Ce témoin empêche de valider le jalon par simple différenciation artificielle de vitesses. C-S05 valide donc que des profils de compétence et de marge de risque produisent des comportements mesurablement différents sans modifier ni le véhicule, ni le circuit, ni le contrat de piste, avec une limite physique minimale démontrée.

Le rendu visuel C-S05 ne cherche pas à prouver des trajectoires nominales différentes : les trois profils visent la même ligne cible et peuvent donc se superposer. La validation visuelle repose plutôt sur les graphes de vitesse, de G latéral demandé et d'erreur latérale, plus le témoin négatif de sur-vitesse.

C-S06 consolide les preuves C-S01 à C-S05 et fige `TrackDefinition` v0.1 comme contrat candidat pour G. Les champs source retenus sont :

- identité et version : `kind`, `schemaVersion`, `trackId`, `name` ;
- conventions : unités SI, axes 2D et orientation ;
- boucle et sens de progression : `closedLoop`, `direction` ;
- surface principale : `surface.type`, `surface.grip` ;
- géométrie source : `centerline[].id`, `x`, `y`, `leftWidth`, `rightWidth` ;
- origine fonctionnelle : `startLine.centerlinePointId`, `startLine.width` ;
- checkpoints : `checkpoints[].id`, `checkpoints[].centerlinePointId`.

Les segments, distances cumulées, tangentes, normales, courbures, projections, erreurs latérales et compteurs de tours restent des valeurs dérivées. C-S06 valide donc que G peut tenter de reconstruire ce contrat depuis UR2D2 sans imposer son format au modèle interne.

## 11. Limites

- La piste canonique est synthétique et ne prouve pas encore qu'un circuit réel importé sera exploitable.
- La courbure est calculée depuis une polyligne, pas depuis une courbe analytique.
- C-S03 valide une adaptation de vitesse autonome, mais sa limite latérale reste un proxy à recalibrer.
- C-S04 injecte des déplacements latéraux idéalisés ; il ne modélise pas encore une perte d'adhérence ou un contact physique.
- C-S05 compare des profils de contrôle heuristiques ; il ne prouve pas encore une architecture IA complète avec décision stratégique.
- La saturation latérale ajoutée à C-S03/C-S04/C-S05 borne le yaw demandé, mais ne distingue pas encore un vrai sous-virage d'un vrai survirage.
- Les limites de piste sont représentées par des largeurs scalaires, pas par des polygones détaillés.

## 12. Conclusion

### Décision

> Validée avec réserves.

### Niveau de confiance

> Moyen à bon pour le contrat minimal C. Le contrat est petit, validable et déjà utilisé par un contrôleur avec adaptation de vitesse, récupération d'écart latéral, profils différenciés et témoin de saturation du grip. La limite latérale du véhicule reste calibrable.

## 13. Conséquences

### Paramètres retenus

- `TrackDefinition` v0.1 comme contrat candidat ;
- unités SI : mètres, secondes, radians ;
- boucle fermée implicite entre dernier et premier point ;
- `1/60 s` comme pas candidat pour le contrôleur ;
- `1/120 s` comme référence de vérification ;
- QFC55 comme véhicule de référence pour C-S03 à C-S05 tant que les données latérales restent à consolider ;
- seuil de récupération C-S04 candidat : erreur latérale absolue inférieure ou égale à `0,75 m` en moins de `7 s` ;
- profils pilote C-S05 candidats : prudent, équilibré, agressif.
- contrat C-S06 candidat pour G : champs source `TrackDefinition` v0.1, valeurs dérivées reconstruites au runtime.

### Risques résiduels

- le contrôleur peut exiger une trajectoire de référence plus riche que la ligne centrale ;
- les largeurs scalaires peuvent être insuffisantes pour certaines géométries ;
- la courbure polygonale peut nécessiter un lissage contrôlé ;
- la limite latérale `FrontGripG + RearGripG` est utile comme garde-fou mais pas encore comme vérité physique ;
- la perturbation C-S04 est cinématique et ne couvre pas encore les erreurs dues à une collision, un dérapage ou une commande pilote incorrecte ;
- les profils C-S05 sont des réglages de contrôle et non encore des politiques IA complètes ;
- G peut ne pas retrouver tous les champs sans calibration.

### Documents affectés

- plan de faisabilité ;
- tableau de bord Phase 1 ;
- rapport consolidé ;
- protocole G lorsque le contrat C sera stabilisé.

### Travaux suivants

- lancer l'expérience G avec `TrackDefinition` v0.1 comme cible de conversion ;
- utiliser C-S01 et C-S02 comme tests minimaux de validation d'un import ;
- conserver la saturation du grip comme garde-fou, sans la traiter comme modèle pneus détaillé.
