# Prototype Vehicle Dynamics

- **Expérience :** B — Dynamique d'une voiture
- **Statut :** B validée avec réserves
- **Ticket :** #4
- **Protocole :** [../../docs/feasibility/experiments/B-VEHICLE-DYNAMICS.md](../../docs/feasibility/experiments/B-VEHICLE-DYNAMICS.md)

Ce prototype vérifie si les exports Automation peuvent alimenter un modèle 2D simple pour une voiture seule. Les jalons initiaux utilisent A8, puis les jalons de direction et de transitions utilisent A9.

Le prototype doit privilégier les courbes déjà calculées par Automation pour l'accélération et le freinage, puis limiter le modèle physique aux états nécessaires à la suite du projet : vitesse, position, orientation, freinage, accélération et virage.

## Entrées prévues

- `outputs/a8-raw-vehicle-data/*/automation-lap-raw-vehicle-data.json`
- `outputs/a9-raw-vehicle-data/*/automation-lap-raw-vehicle-data.json`

## Résultats prévus

- validations de chargement ;
- mesures d'interpolation des courbes ;
- scénarios de stabilité au pas de temps ;
- comparaison inter-voitures ;
- liste des champs ou unités bloquants.

Les résultats devront être placés dans `prototypes/vehicle-dynamics/results/`.

## B-S01 - Chargement A8

Le premier jalon vérifie que les trois documents A8 locaux sont chargeables et conformes au contrat `AutomationRawVehicleData` v0.1.

```powershell
python prototypes\vehicle-dynamics\tools\run_b_s01_load_a8.py
```

Sorties attendues :

- `prototypes/vehicle-dynamics/results/B_S01_LOAD_A8_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s01_load_a8_summary.json`

Résultat courant : 3 documents valides sur 3, avec les graphes `AccelerationToTopSpeed`, `Braking` et `BrakingVGrip` présents pour chaque voiture.

## B-S02 - Accélération 0 à Vmax

Le second jalon construit des interpolateures sur le graphe Automation `AccelerationToTopSpeed`.

```powershell
python prototypes\vehicle-dynamics\tools\run_b_s02_acceleration_curve.py
```

Sorties attendues :

- `prototypes/vehicle-dynamics/results/B_S02_ACCELERATION_CURVE_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s02_acceleration_curve_summary.json`

Résultat courant : 3 courbes valides sur 3. Les repères 0-50, 0-100 et Vmax sont relus depuis `AccelerationToTopSpeed` par premier passage à la vitesse cible.

## B-S03 - Freinage

Le troisième jalon construit des interpolateures sur `Braking` et vérifie la cohérence de l'axe `BrakingVGrip.Speed`.

```powershell
python prototypes\vehicle-dynamics\tools\run_b_s03_braking_curve.py
```

Sorties attendues :

- `prototypes/vehicle-dynamics/results/B_S03_BRAKING_CURVE_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s03_braking_curve_summary.json`

Résultat courant : 3 courbes `Braking` valides sur 3. L'axe `BrakingVGrip.Speed` est identique à `Braking.Speed` pour chaque voiture.

## B-S04 - Virage à rayon constant

Le quatrième jalon estime des vitesses critiques sur rayons constants à partir d'un proxy temporaire de grip.

```powershell
python prototypes\vehicle-dynamics\tools\run_b_s04_constant_radius.py
```

Sorties attendues :

- `prototypes/vehicle-dynamics/results/B_S04_CONSTANT_RADIUS_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s04_constant_radius_summary.json`

Résultat courant : 3 voitures évaluées sur 3. Le scénario est reproductible, mais repose sur le proxy temporaire `FrontGripG + RearGripG` ; les graphes latéraux `LowSpeedSteering` et `HighSpeedSteering` ne sont pas encore exportés en valeurs brutes.

## B-S04 - Graphes de direction A9

Après A9, les graphes `LowSpeedSteering` et `HighSpeedSteering` sont analysables depuis `outputs/a9-raw-vehicle-data/`.

```powershell
python prototypes\vehicle-dynamics\tools\run_b_s04_steering_graphs.py
```

Sorties attendues :

- `prototypes/vehicle-dynamics/results/B_S04_STEERING_GRAPHS_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s04_steering_graphs_summary.json`

Résultat courant : les graphes A9 sont complets et utiles pour analyser l'enveloppe de direction, mais ne donnent pas directement une adhérence latérale brute ni une vitesse critique de rayon constant.

## B-S05 - Transitions throttle / frein / direction

Le cinquième jalon vérifie qu'un état dynamique minimal reste stable lorsque les commandes d'accélération, de freinage et de direction changent pendant un même scénario.

```powershell
python prototypes\vehicle-dynamics\tools\run_b_s05_transitions.py
```

Sorties attendues :

- `prototypes/vehicle-dynamics/results/B_S05_TRANSITIONS_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s05_transitions_summary.json`

Résultat courant : les trois voitures restent stables aux pas `1/30 s`, `1/60 s` et `1/120 s`. Le scénario utilise les pentes des courbes `AccelerationToTopSpeed.Speed/Time` et `Braking.Speed/Time`, puis les graphes `LowSpeedSteering` et `HighSpeedSteering` comme réponse de direction normalisée.

## B-S06 - Sensibilité inter-voitures

Le sixième jalon consolide les résultats B-S02 à B-S05 pour vérifier que le modèle garde des différences plausibles entre les trois voitures.

```powershell
python prototypes\vehicle-dynamics\tools\run_b_s06_vehicle_sensitivity.py
```

Sorties attendues :

- `prototypes/vehicle-dynamics/results/B_S06_VEHICLE_SENSITIVITY_RESULT.md`
- `prototypes/vehicle-dynamics/results/b_s06_vehicle_sensitivity_summary.json`

Résultat courant : les trois voitures restent nettement différenciées. B est validée avec réserves et peut alimenter C avec `1/60 s` comme pas candidat et `1/120 s` comme référence de vérification.
