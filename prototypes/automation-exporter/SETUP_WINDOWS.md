# Installation locale — test de fumée Automation Exporter

Ce guide décrit la première manipulation de l’expérience A. Il ne suppose pas que le SDK officiel est compatible avec la version actuelle d’Automation : cette compatibilité est précisément ce que nous devons mesurer.

## 1. Relever l’environnement

Avant toute modification, consigner dans le ticket #3 :

- version et branche Steam d’Automation ;
- chemin d’installation du jeu ;
- version de Windows ;
- édition et version de Visual Studio ;
- toolset MSVC et Windows SDK disponibles ;
- architecture testée : x64 puis Win32 si encore acceptée par le jeu.

Ne publier aucun chemin contenant un nom d’utilisateur. Les chemins locaux restent dans les notes privées ou sont remplacés par des variables comme `%AUTOMATION_HOME%`.

## 2. Récupérer le SDK officiel

Créer une copie locale séparée du dépôt Automation LAP :

```powershell
$Work = "C:\Dev\AutomationLAP-External"
New-Item -ItemType Directory -Force $Work | Out-Null
Set-Location $Work
git clone https://github.com/AutomationStaff/ExporterSDK.git
git -C ExporterSDK rev-parse HEAD
```

Reporter le commit exact dans #3. Le SDK ne doit pas être copié dans ce dépôt tant que sa licence et ses conditions de redistribution ne sont pas clarifiées.

## 3. Compiler l’exemple officiel sans modification

Ouvrir la solution ou le projet fourni sous `AutomationExportExample`, restaurer les composants Visual Studio demandés, puis compiler d’abord l’exemple officiel sans modifier son comportement.

Le README officiel indique qu’un plugin est une DLL placée dans :

```text
%AUTOMATION_HOME%\Content\ExportPlugins
```

Sur l’installation Steam UE427 testée localement, `%AUTOMATION_HOME%` correspond au sous-dossier du jeu :

```text
E:\SteamLibrary\steamapps\common\Automation\UE427\AutomationGame
```

Le dossier effectif des DLL exporteur est donc :

```text
%AUTOMATION_HOME%\Content\ExportPlugins
```

Il indique également que l’exporteur doit idéalement fournir les architectures 64 bits et 32 bits. La version réellement acceptée par l’installation courante doit être consignée comme résultat expérimental, pas supposée.

### Preuve minimale

- la DLL est chargée sans erreur visible ;
- l’exporteur apparaît dans l’interface ;
- un export officiel se termine ;
- les fichiers de sortie attendus sont créés.

En cas d’échec, conserver le message complet, la configuration de compilation et l’étape précise où l’échec survient.

## 4. Intégrer le payload Lua Automation LAP

Le SDK officiel expose notamment `GetLUAFileLength()` et `GetLUAFile()`. Localiser dans l’exemple l’implémentation qui fournit le script Lua à Automation.

Créer ensuite une branche locale du SDK et remplacer ou inclure le payload retourné par :

```text
prototypes/automation-exporter/src/automation_lap_export.lua
```

La fonction globale exigée est :

```lua
DoExport(CarCalculator, CarFile)
```

Elle retourne :

1. une table `Files`, dont la clé est le nom du fichier et la valeur son contenu ;
2. une table `Data`, réservée aux valeurs scalaires accessibles au pont C++.

Le test Automation LAP doit produire :

```text
automation-lap-vehicle.json
```

À partir d'A3, il doit aussi produire :

```text
automation-lap-field-inventory.json
```

`automation-lap-vehicle.json` reste le contrat minimal de provenance. `automation-lap-field-inventory.json` est une matrice de sondes contrôlées pour préparer l'extraction physique détaillée.

À partir d'A6, il doit aussi produire :

```text
automation-lap-graph-inventory.json
```

Ce fichier inventorie `CarInfo.TrimInfo.Results.GraphData` de façon bornée. Il ne remplace pas encore un export complet des courbes ; il sert à identifier les graphes disponibles, leur forme et leurs aperçus numériques.

À partir d'A7, il doit aussi produire :

