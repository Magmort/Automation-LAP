# A4 — Export des trois voitures

- **Expérience :** A — Extraction Automation
- **Statut :** validée avec réserves
- **Date :** 2026-07-26
- **Exporter observé :** `0.1.4-a3-final-drive`
- **Exporter préparé après confirmation interface :** `0.1.8-a4-braking-vgrip-curves`
- **Dossier analysé :** `C:\Users\jerem\Documents\Automation LAP Smoke Test`

## Synthèse

Les trois dossiers d'export attendus sont présents et contiennent chacun :

- `automation-lap-vehicle.json` ;
- `automation-lap-field-inventory.json` ;
- `License.txt`.

Les six JSON passent les validateurs indépendants du prototype. Le seul avertissement sur les fichiers `vehicle` reste l'avertissement attendu : la version Automation n'est pas exposée par les données Lua.

Les trois inventaires couvrent toutes les sondes A3 : `67 / 67` champs observés pour chaque voiture.

Jeremy a confirmé les valeurs dans l'interface Automation sur l'AIXAM Coupe GTI. Cette vérification est considérée suffisante pour A4, car les chemins et unités sont communs aux autres voitures ; les deux autres exports servent surtout à confirmer le contraste des valeurs et la couverture complète des familles.

## Voitures exportées

| Dossier | Modèle | Trim | Horodatage UTC |
|---|---|---|---|
| `AIXAM Coupe GTI` | `AIXAM` | `Coupe GTI` | `2026-07-26T14:10:17Z` |
| `PCM - Magmort Carcharhini Recif` | `PCM - Magmort` | `Carcharhini Recif` | `2026-07-26T14:11:45Z` |
| `QFC55 - Magmort Carcharhini RCZ` | `QFC55 - Magmort` | `Carcharhini RCZ` | `2026-07-26T13:50:06Z` |

## Validation

| Voiture | `vehicle` | `field-inventory` |
|---|---|---|
| AIXAM Coupe GTI | Réussi, avec avertissement attendu `automation_version_not_exposed` | Réussi |
| PCM - Magmort Carcharhini Recif | Réussi, avec avertissement attendu `automation_version_not_exposed` | Réussi |
| QFC55 - Magmort Carcharhini RCZ | Réussi, avec avertissement attendu `automation_version_not_exposed` | Réussi |

## Empreintes

| Voiture | SHA-256 `vehicle` | SHA-256 `field-inventory` |
|---|---|---|
| AIXAM Coupe GTI | `A889AB7A66A95E9D014E1631530AA772B87F377A234BF02504C6A6FF7C987E2A` | `AB613B21A1598422FD996DE90FBC484F46A4B97FCE28531BF4839399C0501D98` |
| PCM - Magmort Carcharhini Recif | `F9476A5C36783E85450F8051A50F638C4EAF255F70E97FA6DD47343C66754CFD` | `0F426170C37B2B1C38C14E709D5AAD1F8442370E417CE4F8342A9A73C51890FE` |
| QFC55 - Magmort Carcharhini RCZ | `F55D3F8A46218B1FD4F23CE6207C64DFEFB63A03257D39E2B160B52D3358A419` | `5DEE1F31A41754028BAEFD7F6D9846D07E65ACDE1C3EFC206FB880E16FB65B16` |

## Couverture

Chaque voiture présente la même couverture :

| Famille | Présents / sondés |
|---|---:|
| identity | 4 / 4 |
| geometry | 10 / 10 |
| mass | 2 / 2 |
| chassis | 4 / 4 |
| engine | 5 / 5 |
| transmission | 5 / 5 |
| wheels | 7 / 7 |
| brakes | 6 / 6 |
| aerodynamics | 5 / 5 |
| suspension | 16 / 16 |
| performance | 3 / 3 |
| total | 67 / 67 |

## Contrastes observés

