# A7 - Preparation export complet des courbes ciblees

- **Experience :** A - Extraction Automation
- **Statut :** payload corrige pret a compiler et tester dans Automation
- **Date :** 2026-07-26
- **Exporter prepare :** `0.1.12-a7-json-values-fix`

## Diagnostic des exports `0.1.11`

Les trois voitures ont ete reexportees avec `0.1.11-a7-raw-graphs`.

Resultat :

- les quatre fichiers attendus sont produits ;
- les chemins `AccelerationToTopSpeed`, `Braking` et `BrakingVGrip` sont accessibles ;
- les longueurs, min/max et diagnostics de series sont coherents ;
- aucune serie n'est tronquee ;
- le validateur A7 echoue car le champ `values` est absent des series.

Cause : l'encodeur JSON Lua excluait toute cle nommee `values`, alors que cette exclusion ne devait concerner que le wrapper interne des tableaux JSON. La version `0.1.12-a7-json-values-fix` corrige ce point.

## Objectif

Exporter les courbes deja calculees par Automation sans les recalculer dans le projet.

A7 reste volontairement ciblee. Le but est de transformer les graphes les plus utiles identifies en A6 en donnees directement exploitables, sans figer encore le futur modele physique.

## Fichier ajoute

```text
automation-lap-raw-graphs.json
```

Le fichier contient :

- version de schema ;
- version d'exporteur ;
- horodatage UTC injecte cote C++ ;
- chemin racine `CarInfo.TrimInfo.Results.GraphData` ;
- liste des graphes selectionnes ;
- limite de securite par serie ;
- series numeriques completes des graphes selectionnes ;
- nombre de points, min/max, role et unite candidate pour chaque serie ;
- diagnostics agreges.

## Graphes selectionnes

```text
AccelerationToTopSpeed
Braking
BrakingVGrip
```

Ce choix couvre :

- acceleration, vitesse, temps, distance, rapports, regime, puissance et couple ;
- freinage global ;
- decomposition freinage/grip avant/arriere.

## Contrat des series

Chaque serie exportee contient :

- `key` : nom Automation conserve ;
- `path` : chemin Lua relatif ;
- `role` : `axis-candidate` pour `Speed`, `Time`, `Distance`, sinon `value` ;
- `count` : nombre total de points numeriques ;
- `numericMin` / `numericMax` ;
- `values` : valeurs numeriques exportees ;
- `truncated` : indique si la limite de securite a coupe la serie ;
- `unitSource` : `automation-graph` ;
- `unitInternalCandidate` : `unknown`.

Les unites ne sont pas converties a cette etape. Elles seront confirmees plus tard par comparaison UI/documentation.

## Bornes de securite

- maximum 5000 valeurs par serie ;
- export limite aux series numeriques directes des graphes selectionnes ;
- pas de dump recursif non borne ;
- pas d'appel aux fonctions documentees tant que l'absence de `pcall` n'est pas contournee.

Les exports A6 observes sont tres inferieurs a cette limite : entre 98 et 273 points sur les courbes principales.

## Validateur

Le validateur independant est :

```text
prototypes/automation-exporter/tools/validate_raw_graphs.py
```

Commande :

```powershell
python prototypes\automation-exporter\tools\validate_raw_graphs.py `
  "C:\chemin\vers\automation-lap-raw-graphs.json"
```

## Donnees attendues apres export reel

Exporter a nouveau les trois voitures contrastes avec la DLL `0.1.12-a7-json-values-fix`, puis fournir pour chaque voiture :

- `automation-lap-vehicle.json` ;
- `automation-lap-field-inventory.json` ;
- `automation-lap-graph-inventory.json` ;
- `automation-lap-raw-graphs.json`.

## Criteres de sortie

- les quatre fichiers sont produits pour chaque voiture ;
- les quatre validateurs passent ;
- les graphes selectionnes sont presents ;
- aucune serie n'est tronquee ;
- les longueurs de series sont coherentes dans chaque graphe ;
- les unites inconnues restent explicitement marquees.
