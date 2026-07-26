# Résultat — Automation Exporter Smoke Test

- **Expérience :** A — Extraction Automation
- **Ticket :** #3
- **Statut :** préparation CLI terminée, test interface à exécuter
- **Date :** 2026-07-26
- **Opérateur :** Codex + Jeremy

## Environnement

| Élément | Valeur |
|---|---|
| Windows | Windows 10 Home, x64 |
| Automation — version | `180713` d'après `Automation_SDK/AutomationGame/Config/GameVersion.txt` |
| Automation — branche Steam | À confirmer dans Steam / Automation |
| Exporter SDK — commit | `2a35098c6b5e8505b6ebdc01f8b7bede1d11721f` |
| Visual Studio | Visual Studio / Build Tools 2022 `17.14.x` |
| MSVC toolset | MSVC `14.44.35207`, build forcé avec `PlatformToolset=v143` |
| Windows SDK | `10.0.26100.0` |
| Architecture | `x64` |
| Commit Automation LAP | `ad5725448ba616fa115e9ee46b9be0abe2ccd42b` |

## Étape 1 — Exemple officiel

- [x] compilation réussie ;
- [x] DLL installée dans `Content/ExportPlugins` ;
- [ ] exporteur visible ;
- [ ] export terminé ;
- [ ] sortie officielle produite.

### Observations

Compilation propre de l'exemple officiel depuis un worktree détaché du SDK :

- source : `C:\tmp\AutomationLAP-External\ExporterSDK-official-clean`
- sortie : `C:\tmp\AutomationLAP-External\build\official-x64\AutomationExportExampleOfficial.dll`
- résultat MSBuild : 0 avertissement, 0 erreur
- SHA-256 DLL : `60DA7587EF390A32AFEA38200B1C9D647D20D1B94800F05C82C54A2DCCC27C5B`

La DLL officielle n'a pas été installée dans Automation afin de garder l'interface centrée sur la variante Automation LAP.

## Étape 2 — Variante Automation LAP

- [x] payload Lua intégré à la DLL ;
- [x] exporteur identifiable séparément ;
- [x] export terminé ;
- [x] `automation-lap-vehicle.json` produit ;
- [x] sortie UTF-8 valide ;
- [x] validation Python réussie.

### Sortie du validateur

```text
SUCCÈS: l'export respecte le contrat du test de fumée v0.1.0.
AVERTISSEMENT: version d'Automation non exposée par les données Lua
AVERTISSEMENT: horloge UTC indisponible dans l'environnement Lua
```

## Métadonnées observées

| Champ | Valeur | Chemin Lua utilisé |
|---|---|---|
| Nom du modèle | `QFC55 - Magmort` | `CarInfo.PlatformInfo.Name` |
| Nom du trim | `Carcharhini RCZ` | `CarInfo.TrimInfo.Name` |
| Version Automation | `null` | `null` |
| Horodatage UTC | `null` | n/a |

## Diagnostics produits

- `automation_version_not_exposed`
- `utc_clock_not_available`

## Validation UTF-8

| Scénario | Valeur observée | Résultat validation | SHA-256 |
|---|---|---|---|
| Trim accentué | `Stâllöné` | Réussie avec avertissements attendus | `51CAB38A3F993EF5860D581AB397A9054874EF7BED16D96E5FB0DB1033C56CCA` |
| Noms avec caractères spéciaux | Modèle `C1K - GTC - Xepy & chiefzach2018`, trim `Tristella-Zacspeed [Otus GT]-Competizione #1 Clone` | Réussie avec avertissements attendus | `FF45C77DA72E13D10559CABFF20A0CD9B145AA72EAAFBB72960796BFF3E99C46` |

Le JSON est lisible en UTF-8 par Python. L'affichage `StÃ¢llÃ¶nÃ©` observé dans Windows PowerShell vient de l'affichage console d'un fichier UTF-8 sans BOM, pas du contenu exporté.

Les caractères `&`, `[`, `]`, `#`, tirets et espaces sont conservés correctement dans le JSON et le dossier produit par Automation.

