# Expérience B — Dynamique d'une voiture

- **Statut :** validée avec réserves
- **Ticket :** #4
- **Responsable :** à renseigner
- **Date de début :** 2026-07-26
- **Date de conclusion :** 2026-07-26
- **Version du protocole :** 0.1
- **Dépendance d'entrée :** `AutomationRawVehicleData` v0.1 produit par l'expérience A

## 1. Question testée

Un modèle 2D simple, alimenté par les données brutes Automation, peut-il produire des différences plausibles entre voitures pour l'accélération, le freinage, la vitesse maximale et le virage, sans règles spécifiques à une voiture ?

## 2. Hypothèse

Automation fournit déjà des résultats calculés et des courbes exploitables. L'expérience B ne doit donc pas recalculer aveuglément ce qui existe déjà.

L'hypothèse est qu'un prototype peut :

- relire les courbes Automation disponibles comme références ou tables d'entrée ;
- interpoler les graphes d'accélération et de freinage pour les scénarios longitudinaux ;
- utiliser un modèle 2D volontairement simple pour les états nécessaires à la suite du projet ;
- identifier précisément les champs, unités ou courbes manquants pour le virage et les transitions.

## 3. Hors périmètre

- simulation finale de production ;
- comportement de pilote ou trajectoire optimale ;
- trafic, dépassement, collisions entre voitures ;
- modèle détaillé de suspension, pneumatique ou différentiel ;
- intégration Unity ;
- recalcul complet des courbes Automation lorsqu'elles sont déjà disponibles dans l'export.

## 4. Environnement

| Élément | Version ou valeur |
|---|---|
| Système d'exploitation | Windows, machine locale |
| Matériel pertinent | à renseigner si les mesures de performance deviennent significatives |
| Runtime / SDK | à choisir pour le prototype, idéalement hors Unity |
| Version du prototype | à créer dans `prototypes/vehicle-dynamics/` |
| Entrées utilisées | trois exports A9 dans `outputs/a9-raw-vehicle-data/` pour les jalons à partir de B-S04 A9 |
| Graine aléatoire | aucune pour les scénarios déterministes initiaux |

## 5. Protocole reproductible

1. Charger les trois documents `automation-lap-raw-vehicle-data.json` produits par A8 ou A9 selon le jalon.
2. Valider le contrat `AutomationRawVehicleData` v0.1 avant toute simulation.
3. Construire des interpolateures pour les courbes `AccelerationToTopSpeed`, `Braking` et `BrakingVGrip`.
4. Exécuter les scénarios longitudinaux en utilisant les courbes Automation comme références.
5. Exécuter les scénarios de virage avec un modèle 2D minimal et des hypothèses explicitement marquées.
6. Tester plusieurs pas de temps candidats : `1/30 s`, `1/60 s`, `1/120 s`.
7. Collecter les écarts, les instabilités numériques, les champs manquants et les hypothèses d'unité.
8. Archiver les résultats dans `prototypes/vehicle-dynamics/results/`.

Toutes les conversions d'unités doivent rester explicites. Une valeur dont l'unité n'est pas confirmée doit rester étiquetée `unknown` ou `automation-graph`, et ne doit pas être convertie silencieusement.

## 6. Scénarios

| Identifiant | Description | Entrées | Répétitions |
|---|---|---|---:|
| B-S01 | Chargement et validation des trois voitures A8 | AIXAM Coupe GTI, PCM, QFC | 1, validée |
| B-S02 | Relecture accélération 0 à Vmax depuis `AccelerationToTopSpeed` | courbes `Speed`, `Time`, puissance, rapports disponibles | 1 par voiture, validée |
| B-S03 | Relecture freinage depuis `Braking` et comparaison avec `BrakingVGrip` | courbes vitesse, temps, force/grip si présentes | 1 par voiture, validée |
| B-S04 | Virage à rayon constant avec modèle 2D minimal | masse, répartition, grip proxy disponible | 3 rayons par voiture, validée avec réserves |
| B-S05 | Transitions simples throttle / frein / direction | état dynamique minimal | 3 pas de temps par voiture, validée avec réserves |
| B-S06 | Sensibilité inter-voitures | les trois voitures A9 | 1 comparaison globale, validée avec réserves |

## 7. Métriques

