# Plan d’étude de faisabilité

- **Statut :** validé — phase active
- **Version :** 0.2
- **Début :** 25 juillet 2026
- **Ticket directeur :** #2
- **Tableau de bord :** [PHASE_1_STATUS.md](PHASE_1_STATUS.md)
- **Rapport consolidé :** [FEASIBILITY_REPORT.md](FEASIBILITY_REPORT.md)
- **Objectif :** réduire les risques avant la création du code de production

Les prototypes décrits ici sont jetables. Ils doivent répondre à une question précise, produire des mesures et éviter de transformer prématurément une hypothèse en architecture définitive.

## Format commun d’une expérience

Chaque expérience doit documenter :

- l’hypothèse testée ;
- les données et outils utilisés ;
- le protocole reproductible ;
- les métriques collectées ;
- les critères de réussite et d’échec ;
- les limites connues ;
- la conclusion : `validée`, `validée avec réserves`, `à modifier` ou `non viable`.

Le modèle commun se trouve dans [EXPERIMENT_TEMPLATE.md](EXPERIMENT_TEMPLATE.md).

## Expérience A — Extraction Automation

- **Ticket :** #3
- **Protocole :** [experiments/A-AUTOMATION-EXTRACTION.md](experiments/A-AUTOMATION-EXTRACTION.md)
- **État :** prête à démarrer

### Question

Pouvons-nous extraire de manière stable les données nécessaires à trois voitures très différentes ?

### Données minimales

- identité et version de la source ;
- dimensions, masse et répartition ;
- moteur et courbe de couple ;
- transmission et rapports ;
- pneus et freins ;
- aérodynamique ;
- suspension ;
- carburant ;
- résultats de performance disponibles.

### Critères de réussite

- trois voitures sont exportées vers un format structuré ;
- les unités et champs sont documentés ;
- les valeurs manquantes sont détectées ;
- un même export produit des données équivalentes ;
- la version d’Automation et celle de l’exporteur sont enregistrées.

## Expérience B — Dynamique d’une voiture

- **Ticket :** #4
- **État :** bloquée par A

### Question

Un modèle 2D simple peut-il reproduire des différences plausibles d’accélération, freinage, vitesse maximale et virage ?

### Scénarios

- accélération en ligne droite ;
- freinage depuis plusieurs vitesses ;
- virage à rayon constant ;
- changement d’appui ;
- tour simple sans trafic.

### Critères de réussite

- aucune instabilité numérique dans la plage normale ;
- les résultats évoluent dans le bon sens lorsque masse, puissance, pneus ou aérodynamique changent ;
- les paramètres peuvent être calibrés sans règles spécifiques à une voiture.

## Expérience C — Tour autonome

- **Ticket :** #5
- **État :** bloquée par B

### Question

Une IA de conduite peut-elle suivre une trajectoire et adapter sa vitesse sans script par virage ?

### Critères de réussite

- plusieurs tours consécutifs sans sortie systématique ;
- erreur latérale et variation des temps mesurées ;
- reprise après une perturbation modérée ;
- comportement différent selon compétence et marge de risque.

## Expérience D — Trafic et dépassement

- **Ticket :** #6
- **État :** bloquée par C et E

### Question

Plusieurs voitures peuvent-elles partager la piste et produire des dépassements sans collisions constantes ni immobilisme ?

### Scénarios

- voiture plus rapide derrière une voiture lente ;
- deux voitures côte à côte ;
- freinage en trafic ;
- défense ;
- réinsertion après une erreur.

### Critères de réussite

- détection robuste des voisins ;
- anticipation à court terme ;
- changement de ligne progressif ;
- taux de contact mesurable et réglable ;
- absence de blocage collectif récurrent.

## Expérience E — Replay

- **Ticket :** #7
- **État :** bloquée par B, à mener avant D

### Question

Une course enregistrée peut-elle être chargée, parcourue dans les deux sens et affichée sans recalculer toutes les décisions ?

### Critères de réussite

- chargement d’un fichier autonome ;
- lecture à plusieurs vitesses ;
- navigation vers un instant arbitraire ;
- saut vers un événement ;
- suivi cohérent d’une voiture ;
- détection des versions incompatibles ;
- taille du fichier mesurée pour plusieurs durées et fréquences.

## Expérience F — Charge et accélération

- **Ticket :** #8
- **État :** bloquée par la boucle représentative B à E

### Question

Le modèle envisagé permet-il de simuler le nombre cible de voitures en temps réel et plus vite que le temps réel sans rendu ?

### Scénarios

- 1, 12, 20 et 40 voitures ;
- rendu actif et rendu désactivé ;
- télémétrie minimale et détaillée ;
- plusieurs vitesses de simulation.

### Mesures

- durée CPU par système ;
- allocations mémoire ;
- mémoire totale ;
- vitesse de simulation atteinte ;
- taille et débit d’écriture du replay.

### Critères de réussite initiaux

- le scénario cible de douze à vingt voitures fonctionne en temps réel sur la machine de référence ;
- le mode sans rendu dépasse significativement le temps réel ;
- les goulets d’étranglement sont identifiés par mesure.

## Ordre retenu

1. A — Extraction Automation ;
2. B — Dynamique d’une voiture ;
3. C — Tour autonome ;
4. E — Replay minimal, introduit tôt ;
5. D — Trafic et dépassement ;
6. F — Charge et accélération.

## Livrable final

L’étude se termine par un rapport synthétique contenant la décision pour chaque expérience, les paramètres retenus, les risques résiduels et les changements requis dans le plan ou l’architecture.

Le document de sortie est [FEASIBILITY_REPORT.md](FEASIBILITY_REPORT.md).