## Répétabilité

| Exécution | SHA-256 | Résultat validation | Observation |
|---|---|---|---|
| 1 | `5433C0775A52DF8DB2553BE3D5843BAD126A0F9F894B74D191CE3AB79F444294` | Réussie avec avertissements attendus | Dossier `Documents\Automation LAP Smoke Test\QFC55 - Magmort Carcharhini RCZ` |
| 2 | `5433C0775A52DF8DB2553BE3D5843BAD126A0F9F894B74D191CE3AB79F444294` | Réussie avec avertissements attendus | Identique octet par octet à l'exécution 1 |
| Après redémarrage | `5433C0775A52DF8DB2553BE3D5843BAD126A0F9F894B74D191CE3AB79F444294` | Réussie avec avertissements attendus | L'exécution 2 a été faite après redémarrage d'Automation |

### Équivalence sémantique

- [x] mêmes versions ;
- [x] mêmes noms et chemins de récupération ;
- [x] mêmes diagnostics ;
- [x] sortie identique octet par octet pour les exécutions 1 et 2 ;
- [x] aucune donnée personnelle ou chemin absolu.

## Problèmes rencontrés

| Identifiant | Description | Bloquant | Contournement ou suite |
|---|---|---|---|
| A-PREP-001 | Le projet SDK officiel cible `v142`, absent ou non utilisé dans cet environnement. | Non | Build effectué avec `PlatformToolset=v143`. |
| A-PREP-002 | La console PowerShell affiche certains fichiers UTF-8 avec des accents dégradés. | Non | Les fichiers source restent en UTF-8 ; valider les sorties JSON avec le validateur indépendant. |
| A-PREP-003 | `python` n'est pas dans le PATH utilisateur. | Non | Utiliser le Python embarqué Codex ou installer/exposer Python localement. |
| A-PREP-004 | Première installation de la DLL dans `E:\SteamLibrary\steamapps\common\Automation\Content\ExportPlugins`, qui n'est pas le dossier plugin actif de cette installation. | Non | DLL déplacée vers `E:\SteamLibrary\steamapps\common\Automation\UE427\AutomationGame\Content\ExportPlugins`. |
| A-PREP-005 | Le runtime Lua d'Automation ne fournit pas `pcall`, ce qui faisait échouer `DoExport`. | Oui pour la première DLL | Payload Lua corrigé pour ne pas dépendre de `pcall`; DLL recompilée et réinstallée. |
| A-RUN-001 | Le runtime Lua d'Automation ne fournit pas l'horloge UTC via `os.date`. | Non | `exportedAtUtc` reste `null` et le diagnostic `utc_clock_not_available` est émis. |
| A-RUN-002 | Le jeu empêche les noms modèle/trim vides. | Non | Aucun comportement exporter spécifique à tester pour les champs vides à ce stade. |

## Conclusion du test de fumée

Sélectionner une conclusion :

- [ ] réussi ;
- [x] réussi avec réserves ;
- [ ] à reprendre ;
- [ ] SDK non compatible avec l’environnement testé.

### Décision

Le test de fumée est réussi avec réserves non bloquantes. La DLL est chargée par Automation, l'exporteur `Automation LAP - Smoke Test` apparaît, `DoExport` s'exécute, le fichier `automation-lap-vehicle.json` est produit et validé, et deux exports dont un après redémarrage donnent une sortie identique octet par octet.

Réserves :

- le runtime Lua ne fournit pas `pcall` ;
- la version Automation n'est pas exposée par les chemins testés ;
- l'horloge UTC n'est pas accessible via `os.date`.

Ces réserves imposent de fournir certaines métadonnées depuis le pont C++ ou depuis la procédure d'exécution lors des prochains incréments.

## A2 — JSON minimal avec date C++

