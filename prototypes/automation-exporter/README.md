# Prototype — Automation Exporter

- **Expérience :** A — Extraction des données Automation
- **Ticket :** #3
- **Statut :** test de fumée prêt à exécuter localement
- **Nature :** prototype jetable

## But

Prouver que la version installée d’Automation peut charger un exporteur personnalisé et produire un JSON numérique, versionné et reproductible pour trois voitures contrastées.

Le protocole de référence se trouve dans `docs/feasibility/experiments/A-AUTOMATION-EXTRACTION.md`.

## Incrément actuel

Le dépôt contient maintenant le payload Lua et les outils nécessaires au premier test de fumée. Cet incrément ne cherche pas encore à extraire la masse, le moteur, les pneus ou l’aérodynamique.

Le fichier minimal produit est :

```text
automation-lap-vehicle.json
```

Il contient uniquement :

- version du schéma ;
- version de l’exporteur ;
- date d'export UTC injectée par le pont C++ ;
- version d’Automation lorsque disponible ;
- `CarCalculator.lastAccessTime` lorsque disponible ;
- nom du modèle ;
- nom du trim ;
- chemins Lua ayant fourni les noms ;
- diagnostics éventuels.

Les chemins de données sont enregistrés temporairement afin de vérifier quelles propriétés restent réellement valides dans la version installée d’Automation.

## Organisation

```text
prototypes/automation-exporter/
  README.md
  SETUP_WINDOWS.md
  src/
    automation_lap_export.lua
  schemas/
    automation-raw-vehicle-smoke-v0.1.schema.json
  samples/
    smoke-test.example.json
  tools/
    validate_smoke_export.py
  results/
    SMOKE_TEST_RESULT.md
  local/                     # fichiers locaux ignorés
```

## Dépendances externes

Le SDK officiel d’Automation ne doit pas être copié dans ce dépôt sans vérification explicite de sa licence et de ses conditions de redistribution.

Le développeur utilise une copie locale identifiée par URL et commit. Le rapport doit relever :

- le commit du SDK ;
- la version d’Automation ;
- le compilateur et le toolset ;
- l’architecture des binaires ;
- toute modification locale apportée à l’exemple officiel.

La documentation officielle indique que :

- le plugin est une DLL placée sous `Content/ExportPlugins` ;
- le SDK fournit les interfaces C++ de l’exporteur ;
- le DLL charge un ou plusieurs fichiers Lua ;
- Automation appelle `DoExport(CarCalculator, CarFile)` ;
- cette fonction retourne une table de fichiers et une table de données scalaires.

Ces informations restent à confirmer sur la version installée.

Sur l’installation Steam UE427 locale, le dossier plugin complet est `E:\SteamLibrary\steamapps\common\Automation\UE427\AutomationGame\Content\ExportPlugins`.

Le contrat `0.1.1` ne dépend plus de `os.date` côté Lua : le Lua émet un placeholder et la DLL le remplace par une date UTC juste avant l'écriture du JSON.

L'incrément A3 ajoute un second fichier :

```text
automation-lap-field-inventory.json
```

Ce fichier inventorie une liste contrôlée de chemins candidats dans `CarCalculator`, sans dump récursif non borné. Les fonctions documentées sont détectées mais non appelées tant que le runtime Lua ne fournit pas d'appel protégé équivalent à `pcall`.

## Exécuter le test

Suivre [SETUP_WINDOWS.md](SETUP_WINDOWS.md).

Après l’export, valider le document avec :

```powershell
python prototypes\automation-exporter\tools\validate_smoke_export.py `
  "C:\chemin\vers\automation-lap-vehicle.json"
```

Le script n’utilise aucune dépendance Python externe.

## Entrées attendues après le test de fumée

Lorsque l’intégration minimale sera validée, trois voitures seront conçues pour maximiser les contrastes :

1. légère et peu puissante ;
2. puissante et orientée performance ;
3. lourde, à transmission intégrale ou aérodynamiquement complexe.

Les fichiers `.car`, données, captures, textures ou autres contenus issus d’Automation ne doivent être committés qu’après vérification des droits de redistribution. À défaut, conserver une empreinte, les métadonnées et une procédure de reproduction.

## Définition de terminé du test de fumée

- [ ] la version d’Automation est enregistrée ;
- [ ] le commit du SDK est enregistré ;
- [ ] les outils de compilation sont enregistrés ;
- [ ] l’exemple officiel compile et s’exécute ;
- [ ] la variante Automation LAP est visible ;
- [ ] un export se termine sans erreur ;
- [ ] le JSON est analysable par le validateur indépendant ;
- [ ] les noms avec accents sont correctement encodés ;
- [ ] deux exports sont sémantiquement équivalents hors horodatage ;
- [ ] aucune donnée personnelle ou chemin absolu n’apparaît dans la sortie ;
- [ ] les limites rencontrées sont consignées dans `results/SMOKE_TEST_RESULT.md`.

## Décision suivante

Après réussite du test de fumée, l’expérience A pourra ouvrir le second incrément : inventaire des champs disponibles et définition complète de `AutomationRawVehicleData` v0.1.

## Règle de promotion

Aucun fichier de ce prototype ne doit être déplacé vers `src/` avant la conclusion de l’expérience A et une décision explicite sur l’architecture de l’importeur.