| Champ | AIXAM Coupe GTI | PCM Recif | QFC55 RCZ |
|---|---:|---:|---:|
| Masse | `858.39514197568` | `1093.2347318742` | `1278.5554914336` |
| Répartition avant | `0.5` | `0.25` | `0.64999997615814` |
| Cylindrée brute | `0.47479315091095` | `4.8001911865591` | `2.3674131148532` |
| Limite régime | `6000` | `6000` | `7700` |
| Motricité | `DriveType_FTransFWD_Name` | `DriveType_FLongRWD_Name` | `DriveType_FTransAWD_Helical_Name` |
| Boîte | `GearboxType_CVT_Name` | `GearboxType_Manual_Name` | `GearboxType_Manual_Name` |
| Rapport final | `5.6713345530635` | `4.6622336184189` | `4.6945730476373` |
| Pneu avant | `165` | `205` | `215` |
| Pneu arrière | `165` | `225` | `215` |
| Vitesse max brute | `115.17921700986` | `223.00794746926` | `287.79457951094` |
| 0-100 | `51.054999999999` | `5.7249999999999` | `5.4049999999999` |
| Freinage | `49.181076168893` | `42.560204522093` | `37.814283126889` |

Les trois voitures forment un jeu de test utile :

- AIXAM Coupe GTI : légère, traction, CVT, pneus étroits, accélération très faible ;
- PCM Recif : propulsion, gros moteur, pneus arrière plus larges, voiture de performance plus ancienne ;
- QFC55 RCZ : plus lourde, AWD, régime plus élevé, freine plus court, undertray différent.

## Points de vigilance sur les unités

Les chemins sont disponibles. La documentation officielle `CarCalculator` confirme que le `CarCalculator` reçu par `DoExport` expose des tables imbriquées dont `CarInfo.PlatformInfo`, `CarInfo.TrimInfo`, `TrimInfo.Results`, `TrimInfo.EngineInfo`, `TrimInfo.Gearbox` et `EngineCalculator`.

Unités confirmées par la documentation officielle consultée :

| Champ exporté | Chemin observé | Unité source confirmée | Unité interne cible |
|---|---|---|---|
| `mass.total` | `CarInfo.TrimInfo.Results.Weight` | `kg` | `kg` |
| `engine.capacity` | `*.EngineInfo.*.Capacity` | `L`, d'après `TrimInfo.Results.Capacity` | `m3` |
| `performance.topSpeed` | `CarInfo.TrimInfo.Results.TopSpeed` | `km/h` | `m/s` |
| `performance.acceleration0To100` | `CarInfo.TrimInfo.Results.HundredTime` | `s` | `s` |
| `performance.brakingDistance` | `CarInfo.TrimInfo.Results.BrakingDistance` | `m` | `m` |
| `suspension.frontSpringStiffness` / `rearSpringStiffness` | `CarInfo.TrimInfo.SuspensionDetails.*.SpringStiffness` | `N/m` | `N/m` |
| `suspension.frontDamperStiffness` / `rearDamperStiffness` | `CarInfo.TrimInfo.SuspensionDetails.*.DamperStiffness` | `Ns/m` | `N*s/m` |
| `suspension.frontSwayBarStiffness` / `rearSwayBarStiffness` | `CarInfo.TrimInfo.SuspensionDetails.*.ARBStiffness` | `Nm/rad` | `N*m/rad` |
| `suspension.rideHeight` | `CarInfo.TrimInfo.SuspensionDetails.RideHeight` | `cm` | `m` |
| `suspension.frontCamber` / `rearCamber` | `CarInfo.TrimInfo.SuspensionDetails.*.Camber` | `degrees` | `rad` |

Corrections préparées dans le payload Lua `0.1.8-a4-braking-vgrip-curves` :