- **Statut :** prêt à tester depuis Automation
- **Contrat JSON :** `0.1.1`
- **Exporter :** `0.1.1-a2`
- **DLL installée :** `E:\SteamLibrary\steamapps\common\Automation\UE427\AutomationGame\Content\ExportPlugins\AutomationLAPSmokeTest.dll`
- **SHA-256 DLL A2 :** `BC66CDBE6D40E10E94708B4E79125700D9BF7DCA4F10F9E33642A4DB6995BA56`

Changements préparés :

- `exportedAtUtc` est maintenant obligatoire et injecté par C++ au format UTC `YYYY-MM-DDTHH:MM:SSZ` ;
- `source.lastAccessTime` sonde `CarCalculator.lastAccessTime` ;
- `source.lastAccessTimePath` indique le chemin Lua utilisé ;
- le validateur indépendant attend désormais le contrat `0.1.1`.

Validation locale du sample `0.1.1` :

```text
SUCCESS: export satisfies smoke-test contract v0.1.1.
WARNING: Automation version was not exposed by Lua data
```

À vérifier par export Automation :

- [x] `exportedAtUtc` est une date UTC non nulle ;
- [x] `source.lastAccessTime` est présent ;
- [x] `source.lastAccessTimePath` vaut `lastAccessTime` ou un autre chemin documenté ;
- [x] le validateur `0.1.1` passe sur le JSON réel.

Export réel A2 :

| Champ | Valeur |
|---|---|
| Dossier | `Documents\Automation LAP Smoke Test\QFC55 - Magmort Carcharhini RCZ` |
| SHA-256 JSON | `C8DAB94589944C0C99A8958CB471BCBAECDB59C165E84D020BE40D9D935F8821` |
| `schemaVersion` | `0.1.1` |
| `exporterVersion` | `0.1.1-a2` |
| `exportedAtUtc` | `2026-07-26T13:08:48Z` |
| `source.lastAccessTime` | `35.255` |
| `source.lastAccessTimePath` | `lastAccessTime` |
| Diagnostics | `automation_version_not_exposed` |

Le diagnostic `utc_clock_not_available` est résolu par l'injection C++ de `exportedAtUtc`.

## A3 — Inventaire contrôlé des données

- **Statut :** prêt à tester depuis Automation
- **Exporter :** `0.1.2-a3`
- **Fichier ajouté :** `automation-lap-field-inventory.json`
- **Schéma inventaire :** `0.1.0`
- **DLL installée :** `E:\SteamLibrary\steamapps\common\Automation\UE427\AutomationGame\Content\ExportPlugins\AutomationLAPSmokeTest.dll`
- **SHA-256 DLL A3 :** `6441F92FE1D99283AE8301DC62E1214F837975C86A2D4A5D95DD277C404B104E`

Portée :

- sonde contrôlée de chemins candidats dans `CarCalculator` ;
- familles couvertes : identité, géométrie, masse, châssis, moteur, transmission, roues, freins, aérodynamique, suspension, performances ;
- chaque champ contient famille, chemins candidats, chemin résolu, présence, type Lua, valeur résumée, unité source présumée, unité interne candidate, nature, stabilité et redistribution ;
- les fonctions documentées sont détectées mais non appelées tant que le runtime Lua ne fournit pas `pcall` ou équivalent.

Validation locale des samples :

```text
SUCCESS: export satisfies smoke-test contract v0.1.1.
WARNING: Automation version was not exposed by Lua data

SUCCESS: export satisfies A3 field-inventory contract v0.1.0.
```

À vérifier par export Automation :

- [x] `automation-lap-vehicle.json` valide toujours le contrat `0.1.1` ;
- [x] `automation-lap-field-inventory.json` est produit ;
- [x] le validateur `validate_field_inventory.py` passe ;
- [ ] au moins les champs identité, géométrie de base, transmission, pneus/freins et suspension ont des chemins observés ;
- [x] les champs absents restent explicitement `missing`, jamais remplacés par zéro.

Export réel A3 :