| Métrique | Unité | Méthode de collecte | Seuil ou attente |
|---|---|---|---|
| Documents Automation chargés | nombre | validation du contrat | 3 / 3 |
| Erreurs de contrat | nombre | validateur `AutomationRawVehicleData` | 0 |
| Valeurs `NaN` ou infinies | nombre | contrôle runtime | 0 |
| Stabilité au pas de temps | booléen | `1/30 s`, `1/60 s`, `1/120 s` | résultats finis et cohérents |
| Erreur d'interpolation accélération | unité native de la courbe | comparaison avec points Automation | faible et documentée |
| Temps 0-50 / 0-100 / 0-Vmax | seconde | interpolation `AccelerationToTopSpeed` | classement plausible entre voitures |
| Temps et distance de freinage | seconde / unité native | interpolation `Braking` | cohérent avec la courbe source |
| Usage `BrakingVGrip` | qualitatif | comparaison force/grip avant-arrière | unité et axe documentés ou blocage explicite |
| Vitesse critique en virage | km/h ou m/s selon unité confirmée | rayon constant | classement plausible, hypothèses listées |
| Champs bloquants manquants | nombre + liste | audit du prototype | aucun blocage caché |

## 8. Critères de réussite et d'échec

### Réussite

- [x] les trois voitures Automation sont chargées et validées ;
- [x] les scénarios longitudinaux exploitent les courbes Automation sans recalcul inutile ;
- [x] le prototype reste stable aux pas de temps candidats ;
- [x] les trois voitures produisent des différences plausibles d'accélération, freinage et comportement en virage ;
- [x] les unités inconnues restent traçables ;
- [x] les données manquantes pour C, E ou une extension de A sont clairement listées.

### Échec ou révision obligatoire

- [ ] `AutomationRawVehicleData` v0.1 ne contient pas assez d'information pour lancer les scénarios ;
- [ ] le comportement obtenu nécessite des règles spécifiques par voiture ;
- [ ] une unité inconnue empêche d'interpréter les scénarios principaux ;
- [ ] le prototype devient instable dans la plage normale d'utilisation ;
- [ ] les courbes Automation disponibles sont insuffisantes ou incohérentes pour servir de référence.

## 9. Résultats

### Données brutes

Premiers résultats disponibles :

- `prototypes/vehicle-dynamics/results/B_S01_LOAD_A8_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s01_load_a8_summary.json`
- `prototypes/vehicle-dynamics/results/B_S02_ACCELERATION_CURVE_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s02_acceleration_curve_summary.json`
- `prototypes/vehicle-dynamics/results/B_S03_BRAKING_CURVE_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s03_braking_curve_summary.json`
- `prototypes/vehicle-dynamics/results/B_S04_CONSTANT_RADIUS_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s04_constant_radius_summary.json`
- `prototypes/vehicle-dynamics/results/B_S04_STEERING_GRAPHS_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s04_steering_graphs_summary.json`
- `prototypes/vehicle-dynamics/results/B_S05_TRANSITIONS_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s05_transitions_summary.json`
- `prototypes/vehicle-dynamics/results/B_S06_VEHICLE_SENSITIVITY_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s06_vehicle_sensitivity_summary.json`

Sources attendues pour les prochains jalons :

- `outputs/a8-raw-vehicle-data/*/automation-lap-raw-vehicle-data.json`
- `outputs/a9-raw-vehicle-data/*/automation-lap-raw-vehicle-data.json`
- `prototypes/vehicle-dynamics/results/`

### Synthèse

| Scénario | Résultat | Variance | Observation |
|---|---:|---:|---|
| B-S01 | 3 documents valides / 3 | — | 73 / 73 champs, 3 graphes bruts, 24 séries et 13 304 valeurs chargées |
| B-S02 | 3 courbes valides / 3 | erreur interpolation sur axe temps = 0 | 0-50, 0-100 et Vmax relus par premier passage sur `AccelerationToTopSpeed` |
| B-S03 | 3 courbes valides / 3 | axes `Braking.Speed` et `BrakingVGrip.Speed` identiques | 200->fin, 100->fin et 50->fin relus par premier passage descendant |
| B-S04 | 3 voitures évaluées / 3 | proxy latéral, non physique final | vitesses critiques finies pour rayons 25 m, 50 m et 100 m |
| B-S05 | 3 voitures stables / 3 | pas `1/30`, `1/60`, `1/120` | transitions throttle/frein/direction validées avec modèle de cap hypothétique |
| B-S06 | 3 voitures comparées / 3 | écarts relatifs visibles sur toutes les métriques consolidées | sensibilité inter-voitures conservée, validée avec réserves |