```text
automation-lap-raw-graphs.json
```

Ce fichier exporte les séries numériques complètes des graphes ciblés `AccelerationToTopSpeed`, `Braking`, `BrakingVGrip`, `LowSpeedSteering` et `HighSpeedSteering`.

Note de compatibilité observée : le runtime Lua d’Automation peut être restreint par rapport à Lua standard. Ne pas supposer la présence de fonctions comme `pcall`.

## 5. Compiler la variante Automation LAP

Adapter localement les fonctions d’identification de l’exemple pour que l’interface distingue clairement la variante expérimentale, par exemple :

```text
Automation LAP — Smoke Test
```

Ne modifier que ce qui est nécessaire pour :

- charger le payload Lua ;
- identifier l’exporteur ;
- écrire les fichiers retournés par Lua ;
- terminer l’export sans traiter les maillages ou textures si l’interface du SDK l’autorise.

Si le SDK impose les callbacks de maillage et texture, les laisser fonctionnels ou neutres selon le contrat officiel, sans introduire de traitement métier.

## 6. Exécuter le premier export

Créer ou sélectionner une voiture de test avec :

- un nom de modèle reconnaissable ;
- un nom de trim reconnaissable ;
- au moins un caractère accentué pour vérifier l’UTF-8.

Exécuter l’export et retrouver `automation-lap-vehicle.json` dans le dossier produit.

## 7. Valider indépendamment le JSON

Depuis la racine d’Automation LAP :

```powershell
python prototypes\automation-exporter\tools\validate_smoke_export.py `
  "C:\chemin\vers\automation-lap-vehicle.json"
```

Pour A3 :

```powershell
python prototypes\automation-exporter\tools\validate_field_inventory.py `
  "C:\chemin\vers\automation-lap-field-inventory.json"
```

Pour A6 :

```powershell
python prototypes\automation-exporter\tools\validate_graph_inventory.py `
  "C:\chemin\vers\automation-lap-graph-inventory.json"
```

Pour A7 :

```powershell
python prototypes\automation-exporter\tools\validate_raw_graphs.py `
  "C:\chemin\vers\automation-lap-raw-graphs.json"
```

Pour A8, assembler puis valider le contrat brut unifié :

```powershell
python prototypes\automation-exporter\tools\build_raw_vehicle_data.py `
  "C:\chemin\vers\un\dossier\voiture"

python prototypes\automation-exporter\tools\validate_raw_vehicle_data.py `
  "C:\chemin\vers\un\dossier\voiture\automation-lap-raw-vehicle-data.json"
```

Le validateur utilise uniquement la bibliothèque standard Python. Il vérifie notamment :

- la syntaxe JSON et l’encodage UTF-8 ;
- les champs obligatoires ;
- la version de schéma `0.1.0` ;
- la structure `source`, `vehicle` et `diagnostics` ;
- l’absence de chemins absolus dans les données.

Un avertissement sur la version d’Automation est acceptable si cette information n’est pas exposée dans l’environnement Lua. Un nom de modèle ou de trim absent doit être traité comme une anomalie à investiguer.

## 8. Répéter le test

Exporter deux fois la même voiture sans modification.

Les documents ne seront pas identiques octet par octet à cause de `exportedAtUtc`, mais doivent être sémantiquement équivalents après exclusion de cet horodatage.

Vérifier également :

- stabilité des chemins de données utilisés pour retrouver les noms ;
- absence de variation de casse ou d’encodage ;
- diagnostics identiques ;
- résultat identique après redémarrage du jeu.

## 9. Consigner le résultat

Compléter `results/SMOKE_TEST_RESULT.md` et ajouter un commentaire dans #3 avec :

- verdict du chargement du SDK officiel ;
- verdict de la variante Automation LAP ;
- versions et commit ;
- diagnostics produits ;
- empreinte SHA-256 du JSON ;
- éléments à corriger avant l’extraction physique.

Ne committer un fichier produit par Automation que si sa redistribution a été explicitement vérifiée. À défaut, conserver son empreinte et une version anonymisée reproduite manuellement.
