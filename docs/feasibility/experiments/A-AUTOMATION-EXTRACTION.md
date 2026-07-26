# Expérience A — Extraction des données Automation

- **Statut :** prête à démarrer
- **Ticket :** #3
- **Parent :** #2
- **Version du protocole :** 0.1
- **Date d’ouverture :** 25 juillet 2026

## 1. Question testée

Pouvons-nous extraire de manière stable les données nécessaires à trois voitures très différentes, les conserver dans un format brut versionné et identifier explicitement les paramètres manquants nécessaires à notre future simulation ?

## 2. Hypothèse

L’Exporter Plugin SDK fournit une combinaison C++ et Lua :

- la couche Lua reçoit le `CarCalculator` et peut produire des fichiers de configuration ;
- le `CarCalculator` expose les tables de configuration et les résultats calculés de la voiture ;
- le C++ sert à l’intégration du plugin et au traitement de données telles que maillages et textures.

Nous supposons donc qu’un exporteur minimal peut produire un JSON purement numérique sans exploiter les maillages, textures ou sons.

Cette hypothèse doit être vérifiée contre la version d’Automation réellement installée. La documentation officielle disponible est ancienne et ne constitue pas à elle seule une preuve de compatibilité actuelle.

## 3. Objectifs

1. Prouver qu’un plugin exporteur personnalisé peut être chargé et exécuté.
2. Produire un premier JSON comportant identité et versions.
3. Inventorier les données effectivement disponibles au moment de l’export.
4. Définir un schéma brut qui ne confond pas données Automation et modèle physique interne.
5. Tester trois voitures contrastées.
6. mesurer la stabilité sémantique de plusieurs exports identiques.
7. Identifier les champs absents, ambigus, dérivés ou non redistribuables.
8. Confirmer, amender ou remplacer l’ADR-0003.

## 4. Hors périmètre

Cette expérience ne cherche pas à :

- importer un modèle 3D dans Unity ;
- exporter ou réutiliser les sons d’Automation ;
- reproduire la physique de BeamNG.drive ;
- définir la `VehicleDefinition` finale ;
- calibrer le modèle dynamique ;
- garantir la compatibilité avec toutes les versions passées ou futures d’Automation ;
- transformer le prototype d’exporteur en outil de production.

## 5. État des connaissances initiales

La documentation officielle décrit un SDK composé de C++ et de Lua. Lua sert à lire les calculs d’Automation et peut produire directement des fichiers. Le point d’entrée `DoExport(CarCalculator, CarFile)` renvoie une table de fichiers et une table de données.

Le `CarCalculator` est décrit comme une structure de tables imbriquées comprenant notamment :

- `CarInfo.PlatformInfo` ;
- `CarInfo.TrimInfo` ;
- `TrimInfo.Results` ;
- `TrimInfo.EngineInfo` ;
- `TrimInfo.Gearbox` ;
- `EngineCalculator.EngineInfo`.

La documentation mentionne également plusieurs fonctions utiles :

- `GetCarParameters()` ;
- `GetBrakingForces()` ;
- `CalculateDynamicCG(speed, mode)` ;
- `GetTotalEffectiveArea(mode)` ;
- `GetFrontTyreParameters()` ;
- `GetRearTyreParameters()`.

Le dépôt officiel de l’Exporter SDK fournit un projet d’exemple de DLL, les en-têtes d’interface et l’ordre des appels d’export. Il indique que le plugin doit être placé dans le dossier `Content/ExportPlugins` de l’installation d’Automation.

Ces informations servent à préparer le protocole, mais chaque symbole et comportement doit être confirmé localement.

## 6. Sources techniques initiales