| Fichier | SHA-256 |
|---|---|
| `automation-lap-vehicle.json` | `1A705418B2BC1F723D4BE23E024815C2DACB3326AB577043B0B1ED1A934379C7` |
| `automation-lap-field-inventory.json` | `FF46485D80B346945EC158C62AB09C7C1E7437662085E4830B0CA8822745B098` |

Résumé inventaire :

| Famille | Présents / sondés |
|---|---:|
| identity | 3 / 4 |
| mass | 2 / 2 |
| chassis | 4 / 4 |
| aerodynamics | 5 / 5 |
| suspension | 5 / 16 |
| performance | 2 / 3 |
| transmission | 1 / 5 |
| wheels | 1 / 7 |
| geometry | 0 / 10 |
| engine | 0 / 5 |
| brakes | 0 / 6 |

Les six fonctions documentées sont détectées comme fonctions Lua mais non appelées :

- `GetCarParameters`
- `GetBrakingForces`
- `CalculateDynamicCG`
- `GetTotalEffectiveArea`
- `GetFrontTyreParameters`
- `GetRearTyreParameters`

Premiers chemins observés utiles :

- masse : `CarInfo.TrimInfo.Results.Weight`
- répartition de masse : `CarInfo.TrimInfo.WeightDistributionFraction`
- châssis : `CarInfo.PlatformInfo.Chassis`
- matériau châssis : `CarInfo.PlatformInfo.ChassisMaterial`
- matériau panneaux : `CarInfo.PlatformInfo.PanelMaterial`
- placement moteur : `CarInfo.PlatformInfo.EnginePlacement`
- pneus : `CarInfo.TrimInfo.TyreType`
- aérodynamique : `CarInfo.TrimInfo.ActiveWing`, `ActiveCooling`, `Undertray`, `CoolingAirflowFraction`, `BrakeCoolingFraction`
- suspension : `CarInfo.PlatformInfo.FrontSuspension`, `RearSuspension`, `CarInfo.TrimInfo.Springs`, `Dampers`, `SwayBars`
- performance : `CarInfo.TrimInfo.Results.TopSpeed`, `CarInfo.TrimInfo.Results.BrakingDistance`

Conclusion intermédiaire A3 : la matrice fonctionne, mais les chemins candidats doivent être enrichis avant A4, notamment pour géométrie, moteur, freins, roues et transmission.

Préparation réalisée :

- payload Lua `automation_lap_export.lua` remplacé dans la ressource `ExportExample.lua` de la copie SDK externe ;
- exporteur renommé `Automation LAP - Smoke Test` ;
- callbacks mesh/texture neutralisés pour ce jalon ;
- `AddLuaFiles` écrit uniquement les fichiers retournés par Lua dans le dossier d'export ;
- dossier de sortie de la variante : `Documents\Automation LAP Smoke Test\<nom voiture>` ;
- DLL installée : `E:\SteamLibrary\steamapps\common\Automation\UE427\AutomationGame\Content\ExportPlugins\AutomationLAPSmokeTest.dll`
- SHA-256 DLL installée : `6B3AC8A20EABB7293EA7BB883374D2210DCB5655056DEFA818C393A8E9DB70E8`

### Prochaine étape autorisée

L’inventaire et l’extraction des données physiques ne commencent que si le test de fumée est réussi ou réussi avec des réserves compatibles avec la suite de l’expérience A.

## A3 — Enrichissement depuis export JSON communautaire

- **Source analysee :** `C:\Users\jerem\AppData\Local\AutomationGame\jsonExporter\[D.C.o.K] Magmort QFC55 - Magmort Carcharhini RCZ`
- **Fichiers utiles :** `data.json`, `functionData.json`
- **Exporter :** `0.1.3-a3-community-paths`
- **SHA-256 DLL installee :** `2D59D9980670144C83226CFFBB2C0C3406A6F09D474C771A5E254413E27DEDE8`

Constats principaux :

