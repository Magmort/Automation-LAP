# Automation LAP — reprise de définition projet

- **Date de reprise :** 2026-07-26
- **Source projet :** `Magmort/Automation-LAP`, branche `experiment/automation-exporter-smoke-test`
- **Commit source vérifié :** `94ece8954ed7fdf7135c73c3d44af0a7df5bf44c`
- **Source résultats :** `prototypes/automation-exporter/results/SMOKE_TEST_RESULT.md`

## Vision

Automation LAP est une simulation automobile 2D vue du dessus où le joueur prépare, observe et analyse des courses disputées par des pilotes IA. La simulation doit produire des courses plausibles, explicables et rejouables à partir de données de voitures, de pilotes, de circuits, de stratégie, de règles et d'événements.

Unity reste une couche de présentation. Le coeur de simulation doit être indépendant, testable sans scène Unity, et produire l'autorité des états de course.

## Vertical slice cible

Le premier jalon jouable vise une course unique avec :

- un circuit fermé avec secteurs, limites et voie des stands ;
- trois modèles de voitures issus d'Automation ;
- douze à vingt voitures en piste ;
- des pilotes IA différenciés ;
- physique 2D crédible pour accélération, freinage, virage et adhérence ;
- trafic, dépassements, défense, erreurs et incidents simples ;
- pneus, carburant, arrêts aux stands et stratégie ;
- chronométrage, classement, règles de base et pénalités simples ;
- replay autonome avec navigation temporelle, événements et télémétrie.

Sont hors périmètre initial : championnat, économie, multijoueur, dégâts visuels avancés, météo complexe, voiture de sécurité complète, catégories multiples et apprentissage automatique des pilotes.

## Principes structurants

- Le coeur de simulation est indépendant de Unity.
- Les données Automation brutes sont conservées séparément du futur `VehicleDefinition`.
- Les contrats de données sont versionnés.
- Les unités internes utilisent le système international.
- Les définitions immuables, états dynamiques et événements restent séparés.
- L'IA est organisée en couches : stratégie, tactique, perception et contrôle.
- Le replay est hybride : métadonnées, images-clés, événements et télémétrie.
- Les prototypes de faisabilité restent jetables tant qu'une promotion explicite n'a pas été décidée.

## Phase active

La Phase 1 — faisabilité — est active. Elle doit réduire les risques avant tout code de production durable.

Ordre logique des expériences :

1. A — Extraction Automation.
2. B — Dynamique d'une voiture.
3. C — Tour autonome et circuit minimal.
4. E — Replay minimal.
5. D — Trafic et dépassement.
6. F — Charge et accélération.
7. G — Import UR2D2.

L'expérience A débloque B, car le modèle physique a besoin de données représentatives issues d'Automation.

## État repris de l'expérience A

Le smoke test Automation Exporter est réussi avec réserves non bloquantes.

Résultats validés :

- le SDK officiel compile en x64 avec Visual Studio / Build Tools 2022 et `PlatformToolset=v143` ;
- la DLL Automation LAP est chargée par Automation ;
- l'exporteur `Automation LAP - Smoke Test` apparaît et exécute `DoExport` ;
- `automation-lap-vehicle.json` est produit et validé ;
- l'UTF-8 est correct, y compris avec accents et caractères spéciaux ;
- les exports répétés sont identiques octet par octet hors évolution volontaire du contrat ;
- `exportedAtUtc` est maintenant injecté côté C++ dans le contrat `0.1.1` ;
- `automation-lap-field-inventory.json` est produit et validé ;
- l'inventaire contrôlé A3 final couvre `67 / 67` sondes sur le runtime Lua réel.

Réserves et contraintes :

- la version Automation n'est pas exposée par les chemins Lua testés ;
- le runtime Lua d'Automation ne fournit pas `pcall` ;
- les fonctions documentées sont détectées mais non appelées sans appel protégé ;
- certaines métadonnées doivent venir du pont C++ ou de la procédure d'exécution ;
- les fichiers issus d'Automation ne doivent être conservés publiquement qu'après vérification des droits de redistribution.

## Décision d'étape

L'expérience A peut avancer au-delà du smoke test. Les étapes A0 à A3 sont suffisamment validées pour préparer A4.

Le prochain objectif utile est de transformer l'inventaire contrôlé en export brut exploitable sur trois voitures contrastées, sans encore promouvoir le prototype vers du code de production.

Mise à jour A4 : les trois exports de voitures sont présents dans `C:\Users\jerem\Documents\Automation LAP Smoke Test`, les six JSON passent les validateurs, et chaque inventaire couvre `67 / 67` sondes. La documentation officielle `CarCalculator` et la confirmation UI sur l'AIXAM Coupe GTI ont permis de confirmer les unités principales. A4 est validée avec réserves : certains champs sont des sliders Automation ou des valeurs non affichées, mais cela ne bloque plus la suite.

