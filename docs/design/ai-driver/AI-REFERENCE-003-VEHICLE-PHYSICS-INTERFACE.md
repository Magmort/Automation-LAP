# Référence de conception IA pilote — Vehicle Physics Interface

- **Statut :** référence technique retenue
- **Identifiant :** AI-REFERENCE-003
- **Date :** 8 septembre 2026
- **Document :** *Programming Vehicles in Games*
- **Auteur :** Wassim Alhajomar
- **Publication :** article issu d’une conférence du 13 juillet 2025
- **Source :** [wassimulator.com](https://wassimulator.com/blog/programming/programming_vehicles_in_games.html)
- **Statut scientifique :** ressource pédagogique, non évaluée par les pairs
- **Objet :** définir la frontière entre modèle physique, contrôleur et IA pilote dans Automation LAP

## 1. Position de la référence

Cet article ne constitue pas une spécification scientifique du futur modèle physique. Il fournit une décomposition pédagogique utile de la voiture et explique comment les commandes du conducteur deviennent des forces physiques.

Il est retenu pour :

- clarifier les responsabilités de la physique et de l’IA ;
- identifier les états utiles à la perception du pilote ;
- préserver les rétroactions entre groupe motopropulseur, pneus et châssis ;
- relier la physique aux profils GGV et aux racing lines propres aux véhicules ;
- définir une stratégie de caractérisation automatique ;
- éviter qu’un modèle appris contourne ou remplace l’autorité physique.

Les équations heuristiques de l’article ne sont pas adoptées comme implémentation.

## 2. Décomposition conceptuelle

L’article divise le véhicule en trois ensembles couplés :

1. moteur, boîte et transmission ;
2. roues et pneus ;
3. châssis.

    moteur et boîte
        │ couple
        ▼
    roues et pneus
        │ forces aux contacts
        ▼
       châssis

Les échanges sont bidirectionnels :

- la vitesse des roues influence le régime moteur ;
- le couple moteur influence la vitesse des roues ;
- les pneus appliquent leurs forces au châssis ;
- les mouvements du châssis modifient la charge sur les pneus.

Cette structure est retenue comme frontière conceptuelle. Les composants logiciels réels pourront être plus simples ou regroupés tant que ces dépendances physiques essentielles restent représentées.

## 3. Moteur et transmission

Le moteur est présenté comme une fonction transformant régime et accélérateur en couple. La boîte et le différentiel transforment couple et vitesse de rotation selon leurs rapports.

Pour Automation LAP, les grandeurs importantes sont :

- courbe de couple importée ;
- régime courant ;
- rapport engagé ;
- rapports de boîte et de différentiel ;
- rayon de roue ;
- pertes de transmission ;
- délai ou inertie de réponse ;
- interruption éventuelle du couple au changement de rapport ;
- frein moteur.

Une même commande d’accélérateur ne doit pas produire une accélération identique à tous les régimes et sur tous les rapports.

La fonction de courbe moteur construite empiriquement dans l’article est une illustration de réglage. Elle ne doit pas remplacer les courbes issues d’Automation ou les données autoritatives du projet.

## 4. Pneus et glissement

L’article présente les concepts fondamentaux :

- le taux de glissement longitudinal commande la traction et le freinage ;
- l’angle de dérive commande la force latérale ;
- la charge verticale modifie le potentiel d’adhérence ;
- au-delà du pic, une augmentation du glissement peut réduire la force ;
- sous-virage et survirage peuvent émerger des différences de comportement entre essieux.

Une valeur de glissement non nulle ne signifie pas nécessairement une perte totale d’adhérence. La zone utile se situe généralement avant ou autour du pic de force.

Cette progressivité est importante pour le pilote : elle permet une limite contrôlable plutôt qu’une transition binaire entre adhérence parfaite et glissade.

## 5. Adhérence combinée

Un pneu ne peut pas fournir indépendamment sa force longitudinale maximale et sa force latérale maximale.

Une approximation simple utilise un cercle ou une ellipse :

    Fx² + Fy² <= (mu Fz)²

L’article calcule d’abord les composantes puis les ramène dans cette enveloppe. Il modifie aussi certaines caractéristiques des courbes selon l’autre composante de glissement.

Automation LAP retient le principe de budget d’adhérence combiné. La formulation exacte devra être définie et validée séparément.

Cette contrainte doit rendre naturellement possibles :

- freinage maximal en ligne droite ;
- réduction du freinage à mesure que le braquage augmente ;
- trail braking ;
- accélération progressive en sortie ;
- perte de direction lors d’un blocage important ;
- perte de motricité sous forte accélération latérale.

## 6. Châssis et comportements émergents

Les forces des pneus sont appliquées aux points de contact. Leur somme et leurs moments accélèrent et font pivoter le châssis.

La direction seule ne doit pas imposer directement la rotation de la voiture. Elle modifie l’orientation des roues, puis les pneus génèrent des forces selon leur charge, leur dérive et l’adhérence disponible.

Le principe retenu est :

> Sous-virage, survirage, patinage et blocage doivent autant que possible émerger du modèle physique au lieu d’être imposés comme états artificiels.

Cette propriété est essentielle pour que les différences de véhicules aient une signification utilisable par l’IA.

## 7. Autorité de la physique

L’IA produit des commandes de conducteur :

- accélérateur ;
- frein ;
- direction ;
- sélection ou demande de rapport.

La physique décide ensuite :

- du couple effectivement transmis ;
- de la vitesse angulaire des roues ;
- du glissement ;
- des forces longitudinales et latérales ;
- des accélérations ;
- de la trajectoire réelle.

L’IA ne doit jamais écrire directement une vitesse, une accélération, une force, une rotation ou une position sur la piste.

Une vitesse cible issue d’un RacingLineProfile demeure une consigne du contrôleur, pas une contrainte appliquée au véhicule.

## 8. Niveaux d’accès à l’état

Trois niveaux sont distingués.

### 8.1 État autoritatif

Réservé à la physique et aux diagnostics :

- état exact du châssis ;
- vitesses et charges exactes des roues ;
- forces internes ;
- paramètres des pneus ;
- états détaillés de transmission ;
- contacts et collisions.

### 8.2 État dérivé

Accessible aux planificateurs et professeurs déterministes :

- vitesse longitudinale et latérale ;
- accélérations ;
- vitesse de lacet ;
- utilisation estimée de l’adhérence ;
- enveloppe GGV ;
- marge physique ;
- profil de vitesse réalisable.

### 8.3 Perception du pilote

Accessible aux composants représentant le pilote :

- observation limitée ;
- bruit ;
- délai ;
- horizon d’anticipation ;
- estimations plutôt que vérités internes ;
- confiance et incertitude.

Un modèle appris exploité en course ne doit pas bénéficier silencieusement d’informations impossibles à percevoir.

## 9. Contrats candidats

La commande du pilote pourrait être représentée par :

~~~csharp
public readonly record struct DriverCommand(
    double Throttle,
    double Brake,
    double Steering,
    GearCommand Gear);
~~~

Une observation physique dérivée pourrait contenir :

~~~csharp
public readonly record struct VehicleObservation(
    double LongitudinalSpeed,
    double LateralSpeed,
    double YawRate,
    double LongitudinalAcceleration,
    double LateralAcceleration,
    double EngineRpm,
    int Gear,
    double EstimatedGripUsage,
    StabilityTendency Stability);
~~~

Ces contrats sont illustratifs. Ils ne constituent pas encore les types définitifs d’Automation LAP.

## 10. Lien avec les enveloppes GGV

L’adhérence combinée décrite dans l’article est le fondement physique des diagrammes GGV exploités par AI-CANDIDATE-003.

La chaîne retenue est :

    VehicleDefinition
            │
            ▼
    physique autoritative
            │
            ▼
    essais automatisés
            │
            ▼
    enveloppe GGV mesurée
            │
            ▼
    RacingLineProfile
            │
            ▼
    contrôleur du pilote

L’enveloppe doit être mesurée dans le moteur physique d’Automation LAP plutôt que déduite uniquement de paramètres importés. Cela garantit que la trajectoire planifiée correspond au véhicule réellement simulé.

## 11. Banc de caractérisation automatique

### 11.1 Groupe motopropulseur

- accélération selon vitesse, régime et rapport ;
- vitesse maximale ;
- régime de changement optimal ;
- frein moteur ;
- délai de réponse.

### 11.2 Freinage

- décélération maximale selon la vitesse ;
- distance d’arrêt ;
- comportement au blocage ;
- influence de l’appui aérodynamique.

### 11.3 Comportement latéral

- accélération latérale maximale selon la vitesse ;
- dérive au pic d’adhérence ;
- gradient de sous-virage ;
- stabilité après dépassement du pic.

### 11.4 Adhérence combinée

- freinage disponible à plusieurs accélérations latérales ;
- motricité disponible en sortie ;
- comportement en trail braking ;
- récupération après glissement.

Les essais doivent être headless, reproductibles et versionnés avec la définition du véhicule et la physique.

## 12. Niveau de fidélité recommandé

| Composant | Niveau initial recommandé |
|---|---|
| moteur | courbe de couple importée |
| boîte | rapports et changements explicites |
| transmission | couple aux roues avec pertes simples |
| pneus | slip ratio et slip angle par roue ou essieu |
| adhérence combinée | cercle ou ellipse |
| charge | transferts longitudinal et latéral simplifiés |
| aérodynamique | traînée et appui selon la vitesse |
| châssis | corps rigide plan avec lacet |
| suspension détaillée | différée |
| température et usure | couches ultérieures |

Ce niveau vise un compromis entre comportements significatifs, déterminisme, simulation accélérée et coût compatible avec 12 à 20 voitures.

## 13. Conséquences pour l’apprentissage

Un environnement physique insuffisant expose l’apprentissage à plusieurs risques :

- exploitation de transitions impossibles ;
- commandes oscillantes profitant du pas de simulation ;
- confusion entre trajectoire optimale et défaut du moteur ;
- absence de transfert lors d’une amélioration physique ;
- homogénéisation artificielle des voitures.

Les campagnes devront donc :

- versionner le modèle physique ;
- associer chaque donnée d’entraînement à cette version ;
- borner les commandes ;
- tester différentes fréquences de décision ;
- surveiller glissement, saturation et oscillations ;
- invalider les profils et modèles lorsque la physique change significativement.

La physique reste l’autorité finale même lorsque la tactique ou le contrôle comprend des composants appris.

## 14. Limites de la source

L’article est une introduction pédagogique fondée en partie sur l’expérience de l’auteur. Il ne fournit pas :

- de validation expérimentale systématique ;
- de benchmark ;
- de suite de tests ;
- de calibration vérifiée sur des véhicules réels ;
- de méthode complète de transfert de charge ;
- de formulation rigoureuse de la suspension ;
- de traitement détaillé des basses vitesses ;
- de conventions de signe complètes ;
- de méthode d’intégration et de stabilité ;
- de preuve de performance pour de grands pelotons.

La courbe moteur est réglée visuellement. Le couplage moteur–roues repose sur des termes de poursuite proportionnelle. La combinaison des forces de pneus est heuristique.

Ces éléments peuvent guider un prototype, mais ne doivent pas être considérés comme des équations de référence sans validation complémentaire.

## 15. Évaluation selon la grille commune

| Axe | Évaluation |
|---|---|
| architecture conceptuelle | forte |
| définition de la frontière physique–IA | très forte |
| introduction aux pneus | bonne |
| adhérence combinée | pertinente |
| différenciation des véhicules | forte |
| modèle directement implémentable | faible |
| validation scientifique | faible |
| stabilité numérique | insuffisamment traitée |
| lien avec les profils GGV | très fort |
| lien avec l’apprentissage | indirect mais structurant |
| scalabilité à 12–20 voitures | non démontrée |
| testabilité | à construire dans Automation LAP |

## 16. Relation avec les études précédentes

| Étude | Relation |
|---|---|
| AI-REFERENCE-001 — Game-Driven Intelligence | place la physique sous le contrôle et la planification |
| AI-REFERENCE-002 — Race Driver Model | définit le besoin d’une enveloppe dynamique propre au véhicule |
| AI-CANDIDATE-003 — Raceline-Optimization | consomme les enveloppes GGV pour générer trajectoire et vitesse |
| AI-REFERENCE-003 — cette étude | définit comment la physique produit les capacités observables et exécute les commandes |

La direction consolidée est :

1. la physique produit le comportement réel du véhicule ;
2. un banc automatisé en mesure les capacités ;
3. le planificateur génère un profil voiture–circuit ;
4. la tactique peut demander de s’écarter de ce profil ;
5. le contrôleur produit des commandes de conducteur ;
6. la physique applique ces commandes et reste autoritative.

## 17. Décisions de conception enregistrées

Cette référence permet de retenir provisoirement les principes suivants :

1. séparer conceptuellement groupe motopropulseur, pneus et châssis ;
2. conserver leurs boucles de rétroaction ;
3. représenter le glissement longitudinal et latéral ;
4. limiter les forces par une enveloppe d’adhérence combinée ;
5. faire émerger sous-virage et survirage des forces physiques ;
6. limiter les sorties de l’IA à des commandes de conducteur ;
7. ne pas exposer directement les paramètres internes à la perception du pilote ;
8. distinguer état autoritatif, état dérivé et perception ;
9. mesurer automatiquement les enveloppes GGV ;
10. versionner profils, données et modèles avec la physique ;
11. ne pas adopter directement les équations heuristiques de l’article ;
12. valider fidélité, stabilité et coût avant toute décision d’architecture.

Ces principes restent révisables jusqu’à la synthèse finale et à leur éventuelle formalisation dans un ADR.

## 18. Conclusion figée

**Programming Vehicles in Games est retenu comme référence conceptuelle pour la frontière entre physique, contrôle et IA.**

Son apport principal n’est pas une implémentation prête à l’emploi, mais une décomposition claire des rétroactions qui donnent un sens physique aux commandes du pilote.

Automation LAP retiendra le principe suivant :

> L’IA choisit et commande ; le contrôleur traduit ; la physique détermine le résultat réel.

Cette base relie le futur modèle physique à la génération des profils GGV, aux racing lines propres aux véhicules et aux méthodes d’apprentissage, sans transformer l’article pédagogique en spécification scientifique.
