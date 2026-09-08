# Candidat IA pilote — Raceline-Optimization

- **Statut :** retenu pour expérimentation externe hors ligne
- **Identifiant :** AI-CANDIDATE-003
- **Date :** 8 septembre 2026
- **Dépôt étudié :** [CL2-UWaterloo/Raceline-Optimization](https://github.com/CL2-UWaterloo/Raceline-Optimization)
- **Origine :** fork de [TUMFTM/global_racetrajectory_optimization](https://github.com/TUMFTM/global_racetrajectory_optimization)
- **Branche étudiée :** master
- **Dernière activité observée :** 8 décembre 2023
- **Licence déclarée :** LGPL-3.0
- **Objet :** éprouver hors ligne la génération d’une racing line et d’un profil de vitesse propres à chaque couple voiture–circuit

## 1. Décision

Raceline-Optimization est retenu comme **outil externe d’expérimentation**, et non comme dépendance de production d’Automation LAP.

Le dépôt fournit une implémentation suffisamment complète pour tester concrètement la décision issue de AI-REFERENCE-002 :

> La racing line de référence doit être calculée pour un couple voiture–circuit, et non attachée au circuit seul.

L’expérimentation devra mesurer si les trajectoires calculées avec les caractéristiques de plusieurs véhicules produisent réellement des gains et des comportements cohérents dans la physique autoritative d’Automation LAP.

La sélection de cet outil ne vaut pas adoption de son architecture, de son modèle physique, de son environnement Python ou de son code.

## 2. Capacités proposées

Le dépôt permet de générer plusieurs familles de trajectoires globales :

- chemin le plus court ;
- courbure minimale ;
- courbure minimale par optimisation quadratique itérative ;
- temps au tour minimal ;
- temps au tour minimal avec prise en compte du groupe motopropulseur.

| Niveau | Objectif | Usage envisagé |
|---|---|---|
| géométrique | chemin le plus court | contrôle et borne de comparaison |
| géométrique optimisé | courbure minimale | première racing line exploitable |
| dynamique simplifiée | courbure minimale + profil GGV | prototype prioritaire |
| dynamique complète | temps minimal | oracle de recherche |
| énergétique | temps minimal + groupe motopropulseur | étude future |

## 3. Optimisation à courbure minimale

L’approche déplace latéralement les points d’une ligne de référence à l’intérieur des largeurs disponibles. Le résultat est interpolé par splines, puis contrôlé selon sa courbure et sa distance aux limites de piste.

Le dépôt propose une formulation directe et une variante itérative mincurv_iqp.

Cette famille est retenue comme première cible, car elle nécessite moins de paramètres que l’optimisation temporelle complète tout en produisant généralement une trajectoire proche de l’optimum dans les virages.

Elle ne suffit cependant pas à matérialiser entièrement une racing line propre à la voiture. La différenciation devient réellement utile lorsqu’elle est associée à un profil de vitesse et à des limites dynamiques spécifiques.

## 4. Profil dynamique fondé sur les enveloppes GGV

Le calcul simplifié utilise notamment :

- un diagramme GGV décrivant les accélérations disponibles selon la vitesse ;
- une courbe d’accélération maximale du groupe motopropulseur ;
- la masse ;
- la traînée aérodynamique ;
- la vitesse maximale ;
- la courbure de la trajectoire.

Le dépôt produit ensuite une vitesse et une accélération cibles le long du tour.

Cette approche correspond directement à la proposition de AI-REFERENCE-002 consistant à mesurer les enveloppes du véhicule dans la physique d’Automation LAP.

Elle est retenue comme **prototype prioritaire**, avant le mode temps minimal.

## 5. Optimisation complète du temps au tour

Le mode mintime formule un problème de contrôle optimal non linéaire. Il utilise :

- une discrétisation par collocation orthogonale de Gauss-Legendre ;
- CasADi pour la différentiation algorithmique ;
- IPOPT pour la résolution ;
- un modèle véhicule à deux voies ;
- une approximation quasi stationnaire des transferts de charge ;
- un modèle non linéaire de pneus de type Pacejka ;
- des dynamiques de direction, d’accélération et de freinage ;
- des contraintes de piste et de véhicule.

Il peut également considérer :

- une adhérence variable sur la largeur et la longueur de piste ;
- des coefficients d’adhérence propres aux roues ;
- une limite énergétique ;
- les pertes et le comportement thermique du groupe motopropulseur ;
- l’état de charge d’une batterie ;
- une trajectoire volontairement plus sûre.

Cette solution demande beaucoup plus de paramètres et peut diverger du comportement de la physique d’Automation LAP. Elle est donc retenue comme **oracle de comparaison**, pas comme première intégration.

## 6. Entrées et sorties

La piste de référence est représentée par :

    x, y, largeur_droite, largeur_gauche

Les normales calculées à partir de cette ligne permettent de déplacer la trajectoire à l’intérieur du corridor praticable.

L’export principal contient :

| Donnée | Signification |
|---|---|
| s_m | distance curviligne |
| x_m, y_m | position de la racing line |
| psi_rad | orientation |
| kappa_radpm | courbure |
| vx_mps | vitesse cible |
| ax_mps2 | accélération longitudinale cible |

Un second format conserve la ligne de référence, les largeurs, les normales et le décalage latéral optimisé. Ces formats constituent une bonne base de comparaison pour le futur RacingLineProfile, sans imposer le CSV comme contrat interne définitif.

## 7. Architecture d’expérimentation

L’outil doit rester séparé du runtime :

    Automation LAP
        ├── export de TrackDefinition
        └── caractérisation de VehicleDefinition
                    │
                    ▼
        adaptateur d’expérimentation
                    │
                    ▼
        Raceline-Optimization
        ├── shortest_path
        ├── mincurv_iqp
        └── mintime
                    │
                    ▼
        import et validation dans Automation LAP

Le solveur ne doit pas être exécuté dans la boucle de simulation. Les profils validés seront précalculés, versionnés et mis en cache.

## 8. Protocole expérimental

### 8.1 Préparation

1. sélectionner une piste fermée représentative ;
2. exporter sa ligne de référence et ses largeurs ;
3. sélectionner deux véhicules aux caractéristiques très différentes ;
4. mesurer leurs enveloppes dynamiques dans le moteur physique ;
5. convertir ces mesures en diagrammes GGV et courbes d’accélération ;
6. documenter toutes les transformations d’unités.

### 8.2 Première campagne

Pour chaque véhicule :

1. générer le chemin le plus court ;
2. générer la trajectoire mincurv_iqp ;
3. calculer le profil de vitesse GGV ;
4. importer le résultat dans Automation LAP ;
5. faire suivre la trajectoire par le même contrôleur déterministe ;
6. exécuter plusieurs tours reproductibles.

### 8.3 Mesures

- temps au tour prévu par l’outil ;
- temps au tour réellement obtenu ;
- écart entre temps prévu et temps réel ;
- sorties de piste et violations physiques ;
- erreur latérale et oscillations de direction ;
- stabilité des commandes ;
- marge minimale aux bords ;
- coût du calcul hors ligne ;
- coût du suivi dans la simulation ;
- différence de trajectoire entre véhicules.

### 8.4 Critère décisif

L’hypothèse « une racing line par voiture » sera renforcée si :

- les trajectoires optimales diffèrent de manière mesurable ;
- chaque voiture obtient son meilleur résultat avec son propre profil ;
- les gains persistent dans la physique autoritative ;
- les trajectoires restent stables et crédibles ;
- le coût de préparation demeure acceptable.

## 9. Usage comme professeur

Les profils générés peuvent fournir :

- une baseline déterministe ;
- des démonstrations pour l’apprentissage par imitation ;
- une fonction de fitness pour l’apprentissage évolutionnaire ;
- un adversaire stable dans un curriculum ;
- une référence pour noter les trajectoires proposées par un modèle appris ;
- plusieurs niveaux de difficulté selon la part d’adhérence autorisée.

| Professeur | Rôle |
|---|---|
| chemin le plus court | baseline géométrique |
| courbure minimale | trajectoire rapide simple |
| profil GGV | référence propre au véhicule |
| temps minimal | oracle coûteux |
| profil dégradé | comportement de pilote imparfait |

## 10. Éléments à reprendre conceptuellement

- représentation ligne centrale, largeurs et normales ;
- déplacement latéral optimisé ;
- continuité par splines ;
- optimisation quadratique itérative ;
- diagrammes GGV ;
- génération du profil vitesse/accélération ;
- vérification après optimisation ;
- warm start ;
- pénalités de variation des commandes ;
- objectifs de sécurité limitant l’adhérence exploitée ;
- comparaison de plusieurs objectifs ;
- carte d’adhérence variable comme extension future.

## 11. Éléments à ne pas intégrer directement

- le script principal monolithique ;
- les variables globales et fichiers INI comme modèle de domaine ;
- les visualisations mélangées au calcul ;
- Python, CasADi et IPOPT dans le runtime ;
- le CSV comme contrat interne permanent ;
- les paramètres fournis comme vérité physique ;
- le fork entier comme sous-module ou dépendance sans étude complémentaire.

Une éventuelle implémentation de production devra être native, testable et alignée avec les contrats du cœur d’Automation LAP.

## 12. Maturité et maintenabilité

Points favorables :

- plusieurs méthodes comparables ;
- documentation des entrées et sorties ;
- références scientifiques identifiées ;
- paramètres physiques détaillés ;
- format d’export simple.

Risques :

- environnement annoncé Ubuntu 20.04 et Python 3.8 ;
- versions anciennes de NumPy, SciPy, CasADi et scikit-learn ;
- dépendance Git vers un fork de trajectory_planning_helpers ;
- difficultés d’installation signalées ;
- absence apparente de tests automatisés et de CI ;
- API non stabilisée ;
- configuration largement manuelle ;
- dernière activité observée en décembre 2023.

Le résultat d’une exécution doit toujours être revérifié dans la physique d’Automation LAP.

## 13. Fork Waterloo et amont TUM

Le dépôt Waterloo est dérivé de TUMFTM/global_racetrajectory_optimization. Ses adaptations visibles facilitent notamment certains usages F1TENTH, la conversion de cartes et l’exécution en ligne de commande.

Avant toute réutilisation plus profonde, il faudra comparer :

- l’état du fork Waterloo ;
- l’état et la licence du dépôt TUM ;
- la bibliothèque trajectory_planning_helpers réellement utilisée ;
- les écarts fonctionnels ;
- la compatibilité avec un environnement reproductible moderne.

Le fork Waterloo est retenu comme point d’entrée expérimental. Il n’est pas présumé être la meilleure base à maintenir.

## 14. Licence

Le dépôt déclare une licence LGPL-3.0.

L’expérimentation externe, avec échange de fichiers, maintient une frontière claire. Toute copie, modification, liaison ou distribution de code devra faire l’objet d’une vérification spécifique des obligations applicables au dépôt et à chacune de ses dépendances.

La présente étude ne valide aucune incorporation de code dans Automation LAP.

## 15. Évaluation selon la grille commune

| Axe | Évaluation |
|---|---|
| génération de trajectoire globale | très forte |
| prise en compte du véhicule | très forte |
| profil de vitesse | très fort |
| explicabilité | forte |
| reproductibilité conceptuelle | forte |
| reproductibilité de l’environnement | moyenne à faible |
| intégration directe | faible |
| expérimentation hors ligne | très forte |
| trafic et dépassement | absents |
| stratégie de course | absente |
| diversité des pilotes | indirecte |
| apprentissage | absent, mais excellent professeur potentiel |
| scalabilité à 12–20 voitures | favorable après précalcul |
| maintenabilité comme dépendance | faible à moyenne |
| testabilité du dépôt | faible en l’état |

## 16. Conditions de réussite

L’expérimentation est considérée réussie si elle permet :

1. d’exécuter l’outil dans un environnement isolé et reproductible ;
2. de convertir une piste Automation LAP sans correction manuelle ;
3. de dériver les paramètres nécessaires depuis la physique du projet ;
4. de générer deux profils véhicule–circuit distincts ;
5. de réimporter les profils sans ambiguïté d’unités ;
6. d’obtenir un bénéfice mesurable avec le moteur physique autoritatif ;
7. de documenter les écarts entre prédiction et simulation.

Si ces conditions ne sont pas réunies, le dépôt restera une source algorithmique et documentaire sans devenir un outil régulier du projet.

## 17. Conclusion figée

**Raceline-Optimization est retenu pour une expérimentation externe hors ligne.**

Il fournit une mise en pratique crédible de la racing line propre au véhicule et un banc d’essai pour comparer chemin court, courbure minimale, profil GGV et temps minimal.

Le prototype prioritaire utilisera mincurv_iqp et le profil GGV. Le mode mintime sera traité comme un oracle de recherche plus coûteux. Aucun solveur Python ne sera introduit dans le runtime et aucune dépendance de production n’est adoptée à ce stade.