- `performance.topSpeed` passe de source `unknown` à `km/h`, cible `m/s` ;
- `engine.capacity` passe de source `unknown` à `L`, cible `m3` ;
- `mass.total` passe de source `unknown` à `kg` ;
- raideurs, amortissement, barres antiroulis, hauteur de caisse et carrossage utilisent les unités documentées ;
- `geometry.wheelBase` passe à `cm` après confirmation interface ;
- `geometry.frontalArea` passe à `m2` après confirmation interface ;
- pneus et diamètres de roues passent à `mm` ou `inch` selon l'affichage confirmé ;
- `brakes.*BrakeForce` est une valeur de réglage en `%`, pas une force en newtons ;
- quatre courbes `BrakingVGrip` sont ajoutées depuis `CarInfo.TrimInfo.Results.GraphData.BrakingVGrip` comme courbes brutes à investiguer : `FrontBrakeForce`, `FrontBrakeGrip`, `RearBrakeForce`, `RearBrakeGrip` ;
- `brakes.*PadSize`, `aerodynamics.coolingAirflow*` et `aerodynamics.brakeCooling*` sont traités comme positions de slider Automation ;
- `mass.frontDistribution` utilise désormais `CarInfo.TrimInfo.Results.cg.WeightDistribution`, la valeur calculée réelle ;
- `mass.weightDistributionSlider` conserve l'ancien chemin `CarInfo.TrimInfo.WeightDistributionFraction`, car cette valeur correspond à un slider et non à une répartition physique réelle ;
- `suspension.frontToe` et `suspension.rearToe` restent en unité `unknown`.

Points encore non exploitables physiquement sans traitement :

- voies avant/arrière : non trouvées dans l'interface, mais exportées ;
- dimensions de carrosserie `bodyDimensions.*` : non trouvées dans l'interface, probablement convertibles depuis cm, mais non confirmées par affichage ;
- `mass.weightDistributionSlider` : disponible comme réglage Automation, à ne pas utiliser comme répartition de masse réelle ;
- courbes `brakes.brakingVGrip.*` : probablement indexées par vitesse, mais l'unité des valeurs, l'axe d'index et la normalisation éventuelle restent à déterminer ;
- `brakes.*PadSize` : position de slider, pas une grandeur physique directe ;
- refroidissement aéro/freins : position de slider, pas une grandeur physique directe ;
- `suspension.frontToe` et `suspension.rearToe` : valeurs visibles, unité non confirmée ;
- `transmission.gearboxRatios` : introuvable sur l'AIXAM CVT, à revisiter sur une voiture manuelle si nécessaire.

Note : la cellule de confirmation AIXAM pour `performance.brakingDistance` indique `mm`, mais la documentation officielle et l'ordre de grandeur de `49.2` confirment une distance en mètres. La cible retenue reste donc `m`.

Conclusion : A4 valide la disponibilité des champs, le contraste des voitures et les unités nécessaires pour ouvrir la suite, avec quelques champs explicitement classés comme sliders ou non exploitables directement.

Sources documentaires consultées :

- `CarCalculator` — structure générale et fonctions utiles : https://wiki.automationgame.com/index.php?title=CarCalculator
- `TrimInfo.Results` — unités des résultats calculés : https://wiki.automationgame.com/index.php?title=TrimInfo.Results
- `CarInfo.TrimInfo` — unités suspension et tables trim : https://wiki.automationgame.com/index.php?title=CarInfo.TrimInfo
- `TrimInfo.Gearbox` — rapport final, transmission et types de boîte : https://wiki.automationgame.com/index.php?title=TrimInfo.Gearbox

## Licence et conservation

Chaque dossier contient une licence indiquant que les données et assets produits par Automation sont sous Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International.

Décision Jeremy, 2026-07-26 : la licence `CC BY-NC-SA 4.0` est compatible avec la portée actuelle du projet, limitée à un usage privé non lucratif.

Conséquence : les exports peuvent servir de base de travail et de fixtures privées pour A4/A5. Si un partage public est envisagé plus tard, il faudra conserver attribution, licence et contraintes `NonCommercial` / `ShareAlike`.

## Tableur de confirmation