- `data.json` contient une racine `CarCalculator` avec `CarInfo`, `CarParameters`, `EngineCalculator`, `AccelerationDetails` ;
- plusieurs champs absents de notre premier export reel A3 sont visibles via des sous-objets plus profonds : `CarInfo.PlatformInfo.Body`, `CarInfo.TrimInfo.Body`, `CarInfo.TrimInfo.Brakes`, `CarInfo.TrimInfo.TyreDetails`, `CarInfo.TrimInfo.SuspensionDetails`, `CarInfo.TrimInfo.Gearbox` ;
- les champs moteur sont disponibles via `CarInfo.TrimInfo.EngineInfo.ModelInfo` et `CarInfo.TrimInfo.EngineInfo.PlatformInfo`, avec miroir sous `EngineCalculator.EngineInfo` ;
- `functionData.json` expose des resultats de fonctions, notamment pour `FN.EngineCalculator`, mais ces appels ne sont pas integres au prototype tant que l'absence de `pcall` rend les appels Lua non proteges.

Couverture simulee de la matrice A3 enrichie contre `data.json` communautaire :

| Famille | Presents / sondes |
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

Prochaine verification : regenerer un export depuis Automation et valider que la couverture observee dans `automation-lap-field-inventory.json` augmente effectivement sur l'objet Lua reel, pas seulement dans le dump communautaire.

### Export reel apres enrichissement communautaire

- **Dossier :** `C:\Users\jerem\Documents\Automation LAP Smoke Test\QFC55 - Magmort Carcharhini RCZ`
- **Exporter observe :** `0.1.3-a3-community-paths`
- **Horodatage export :** `2026-07-26T13:45:33Z`
- **Validation vehicle :** reussie, avec avertissement attendu `automation_version_not_exposed`
- **Validation inventaire :** reussie
- **SHA-256 vehicle :** `6AF7ADA823FF6C1B43C066D840B3AB381C5DCFD86E1347C34C2B65EF11E813DD`
- **SHA-256 inventaire :** `34A80CE677BDF1AA90ECEB16EF572F251DD75FE252A47DD9BF6EFD5408C36B8A`

Couverture observee dans le runtime Lua reel :

| Famille | Presents / sondes |
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

Toutes les sondes A3 trouvent un chemin dans l'objet Lua reel.

Correction appliquee apres analyse : `transmission.finalDrive` resolvait encore `CarInfo.TrimInfo.AdvancedGearing.FinalDrive.Ratio = 0`; le prototype `0.1.4-a3-final-drive` privilegie maintenant `CarInfo.TrimInfo.Gearbox.DiffRatio`, puis `CarParameters.DiffRatio`.

- **Exporter prepare pour prochain export :** `0.1.4-a3-final-drive`
- **SHA-256 DLL installee :** `D84564622A9F10FA50BA2102E01FDFEE680E432E85943A5BA027A17843519217`

### Export reel final `0.1.4-a3-final-drive`

- **Dossier :** `C:\Users\jerem\Documents\Automation LAP Smoke Test\QFC55 - Magmort Carcharhini RCZ`
- **Horodatage export :** `2026-07-26T13:50:06Z`
- **Validation vehicle :** reussie, avec avertissement attendu `automation_version_not_exposed`
- **Validation inventaire :** reussie
- **Couverture observee :** `67 / 67`
- **SHA-256 vehicle :** `F55D3F8A46218B1FD4F23CE6207C64DFEFB63A03257D39E2B160B52D3358A419`
- **SHA-256 inventaire :** `5DEE1F31A41754028BAEFD7F6D9846D07E65ACDE1C3EFC206FB880E16FB65B16`

Verification de la correction :

- `transmission.finalDrive.resolvedPath` vaut `CarInfo.TrimInfo.Gearbox.DiffRatio` ;
- `transmission.finalDrive.valuePreview` vaut `4.6945730476373` ;
- l'ancien chemin `CarInfo.TrimInfo.AdvancedGearing.FinalDrive.Ratio` reste seulement en candidat de repli.

Conclusion A3 : l'inventaire controle est valide sur l'export reel enrichi. Toutes les sondes trouvent un chemin, et les champs absents du premier prototype sont maintenant resolus sans appel de fonction Lua non protege.
