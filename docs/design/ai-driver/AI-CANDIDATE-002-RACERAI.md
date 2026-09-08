# Étude de candidat IA pilote — RacerAI

- **Statut :** candidat rejeté comme architecture ; approche d’apprentissage évolutionnaire retenue
- **Identifiant :** AI-CANDIDATE-002
- **Date :** 8 septembre 2026
- **Source étudiée :** [erjbroek/RacerAI](https://github.com/erjbroek/RacerAI)
- **Licence :** MIT
- **Objet :** évaluer RacerAI comme architecture de pilote et identifier les éléments transversaux réutilisables pour Automation LAP

## 1. Décision synthétique

RacerAI n’est pas retenu comme candidat à l’architecture de l’IA pilote d’Automation LAP.

Son approche générale d’apprentissage par évolution est toutefois conservée comme piste de conception pour :

- calibrer hors ligne des paramètres interprétables ;
- explorer plusieurs familles de comportements ;
- maintenir une diversité de profils de pilotes ;
- conserver et comparer des champions ;
- visualiser la progression d’une campagne d’apprentissage.

Cette décision ne retient ni le réseau neuronal du projet, ni son modèle physique, ni sa fonction de fitness, ni son couplage entre rendu, entraînement et simulation.

## 2. Nature du projet

RacerAI est une démonstration pédagogique en TypeScript conçue pour montrer comment des algorithmes génétiques peuvent apprendre à des voitures à parcourir des circuits dessinés par l’utilisateur.

Le dépôt propose deux approches :

1. faire évoluer une séquence ouverte de commandes discrètes ;
2. faire évoluer les poids d’un petit réseau qui transforme des rayons de détection en commandes discrètes.

Le projet privilégie la visibilité immédiate de l’évolution et la légèreté du calcul. Il ne cherche pas à modéliser une course complète, une physique automobile crédible ou des interactions tactiques complexes.

## 3. Architecture observée

### 3.1 Variante par séquence de commandes

Chaque voiture possède une liste d’actions choisies parmi :

- accélérer ;
- freiner ;
- tourner à gauche ou à droite ;
- tourner fortement à gauche ou à droite.

Après extinction de la population, les meilleurs individus sont conservés ou reproduits, puis une partie de leurs commandes est mutée. Cette méthode correspond à une recherche de trajectoire ouverte adaptée à un circuit et un départ donnés.

### 3.2 Variante par réseau

La variante neuronale utilise :

- cinq rayons couvrant 180 degrés ;
- quatre sorties : gauche, droite, accélération et freinage ;
- vingt connexions directes entre les cinq entrées et les quatre sorties ;
- aucune couche cachée ;
- une activation sigmoïde ;
- une sélection binaire par comparaison des sorties.

Les biais sont créés et mutés, mais leur application est commentée dans la fonction d’inférence étudiée.

### 3.3 Évolution

Le cycle d’évolution contient :

- calcul d’un fitness ;
- regroupement des génomes proches en espèces ;
- sélection des survivants ;
- sélection proportionnelle au fitness ;
- croisement des poids ;
- petites et grandes mutations ;
- conservation optionnelle de deux champions ;
- historique des records et visualisation de la progression.

## 4. Raisons du rejet comme architecture de pilote

### 4.1 Perception insuffisante

Le réseau ne reçoit que les distances aux limites de piste. Il ignore notamment :

- vitesse et accélération ;
- orientation relative à la piste ;
- taux de lacet ;
- courbure à venir ;
- progression longitudinale structurée ;
- autres voitures ;
- état des pneus et du véhicule ;
- stratégie et règles de course.

Il apprend à rester sur une surface, pas à raisonner comme un pilote de course.

### 4.2 Absence de trafic et de tactique

Le modèle ne représente pas le suivi, le dépassement, la défense, le côte-à-côte, la réinsertion ou la gestion du risque. Il ne peut donc pas répondre aux besoins centraux du vertical slice.

### 4.3 Couplage direct perception-commandes

Le réseau transforme directement ses rayons en commandes gauche/droite et gaz/frein. Décision, trajectoire, contrôle et physique sont confondus.

Cette structure est incompatible avec la séparation visée dans Automation LAP entre :

1. perception ;
2. décision stratégique ;
3. décision tactique ;
4. intention ou trajectoire ;
5. contrôle de conduite ;
6. modèle physique.

### 4.4 Physique non représentative

Le mouvement repose sur des constantes empiriques, des modifications directes de l’angle et des composantes de vitesse. Certains paramètres dépendent de la fenêtre de rendu. Cette physique ne peut servir ni à valider une conduite automobile crédible ni à entraîner directement un modèle destiné au cœur autoritatif.

### 4.5 Fitness trop pauvre

Le fitness utilise principalement :

- distance parcourue ;
- nombre de tours ;
- durée ;
- franchissement du départ ;
- élimination après sortie de piste.

Il ne représente pas la stabilité, le confort dynamique, la consommation, l’usure, le risque, les contacts, les pénalités ou le respect d’une stratégie. Il peut donc récompenser des comportements efficaces dans la démonstration mais indésirables dans Automation LAP.

### 4.6 Généralisation non démontrée

L’apprentissage dépend fortement du circuit, du départ, de la physique et de la disposition des rayons. Aucune preuve ne montre un transfert robuste entre circuits, voitures ou contextes de trafic.

### 4.7 Reproductibilité insuffisante

La création, le croisement et la mutation utilisent directement `Math.random()`. Les graines et les flux aléatoires ne sont pas versionnés, ce qui empêche de reproduire exactement une campagne.

## 5. Éléments rejetés

| Élément | Décision | Motif |
|---|---|---|
| réseau direct 5 × 4 | Rejeté | perception et expressivité insuffisantes |
| cinq rayons vers les bords | Rejeté comme perception principale | aucune information véhicule, piste structurée ou trafic |
| commandes binaires directes | Rejeté | couplage décision/contrôle |
| séquence ouverte de mouvements | Rejetée | mémorisation d’un scénario plutôt que conduite adaptative |
| modèle physique | Rejeté | non représentatif et lié au rendu |
| fitness distance/tours | Rejeté | objectif incomplet et facilement exploitable |
| implémentation de la spéciation | Non reprise telle quelle | méthode rudimentaire et non validée |
| architecture TypeScript navigateur | Rejetée | incompatible avec le cœur C# headless |

## 6. Apports retenus

### 6.1 Apprentissage évolutionnaire hors ligne

Le principe d’une population de solutions évaluées par le simulateur est retenu.

Dans Automation LAP, les génomes ne devraient pas encoder des commandes instantanées. Ils pourraient encoder des paramètres interprétables comme :

- rythme cible ;
- anticipation de freinage ;
- adhérence à la ligne ;
- distance de suivi ;
- dégagement de dépassement ;
- intensité de défense ;
- tolérance au risque ;
- hystérésis des décisions.

Cette piste complète naturellement α-RACER : un algorithme évolutionnaire pourrait calibrer ses paramètres tactiques, leurs bornes ou certains poids de la fonction d’utilité.

### 6.2 Maintien de la diversité

Le regroupement en espèces traduit une idée pertinente : éviter qu’une population converge vers un seul comportement.

Automation LAP a besoin de plusieurs styles viables plutôt que d’un unique pilote optimal. La mise en œuvre future pourrait employer des méthodes plus robustes :

- niches comportementales ;
- recherche de nouveauté ;
- optimisation multi-objectifs ;
- quality diversity ;
- archive de type MAP-Elites.

Aucune de ces méthodes n’est encore choisie. Le besoin de préserver la diversité est toutefois retenu.

### 6.3 Élitisme et archive des champions

La conservation des meilleurs individus est retenue comme principe de campagne.

Un champion d’Automation LAP devrait être enregistré avec :

- paramètres ou modèle ;
- versions des contrats ;
- version du simulateur ;
- empreintes des voitures et circuits ;
- graines ;
- métriques ;
- résultats par scénario ;
- replays de référence.

Une nouvelle génération ne devrait remplacer un champion qu’après validation sur une suite de scénarios, afin d’éviter la suradaptation à une piste.

### 6.4 Visualisation de l’apprentissage

RacerAI rend visibles les capteurs, connexions, trajectoires, espèces et records. Ce principe est retenu pour les outils de conception et de calibration.

Un outil Automation LAP pourrait exposer :

- perception effective du pilote ;
- adversaires considérés ;
- trajectoires candidates ;
- coût ou utilité de chaque option ;
- intention retenue ;
- limites physiques actives ;
- population et diversité ;
- courbes de progression ;
- comparaison avec la baseline ;
- accès direct aux replays des meilleurs et pires cas.

### 6.5 Évaluation massive par simulation simplifiée

La légèreté des individus illustre l’intérêt d’une évaluation en plusieurs étages :

1. filtrage rapide dans un environnement simplifié ;
2. évaluation des survivants dans le cœur physique autoritatif ;
3. validation statistique finale sur plusieurs circuits, voitures et situations.

Le modèle simplifié ne doit jamais devenir la preuve finale de validité.

## 7. Risques de l’apprentissage évolutionnaire

Le fait de retenir l’approche par apprentissage ne suffit pas à garantir de bons pilotes.

Les risques à contrôler sont :

- exploitation de défauts du simulateur ;
- surapprentissage à une piste ou une voiture ;
- convergence vers un style unique ;
- comportement rapide mais non crédible ;
- fitness mal équilibré ;
- coût élevé des campagnes ;
- absence d’explication des résultats ;
- régression invisible sur certains scénarios ;
- dépendance à des paramètres ou modèles non versionnés.

Chaque campagne devra utiliser des graines explicites, un corpus de scénarios versionné et des métriques multicritères.

## 8. Position dans l’architecture cible

L’apprentissage doit rester hors de la boucle autoritative de production :

```text
Campagnes headless hors ligne
        │
        ▼
Évaluation et optimisation
        │
        ▼
Artefact candidat versionné
        │
        ▼
Validation multi-scénarios
        │
        ▼
Paramètres ou modèle approuvé
        │
        ▼
Inférence déterministe dans AutomationLAP.AI
```

Le cœur de simulation fournit l’environnement et les métriques. Il ne doit pas dépendre d’une bibliothèque d’apprentissage. Les outils d’entraînement peuvent vivre dans un projet ou processus séparé.

## 9. Relation avec AI-CANDIDATE-001

| Sujet | α-RACER | Apport retenu de RacerAI |
|---|---|---|
| politique | paramètres tactiques interprétables | optimisation possible de ces paramètres |
| données | courses simulées hors ligne | génération par populations |
| diversité | non centrale | niches et familles de comportements |
| sélection | maximisation d’une fonction de potentiel | évolution multicritère |
| déploiement | optimisation en ligne puis contrôle | artefact entraîné validé hors ligne |
| explicabilité | forte grâce aux paramètres | à préserver dans le génome et le fitness |

RacerAI ne concurrence donc pas α-RACER comme architecture. Il ajoute une piste de méthode pour rechercher, calibrer et diversifier des politiques interprétables.

## 10. Expérience future candidate

Une expérience dédiée pourrait comparer :

- réglage manuel ;
- recherche par grille ;
- optimisation bayésienne ;
- algorithme génétique simple ;
- méthode de quality diversity.

Les individus encoderaient uniquement des paramètres tactiques explicites. Ils seraient testés sur un corpus de scénarios comprenant au minimum :

- plusieurs circuits ;
- plusieurs voitures ;
- plusieurs positions de départ ;
- conduite libre et trafic ;
- profils prudent, équilibré et agressif ;
- cas nominaux et perturbations ;
- graines répétées.

Les sorties mesureraient simultanément :

- temps au tour et progrès ;
- contacts et sorties ;
- stabilité de trajectoire ;
- oscillations tactiques ;
- usure et consommation ;
- qualité des dépassements ;
- diversité comportementale ;
- coût de simulation ;
- robustesse hors distribution d’entraînement.

## 11. Conclusion figée

**Candidat RacerAI : rejeté comme architecture d’IA pilote.**

**Approche retenue : apprentissage évolutionnaire hors ligne appliqué à des paramètres tactiques interprétables, avec maintien de diversité, archive de champions, campagnes reproductibles et visualisation des résultats.**

Cette piste est enregistrée comme apport transversal à confronter aux prochains candidats. Elle ne constitue pas encore le choix d’un algorithme génétique précis, d’une bibliothèque d’apprentissage ou d’un format de modèle de production.
