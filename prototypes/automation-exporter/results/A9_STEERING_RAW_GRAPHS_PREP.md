# A9 - Preparation steering raw graphs

- **Experience :** A - Extraction Automation
- **Statut :** exporteur prepare et DLL compilee, attente de nouveaux exports Automation
- **Date :** 2026-07-26
- **Version source :** `0.1.13-a9-steering-raw-graphs`

## Objectif

Ajouter aux graphes bruts les donnees de direction identifiees dans l'export JSON communautaire :

- `CarInfo.TrimInfo.Results.GraphData.LowSpeedSteering`
- `CarInfo.TrimInfo.Results.GraphData.HighSpeedSteering`

Chaque graphe contient les series :

- `Speed`
- `Steering`
- `UnderSteer`
- `OverSteer`

## Changements

- `automation-lap-raw-graphs.json` selectionne maintenant cinq graphes :
  - `AccelerationToTopSpeed`
  - `Braking`
  - `BrakingVGrip`
  - `LowSpeedSteering`
  - `HighSpeedSteering`
- `RAW_GRAPH_VALUE_LIMIT` passe de `5000` a `10000` pour eviter la troncature de `LowSpeedSteering`.
- Le validateur `AutomationRawVehicleData` accepte les graphes A8 historiques et verifie que les graphes de direction A9 sont presents par paire lorsqu'ils apparaissent.

## DLL compilee

- Chemin installe : `E:\SteamLibrary\steamapps\common\Automation\UE427\AutomationGame\Content\ExportPlugins\AutomationLAPA9SteeringRawGraphs.dll`
- Copie de secours : `C:\tmp\AutomationLAP-A9-SteeringRawGraphs.dll`
- SHA-256 : `05452BF90B913F63C56B3867C612AD7E0743148512EC8ED42FEE5791B7AC7F3B`
- Nom affiche dans Automation : `Automation LAP - A9 Steering Raw Graphs`

Note de packaging : la DLL peut etre installee sous un nom different du nom cible de compilation. Le code C++ local du SDK a donc ete corrige pour retrouver la ressource Lua embarquee via le module courant, et non via `GetModuleHandle(PROJECT_FILENAME)`.

## Justification

L'analyse du JSON communautaire de la QFC55 confirme que ces graphes fournissent un axe `Speed` et des series denses `Steering`, `UnderSteer` et `OverSteer`.

Ils ne doivent pas encore etre interpretes comme une adherence laterale brute, mais ils peuvent remplacer le proxy trop faible utilise en B-S04 et permettre une meilleure analyse du comportement de direction.

## Prochaine etape

Les trois voitures ont ete reexportees et validees. Voir `A9_STEERING_RAW_GRAPHS_RESULT.md`.

Commandes de validation utilisees :

```powershell
python prototypes\automation-exporter\tools\validate_raw_graphs.py `
  "C:\chemin\vers\automation-lap-raw-graphs.json"

python prototypes\automation-exporter\tools\build_raw_vehicle_data.py `
  "C:\chemin\vers\un\dossier\voiture"

python prototypes\automation-exporter\tools\validate_raw_vehicle_data.py `
  "C:\chemin\vers\un\dossier\voiture\automation-lap-raw-vehicle-data.json"
```