## 10. Analyse

B-S01 confirme que le prototype B peut reprendre directement les exports A8.

Le seul avertissement commun reste l'absence de version Automation exposée par les données Lua, déjà identifiée pendant A.

Les prochains jalons peuvent donc travailler sur les graphes présents :

- `AccelerationToTopSpeed` pour B-S02 ;
- `Braking` et `BrakingVGrip` pour B-S03.

B-S02 confirme que `AccelerationToTopSpeed` est exploitable comme courbe longitudinale d'accélération. Les temps relus sont :

- AIXAM Coupe GTI : 0-50 en 20,19 s, 0-100 en 50,07 s, Vmax 115,18 atteinte en 75,25 s ;
- PCM - Magmort Carcharhini Recif : 0-50 en 2,66 s, 0-100 en 5,69 s, Vmax 223,01 atteinte en 49,40 s ;
- QFC55 - Magmort Carcharhini RCZ : 0-50 en 2,28 s, 0-100 en 5,40 s, Vmax 287,79 atteinte en 73,70 s.

Deux voitures rapides ont une petite baisse de vitesse en fin de courbe après Vmax. Le prototype conserve cette information source et utilise le premier passage à la vitesse cible pour les repères d'accélération.

B-S03 confirme que `Braking` est exploitable comme courbe longitudinale de freinage et que `BrakingVGrip` est aligné sur le même axe vitesse. Les durées relues depuis 100 vers la fin de courbe sont :

- AIXAM Coupe GTI : 100->fin en 3,42 s ;
- PCM - Magmort Carcharhini Recif : 100->fin en 2,94 s ;
- QFC55 - Magmort Carcharhini RCZ : 100->fin en 2,63 s.

La courbe `Braking` ne fournit pas directement une distance. Le prototype calcule donc seulement une aire vitesse-temps en unité native Automation, utilisable comme distance candidate après confirmation d'unité. `BrakingVGrip` fournit bien les séries `FrontBrakeForce`, `FrontBrakeGrip`, `RearBrakeForce`, `RearBrakeGrip` et `Speed`, avec unité encore inconnue.

B-S04 confirme qu'un scénario de virage à rayon constant peut être exécuté avec les données actuelles, mais seulement avec un proxy de grip : `AccelerationToTopSpeed.FrontGripG + AccelerationToTopSpeed.RearGripG`. Les vitesses critiques estimées à 50 m de rayon sont :

- AIXAM Coupe GTI : 54,95 km/h ;
- PCM - Magmort Carcharhini Recif : 58,27 km/h ;
- QFC55 - Magmort Carcharhini RCZ : 86,23 km/h.

Ce résultat ne valide pas encore un modèle latéral physique. Il met en évidence un besoin probable d'extension A : exporter en valeurs brutes les graphes `LowSpeedSteering` et `HighSpeedSteering`, ou une donnée d'adhérence latérale explicite.

Mise à jour A9 : les trois voitures ont été réexportées avec `0.1.13-a9-steering-raw-graphs`. Les graphes `LowSpeedSteering` et `HighSpeedSteering` sont maintenant disponibles en valeurs brutes complètes dans `outputs/a9-raw-vehicle-data/`. B-S04 doit être repris ou complété avec ces courbes avant de conclure sur le modèle de virage.

Complément B-S04 A9 : les graphes de direction ont été analysés dans `prototypes/vehicle-dynamics/results/B_S04_STEERING_GRAPHS_RESULT.md`. Ils sont complets, non tronqués et exploitables numériquement pour les trois voitures. Ils confirment une information utile de comportement directionnel :

- axe `Speed` monotone ;
- séries `Steering`, `UnderSteer`, `OverSteer` complètes ;
- enveloppe permettant de qualifier les zones sous-vireuses/survireuses ;
- pic `Steering` suivi d'une chute en fin de domaine, à conserver comme donnée source.

