# Candidat IA pilote — Evolutionary F1 Race Strategy

- **Statut :** retenu comme point de départ pour expérimentation stratégique hors ligne
- **Identifiant :** AI-CANDIDATE-004
- **Date :** 8 septembre 2026
- **Dépôt étudié :** [bonom/Evolutionary-F1-Race-Strategy](https://github.com/bonom/Evolutionary-F1-Race-Strategy)
- **Publication :** *Evolutionary F1 Race Strategy*, GECCO 2023 Companion
- **Source scientifique :** [DOI 10.1145/3583133.3596349](https://doi.org/10.1145/3583133.3596349)
- **Dernière activité observée :** 22 août 2023
- **Licence observée :** fichier ambigu contenant GPL-3.0 et BSD-3-Clause ; GitHub identifie GPL-3.0
- **Objet :** ouvrir l’étude de la couche stratégique d’Automation LAP

## 1. Décision

Evolutionary F1 Race Strategy est retenu comme **point de départ conceptuel et expérimental** pour la stratégie hors ligne.

Son principe est compatible avec l’architecture hiérarchique retenue :

1. représenter un plan de course lisible ;
2. simuler ses conséquences ;
3. mesurer sa valeur ;
4. employer une recherche évolutionnaire pour explorer les combinaisons ;
5. transmettre le plan retenu aux couches tactiques et de contrôle.

Le dépôt n’est pas retenu comme dépendance de production. Son implémentation optimise essentiellement le temps d’une voiture isolée avec une météo connue à l’avance. Elle ne représente pas encore une stratégie multi-voiture adaptative.

## 2. Problème traité

Le programme cherche une combinaison minimisant le temps total de course à partir de données d’essais.

Il considère notamment :

- le composé pneumatique ;
- l’âge et l’usure des quatre pneus ;
- les arrêts ;
- la masse de carburant ;
- la consommation ;
- la météo ;
- le coût d’un arrêt ;
- certaines règles d’utilisation des composés.

Le dépôt indique une évaluation sur les données du jeu F1 2021 et sur des données d’usure fournies par Pirelli, avec retour d’ingénieurs de Pirelli.

Cette validation donne de la valeur au principe général. Elle ne prouve pas que le modèle, ses paramètres ou son code soient directement transférables à Automation LAP.

## 3. Représentation actuelle d’une stratégie

Chaque individu de la population contient des listes indexées par tour :

- TyreCompound ;
- TyreAge ;
- TyreWear ;
- FuelLoad ;
- PitStop ;
- LapTime ;
- Weather ;
- TotalTime ;
- Valid.

Cette représentation facilite l’évaluation, mais elle est redondante. Une modification d’un arrêt oblige le programme à recalculer et corriger toutes les valeurs dérivées des tours suivants.

Pour Automation LAP, il est préférable de représenter les décisions primaires sous forme de stints. Les valeurs par tour seront produites par le simulateur stratégique.

~~~csharp
public sealed record RaceStrategyPlan(
    IReadOnlyList<StintPlan> Stints,
    FuelPlan Fuel,
    StrategyObjective Objective,
    StrategyAssumptions Assumptions);

public sealed record StintPlan(
    LapWindow PitWindow,
    TyreCompound Compound,
    double TargetPace,
    double GripReserve);
~~~

Ces contrats restent illustratifs.

## 4. Modèle de temps au tour

Le dépôt apprend ou estime plusieurs coefficients à partir des données disponibles. Le temps au tour est ensuite construit comme une somme de contributions :

    temps de référence
    + écart du composé
    + pénalité du carburant
    + pénalité de l’usure
    + pénalité météorologique
    + événements et arrêt éventuel

Les éléments modélisés comprennent :

- la consommation selon les conditions sèches ou humides ;
- la perte de temps liée à la masse de carburant ;
- l’usure de chaque pneu ;
- la perte de temps attribuée à cette usure ;
- la différence de performance entre composés ;
- une pénalité météorologique non linéaire ;
- une pénalité fixe propre au circuit pour les arrêts.

Cette décomposition est retenue. Elle permet de faire évoluer chaque prédicteur indépendamment de l’algorithme de recherche.

## 5. Fonction de fitness et contraintes

La fitness principale est le temps total simulé :

    Fitness = somme des temps au tour + temps des arrêts

Une stratégie est considérée valide si elle respecte notamment :

- un carburant final non négatif ;
- l’utilisation de plusieurs composés lorsque la course est entièrement sèche ;
- certaines limites pratiques d’usure et d’arrêts.

Cette fonction convient à une voiture isolée, mais elle ne suffit pas à la course multi-agent.

Automation LAP devra progressivement considérer :

- position finale ;
- points attendus ;
- probabilité de victoire ou de podium ;
- risque d’abandon ;
- trafic après l’arrêt ;
- possibilité de dépasser ;
- objectifs d’équipe ;
- conservation de la voiture ;
- variance du résultat.

## 6. Recherche évolutionnaire

Le solveur utilise :

- une population initiale aléatoire ;
- une sélection par pénalité dynamique ;
- des mutations ;
- un crossover ;
- une réinjection d’individus en cas de stagnation ;
- une recherche locale finale.

Les mutations portent principalement sur :

- le composé ;
- l’ajout ou le retrait d’un arrêt ;
- la position d’un arrêt ;
- la quantité initiale de carburant.

Le crossover observé agit essentiellement sur le carburant initial. L’exploration des stratégies de pneus et d’arrêts dépend donc fortement des mutations.

La recherche locale est conservée pour complétude, mais le code indique qu’elle n’a pas amélioré les solutions lors des essais.

## 7. Pourquoi l’évolution est pertinente ici

Cette application est plus naturelle que l’évolution directe d’un pilote bas niveau :

- l’espace de décision est discret ;
- l’horizon est long ;
- les plans restent lisibles ;
- l’évaluation peut être beaucoup plus rapide que la physique complète ;
- les contraintes peuvent être vérifiées explicitement ;
- plusieurs plans alternatifs peuvent être conservés.

La conclusion retenue après AI-CANDIDATE-002 est ainsi renforcée :

> L’apprentissage évolutionnaire paraît plus prometteur pour rechercher, calibrer et diversifier des plans que pour produire directement les commandes de conduite.

## 8. Séparation du modèle et de la recherche

Le modèle prédisant le résultat d’un plan doit être indépendant de l’algorithme qui explore les plans.

~~~csharp
public interface IRaceOutcomeModel
{
    StrategyEvaluation Evaluate(
        RaceStrategyPlan plan,
        StrategyScenario scenario);
}
~~~

Cette séparation permettra de comparer :

- recherche exhaustive bornée ;
- algorithme génétique ;
- beam search ;
- recherche locale ;
- Monte-Carlo Tree Search ;
- programmation dynamique ;
- modèle appris.

Elle permettra également de faire évoluer le modèle de course sans réécrire tous les optimiseurs.

## 9. Planification et replanification

Le dépôt produit principalement un plan complet avant le départ. Automation LAP doit distinguer :

### 9.1 Planification initiale

- pneus de départ ;
- carburant ou énergie ;
- nombre probable d’arrêts ;
- fenêtres d’arrêt ;
- composés alternatifs ;
- rythme et marges ;
- scénarios météorologiques.

### 9.2 Replanification en course

- usure observée différente de la prévision ;
- changement de météo ;
- safety car ou neutralisation ;
- incident ;
- trafic ;
- undercut ou overcut ;
- arrêt d’un adversaire ;
- changement d’objectif ;
- plan devenu irréalisable.

La stratégie devrait préférer des fenêtres et des conditions de déclenchement à un ordre rigide tel que « arrêt obligatoire au tour 23 ».

## 10. Incertitude et absence d’omniscience

Dans le dépôt, un fichier décrit les conditions météorologiques futures tour par tour. L’optimiseur dispose donc d’un scénario entièrement connu.

Cette configuration est admissible pour :

- un oracle ;
- une analyse rétrospective ;
- un test contrôlé ;
- une borne supérieure.

Elle n’est pas admissible comme perception normale du stratège.

Automation LAP devra distinguer :

- la météo réelle autoritative ;
- la prévision disponible ;
- l’incertitude ;
- la confiance du stratège ;
- les observations accumulées ;
- les scénarios alternatifs.

Un plan devrait être évalué sur un ensemble de scénarios :

    Score(plan)
      = résultat moyen
      + coefficient de risque × exposition aux mauvais scénarios

Le profil du stratège pourra modifier ce coefficient.

## 11. Trafic et adversaires

Le candidat optimise une voiture isolée. Il ne modélise pas directement :

- le trafic après un arrêt ;
- les positions et écarts ;
- la perte derrière une voiture lente ;
- les probabilités de dépassement ;
- l’undercut et l’overcut ;
- les arrêts des adversaires ;
- les doubles arrêts ;
- les files dans les stands ;
- la safety car ;
- les objectifs de championnat.

Une stratégie minimisant le temps absolu peut donc être inférieure en situation de course.

La progression expérimentale recommandée est :

| Niveau | Objectif |
|---|---|
| 1 | temps total d’une voiture isolée |
| 2 | temps sous météo incertaine |
| 3 | temps avec trafic simplifié |
| 4 | position finale attendue |
| 5 | résultat pondéré par risque |
| 6 | objectifs d’équipe ou de championnat |

## 12. Interface avec les autres couches

La stratégie ne commande jamais directement le véhicule.

    Stratégie
        │ rythme, pneus, arrêt, risque
        ▼
    Tactique
        │ intention locale
        ▼
    Planification
        │ trajectoire et vitesse
        ▼
    Contrôle
        │ commandes du conducteur
        ▼
    Physique
        │ usure, carburant, temps réel
        └────────────────────────► Stratégie

La stratégie peut émettre :

- rythme cible ;
- niveau de préservation ;
- objectif énergétique ;
- intention de rentrer ;
- fenêtre d’arrêt ;
- priorité attaque ou défense ;
- composé prévu ;
- niveau de risque accepté.

La tactique décide comment appliquer ces objectifs dans le trafic.

## 13. Profils de stratèges

Des comportements distincts peuvent être obtenus en variant :

- aversion au risque ;
- confiance dans les prévisions ;
- marge de carburant ;
- préférence pour les relais longs ;
- valeur accordée à l’air libre ;
- propension à anticiper un arrêt ;
- budget de recherche ;
- nombre de scénarios envisagés ;
- fréquence de replanification ;
- objectif victoire, podium ou points.

La compétence doit aussi dépendre de la qualité des informations et prédictions. Un stratège moins compétent ne doit pas simplement choisir volontairement une mauvaise solution parmi des plans parfaitement évalués.

## 14. Premier prototype Automation LAP

Le premier vertical slice stratégique peut rester borné :

1. une voiture isolée ;
2. course sèche ;
3. deux ou trois composés ;
4. perte de performance déterministe ;
5. consommation de carburant ;
6. temps d’arrêt fixe ;
7. plans représentés par stints ;
8. comparaison entre recherche exhaustive et évolution.

Mesures requises :

- meilleure stratégie trouvée ;
- écart à l’optimum exhaustif ;
- temps de calcul ;
- variabilité entre graines ;
- vitesse de convergence ;
- proportion de plans invalides ;
- sensibilité aux erreurs du modèle ;
- stabilité du résultat après modification mineure des paramètres.

La recherche évolutionnaire ne sera retenue pour la production que si elle apporte un bénéfice mesurable face à des méthodes plus simples.

## 15. Reproductibilité

Le dépôt utilise SystemRandom, ce qui ne fournit pas la reproductibilité nécessaire aux tests d’Automation LAP.

Notre expérimentation doit imposer :

- une graine explicite ;
- un générateur pseudo-aléatoire injecté ;
- une configuration versionnée ;
- des scénarios fixes ;
- l’enregistrement des populations et résultats ;
- la capacité de rejouer exactement une optimisation.

Les résultats devront être comparés sur plusieurs graines connues.

## 16. Maturité de l’implémentation

Points favorables :

- implémentation officielle de l’article ;
- Python 3.11 ;
- peu de dépendances ;
- données et circuits fournis ;
- visualisation de la convergence ;
- modèle construit depuis des essais ;
- sortie lisible.

Risques :

- architecture fortement couplée à la Formule 1 ;
- valeurs codées en dur ;
- stratégie redondante tour par tour ;
- logique, fichiers, interaction et visualisation mêlés ;
- absence apparente de tests automatisés et de CI ;
- état global dans certaines recherches ;
- reproductibilité insuffisante ;
- recherche locale inefficace ;
- météo omnisciente ;
- aucune simulation multi-voiture ;
- dernière activité observée en août 2023.

Le dépôt doit être traité comme code de recherche.

## 17. Licence

Le fichier LICENSE contient successivement le texte de la GPL-3.0 et celui de la BSD-3-Clause, sans préciser clairement leur articulation. GitHub identifie le dépôt comme GPL-3.0.

Aucun code ne doit être copié, lié ou distribué avec Automation LAP sans clarification juridique.

L’usage retenu est limité à :

- étude des concepts ;
- reproduction externe ;
- comparaison expérimentale ;
- implémentation native de contrats et algorithmes ;
- citation de l’article.

## 18. Évaluation selon la grille commune

| Axe | Évaluation |
|---|---|
| pertinence stratégique | forte |
| plans interprétables | forte |
| optimisation hors ligne | forte |
| modèle pneus/carburant | utile mais simplifié |
| gestion de la météo | présente mais omnisciente |
| gestion du trafic | absente |
| multi-agent | absent |
| replanification en ligne | absente |
| diversité des stratèges | potentiel fort |
| reproductibilité | faible en l’état |
| intégration directe | déconseillée |
| potentiel expérimental | très fort |
| scalabilité à 12–20 voitures | à démontrer |
| maturité de production | faible |

## 19. Conditions de réussite

L’expérience est considérée concluante si :

1. les cas réduits sont vérifiables par recherche exhaustive ;
2. l’évolution retrouve régulièrement des solutions proches de l’optimum ;
3. le temps de calcul reste compatible avec la planification hors ligne ;
4. les résultats sont reproductibles ;
5. la représentation par stints réduit fortement les plans invalides ;
6. le modèle de résultat est indépendant de la recherche ;
7. l’introduction de scénarios incertains produit des compromis explicables ;
8. le plan peut être transmis aux couches tactiques sans couplage direct.

## 20. Décisions de conception enregistrées

Cette étude permet de retenir provisoirement :

1. employer l’évolution pour les plans stratégiques discrets plutôt que les commandes directes ;
2. représenter les stratégies par stints et fenêtres ;
3. séparer le modèle de résultat de l’algorithme de recherche ;
4. comparer l’évolution à une recherche exhaustive sur les petits cas ;
5. commencer par une voiture isolée et une course sèche ;
6. ajouter ensuite météo incertaine, replanification et trafic ;
7. interdire l’accès normal à la météo future autoritative ;
8. évaluer résultat moyen, risque et position plutôt que le seul temps ;
9. rendre la recherche entièrement reproductible ;
10. ne pas reprendre directement le code sous licence ambiguë.

Ces principes restent révisables jusqu’à la synthèse finale et à leur éventuelle formalisation dans un ADR.

## 21. Conclusion figée

**Evolutionary F1 Race Strategy est retenu comme premier candidat dédié à la couche stratégique.**

Il fournit un squelette convaincant pour rechercher des plans de course explicables à partir d’un simulateur rapide. Son usage confirme que l’apprentissage évolutionnaire est mieux adapté à l’exploration de plans qu’à la commande directe du véhicule.

Automation LAP devra cependant remplacer la représentation tour par tour par des stints, isoler le modèle de résultat, introduire l’incertitude et la replanification, puis étendre l’objectif du temps absolu vers la position et le risque.

Aucune dépendance de production ni reprise de code n’est adoptée à ce stade.


## 22. Validation par le papier scientifique

Le papier complet associé au dépôt a été analysé séparément. Il confirme le fonctionnement général décrit ci-dessus et précise la portée réelle des résultats.

### 22.1 Protocole publié

Les expériences utilisent :

| Paramètre | Valeur |
|---|---:|
| population | 250 |
| générations | 1 000 |
| probabilité de mutation | 0,9 |
| probabilité de crossover | 0,6 |
| répétitions | 30 par circuit et condition |

Les hyperparamètres ont été choisis empiriquement. Le papier ne fournit ni recherche systématique des hyperparamètres ni ablation complète des opérateurs.

Le taux de mutation élevé et le crossover limité au carburant confirment que la méthode repose surtout sur une exploration mutative avec élitisme et réinjection aléatoire.

### 22.2 Résultats simulés en conditions sèches

Le meilleur résultat parmi 30 exécutions est généralement proche de la baseline publiée :

| Circuit | Écart du meilleur GA à la baseline |
|---|---:|
| Bahreïn | -0,003 s |
| Montréal | -4,479 s |
| Monza | +0,060 s |
| Portimão | +0,357 s |
| Spielberg | +0,220 s |
| Zandvoort | -0,184 s |

Ces résultats montrent que certaines campagnes trouvent de très bons plans. Ils ne prouvent pas une convergence fiable à chaque exécution.

Les moyennes sont sensiblement moins bonnes et les écarts-types publiés vont approximativement de 1 min 16 s à 2 min 28 s. L’évaluation d’Automation LAP devra donc privilégier médiane, percentiles, taux de succès et dispersion entre graines, plutôt que le seul meilleur résultat.

### 22.3 Baseline réduite

La baseline décrite comme brute-force est explicitement réduite :

- deux arrêts au maximum ;
- certains choix pneumatiques imposés selon la météo ;
- espace de recherche volontairement restreint.

Le GA peut la dépasser en trouvant une stratégie à trois arrêts que la baseline n’autorise pas. Cela ne signifie pas qu’il dépasse un optimum exhaustif.

La décision de comparer notre prototype à une véritable recherche exhaustive sur des cas courts est donc confirmée et renforcée.

### 22.4 Conditions météorologiques

Le scénario mixte alterne pluie, sec, pluie puis sec. Il sert à stresser le solveur, mais son déroulement complet est fourni tour par tour à l’algorithme.

Le papier démontre l’adaptation à un scénario complexe connu, pas la robustesse face à une météo incertaine.

La météo autoritative ne devra être accessible qu’aux oracles de test. Le stratège exploité en course recevra une prévision, une confiance et plusieurs scénarios possibles.

### 22.5 Comparaison avec Pirelli

Les données communiquées par Pirelli comprennent principalement :

- le delta de performance des composés ;
- une dégradation linéaire ;
- une durée maximale par pneu et circuit.

Ces paramètres restent confidentiels. Les résultats ne sont donc pas entièrement reproductibles.

Faute de données réelles de carburant, les auteurs utilisent des hypothèses simplifiées. Les stratégies sont comparées aux propositions publiques de Pirelli dans la fonction de temps du papier, pas dans une course réelle.

Le résultat probant est que le GA retrouve fréquemment :

- les mêmes structures à un ou deux arrêts ;
- les mêmes associations de composés ;
- des fenêtres d’arrêt proches.

Il n’est pas démontré que les quelques gains numériques auraient produit un meilleur résultat réel.

### 22.6 Risques pneumatiques et inventaire

Le papier reconnaît que certains plans numériquement rapides sont peu crédibles :

- deux trains durs neufs peuvent ne pas être disponibles ;
- certains relais atteignent la durée maximale théorique ;
- un plan peut exposer à un risque de crevaison.

La contrainte d’inventaire des pneus, bien que discutée, n’est pas implémentée.

Automation LAP doit donc représenter explicitement chaque train disponible :

~~~csharp
public sealed record TyreInventory(
    IReadOnlyDictionary<TyreSpecification, IReadOnlyList<TyreSet>> Sets);
~~~

La faisabilité doit inclure stock, état, allocation et risque, pas seulement composé et âge.

### 22.7 Pénalité dynamique

Le papier compare la pénalité dynamique à un classement sans pénalité sur quatre circuits et dix exécutions. La moyenne publiée est meilleure avec la pénalité.

Cette expérience soutient le maintien temporaire de solutions proches de la faisabilité, mais elle reste limitée :

- peu de campagnes ;
- quatre circuits ;
- absence de test statistique ;
- absence de comparaison avec des opérateurs de réparation.

Pour Automation LAP, les contraintes seront séparées en :

1. contraintes inviolables ;
2. contraintes réparables pendant la recherche ;
3. marges de sécurité ;
4. objectifs optimisables.

### 22.8 Temps de calcul

Les auteurs indiquent que le meilleur minimum est atteint en moins d’une minute sur les données simulées et autour de cinq secondes sur le modèle Pirelli simplifié, avec une implémentation monothread.

Le papier propose comme suites :

- parallélisation ;
- populations multiples ;
- migrations ;
- génotype plus compact ;
- relance du solveur en course lorsque les hypothèses changent.

Ces résultats rendent la planification hors ligne crédible. Ils ne suffisent pas encore à garantir la replanification d’un peloton de 12 à 20 voitures.

## 23. Ajustements de conception issus du papier

L’analyse du papier ajoute les exigences suivantes :

1. produire un portefeuille de stratégies plutôt qu’un optimum unique ;
2. regrouper les solutions proches sous forme de fenêtres d’arrêt ;
3. représenter l’inventaire réel des pneus ;
4. séparer performance nominale et risque de défaillance ;
5. mesurer la fiabilité sur plusieurs graines ;
6. ne pas présenter la baseline réduite comme un optimum ;
7. traiter la météo connue comme un oracle de test ;
8. déclencher la replanification lorsque les observations invalident les hypothèses ;
9. comparer les résultats dans la physique et le trafic réels d’Automation LAP ;
10. conserver explicitement les hypothèses ayant produit chaque plan.

Un portefeuille candidat pourrait être représenté par :

~~~csharp
public sealed record StrategyPortfolio(
    RaceStrategyPlan Primary,
    IReadOnlyList<RaceStrategyPlan> Alternatives);
~~~

Les alternatives couvriront au minimum nombre d’arrêts, météo, niveau de dégradation et niveau de risque.

## 24. Verdict consolidé

Le papier confirme le maintien de AI-CANDIDATE-004 avec le statut **retenu pour expérimentation stratégique hors ligne**.

Le niveau de preuve est toutefois borné :

| Question | Conclusion |
|---|---|
| produit des plans plausibles | oui |
| retrouve des structures proches de Pirelli | oui |
| paraît rapide sur un modèle agrégé | oui |
| bat un optimum exhaustif | non démontré |
| gère une météo réellement incertaine | non |
| optimise la position face au trafic | non |
| fournit des données réelles reproductibles | non |
| justifie une expérimentation Automation LAP | oui |
| justifie une intégration directe | non |

La conclusion centrale est conservée :

> La qualité stratégique dépend d’abord du modèle de résultat, des contraintes et des scénarios. L’algorithme génétique n’est que le moteur de recherche de plans construits sur ces hypothèses.
