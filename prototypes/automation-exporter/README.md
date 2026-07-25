# Prototype — Automation Exporter

- **Expérience :** A — Extraction des données Automation
- **Ticket :** #3
- **Statut :** préparation
- **Nature :** prototype jetable

## But

Prouver que la version installée d’Automation peut charger un exporteur personnalisé et produire un JSON numérique, versionné et reproductible pour trois voitures contrastées.

Le protocole de référence se trouve dans `docs/feasibility/experiments/A-AUTOMATION-EXTRACTION.md`.

## Résultat minimal attendu

Le premier incrément du prototype doit produire un fichier JSON valide contenant uniquement :

- version du schéma ;
- version de l’exporteur ;
- version d’Automation lorsque disponible ;
- nom du modèle ;
- nom du trim ;
- horodatage UTC ;
- diagnostics éventuels.

Aucune donnée physique détaillée ne doit être ajoutée avant que ce test de fumée fonctionne.

## Organisation prévue

```text
prototypes/automation-exporter/
  README.md
  src/                  # code original du prototype
  schemas/              # schémas JSON propres au projet
  samples/              # exemples redistribuables uniquement
  results/              # synthèses et mesures légères
  local/                # fichiers locaux ignorés, à créer si nécessaire
```

## Dépendances externes

Le SDK officiel d’Automation ne doit pas être copié dans ce dépôt sans vérification explicite de sa licence et de ses conditions de redistribution.

Le développeur doit utiliser une copie locale identifiée par URL et commit. Le rapport doit relever :

- le commit du SDK ;
- la version d’Automation ;
- le compilateur et le toolset ;
- l’architecture des binaires ;
- toute modification locale apportée à l’exemple officiel.

## Entrées attendues

Trois voitures conçues pour maximiser les contrastes :

1. légère et peu puissante ;
2. puissante et orientée performance ;
3. lourde, à transmission intégrale ou aérodynamiquement complexe.

Les fichiers `.car`, données, captures, textures ou autres contenus issus d’Automation ne doivent être committés qu’après vérification des droits de redistribution. À défaut, conserver une empreinte, les métadonnées et une procédure de reproduction.

## Première séquence de travail

1. Renseigner la fiche d’environnement du protocole.
2. Récupérer une copie locale du dépôt officiel `AutomationStaff/ExporterSDK`.
3. Compiler l’exemple officiel sans modification fonctionnelle.
4. Installer le plugin dans l’emplacement requis par Automation.
5. Vérifier que l’exporteur apparaît et termine un export.
6. Créer une variante minimale portant le nom Automation LAP.
7. Produire et valider le premier JSON.
8. Documenter le résultat dans le ticket #3.

## Définition de terminé pour le test de fumée

- [ ] la version d’Automation est enregistrée ;
- [ ] le commit du SDK est enregistré ;
- [ ] les outils de compilation sont enregistrés ;
- [ ] le plugin est visible dans Automation ;
- [ ] un export se termine sans erreur ;
- [ ] le JSON est analysable par un outil indépendant ;
- [ ] les noms avec accents sont correctement encodés ;
- [ ] aucune donnée personnelle ou chemin absolu n’apparaît dans la sortie ;
- [ ] les limites rencontrées sont consignées.

## Règle de promotion

Aucun fichier de ce prototype ne doit être déplacé vers `src/` avant la conclusion de l’expérience A et une décision explicite sur l’architecture de l’importeur.
