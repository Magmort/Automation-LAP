# Plan général du projet Automation LAP

- **Statut :** référence proposée — baseline v0.1
- **Date :** 25 juillet 2026
- **Portée :** préproduction jusqu’au premier vertical slice jouable
- **Politique d’évolution :** modification par pull request ; décision structurante par ADR

Ce document est la **source de vérité** du plan général. Il fixe l’intention, le périmètre, l’ordre de travail et les critères permettant de décider quand le projet peut passer de l’expérimentation au code de production.

---

## 1. Vision

Automation LAP est un jeu de simulation automobile dans lequel le joueur observe, prépare et analyse des compétitions entièrement disputées par des pilotes IA.

La simulation doit faire émerger des courses plausibles à partir de quatre familles de causes :

1. les capacités physiques et mécaniques des voitures ;
2. les aptitudes, la personnalité et l’état des pilotes ;
3. les décisions tactiques et stratégiques ;
4. l’environnement de course : circuit, trafic, règlement, météo et incidents.

Le rendu principal est une vue 2D du dessus. Le spectateur peut suivre une voiture, observer l’ensemble du circuit, consulter le classement et comprendre les décisions importantes. La course produit un enregistrement autonome qui peut être chargé et revisionné ultérieurement.

## 2. Promesse de simulation

Le projet doit privilégier une causalité lisible plutôt qu’une accumulation de hasard invisible. Une différence de performance ou un incident doit pouvoir être expliqué par les données de la voiture, la situation de course, une décision, une erreur ou un événement enregistré.

Le réalisme recherché est un réalisme de comportement et de résultats. La première version n’a pas pour objectif de reproduire tous les phénomènes mécaniques d’un simulateur de conduite en temps réel.

## 3. Objectifs du produit

- Exécuter une course complète sans commandes humaines sur les véhicules.
- Différencier durablement les pilotes par leurs compétences et leur comportement.
- Différencier les voitures à partir de données issues d’Automation et de paramètres dérivés.
- Produire dépassements, défense, erreurs, usure, consommation, arrêts et incidents crédibles.
- Exécuter la simulation en temps réel, accélérée ou sans rendu.
- Afficher la course dans Unity sans que Unity soit l’autorité de simulation.
- Enregistrer la course, les décisions et la télémétrie dans un format versionné.
- Permettre des campagnes de simulations répétées pour la calibration et l’équilibrage.

## 4. Principes figés pour la baseline v0.1

Les principes suivants sont considérés comme acquis tant qu’un ADR ne les remplace pas :

1. **Cœur indépendant de Unity.** La simulation est une bibliothèque C# testable et exécutable sans scène Unity.
2. **Autorité unique.** Les positions, vitesses, états mécaniques et résultats sont produits par le cœur de simulation.
3. **Import découplé.** Les données Automation brutes sont conservées, validées puis converties vers `VehicleDefinition`.
4. **Unités SI.** Les calculs internes utilisent kilogrammes, mètres, secondes, newtons, watts, pascals et radians.
5. **Séparation des données.** Les définitions immuables, les états dynamiques et les événements sont des concepts distincts.
6. **Pas de temps maîtrisé.** La simulation avance par ticks fixes ; le rendu interpole les états.
7. **IA en couches.** Stratégie, tactique, perception et contrôle de conduite sont séparés.
8. **Aléatoire contrôlé.** Les flux aléatoires sont nommés, initialisés et enregistrés pour faciliter les tests.
9. **Replay hybride.** Les replays combinent métadonnées, images-clés, événements et télémétrie.
10. **Optimisation après mesure.** Jobs, Burst et structures spécialisées ne sont introduits qu’après profilage.

## 5. Périmètre du premier vertical slice

Le vertical slice doit démontrer la boucle complète du produit sur une course unique.

### Inclus

- un circuit fermé avec ligne de départ, secteurs, limites et voie des stands ;
- trois modèles de voitures issus d’Automation ;
- douze à vingt voitures en piste ;
- profils de pilotes différenciés ;
- départ arrêté ;
- accélération, freinage, virage et adhérence simplifiée mais dynamique ;
- trafic, aspiration simple, dépassement, défense et évitement ;
- carburant et usure des pneus ;
- au moins un type d’arrêt aux stands ;
- stratégie initiale et adaptation pendant la course ;
- erreurs de pilotage, contacts et pannes simples ;
- chronométrage, classement, drapeaux de base et pénalités simples ;
- vue globale et caméra de suivi ;
- enregistrement de la course ;
- replay avec lecture, pause, vitesses variables, navigation temporelle et saut vers un événement ;
- écran de résultats et données essentielles de télémétrie.