Un tableur de validation a été préparé :

```text
outputs/a4-validation/Automation_LAP_A4_validation.xlsx
```

Il contient :

- `Instructions` : procédure de remplissage et décision licence ;
- `Comparaison jeu` : valeurs exportées préremplies, colonnes à compléter avec les valeurs visibles dans Automation ;
- `Unites a confirmer` : liste courte des champs dont l'unité reste observée, inférée ou inconnue ;
- `Sources` : liens documentaires utilisés.

Champs prioritaires dont l'unité reste à confirmer :

- géométrie : année/body si libellé différent, empattement, voies, surface frontale, dimensions de carrosserie ;
- masse : répartition avant, notamment confirmation fraction vs pourcentage affiché ;
- transmission : rapports de boîte si affichables ;
- roues : largeurs, jantes, diamètre total ;
- freins : `BrakeForce` et `PadSize`, documentés seulement comme numériques ;
- aérodynamique : fractions de refroidissement ;
- suspension : toe avant/arrière.

## Confirmation interface AIXAM

Résumé du remplissage AIXAM Coupe GTI :

| Statut | Nombre |
|---|---:|
| OK | 54 |
| Écart acceptable | 1 |
| Introuvable | 7 |
| À investiguer | 3 |
| Total | 65 |

Champs introuvables dans l'interface :

- `geometry.frontTrackWidth` ;
- `geometry.rearTrackWidth` ;
- `geometry.bodyDimensions.x` ;
- `geometry.bodyDimensions.y` ;
- `geometry.bodyDimensions.z` ;
- `engine.fuelType`, non bloquant car l'essence est le seul carburant actuellement disponible ;
- `transmission.gearboxRatios`, non bloquant sur cette voiture équipée d'une CVT.

Champs à investiguer :

- `mass.weightDistributionSlider`, anciennement `mass.frontDistribution` dans les exports `0.1.4`, car la valeur est une position de slider ;
- `aerodynamics.coolingAirflowSlider`, anciennement `aerodynamics.coolingAirflowFraction` ;
- `aerodynamics.brakeCoolingSlider`, anciennement `aerodynamics.brakeCoolingFraction` ;
- courbes `brakes.brakingVGrip.*`, ajoutées après A4 depuis `CarInfo.TrimInfo.Results.GraphData.BrakingVGrip`, car elles pourraient contenir une information de freinage plus exploitable que les réglages en `%`.

Écart acceptable :

- `suspension.dampers` : l'export donne `Dampers_Passive_Name`, l'interface affiche `Twin-Tube`. Cela ressemble à une différence entre catégorie interne et libellé UI, pas à une incohérence bloquante.

## Décision d'étape

A4 est validée avec réserves :

- les trois exports existent ;
- les contrats JSON passent ;
- toutes les familles sont couvertes ;
- les trois voitures sont suffisamment contrastées pour alimenter la suite ;
- les valeurs AIXAM confirment la correspondance générale entre export et affichage en jeu ;
- les unités bloquantes ont été confirmées ou classées explicitement comme sliders/valeurs Automation.

Réserves :

- ne pas utiliser les sliders comme grandeurs physiques sans conversion ou modèle dérivé ;
- utiliser `mass.frontDistribution` pour la répartition calculée et ne pas utiliser `mass.weightDistributionSlider` comme répartition de masse réelle ;
- ne pas interpréter les courbes `brakes.brakingVGrip.*` avant d'avoir confirmé leur axe et leurs unités ;
- revisiter les fonctions documentées lorsque le prototype disposera d'appels protégés côté Lua ou C++ ;
- vérifier les rapports de boîte sur une voiture manuelle si ce champ devient nécessaire à B.

Prochaine étape autorisée :

- ouvrir A5 pour la répétabilité multi-export ;
- en parallèle, commencer la définition `AutomationRawVehicleData` v0.1 en séparant clairement valeurs physiques, choix bruts, résultats calculés et sliders Automation.