Conclusion : les graphes A9 doivent être conservés pour la suite, mais ne remplacent pas seuls une formule de vitesse critique en rayon constant. Ils complètent B-S04 plutôt qu'ils ne fournissent une adhérence latérale brute.

B-S05 confirme qu'un état dynamique minimal peut intégrer accélération, freinage et direction sans instabilité numérique sur les trois voitures et les trois pas de temps candidats. Le scénario combine :

- accélération depuis la pente `AccelerationToTopSpeed.Speed/Time` ;
- freinage depuis la pente `Braking.Speed/Time` ;
- direction depuis `LowSpeedSteering` puis `HighSpeedSteering`, normalisés car leur unité reste inconnue.

Au pas de référence `1/120 s`, les états finaux sont :

- AIXAM Coupe GTI : vitesse finale 7,70 km/h, cap 0,0211 rad ;
- PCM - Magmort Carcharhini Recif : vitesse finale 107,36 km/h, cap 0,0885 rad ;
- QFC55 - Magmort Carcharhini RCZ : vitesse finale 107,28 km/h, cap 0,2511 rad.

Le résultat valide la stabilité du squelette 2D, mais pas encore la fidélité latérale physique. La direction reste une hypothèse calibrable à partir de graphes Automation, à reprendre dans C lorsque le contrôleur autonome aura besoin d'une loi de suivi de trajectoire.

B-S06 consolide les résultats B-S02 à B-S05 et confirme que les trois voitures restent différenciées sans règle spécifique par voiture. Les classements principaux sont :

- Vmax : QFC55, PCM, AIXAM ;
- 0-100 : QFC55, PCM, AIXAM ;
- freinage 100->fin : QFC55, PCM, AIXAM ;
- distance sur transition B-S05 : QFC55, PCM, AIXAM.

Les écarts relatifs restent supérieurs au seuil de 5 % sur les métriques consolidées. L'AIXAM reste clairement séparée des deux voitures rapides, tandis que PCM et QFC55 restent proches sur la vitesse finale de transition mais distinctes sur la distance, le cap et la réponse de direction.

L'analyse devra séparer :

- les résultats directement relus depuis Automation ;
- les résultats produits par interpolation ;
- les résultats réellement issus du modèle 2D ;
- les écarts dus aux unités inconnues ou aux hypothèses temporaires.

## 11. Limites

- Les courbes Automation ne documentent pas toujours leurs unités.
- Les graphes longitudinaux suffisent pour relire accélération et freinage dans les scénarios initiaux, mais pas pour prédire seuls le virage.
- Un modèle 2D simple ne représentera pas le détail suspension/pneus d'Automation.
- Les résultats B ne valident pas encore un contrôleur de conduite autonome.

## 12. Conclusion

### Décision

> Validée avec réserves.

### Niveau de confiance

> Moyen. Les scénarios longitudinaux et la stabilité numérique sont solides pour passer à C, mais le modèle latéral reste une hypothèse calibrable.

## 13. Conséquences

### Paramètres retenus

- pas de temps physique candidat : `1/60 s` ;
- pas de temps de référence pour vérification : `1/120 s` ;
- stratégie : relire et interpoler les courbes Automation avant de dériver une physique simplifiée ;
- état dynamique minimal : vitesse, position, cap, commandes throttle/frein/direction ;
- direction : utiliser `LowSpeedSteering` et `HighSpeedSteering` comme réponse normalisée, avec unité `automation-graph` encore inconnue.

### Risques résiduels

- dépendance aux courbes Automation si elles ne couvrent pas certains cas de course ;
- interprétation physique incomplète des graphes de direction ;
- conversions d'unités partielles pour certaines courbes ;
- modèle latéral à calibrer pendant C.

### Documents affectés

- plan de faisabilité ;
- tableau de bord Phase 1 ;
- rapport consolidé ;
- ADR-0001 et ADR-0003 si la stratégie de simulation ou d'adaptation Automation change.

### Travaux suivants

- préparer l'expérience C avec `1/60 s` comme pas candidat ;
- conserver `1/120 s` comme référence de vérification ;
- définir le contrat minimal de circuit nécessaire au contrôleur ;
- reprendre la loi latérale dans C sans présenter `Steering` comme une adhérence brute.