Correction post-A4 : la vraie répartition de masse avant doit être sondée via `CarInfo.TrimInfo.Results.cg.WeightDistribution`. L'ancien chemin `CarInfo.TrimInfo.WeightDistributionFraction` est conservé comme slider Automation. Quatre sondes sont ajoutées sous `CarInfo.TrimInfo.Results.GraphData.BrakingVGrip` : `FrontBrakeForce`, `FrontBrakeGrip`, `RearBrakeForce`, `RearBrakeGrip`, avec axe et unités à déterminer.

Mise à jour A5 : cinq exports AIXAM Coupe GTI avec `0.1.8-a4-braking-vgrip-curves` sont valides. Après exclusion de `exportedAtUtc` et `lastAccessTime`, les empreintes sémantiques sont identiques sur les 5 exports, y compris après redémarrage du jeu. A5 est validée.

Mise à jour A6 : les trois exports `0.1.9-a6-graph-inventory` contiennent `automation-lap-graph-inventory.json`, valide et sans diagnostic. Les 10 graphes racine communs sont `AccelerationToTopSpeed`, `Braking`, `BrakingVGrip`, `BumpGraph`, `Downforce`, `Drag`, `GearboxGraph`, `GearingEff`, `HighSpeedSteering` et `LowSpeedSteering`. `BrakingVGrip` contient les quatre courbes `FrontBrakeForce`, `FrontBrakeGrip`, `RearBrakeForce`, `RearBrakeGrip`, plus `Speed` comme axe probable. A6 est validée.

Correction post-A6 : `CarInfo.TrimInfo.Results.cg.WeightDistribution` est conservé comme vraie répartition avant, mais son unité source est corrigée en pourcentage, avec fraction comme cible interne. L'axe `CarInfo.TrimInfo.Results.GraphData.BrakingVGrip.Speed` est ajouté à l'inventaire contrôlé.

Préparation A7 : la version source `0.1.12-a7-json-values-fix` ajoute `automation-lap-raw-graphs.json`. Ce fichier exporte les séries numériques directes de `AccelerationToTopSpeed`, `Braking` et `BrakingVGrip`, avec valeurs complètes, longueurs, min/max, rôle d'axe candidat et unités conservatrices `automation-graph` / `unknown`.

Diagnostic A7 `0.1.11` : les trois exports prouvent que les séries ciblées sont accessibles, avec longueurs/min/max cohérents et sans troncature, mais le champ `values` était absent à cause d'une exclusion trop large dans l'encodeur JSON Lua. Le payload `0.1.12-a7-json-values-fix` corrige cette sérialisation.

Mise à jour A7 : les trois exports `0.1.12-a7-json-values-fix` valident les quatre contrats. `automation-lap-raw-graphs.json` contient 24 séries ciblées par voiture, avec `values` complet, aucune troncature et aucune incohérence de longueur. A7 est validée.

Préparation A8 : le contrat `AutomationRawVehicleData` v0.1 est défini par `automation-raw-vehicle-data-v0.1.schema.json`. L'outil `build_raw_vehicle_data.py` assemble les quatre sorties Automation en `automation-lap-raw-vehicle-data.json`, et `validate_raw_vehicle_data.py` valide le document unifié. Les trois voitures locales ont été assemblées et validées dans `outputs/a8-raw-vehicle-data/`.

Décision licence A4 : `CC BY-NC-SA 4.0` est compatible avec la portée actuelle du projet, car l'usage prévu est privé et non lucratif. Les exports peuvent donc servir de fixtures privées de validation, avec attribution/licence conservées.

## Prochaine étape proposée

### Revue de clôture A

La prochaine étape utile est une revue de clôture de l'expérience A avant de passer à B :

- confirmer que `AutomationRawVehicleData` v0.1 est le bon format d'entrée pour B ;
- décider quelles conversions SI sont suffisamment sûres ;
- lister les unités encore inconnues ;
- choisir si l'assembleur Python reste un outil de fixtures ou devient un composant temporaire de pipeline ;
- ne promouvoir aucun prototype vers du code production sans décision explicite.

Le contrat A8 ne choisit pas encore le modèle physique final. Il fournit une base stable, traçable et validable pour l'expérience B.

Critères de sortie :

- la revue A conclut sur un verdict explicite ;
- les réserves restantes sont listées ;
- l'entrée de l'expérience B est nommée ;
- les fixtures privées utilisables par B sont identifiées ;
- la suite peut démarrer sans dépendre de nouveaux exports Automation.