### Hors périmètre

- championnat et progression de saison ;
- économie, contrats et marché des pilotes ;
- multijoueur ;
- dégâts structurels ou visuels détaillés ;
- déformation de carrosserie ;
- météo dynamique avancée ;
- voiture de sécurité complète et drapeau rouge ;
- catégories multiples simultanées ;
- éditeur visuel complet de circuits ;
- apprentissage automatique des pilotes ;
- import direct des sons ou graphismes d’Automation.

## 6. Chantiers fonctionnels

### 6.1 Données Automation

Créer un exporteur ou un pipeline capable de produire des données structurées. Conserver les valeurs brutes et leur provenance, puis générer un format interne versionné. Les champs manquants doivent être dérivés, remplacés par des valeurs par défaut explicites ou rendus configurables.

Livrables attendus : dictionnaire des données, schéma d’export, validateur, convertisseur, rapport d’import et jeux de données de référence.

### 6.2 Modèle physique

Commencer par un modèle cinématique pour éprouver la boucle de course, puis évoluer vers un modèle bicyclette dynamique. Un modèle quatre roues n’est envisagé qu’après validation du besoin.

Le modèle doit couvrir : groupe motopropulseur, freinage, masse, inertie, adhérence, traînée, appui, consommation, températures et usure selon le niveau de fidélité validé.

### 6.3 Circuit

Le circuit est une donnée de simulation, pas seulement un décor. Il doit fournir une ligne de référence, la courbure, les largeurs, les surfaces, les limites, les secteurs, les stands et plusieurs trajectoires utilisables par l’IA.

### 6.4 Pilotes IA

Les pilotes combinent caractéristiques permanentes et états temporaires. Leurs décisions doivent résulter d’une perception imparfaite, d’objectifs, d’une estimation des gains et risques, puis d’un contrôleur transformant l’intention en commandes.

Les décisions importantes sont enregistrées avec une raison exploitable par le replay et les outils de débogage.

### 6.5 Stratégie d’équipe

La stratégie gère pneus, carburant, rythme, fenêtres d’arrêt, trafic estimé et réaction aux événements. Le pilote applique ou adapte cette stratégie selon sa situation et ses caractéristiques.

### 6.6 Direction de course

Un module indépendant gère le départ, le chronométrage, le classement, les drapeaux, les limites de piste, les pénalités, les stands, les abandons et le résultat final.

### 6.7 Replay et télémétrie

Le replay doit être conçu dès la première boucle de simulation. Il stocke les versions des modèles, les empreintes des définitions, les graines aléatoires, des images-clés, les événements et des canaux de télémétrie sélectionnés.

### 6.8 Présentation Unity

Unity affiche les états publiés par le cœur. La couche graphique comprend le rendu 2D, les caméras, l’interface spectateur, les écrans de préparation et de résultats, les effets et le lecteur de replay.

## 7. Architecture logique cible

```text
Automation
    │
    ▼
Automation Exporter / Importer
    │ données brutes + rapport
    ▼
VehicleDefinition
    │
    ├──────── DriverDefinition
    ├──────── TrackDefinition
    ├──────── TeamDefinition
    └──────── RaceRulesDefinition
                 │
                 ▼
        RaceSimulation.Core
        ├── Physics
        ├── Driver Control
        ├── Tactical AI
        ├── Strategy
        ├── Race Control
        ├── Events
        └── Telemetry
                 │
          ┌──────┴──────┐
          ▼             ▼
     Unity View     Race Recorder
                          │
                          ▼
                     Replay Reader
```

Les détails et règles de dépendance sont définis dans [l’architecture cible](architecture/OVERVIEW.md).

## 8. Phases de travail

### Phase 0 — Cadrage

Produire la vision, le périmètre, le glossaire, les contraintes et les critères du vertical slice.

**Sortie :** le présent plan est accepté comme baseline.

### Phase 1 — Étude de faisabilité

Réaliser des prototypes jetables pour l’import Automation, le mouvement physique, la conduite IA, le trafic, le replay et la charge.

**Sortie :** chaque hypothèse critique est classée `validée`, `validée avec réserves`, `à modifier` ou `non viable`.

### Phase 2 — Cahier des charges fonctionnel

Décrire les sessions, les règles, les comportements, les stands, les incidents, les interfaces et le replay avec des critères d’acceptation mesurables.

