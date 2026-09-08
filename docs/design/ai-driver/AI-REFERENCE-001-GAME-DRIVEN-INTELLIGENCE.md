# Référence de conception IA pilote — Game-Driven Intelligence

- **Statut :** référence structurante retenue
- **Identifiant :** AI-REFERENCE-001
- **Date :** 8 septembre 2026
- **Document :** *Game-Driven Intelligence: A Systematic Review of Driving and Racing AI from Track to Battlefield*
- **Version étudiée :** TechRxiv v1, 25 novembre 2025
- **Source :** [DOI 10.36227/techrxiv.176404051.18324425/v1](https://doi.org/10.36227/techrxiv.176404051.18324425/v1)
- **Statut scientifique :** preprint non évalué par les pairs
- **Objet :** fournir un cadre architectural et une grille de comparaison pour la redéfinition de l’IA pilote d’Automation LAP

## 1. Position de la référence

Ce document n’est pas un candidat algorithmique directement implémentable. Il s’agit d’une revue proposant une taxonomie des systèmes d’intelligence de conduite.

Il est retenu comme référence de conception pour :

- structurer la future architecture de l’IA pilote ;
- positionner les composants appris dans cette architecture ;
- comparer les prochains candidats avec des critères communs ;
- conserver un équilibre entre performance, crédibilité, robustesse et contrôle du concepteur.

Cette référence ne constitue pas un ADR et ne sélectionne aucune méthode d’apprentissage particulière.

## 2. Apport central : architecture hiérarchique

La revue organise l’intelligence de conduite en trois couches :

1. **stratégique**, pour les objectifs à long horizon ;
2. **tactique**, pour les manœuvres et interactions à horizon intermédiaire ;
3. **contrôle**, pour les commandes continues à haute fréquence.

Pour Automation LAP, cette taxonomie est retenue avec deux frontières supplémentaires : la perception et la planification de trajectoire.

```text
Perception du pilote
        │
        ├──────────────► Stratégie
        │                    │
        ▼                    ▼
      Tactique ◄─────────────┘
        │
        ▼
Planification de trajectoire
        │
        ▼
Contrôle de conduite
        │
        ▼
Physique du véhicule
```

### 2.1 Perception

La perception transforme l’état autoritatif en informations accessibles au pilote. Elle applique :

- portée et visibilité ;
- délais ;
- bruit ;
- incertitude ;
- oubli ou perte de suivi ;
- compétence du pilote.

Les composants décisionnels ne doivent pas lire directement le `RaceState` complet lorsqu’ils représentent le raisonnement du pilote.

### 2.2 Stratégie

La stratégie traite notamment :

- objectifs de course ;
- rythme global ;
- pneus et carburant ;
- fenêtres d’arrêt ;
- consignes d’équipe ;
- réaction aux événements ;
- compromis entre résultat immédiat et course complète.

### 2.3 Tactique

La tactique sélectionne des intentions interprétables :

- suivre ;
- attaquer ;
- dépasser à gauche ou à droite ;
- défendre ;
- céder ;
- interrompre une manœuvre ;
- préserver la voiture ;
- récupérer après une erreur.

### 2.4 Planification de trajectoire

Le planificateur transforme l’intention en trajectoire faisable. Il tient compte :

- des limites de piste ;
- des trajectoires des concurrents ;
- de la dynamique du véhicule ;
- des marges du pilote ;
- des règles ;
- des risques.

### 2.5 Contrôle

Le contrôle transforme la trajectoire et la vitesse cibles en commandes continues :

- direction ;
- accélération ;
- freinage.

Il reste soumis aux limites et à l’autorité du modèle physique.

## 3. Principe retenu : architecture hybride

La revue conclut qu’aucune famille de méthodes ne couvre seule tous les besoins.

| Famille | Forces | Limites principales |
|---|---|---|
| règles, FSM et behavior trees | prévisibilité, coût faible, explicabilité | calibration manuelle, généralisation limitée |
| recherche et MCTS | anticipation et évaluation explicites | coût de calcul |
| MPC et contrôle modèle | contraintes et stabilité physique | complexité du modèle et de l’optimisation |
| imitation | comportement humain et efficacité des données | dépendance aux démonstrations |
| reinforcement learning | découverte autonome de politiques | opacité, instabilité, volume de données |
| self-play | adaptation compétitive | non-stationnarité et conventions fermées |
| méthodes hybrides | compromis entre contrôle et adaptation | intégration et validation plus complexes |

La direction retenue pour Automation LAP est donc une architecture hybride :

- stratégie, règles et sécurité explicites ;
- intentions tactiques inspectables ;
- apprentissage possible pour la perception, la prédiction et l’évaluation ;
- planification vérifiable ;
- contrôle contraint par la physique ;
- autorité finale conservée par le cœur déterministe.

## 4. Place recommandée de l’apprentissage

L’apprentissage n’est pas retenu comme autorité globale produisant directement toutes les commandes.

| Domaine | Socle recommandé | Apprentissage envisageable |
|---|---|---|
| perception | modèle déterministe bruité | estimation et suivi d’intentions |
| stratégie | utilités et objectifs explicites | estimation de résultats futurs |
| tactique | catalogue d’intentions interprétables | proposition, classement ou notation |
| trajectoire | génération géométrique contrainte | priorisation de candidats |
| contrôle | contrôleur déterministe | correction résiduelle bornée |
| sécurité et règles | contraintes explicites | aucune autorité finale apprise |

Le rôle privilégié de l’apprentissage est :

> proposer, classer ou évaluer des options admissibles, sans contourner les contraintes physiques, réglementaires et de sécurité.

## 5. Guidage de la recherche par apprentissage

Une architecture candidate cohérente avec la référence est :

1. générer un ensemble borné d’intentions tactiques ;
2. utiliser un modèle appris pour les classer ;
3. simuler ou évaluer les meilleures options ;
4. éliminer les options non admissibles ;
5. construire une trajectoire explicite ;
6. exécuter cette trajectoire avec un contrôleur déterministe.

Exemples d’intentions :

- conserver la ligne ;
- suivre à distance ;
- attaquer à gauche ;
- attaquer à droite ;
- défendre l’intérieur ;
- abandonner le dépassement ;
- réduire le rythme ;
- préserver les pneus.

Cette structure conserve un espace de décision compréhensible, un coût calculatoire borné et une raison journalisable.

## 6. Imitation depuis un professeur privilégié

La revue présente l’approche dite *Learning by Cheating* :

- un professeur dispose d’un état complet pendant l’entraînement ;
- il génère des décisions ou trajectoires expertes ;
- un élève apprend à reproduire ces décisions avec une observation limitée ;
- seule la politique limitée est utilisée en exploitation.

Ce principe est retenu comme piste particulièrement compatible avec Automation LAP.

Le professeur peut lire l’état autoritatif et utiliser un planificateur coûteux. L’élève doit fonctionner à partir de la perception imparfaite du pilote. Les différences de compétence peuvent alors provenir de :

- précision des observations ;
- horizon de perception ;
- qualité ou quantité des démonstrations ;
- capacité de prédiction ;
- fonction d’utilité ;
- propension à suivre ou contester le professeur.

Cette méthode pourrait produire des pilotes moins compétents sans réduire artificiellement leurs performances physiques.

## 7. Apprentissage multi-agent

### 7.1 Self-play

Le self-play est retenu comme méthode possible pour faire émerger attaque, défense et adaptation.

Il ne doit pas être utilisé seul. Les campagnes devraient également contenir :

- pilotes heuristiques fixes ;
- anciennes générations ;
- profils spécialisés ;
- comportements irréguliers ;
- scénarios de référence écrits.

Cette diversité limite le risque qu’une population apprenne uniquement à exploiter ses propres conventions.

### 7.2 Curriculum

L’apprentissage devrait progresser par étapes :

1. tour autonome ;
2. suivi d’une voiture lente ;
3. dépassement sans défense ;
4. défense simple ;
5. côte-à-côte ;
6. trafic à trois voitures ;
7. petit peloton ;
8. peloton de 12 à 20 voitures ;
9. usure, carburant et stratégie ;
10. incidents, règles et drapeaux.

Chaque étape doit conserver les scénarios précédents dans les tests de non-régression.

### 7.3 Modélisation des adversaires

Un pilote doit pouvoir estimer les mouvements futurs des concurrents.

Un contrat candidat pourrait exposer :

```csharp
public readonly record struct OpponentPrediction(
    VehicleId VehicleId,
    ManeuverIntent ExpectedIntent,
    TrajectoryEnvelope PredictedEnvelope,
    double Confidence,
    double PredictionHorizon);
```

La compétence, l’attention et l’état temporaire du pilote influenceraient la précision et l’horizon de cette prédiction.

## 8. Contrôle du concepteur et crédibilité

La revue souligne la tension entre :

- optimalité ;
- réalisme ;
- comportement humain ;
- équité ;
- intérêt de l’expérience ;
- contrôle du concepteur.

Pour Automation LAP, un pilote mathématiquement optimal n’est pas nécessairement souhaitable. La simulation doit produire des courses :

- plausibles ;
- variées ;
- explicables ;
- cohérentes avec les voitures et pilotes ;
- imparfaites sans sembler manipulées ;
- statistiquement calibrables.

Les erreurs doivent découler d’une cause enregistrée : perception, décision, risque accepté, état du pilote, limite physique ou événement.

## 9. Grille d’évaluation retenue

La revue distingue quatre axes : performance, qualité comportementale, robustesse et praticité. Ils sont retenus comme structure commune.

### 9.1 Performance

- temps au tour ;
- progression ;
- régularité ;
- positions gagnées ou défendues ;
- qualité des dépassements ;
- résultat relatif à la voiture disponible ;
- qualité stratégique.

### 9.2 Qualité comportementale

- crédibilité des trajectoires ;
- style identifiable ;
- cohérence avec le profil du pilote ;
- respect des règles et de l’étiquette ;
- absence d’oscillations artificielles ;
- lisibilité et explicabilité des décisions.

### 9.3 Robustesse

- transfert entre circuits ;
- transfert entre voitures ;
- réaction au trafic dense ;
- récupération après perturbation ;
- résistance au bruit de perception ;
- stabilité hors distribution d’entraînement ;
- absence de régression sur les anciens scénarios.

### 9.4 Praticité

- coût CPU et mémoire ;
- coût par voiture ;
- compatibilité avec 12 à 20 voitures ;
- simulation headless accélérée ;
- volume et coût des données ;
- déterminisme et reproductibilité ;
- facilité de calibration ;
- contrôle du concepteur ;
- versionnement et déploiement ;
- diagnostic et testabilité.

## 10. Relation avec les études précédentes

| Étude | Apport retenu |
|---|---|
| AI-CANDIDATE-001 — α-RACER | paramètres tactiques interprétables et fonction apprise d’évaluation |
| AI-CANDIDATE-002 — RacerAI | apprentissage évolutionnaire, diversité et archive de champions |
| AI-REFERENCE-001 — cette revue | architecture hiérarchique hybride et grille d’évaluation |
| faisabilité Automation LAP | cœur déterministe, physique, trafic, replay et exécution headless |

La direction émergente est la suivante :

```text
Architecture hiérarchique hybride
        │
        ├── Perception et prédiction éventuellement apprises
        ├── Intentions tactiques interprétables
        ├── Évaluation apprise ou évolutionnaire
        ├── Planification explicite
        └── Sécurité et contrôle déterministes
```

Cette direction reste une hypothèse de conception à comparer aux prochaines références et aux prochains candidats.

## 11. Limites de la source

Le document est un preprint non évalué par les pairs. Sa portée est large, mais sa valeur probante est limitée par :

- l’absence d’implémentation ;
- l’absence de contrat logiciel ;
- l’absence de benchmark unifié ;
- des comparaisons principalement qualitatives ;
- la forte hétérogénéité des jeux et simulateurs comparés ;
- l’usage de sources industrielles secondaires ;
- une traçabilité de sélection moins détaillée que dans les meilleures revues systématiques ;
- l’absence de preuve propre concernant 12 à 20 voitures.

La source doit donc être utilisée comme taxonomie argumentée, pas comme démonstration qu’une architecture particulière est supérieure.

## 12. Décisions de conception enregistrées

Cette référence permet de retenir provisoirement les principes suivants pour la phase d’analyse :

1. séparer perception, stratégie, tactique, trajectoire et contrôle ;
2. privilégier une architecture hybride ;
3. conserver des intentions tactiques interprétables ;
4. employer l’apprentissage pour proposer, classer, prédire ou évaluer ;
5. maintenir des contraintes déterministes de sécurité, de règles et de physique ;
6. étudier l’imitation depuis un professeur privilégié ;
7. étudier le self-play avec curriculum et adversaires archivés ;
8. représenter explicitement les prédictions d’adversaires ;
9. évaluer tout candidat selon performance, qualité, robustesse et praticité ;
10. ne pas confondre performance brute et crédibilité du pilote.

Ces principes restent révisables jusqu’à la synthèse finale et à leur éventuelle formalisation dans un ADR.

## 13. Conclusion figée

**Game-Driven Intelligence est retenu comme référence structurante de la phase d’analyse de conception de l’IA pilote.**

Il ne fournit pas de pilote directement implémentable. Il fixe néanmoins un cadre cohérent pour comparer les solutions et consolide une direction : architecture hiérarchique hybride, apprentissage borné par des composants déterministes, planification inspectable et évaluation multicritère.

Les prochains candidats devront être positionnés dans cette taxonomie et évalués avec la grille enregistrée dans le présent document.
