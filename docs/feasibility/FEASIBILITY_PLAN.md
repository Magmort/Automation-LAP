# Plan d’étude de faisabilité

- **Statut :** validé — phase active
- **Version :** 0.3
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

## Principe de conception des circuits

Le modèle de circuit interne doit être défini à partir des besoins de la simulation et non à partir du format d’un éditeur tiers.

L’expérience C définit donc un `TrackDefinition` minimal, indépendant de Unity et de toute source externe, puis le valide à l’aide d’une piste canonique créée directement dans ce format.

L’expérience G teste ensuite si les fichiers produits par le Track Editor d’Ultimate Racing 2D 2 permettent de reconstruire ce même contrat. Un échec de G ne remet pas en cause le contrôleur validé par C ; il remet uniquement en cause UR2D2 comme chaîne de création de circuits.

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

## Expérience C — Tour autonome et modèle minimal de circuit

- **Ticket :** #5
- **État :** bloquée par B
- **Dépendance produite :** contrat d’entrée de G

### Question

Une IA de conduite peut-elle suivre une trajectoire, adapter sa vitesse et récupérer une perturbation à partir d’un modèle de circuit minimal indépendant de tout format tiers, sans script par virage ?

### Données de circuit candidates

Le contrat exact doit être réduit et confirmé par l’usage. Le candidat initial comprend :

- identifiant et version du schéma ;
- conventions de coordonnées, origine, orientation et unités SI ;
- boucle centrale fermée ou succession ordonnée de segments ;
- sens de circulation ;
- distance curviligne cumulée ;
- tangente, normale et courbure calculables ;
- limite ou largeur disponible à gauche et à droite ;
- ligne de départ et d’arrivée ;
- checkpoints ordonnés ;
- surface roulable principale et adhérence minimale ;
- trajectoire de référence facultative ;
- invariants de fermeture, continuité et validation.

Les stands, secteurs multiples, dénivelé, dévers, murs détaillés, terrains décoratifs et variantes de tracé restent hors périmètre sauf nécessité démontrée par le contrôleur.

### Critères de réussite

- le `TrackDefinition` minimal ne dépend ni d’Unity ni d’un éditeur externe ;
- une piste canonique peut être validée et prétraitée automatiquement ;
- plusieurs tours sont effectués sans sortie systématique ;
- l’erreur latérale et la variation des temps sont mesurées ;
- une perturbation modérée peut être récupérée ;
- compétence et marge de risque produisent des comportements différents ;
- les champs strictement nécessaires au contrôleur sont identifiés ;
- le contrat permet de tester ultérieurement un importeur externe.

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

## Expérience G — Import du modèle minimal depuis UR2D2

- **Ticket :** #10
- **Protocole :** [experiments/G-UR2D2-TRACK-IMPORT.md](experiments/G-UR2D2-TRACK-IMPORT.md)
- **État :** bloquée par la définition du contrat en C
- **Caractère :** non bloquante pour E, D et F ; bloquante pour l’adoption d’UR2D2 comme outil de création

### Question

Pouvons-nous reconstruire automatiquement le `TrackDefinition` minimal validé par C à partir des fichiers produits par le Track Editor d’Ultimate Racing 2D 2 ?

### Approche

- constituer des circuits différentiels où une seule famille d’éléments change ;
- identifier les fichiers et structures correspondantes ;
- décoder les données dans `UR2D2RawTrackData` ;
- convertir explicitement les données brutes vers `TrackDefinition` ;
- valider le résultat avec les invariants et le contrôleur issus de C ;
- mesurer les corrections manuelles et pertes d’information.

### Critères de réussite

- au moins un circuit simple est importé sans édition point par point ;
- la boucle, le sens, les limites et le chronométrage satisfont le contrat minimal ou les limitations sont explicites ;
- les transformations de coordonnées et l’échelle sont documentées ;
- l’import est déterministe et versionné ;
- la simulation ne dépend plus des fichiers UR2D2 après conversion ;
- le circuit converti est utilisable par le contrôleur validé en C ;
- les informations non récupérables sont identifiées et quantifiées.

## Ordre et dépendances retenus

```text
A — Extraction Automation
        ↓
B — Dynamique d’une voiture
        ↓
C — Tour autonome + TrackDefinition minimal
        ├──────────────→ G — Import UR2D2
        ↓
E — Replay minimal
        ↓
D — Trafic et dépassement
        ↓
F — Charge et accélération
```

G peut commencer dès que C a suffisamment stabilisé le contrat de circuit. Elle peut être menée en parallèle d’E, D ou F.

G ne bloque pas la validation du contrôleur, du replay, du trafic ou des performances. Elle doit toutefois être conclue avant de considérer UR2D2 comme la chaîne officielle de création de circuits du vertical slice.

## Livrable final

L’étude se termine par un rapport synthétique contenant la décision pour chaque expérience, les paramètres retenus, les risques résiduels et les changements requis dans le plan ou l’architecture.

Le document de sortie est [FEASIBILITY_REPORT.md](FEASIBILITY_REPORT.md).