### Phase 3 — Spécifications de simulation

Formaliser le modèle physique, les pneus, la consommation, l’usure, les dégâts, les risques, les fréquences et la gestion de l’aléatoire.

### Phase 4 — Données et import Automation

Définir le format brut, le schéma interne, les conversions, la provenance, le versionnement et les tests de compatibilité.

### Phase 5 — Architecture logicielle

Créer les solutions et projets, fixer leurs dépendances, définir les interfaces publiques et mettre en place tests et intégration continue.

### Phase 6 — Interfaces

Concevoir les parcours et maquettes de préparation, course, suivi, résultats, replay, télémétrie et import.

### Phase 7 — Validation et calibration

Construire les tests techniques, physiques et statistiques. Définir les voitures, pilotes et circuits de référence.

### Phase 8 — Vertical slice

Implémenter la boucle complète selon un ordre incrémental : simulation, circuit, véhicule, pilote, trafic, chronométrage, physique dynamique, tactique, consommables, stands, stratégie, règles, replay, interfaces, calibration.

## 9. Jalons

| Jalon | Résultat attendu |
|---|---|
| M0 — Baseline | Vision, périmètre, architecture et plan de faisabilité versionnés |
| M1 — Données | Trois voitures Automation importées et validées |
| M2 — Tour autonome | Une voiture IA réalise des tours stables |
| M3 — Course minimale | Plusieurs voitures disputent une course chronométrée |
| M4 — Course stratégique | Pneus, carburant, stands et décisions tactiques fonctionnent |
| M5 — Course enregistrée | Une course complète est relue depuis un fichier versionné |
| M6 — Vertical slice | Expérience spectateur cohérente, testée et calibrée |

## 10. Critères de réussite du vertical slice

Le vertical slice est considéré réussi lorsque :

- une course de douze à vingt voitures se termine sans erreur bloquante ;
- les voitures présentent des performances cohérentes avec leurs définitions ;
- les pilotes montrent des différences statistiques mesurables ;
- les dépassements et incidents ne reposent pas sur des scripts de résultat ;
- les stratégies influencent réellement l’issue de la course ;
- la simulation peut fonctionner sans affichage ;
- la vitesse d’affichage peut varier sans modifier le résultat enregistré ;
- le replay permet de retrouver les événements importants et de suivre une voiture ;
- les fichiers de replay détectent les incompatibilités de version ;
- les principaux systèmes disposent de tests automatisés et de métriques de calibration.

## 11. Risques principaux

| Risque | Réponse prévue |
|---|---|
| Données Automation incomplètes | Provenance, paramètres dérivés, valeurs par défaut et calibration manuelle |
| Changement d’Automation | Adaptateur isolé, schémas et versions enregistrés |
| Physique trop ambitieuse | Progression cinématique → bicyclette → quatre roues si nécessaire |
| IA uniforme | Personnalité, perception imparfaite, états temporaires et utilités explicables |
| Accidents excessifs ou absents | Prédiction locale, marges de sécurité et tests statistiques |
| Replay divergent | Images-clés et événements, pas seulement une re-simulation |
| Performances insuffisantes | Fréquences différenciées, profilage puis optimisation ciblée |
| Explosion du périmètre | Vertical slice verrouillé et liste explicite des non-objectifs |
| Résultats impossibles à expliquer | Journalisation des décisions, événements et données de contexte |

## 12. Livrables avant code de production

1. vision et périmètre validés ;
2. étude de faisabilité ;
3. cahier des charges fonctionnel ;
4. spécification du modèle physique ;
5. spécification de l’IA des pilotes ;
6. spécification stratégique ;
7. dictionnaire des données Automation ;
8. modèle de données interne ;
9. architecture logicielle ;
10. format de replay et télémétrie ;
11. maquettes des interfaces ;
12. plan de tests et calibration ;
13. registre des risques ;
14. backlog du vertical slice.

Les prototypes de faisabilité sont volontairement jetables et peuvent commencer avant que tous les documents soient finalisés.

## 13. Gouvernance du plan

- Ce fichier doit rester synthétique et orienté décision.
- Les spécifications détaillées seront créées dans des documents dédiés.
- Une modification majeure du périmètre ou de l’architecture requiert une pull request motivée.
- Toute décision qui impose durablement une contrainte technique doit être consignée dans un ADR.
- Chaque jalon doit être associé à des critères de sortie mesurables.
- Les hypothèses non vérifiées doivent être signalées comme telles, jamais présentées comme acquises.
