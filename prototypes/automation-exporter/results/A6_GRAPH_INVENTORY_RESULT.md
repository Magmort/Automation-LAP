# A6 - Resultat inventaire GraphData

- **Experience :** A - Extraction Automation
- **Statut :** validee
- **Date :** 2026-07-26
- **Exports analyses :** `C:\Users\jerem\Documents\Automation LAP Smoke Test`
- **Version exportee :** `0.1.9-a6-graph-inventory`
- **Version source apres analyse :** `0.1.10-a6-graph-axis-hints`

## Synthese

Les trois voitures exportees produisent les trois fichiers attendus :

- `automation-lap-vehicle.json`
- `automation-lap-field-inventory.json`
- `automation-lap-graph-inventory.json`

Les inventaires GraphData sont valides, sans diagnostic, et exposent tous les memes 10 graphes racine :

```text
AccelerationToTopSpeed
Braking
BrakingVGrip
BumpGraph
Downforce
Drag
GearboxGraph
GearingEff
HighSpeedSteering
LowSpeedSteering
```

## Validation

| Voiture | GraphData present | Graphes racine | Noeuds inventories | Series numeriques | Diagnostics |
| --- | ---: | ---: | ---: | ---: | ---: |
| AIXAM Coupe GTI | oui | 10 | 102 | 73 | 0 |
| PCM - Magmort Carcharhini Recif | oui | 10 | 105 | 77 | 0 |
| QFC55 - Magmort Carcharhini RCZ | oui | 10 | 111 | 83 | 0 |

Les differences de nombre de noeuds et de series sont attendues : elles dependent notamment du nombre de rapports, de la vitesse maximale et de la forme des courbes calculees.

## BrakingVGrip

`BrakingVGrip` contient bien les 4 courbes identifiees, plus une courbe `Speed` exploitable comme axe probable.

| Voiture | Points | Speed min | Speed max | FrontBrakeForce | RearBrakeForce |
| --- | ---: | ---: | ---: | ---: | ---: |
| AIXAM Coupe GTI | 98 | 0.409 | 113.685 | 2939.046 | 950.064 |
| PCM - Magmort Carcharhini Recif | 159 | 1.207 | 220.560 | 4030.895 | 1345.350 |
| QFC55 - Magmort Carcharhini RCZ | 184 | 0.033 | 284.945 | 5946.793 | 1917.058 |

Observations :

- `FrontBrakeForce` et `RearBrakeForce` sont constantes sur chaque voiture.
- `FrontBrakeGrip` et `RearBrakeGrip` varient avec `Speed`.
- Les valeurs de `Speed` correspondent a un axe descendant depuis la vitesse de freinage vers 0.
- L'unite de `Speed` reste a confirmer, mais l'ordre de grandeur correspond tres probablement a des km/h.
- L'unite des forces et grips reste a confirmer avant conversion en SI.

## Courbes directement interessantes

`AccelerationToTopSpeed` est tres riche et probablement prioritaire pour la suite. Il contient notamment :

- `Speed`
- `Time`
- `Distance`
- `AccelG`
- `EngineTorque`
- `enginePower`
- `engineRPM`
- `gear`
- `WeightDistribution`
- `FrontGripG` / `RearGripG`
- resistances aero/roulement et downforce

`Braking` contient au minimum :

- `Speed`
- `Time`

`BrakingVGrip` fournit la decomposition force/grip avant/arriere pendant le freinage.

Les autres graphes racine (`Drag`, `Downforce`, `GearboxGraph`, `GearingEff`, `BumpGraph`, `HighSpeedSteering`, `LowSpeedSteering`) sont presents mais doivent etre inspectes avec un export complet des courbes avant interpretation.

## Corrections source decidees

Deux ajustements ont ete appliques apres lecture des exports :

- `mass.frontDistribution` reste sonde via `CarInfo.TrimInfo.Results.cg.WeightDistribution`, mais son unite source est maintenant `percent`, avec conversion interne cible `fraction`.
- `CarInfo.TrimInfo.Results.GraphData.BrakingVGrip.Speed` est ajoute a l'inventaire controle comme axe de courbe explicite.

Ces ajustements donnent la version source `0.1.10-a6-graph-axis-hints`. Ils ne remettent pas en cause les exports A6 `0.1.9`, car `Speed` etait deja visible dans `automation-lap-graph-inventory.json`.

## Decision A6

A6 est validee.

Le prototype prouve que `CarInfo.TrimInfo.Results.GraphData` est accessible, structure, et exploitable sur trois voitures contrastees. L'inventaire borne suffit a choisir les prochaines courbes a exporter completement.

## Prochaine etape proposee

Passer a A7 : export complet mais selectionne des courbes GraphData.

Je propose de commencer par un payload `automation-lap-raw-graphs.json` contenant :

- `AccelerationToTopSpeed`
- `Braking`
- `BrakingVGrip`

avec toutes leurs series numeriques, leurs longueurs, leurs min/max, et une preservation stricte des noms Automation. Les unites resteraient marquees `unknown` quand elles ne sont pas confirmees, afin de ne pas polluer la future simulation avec de fausses conversions.