- [Exporter Plugin SDK — Automation Game Wiki](https://wiki.automationgame.com/index.php?title=Exporter_Plugin_SDK)
- [Lua Exporter Code — Automation Game Wiki](https://wiki.automationgame.com/index.php?title=Lua_Exporter_Code)
- [CarCalculator — Automation Game Wiki](https://wiki.automationgame.com/index.php?title=CarCalculator)
- [AutomationStaff/ExporterSDK — dépôt officiel](https://github.com/AutomationStaff/ExporterSDK)

### Réserve documentaire

Les pages principales consultées ont été modifiées en 2021 ou 2022. Le protocole doit donc commencer par un inventaire de versions et un test de fumée, sans supposer que la documentation reflète exactement la build actuelle.

## 7. Environnement à relever

Avant toute compilation ou export, consigner :

| Élément | Valeur |
|---|---|
| Version exacte d’Automation | À renseigner |
| Branche Steam éventuelle | À renseigner |
| Chemin d’installation | À renseigner |
| Version ou commit de l’Exporter SDK | À renseigner |
| Version de Visual Studio | À renseigner |
| Toolset C++ | À renseigner |
| Version de Windows | À renseigner |
| Architecture du binaire chargé | À renseigner |
| Réglages d’export pertinents | À renseigner |

Ne jamais committer de chemin personnel absolu. Les chemins locaux appartiennent à un fichier ignoré ou à la documentation de procédure avec variables symboliques.

## 8. Sélection des trois voitures

Les trois voitures doivent maximiser les contrastes utiles, sans chercher une représentation exhaustive du jeu.

### Véhicule A1 — Léger et peu puissant

Profil recherché :

- faible masse ;
- puissance modérée ;
- traction avant ou propulsion simple ;
- pneus étroits ;
- faible appui aérodynamique.

But : vérifier les faibles valeurs, la motricité et les effets de masse.

### Véhicule A2 — Puissant et orienté performance

Profil recherché :

- puissance élevée ;
- propulsion ;
- pneus larges ;
- freins importants ;
- boîte comportant plusieurs rapports.

But : vérifier les courbes moteur, limites de transmission et valeurs élevées.

### Véhicule A3 — Lourd ou aérodynamiquement complexe

Profil recherché :

- masse élevée ou transmission intégrale ;
- dispositifs aérodynamiques ;
- répartition de masse différente ;
- suspension distincte des deux autres voitures.

But : vérifier les champs de châssis, d’aérodynamique, de transmission et de suspension.

Chaque voiture doit être identifiée par :

- nom du modèle et du trim ;
- année ou ère de conception ;
- version de la voiture ;
- empreinte du fichier source lorsque disponible ;
- capture ou fiche récapitulative des performances de référence.

## 9. Données minimales recherchées

### 9.1 Identité et provenance

- nom du modèle ;
- nom du trim ;
- identifiant stable disponible ;
- version d’Automation ;
- version de l’exporteur ;
- version du schéma brut ;
- date d’export en UTC ;
- empreinte du contenu source ou du résultat normalisé.

### 9.2 Géométrie et masse

- masse totale ;
- empattement ;
- voies avant et arrière ;
- dimensions utiles disponibles ;
- répartition statique avant-arrière ;
- position ou hauteur de centre de gravité si accessible ;
- informations de roulis ou suspension utiles.

### 9.3 Moteur

- architecture et cylindrée ;
- carburant ;
- régime maximal ;
- régime de ralenti si pertinent ;
- puissance et couple maximaux ;
- courbe de couple ou points permettant de la reconstruire ;
- inertie ou réponse disponible ;
- consommation ou rendement disponible.

### 9.4 Transmission

- type de motricité ;
- rapports de boîte ;
- rapport final ;
- rendement de transmission ;
- type de différentiel ;
- aides à la motricité disponibles ;
- temps de passage de rapport s’il existe.

### 9.5 Pneus et roues

- dimensions avant et arrière ;
- type ou composé ;
- paramètres de charge ou d’adhérence accessibles ;
- rayon roulant ;
- inertie disponible ;
- pression ou rigidité si accessible.

### 9.6 Freins

- type ;
- diamètre ;
- force de freinage disponible ;
- équilibre avant-arrière ;
- aides telles que l’ABS.

### 9.7 Aérodynamique

- aire frontale ou aire de traînée effective ;
- coefficient de traînée si accessible ;
- appui avant et arrière ou valeurs équivalentes ;
- comportement des éléments actifs selon les modes disponibles.

### 9.8 Suspension

- architecture avant et arrière ;
- raideurs ou paramètres calculés disponibles ;
- amortissement disponible ;
- barres antiroulis ;
- hauteur de caisse ;
- géométrie utile disponible.

### 9.9 Carburant et performances

- capacité du réservoir ;
- masse de carburant de référence ;
- vitesse maximale ;
- accélérations de référence ;
- distances de freinage ;
- valeurs de virage ou de skidpad ;
- autres résultats calculés disponibles.

## 10. Classification obligatoire des champs

Chaque champ exporté doit recevoir les métadonnées suivantes dans le dictionnaire de données :

| Propriété | Valeurs possibles |
|---|---|
| Origine | `automation`, `calculated-by-exporter`, `default`, `manual` |
| Présence | `required`, `optional`, `unknown` |
| Nature | `raw-choice`, `raw-result`, `sampled-curve`, `derived` |
| Unité source | unité exacte ou `dimensionless` |
| Unité interne candidate | unité SI ou `not-applicable` |
| Stabilité | `stable`, `observed`, `unstable`, `untested` |
| Confidentialité / redistribution | `allowed`, `restricted`, `unknown` |

Un champ absent ne doit jamais recevoir silencieusement la valeur numérique zéro. Il doit être représenté comme absent, inconnu ou remplacé par une valeur par défaut explicitement sourcée.

## 11. Forme provisoire du fichier brut

Le format précis reste à valider, mais le fichier doit séparer provenance, données et diagnostics.

```json
{
  "schemaVersion": "0.1.0",
  "source": {
    "application": "Automation",
    "applicationVersion": "unknown",
    "exporterVersion": "0.1.0",
    "exportedAtUtc": "2026-07-25T00:00:00Z"
  },
  "vehicleIdentity": {
    "modelName": "Example",
    "trimName": "Example Trim"
  },
  "data": {
    "mass": {},
    "geometry": {},
    "engine": {},
    "transmission": {},
    "tyres": {},
    "brakes": {},
    "aerodynamics": {},
    "suspension": {},
    "fuel": {},
    "referenceResults": {}
  },
  "diagnostics": {
    "missingFields": [],
    "warnings": [],
    "unsupportedFields": []
  }
}
```

Ce JSON n’est pas une `VehicleDefinition`. Il représente ce que l’exporteur a observé, avec le minimum d’interprétation nécessaire.

## 12. Protocole

### A0 — Inventaire et conformité

1. relever toutes les versions de l’environnement ;
2. consulter les conditions de licence du SDK et des données produites ;
3. définir ce qui peut ou non être committé dans ce dépôt public ;
4. noter les divergences entre documentation et fichiers du SDK.

**Sortie attendue :** fiche d’environnement et décision sur la conservation des fixtures.

### A1 — Test de fumée du SDK

1. récupérer une copie identifiée du dépôt officiel ;
2. compiler l’exemple sans modification fonctionnelle ;
3. installer les binaires selon la procédure du SDK ;
4. lancer Automation ;
5. confirmer que l’exporteur apparaît et qu’un export se termine ;
6. conserver les journaux de compilation et d’exécution utiles.

**Sortie attendue :** preuve que la chaîne de plugin fonctionne sur la build installée.

### A2 — Export JSON minimal

1. créer un exporteur portant un nom distinct ;
2. retourner un fichier JSON contenant seulement :
   - version du schéma ;
   - version de l’exporteur ;
   - identité du modèle et du trim ;
   - horodatage ;
3. exporter une voiture ;
4. valider le JSON avec un parseur indépendant ;
5. vérifier les caractères non ASCII dans les noms.

**Sortie attendue :** premier fichier autonome valide.

### A3 — Inventaire des données

1. sonder les tables documentées ;
2. appeler prudemment les fonctions documentées ;
3. capturer le type, la présence et l’unité présumée ;
4. éviter un dump récursif non borné de tout le `CarCalculator` ;
5. documenter chaque accès qui provoque une erreur ou une valeur incohérente ;
6. construire progressivement le dictionnaire de données.

**Sortie attendue :** matrice `champ → accès → type → unité → disponibilité`.

### A4 — Export des trois voitures

Pour chaque voiture :

1. sauvegarder une version source identifiée ;
2. relever les valeurs visibles de référence dans Automation ;
3. effectuer l’export ;
4. valider le schéma ;
5. comparer les valeurs exportées aux valeurs visibles ;
6. vérifier les ordres de grandeur et unités ;
7. consigner les champs manquants.

**Sortie attendue :** trois rapports d’export et, lorsque légalement possible, trois fixtures anonymisées ou redistribuables.

### A5 — Répétabilité

Pour une voiture inchangée :

1. effectuer au moins cinq exports ;
2. retirer de la comparaison les champs volontairement variables tels que l’horodatage ;
3. canonicaliser l’ordre des propriétés et le format des nombres ;
4. calculer une empreinte sémantique ;
5. comparer champ par champ ;
6. répéter après redémarrage d’Automation.

**Sortie attendue :** taux de stabilité et liste des champs non déterministes.

### A6 — Variation contrôlée

Modifier une seule propriété à la fois sur une copie d’une voiture :

- masse ou équipement ;
- rapport final ;
- largeur de pneu ;
- réglage aérodynamique ;
- puissance moteur.

Pour chaque changement :

1. exporter avant et après ;
2. produire un diff sémantique ;
3. vérifier que les champs attendus évoluent ;
4. relever les effets secondaires calculés ;
5. identifier les champs redondants ou dérivés.

**Sortie attendue :** preuve que le format permet d’expliquer les différences entre véhicules.

### A7 — Conclusion

1. classer chaque famille de données : disponible, partielle, dérivable ou absente ;
2. déterminer si un exporteur Lua et C++ minimal suffit ;
3. proposer le schéma brut v0.1 ;
4. lister les paramètres physiques qui devront être estimés ailleurs ;
5. évaluer la fragilité aux versions ;
6. statuer sur l’ADR-0003 ;
7. mettre à jour le rapport consolidé.

## 13. Scénarios et répétitions

| Identifiant | Scénario | Répétitions minimales |
|---|---|---:|
| A-S01 | Test de fumée de l’exemple officiel | 1 installation propre |
| A-S02 | JSON minimal | 3 exports |
| A-S03 | Véhicule léger | 5 exports |
| A-S04 | Véhicule puissant | 5 exports |
| A-S05 | Véhicule lourd ou aérodynamique | 5 exports |
| A-S06 | Même voiture après redémarrage | 3 exports |
| A-S07 | Variation contrôlée d’un paramètre | 5 paramètres |

## 14. Métriques

| Métrique | Unité | Attente initiale |
|---|---|---|
| Taux de champs minimaux disponibles | % | À mesurer |
| Champs sans unité confirmée | nombre | Doit tendre vers 0 pour les champs retenus |
| Exports JSON valides | % | 100 % |
| Exports sémantiquement identiques | % | 100 % hors champs variables documentés |
| Écart aux valeurs visibles de référence | % ou unité native | Expliqué champ par champ |
| Champs manquants non signalés | nombre | 0 |
| Erreurs d’exécution de l’exporteur | nombre | 0 sur scénarios retenus |
| Temps d’export numérique | ms ou s | Mesuré, sans seuil bloquant initial |

## 15. Critères de réussite

L’expérience est `validée` si :

- [ ] le plugin est chargé sur la version installée ;
- [ ] les trois voitures produisent un JSON valide ;
- [ ] les familles de données minimales sont couvertes ou leurs absences explicitement identifiées ;
- [ ] les unités des champs retenus sont documentées ;
- [ ] les exports répétés sont sémantiquement équivalents ;
- [ ] les diagnostics distinguent absence, zéro et valeur inconnue ;
- [ ] les versions source, exporteur et schéma sont enregistrées ;
- [ ] les données brutes restent séparées de la future `VehicleDefinition` ;
- [ ] la politique de conservation et de redistribution est documentée.

L’expérience peut être `validée avec réserves` si certaines données nécessaires à la physique sont absentes mais peuvent être dérivées ou calibrées par une méthode générale et documentée.

## 16. Conditions de révision ou d’échec

L’expérience doit être `à modifier` ou `non viable` si :

- le SDK ne peut pas être chargé avec la version actuelle sans dépendance obsolète non maîtrisable ;
- les données essentielles varient de façon non explicable entre exports ;
- les principales courbes ou caractéristiques ne sont pas accessibles et aucune alternative générale n’est crédible ;
- l’export nécessite de distribuer des contenus dont les droits sont incompatibles avec le projet ;
- la structure disponible oblige à dépendre directement de champs internes instables sans couche d’adaptation ;
- les valeurs ne peuvent pas être reliées aux performances visibles dans Automation.

## 17. Sécurité et robustesse du prototype

Même jetable, l’exporteur doit :

- limiter les noms et chemins de fichiers produits ;
- nettoyer les caractères interdits ;
- ne jamais écrire en dehors du dossier choisi ;
- ne pas embarquer de chemin local, secret ou donnée personnelle ;
- borner toute exploration de table ;
- produire des erreurs lisibles sans masquer les champs non supportés ;
- sérialiser les nombres avec une culture indépendante de la machine ;
- utiliser un encodage UTF-8 explicite.

## 18. Organisation des livrables

```text
prototypes/automation-exporter/
  README.md
  src/
  schemas/
  samples/
  results/

docs/feasibility/experiments/
  A-AUTOMATION-EXTRACTION.md
```

Les dossiers `samples` et `results` ne doivent contenir que des fichiers dont la redistribution a été vérifiée. Sinon, conserver :

- empreinte cryptographique ;
- taille ;
- version ;
- résumé des champs ;
- procédure permettant au propriétaire d’origine de reproduire le fichier localement.

## 19. Conclusion actuelle

- **Conclusion :** en attente
- **Niveau de confiance :** faible tant que le test de fumée n’a pas été exécuté
- **Prochaine action :** renseigner l’environnement, compiler l’exemple officiel et produire le JSON minimal.
