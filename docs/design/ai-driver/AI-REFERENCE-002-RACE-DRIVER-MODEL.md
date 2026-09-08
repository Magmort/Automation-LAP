# Référence de conception IA pilote — Race Driver Model

- **Statut :** référence technique retenue
- **Identifiant :** AI-REFERENCE-002
- **Date :** 8 septembre 2026
- **Document :** *Race driver model*
- **Auteurs :** F. Braghin, F. Cheli, S. Melzi et E. Sabbioni
- **Publication :** *Computers & Structures*, volume 86, 2008, pages 1503–1516
- **Source :** [DOI 10.1016/j.compstruc.2007.04.028](https://doi.org/10.1016/j.compstruc.2007.04.028)
- **Objet :** fournir une base déterministe pour la génération de racing lines propres aux véhicules, les profils de vitesse et le contrôle de conduite d’Automation LAP

## 1. Position de la référence

Ce document ne décrit ni une IA de course complète ni une méthode d’apprentissage. Il modélise un pilote visant à minimiser le temps au tour pour une voiture et une piste données.

Il est retenu comme référence technique pour :

- calculer une trajectoire de référence propre à chaque véhicule ;
- construire un profil de vitesse physiquement réalisable ;
- séparer la planification hors ligne du contrôle en simulation ;
- fournir une baseline déterministe, explicable et reproductible ;
- produire un professeur potentiel pour l’apprentissage par imitation ;
- caractériser des pilotes par leurs paramètres de contrôle et leurs marges.

Cette référence ne constitue pas un ADR et ne sélectionne pas l’algorithme final de l’IA pilote.

## 2. Principe central : une racing line par voiture

Le papier compare deux trajectoires géométriques extrêmes :

- la trajectoire la plus courte ;
- la trajectoire de courbure minimale.

La piste est discrétisée en sections. La position latérale de la trajectoire dans chaque section est définie par une variable bornée entre les deux bords. Des splines cubiques naturelles fermées assurent une trajectoire continue sans rupture artificielle de pente ou de courbure.

L’objectif combine courbure et longueur :

```text
F² = (1 - e) C² + e S²
```

où :

- `C` mesure la courbure ;
- `S` mesure la longueur ;
- `e` règle le compromis entre les deux.

Le coefficient pertinent n’est pas choisi uniquement par la géométrie. Il est sélectionné en minimisant le temps au tour prédit avec les performances du véhicule.

La décision de conception retenue pour Automation LAP est donc :

> La racing line de référence appartient au couple voiture–circuit, et non au circuit seul.

Une voiture peu puissante peut davantage bénéficier d’un chemin court. Une voiture puissante, très adhérente ou disposant d’appui aérodynamique peut accepter une distance supérieure afin de réduire la courbure et de conserver davantage de vitesse.

## 3. Enveloppe dynamique du véhicule

Le planificateur du papier emploie un modèle ponctuel simplifié. Ses contraintes proviennent cependant d’un modèle non linéaire détaillé à quatorze degrés de liberté, ou pourraient provenir de mesures expérimentales.

Les caractéristiques requises sont :

- accélération longitudinale maximale selon la vitesse ;
- décélération maximale selon la vitesse ;
- accélération latérale maximale selon la vitesse ;
- influence de la direction et de l’appui aérodynamique ;
- partage de l’adhérence entre accélérations longitudinale et latérale.

Le partage d’adhérence est représenté par une ellipse de friction. Accélérer ou freiner en virage réduit donc la force longitudinale disponible.

Pour Automation LAP, ces enveloppes ne devraient pas dépendre aveuglément de données importées dont les unités ou l’interprétation resteraient incertaines. Elles pourraient être mesurées directement dans le moteur physique par une campagne automatique :

1. accélération en ligne droite ;
2. freinage maximal ;
3. virage stabilisé ;
4. accélération en appui ;
5. freinage en appui ;
6. répétition à plusieurs vitesses et, si nécessaire, sur plusieurs surfaces.

Cette procédure assurerait la cohérence entre le planificateur et la physique réellement exécutée.

## 4. Construction du profil de vitesse

Une fois la trajectoire fixée, la vitesse maximale locale est d’abord dérivée de la courbure et de l’accélération latérale disponible.

Cette première estimation est ensuite rendue réalisable par des passes tenant compte :

- de la distance nécessaire au freinage avant un virage ;
- de l’accélération disponible à la sortie ;
- de l’ellipse de friction ;
- de l’évolution des performances avec la vitesse.

Le résultat n’est donc pas une simple limitation de vitesse basée sur la courbure. Il constitue un profil longitudinal cohérent sur l’ensemble du tour.

Pour Automation LAP, un profil de référence devrait au minimum contenir :

```csharp
public sealed record RacingLineProfile(
    TrackDefinitionId Track,
    VehicleDefinitionId Vehicle,
    PhysicsVersion PhysicsVersion,
    IReadOnlyList<RacingLineSample> Samples);

public readonly record struct RacingLineSample(
    double Distance,
    double LateralOffset,
    double Curvature,
    double TargetSpeed,
    double LongitudinalAccelerationLimit,
    double LateralAccelerationLimit);
```

Ces contrats sont illustratifs. Leur forme définitive dépendra des types et unités autoritatifs du projet.

## 5. Contrôle longitudinal

Le conducteur du papier combine :

- une commande anticipative issue d’un modèle longitudinal ;
- une correction PI de l’erreur de vitesse ;
- une distance de vision dépendant de la vitesse, de l’accélération et d’un temps d’anticipation ;
- une logique de changement de rapport ;
- une dynamique d’embrayage et un délai représentant la promptitude du pilote.

L’intérêt pour Automation LAP n’est pas de reproduire littéralement ce contrôleur, mais de conserver la séparation entre :

- le profil de vitesse désiré ;
- l’anticipation des événements futurs ;
- la correction de l’erreur actuelle ;
- les limites physiques de l’actionneur.

Cette structure fournit une baseline plus riche qu’une adaptation locale de vitesse fondée uniquement sur la courbure immédiate.

## 6. Contrôle latéral

La commande de direction combine principalement :

- une erreur d’orientation mesurée sur un point anticipé ;
- une erreur latérale mesurée à la position actuelle ;
- une compensation du sous-virage ou du survirage ;
- une correction transitoire visant à lisser le comportement.

La distance d’anticipation dépend de la vitesse et d’un temps de réponse caractéristique du conducteur.

Cette approche pourrait enrichir ou remplacer progressivement un suivi de trajectoire purement géométrique. Elle doit toutefois être comparée aux contrôleurs déjà employés dans Automation LAP et validée avec les unités et la dynamique réelles du moteur.

## 7. Paramétrisation des pilotes

Optimisé uniquement pour le temps au tour, le modèle tend à produire un pilote idéal plutôt que des individus distincts. Plusieurs paramètres peuvent néanmoins devenir des caractéristiques de pilote :

- temps de réaction ;
- horizon d’anticipation ;
- précision latérale ;
- gains de correction ;
- agressivité du freinage ;
- promptitude des changements de rapport ;
- douceur des transitions ;
- part de l’enveloppe d’adhérence volontairement exploitée.

Pour préserver une diversité crédible, Automation LAP ne devrait pas optimiser chaque pilote vers exactement le même optimum. La racing line idéale sert de référence, puis chaque pilote reçoit des contraintes, marges ou déformations cohérentes avec son profil.

Les erreurs devraient rester explicables : anticipation insuffisante, retard de réaction, marge de sécurité, imprécision de contrôle, risque volontaire ou perturbation tactique.

## 8. Architecture proposée

La référence suggère une séparation entre préparation hors ligne et exécution en course.

```text
TrackDefinition ───────────────┐
                              ├──► caractérisation et optimisation
VehicleDefinition ────────────┤
                              │
Version de la physique ───────┘
                                         │
                                         ▼
                                RacingLineProfile
                                         │
Perception ─► stratégie ─► tactique ─────┤
                                         ▼
                              contrôleur déterministe
                                         │
                                         ▼
                                physique du véhicule
```

La tactique ne doit pas être enfermée sur la ligne optimale. Elle peut demander :

- une trajectoire de dépassement ;
- une ligne défensive ;
- un décalage pour le trafic ;
- une vitesse réduite ;
- une marge de sécurité supplémentaire.

Le planificateur produit alors une trajectoire faisable à partir de l’intention, tandis que la racing line reste la référence sans trafic.

## 9. Cache et invalidation

Le profil calculé devrait être versionné ou invalidé selon au moins :

- la géométrie et la largeur de piste ;
- la définition du véhicule ;
- la version du moteur physique ;
- les pneus et l’aérodynamique lorsque ces paramètres varient ;
- l’état de surface si celui-ci modifie significativement l’adhérence.

L’objectif est d’éviter qu’une modification de physique conserve silencieusement une racing line ou un profil de vitesse devenu incohérent.

## 10. Relation avec l’apprentissage

Cette référence fournit un pont concret vers l’orientation par apprentissage déjà retenue.

Le pilote déterministe peut servir :

- de baseline pour mesurer les progrès ;
- de professeur disposant d’un état privilégié ;
- de générateur de démonstrations ;
- de fonction de référence pour l’apprentissage par imitation ;
- d’adversaire stable pendant un curriculum ;
- de solution de repli lorsqu’un composant appris devient incertain.

L’apprentissage peut ensuite intervenir pour :

- estimer les intentions adverses ;
- sélectionner une intention tactique ;
- classer des trajectoires candidates ;
- adapter les marges ;
- reproduire ou enrichir le comportement du professeur.

La ligne et le profil de vitesse demeurent inspectables, tandis que règles, sécurité et autorité physique restent déterministes.

## 11. Complémentarité avec les références précédentes

| Étude | Apport retenu |
|---|---|
| AI-CANDIDATE-001 — α-RACER | paramètres tactiques interprétables et fonction apprise d’évaluation |
| AI-CANDIDATE-002 — RacerAI | apprentissage évolutionnaire, diversité et archive de champions |
| AI-REFERENCE-001 — Game-Driven Intelligence | architecture hiérarchique hybride et grille d’évaluation |
| AI-REFERENCE-002 — cette étude | racing line propre au véhicule, profil de vitesse et contrôleur déterministe de référence |

La combinaison envisagée devient :

1. une enveloppe dynamique mesurée dans la physique d’Automation LAP ;
2. une racing line et un profil de vitesse propres à chaque voiture ;
3. un contrôleur déterministe capable de suivre cette référence ;
4. une couche tactique capable de s’en écarter explicitement ;
5. des composants appris pour proposer, prédire, classer ou calibrer ;
6. des contraintes déterministes pour valider et exécuter.

## 12. Évaluation selon la grille commune

| Axe | Évaluation |
|---|---|
| performance sans trafic | forte |
| crédibilité des trajectoires | forte |
| prise en compte des différences de véhicule | forte |
| explicabilité et reproductibilité | très forte |
| diversité des pilotes | moyenne, à construire par paramétrisation |
| robustesse entre véhicules | prometteuse, sous réserve de caractérisation automatique |
| trafic, dépassement et défense | absents |
| stratégie de course | absente |
| apprentissage et adaptation | absents |
| coût en simulation | favorable après calcul hors ligne |
| coût de préparation | à mesurer pour chaque couple voiture–circuit |
| scalabilité à 12–20 voitures | favorable pour le suivi ; non démontrée pour la tactique |

## 13. Limites de la source

Le papier étudie principalement le tour chronométré d’une voiture isolée. Il ne traite pas :

- du trafic ;
- des dépassements et de la défense ;
- de la stratégie de course ;
- des règles et drapeaux ;
- des erreurs de perception ;
- de l’usure, du carburant ou de la météo ;
- de l’apprentissage ;
- de l’adaptation en ligne.

L’objectif est le temps au tour. Il ne suffit donc pas à produire un pilote humain, crédible et intentionnellement imparfait.

Le papier évoque une optimisation mutuelle plus complète du conducteur et du véhicule, mais cette troisième couche n’est pas développée dans l’étude. Les résultats dépendent aussi de la qualité des enveloppes dynamiques fournies au planificateur.

## 14. Expériences proposées

Avant toute intégration structurante, les expériences suivantes sont recommandées :

1. mesurer automatiquement les enveloppes dynamiques de deux véhicules très différents ;
2. calculer pour chacun la trajectoire la plus courte et celle de courbure minimale ;
3. rechercher le compromis donnant le meilleur temps simulé ;
4. vérifier que les trajectoires optimales diffèrent effectivement entre véhicules ;
5. générer un profil de vitesse et le comparer au contrôleur actuel ;
6. mesurer temps au tour, stabilité, sorties de piste et coût CPU ;
7. introduire plusieurs profils de réaction et de marge ;
8. utiliser le pilote déterministe comme professeur dans une expérience d’imitation limitée.

## 15. Décisions de conception enregistrées

Cette référence permet de retenir provisoirement les principes suivants :

1. associer la racing line de référence au couple voiture–circuit ;
2. inclure la version de la physique et les conditions influentes dans son identité ;
3. dériver le profil de vitesse d’une enveloppe dynamique mesurée ;
4. calculer les profils coûteux hors ligne et les mettre en cache ;
5. séparer ligne idéale, adaptation tactique et contrôle ;
6. conserver un contrôleur déterministe comme baseline ;
7. utiliser les temps de réponse, marges et gains pour caractériser les pilotes ;
8. exploiter cette baseline comme professeur potentiel pour l’apprentissage ;
9. ne pas considérer ce modèle comme une IA de course complète ;
10. valider expérimentalement les bénéfices avant de modifier l’architecture de production.

Ces principes restent révisables jusqu’à la synthèse finale et à leur éventuelle formalisation dans un ADR.

## 16. Conclusion figée

**Race Driver Model est retenu comme référence technique pour la trajectoire et le contrôle de l’IA pilote.**

Son apport central est la génération d’une racing line et d’un profil de vitesse adaptés aux performances de chaque véhicule. Cette base déterministe peut rendre les voitures réellement distinctes, fournir un pilote de référence explicable et devenir un professeur pour les futures méthodes apprises.

Le modèle ne couvre ni la tactique, ni le trafic, ni la stratégie. Il doit donc être intégré comme fondation sous les couches décisionnelles, et non comme remplacement complet de l’architecture hiérarchique hybride.
