# Architecture cible

- **Statut :** proposée
- **Version :** 0.1
- **Date :** 25 juillet 2026

## 1. Objectif

L’architecture doit permettre de simuler une course indépendamment de son affichage, de répéter rapidement des expériences, de tester chaque système et de conserver des replays lisibles malgré l’évolution du projet.

## 2. Frontières principales

```text
┌───────────────────────────┐
│ Automation                │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ Import / Normalisation    │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ Définitions de simulation │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ Cœur de simulation        │
└───────┬───────────┬───────┘
        ▼           ▼
   Présentation   Enregistrement
     Unity          / Replay
```

### Cœur de simulation

Responsable du temps, de la physique, des pilotes, de la stratégie, des règles, des événements, du classement et de la télémétrie. Il ne référence aucune API Unity.

### Présentation Unity

Consomme des états de lecture. Elle gère scènes, sprites, caméras, interface, sons et contrôles du lecteur de replay. Elle ne modifie pas directement l’état physique autoritatif.

### Import Automation

Traduit une structure externe et instable vers des définitions internes stables. Il produit un rapport de validation et conserve la provenance de chaque champ.

### Persistance et replay

Écrit et lit les formats versionnés. Cette couche ne doit pas dépendre des objets de scène Unity.

## 3. Projets cibles

```text
AutomationLAP.Core
AutomationLAP.Physics
AutomationLAP.AI
AutomationLAP.Strategy
AutomationLAP.Rules
AutomationLAP.Replay
AutomationLAP.Automation
AutomationLAP.Persistence
AutomationLAP.Unity
AutomationLAP.Editor
AutomationLAP.Tests.Unit
AutomationLAP.Tests.Integration
AutomationLAP.Tests.Simulation
```

Cette séparation pourra être réduite au démarrage si elle ralentit les prototypes. Les frontières conceptuelles doivent néanmoins rester respectées.

## 4. Règles de dépendance

- `Core` ne dépend d’aucun autre module applicatif.
- `Physics`, `AI`, `Strategy` et `Rules` dépendent des contrats de `Core`.
- `Automation` produit des définitions compatibles avec `Core`, sans être requis pour exécuter une course.
- `Replay` et `Persistence` consomment les contrats et événements, sans dépendre de Unity.
- `Unity` peut dépendre des modules de simulation, jamais l’inverse.
- `Editor` contient les outils de création et validation propres à Unity.
- Les tests peuvent référencer les modules qu’ils valident ; le code de production ne référence jamais les projets de tests.

## 5. Modèle de données

### Définitions immuables

```text
VehicleDefinition
DriverDefinition
TeamDefinition
TrackDefinition
RaceRulesDefinition
WeatherDefinition
RaceSessionDefinition
StrategyDefinition
```

Elles décrivent les conditions initiales et doivent pouvoir être identifiées par une version et une empreinte.

### États dynamiques

```text
VehicleState
DriverState
TeamState
TrackState
WeatherState
RaceState
```

Ils évoluent à chaque tick ou à une fréquence spécifique. Les identifiants relient les états aux définitions sans dupliquer les données immuables.

### Événements

```text
RaceEvent
OvertakeEvent
ContactEvent
PitStopEvent
PenaltyEvent
FailureEvent
StrategyDecisionEvent
WeatherChangeEvent
```

Les événements sont horodatés dans le temps de simulation. Ils servent à la logique, au débogage, au replay et à l’analyse.

## 6. Boucle de simulation

La simulation utilise un pas fixe et des fréquences différenciées.

```text
1. Avancer l’horloge de simulation
2. Mettre à jour l’environnement
3. Mettre à jour la perception locale
4. Évaluer tactique et stratégie selon leur cadence
5. Produire les commandes des pilotes
6. Intégrer la physique des véhicules
7. Résoudre proximité, contact et limites
8. Mettre à jour règles, chronométrage et classement
9. Publier les événements
10. Échantillonner télémétrie et replay
11. Exposer un état de lecture au rendu
```

Fréquences initiales à tester :

| Système | Fréquence indicative |
|---|---:|
| Physique | 50 à 100 Hz |
| Contrôle de conduite | 20 à 50 Hz |
| Perception du trafic | 10 à 20 Hz |
| Tactique | 2 à 10 Hz |
| Stratégie | 0,2 à 1 Hz et sur événement |
| Télémétrie | 10 à 50 Hz |
| Images-clés du replay | 5 à 20 Hz |

Ces valeurs sont des hypothèses de faisabilité, pas des constantes figées.

## 7. Aléatoire et reproductibilité

Chaque domaine aléatoire doit disposer d’un flux identifié, par exemple :

```text
DriverErrors
MechanicalFailures
WeatherEvolution
RaceControl
StrategyUncertainty
```

La graine racine et les versions des modèles sont enregistrées. Les tests peuvent imposer des graines fixes. Le replay ne dépend toutefois pas exclusivement de la reproductibilité numérique : il conserve également des états et événements.

## 8. Publication d’état vers Unity

Le cœur publie un instantané de lecture ou un tampon double contenant uniquement les données nécessaires au rendu. Unity interpole entre deux états de simulation afin de conserver une animation fluide indépendamment de la cadence graphique.

Aucun `MonoBehaviour`, `GameObject`, `Transform`, `Rigidbody2D`, `ScriptableObject` ou type mathématique Unity ne doit apparaître dans les contrats du cœur.

## 9. Gestion des performances

Ordre d’optimisation :

1. mesurer avec des scénarios reproductibles ;
2. éliminer allocations et calculs inutiles ;
3. adapter les fréquences ;
4. structurer les données pour les accès fréquents ;
5. paralléliser les systèmes sans dépendances ;
6. utiliser Jobs ou Burst seulement si le profilage le justifie.

## 10. Arborescence documentaire et source

```text
docs/
  architecture/
  decisions/
  feasibility/
  specifications/
src/
tests/
tools/
```

Les répertoires de code seront ajoutés au moment où leur première responsabilité est validée. Les dossiers vides ne sont pas conservés artificiellement.
