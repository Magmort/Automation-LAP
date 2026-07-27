# Prototype Traffic

- **Expérience :** D - Trafic et dépassement
- **Statut :** D-S06 validé, expérience D validée avec réserves
- **Ticket :** #6
- **Protocole :** [../../docs/feasibility/experiments/D-TRAFFIC-OVERTAKING.md](../../docs/feasibility/experiments/D-TRAFFIC-OVERTAKING.md)

Ce prototype vérifie progressivement qu'un ensemble de voitures peut partager un `TrackDefinition` sans scripts de résultat.

## Entrées prévues

- `prototypes/autonomous-lap/fixtures/canonical_track.json`
- `prototypes/traffic/fixtures/d_s01_multicar_scene.json`
- `prototypes/traffic/fixtures/d_s02_longitudinal_follow_scene.json`
- `prototypes/traffic/fixtures/d_s03_overtake_candidate_scene.json`
- `prototypes/traffic/fixtures/d_s04_side_by_side_scene.json`
- `prototypes/traffic/fixtures/d_s05_rejoin_scene.json`
- résultats C-S06 pour le contrat `TrackDefinition` v0.1

## D-S01 - Perception des voisins

Le premier jalon place six voitures sur la piste canonique et calcule les voisins avant/arrière dans un corridor latéral.

```powershell
python prototypes\traffic\tools\run_d_s01_neighbor_perception.py
python prototypes\traffic\tools\render_d_s01_visualization.py
```

Sorties attendues :

- `prototypes/traffic/results/D_S01_NEIGHBOR_PERCEPTION_RESULT.md`
- `prototypes/traffic/results/d_s01_neighbor_perception_summary.json`
- `prototypes/traffic/results/D_S01_NEIGHBOR_PERCEPTION_VISUALIZATION.svg`

Résultat courant : 6 voitures projetées sans erreur, aucun hors-piste, 6 liens de voisinage détectés, et le wrap autour de la ligne de départ validé.

## D-S02 - Suivi longitudinal derrière voiture lente

Le second jalon place deux voitures dans le même corridor : un leader lent et un suiveur plus rapide. Le suiveur doit rattraper puis stabiliser son gap sans contact.

```powershell
python prototypes\traffic\tools\run_d_s02_longitudinal_follow.py
python prototypes\traffic\tools\render_d_s02_visualization.py
```

Sorties attendues :

- `prototypes/traffic/results/D_S02_LONGITUDINAL_FOLLOW_RESULT.md`
- `prototypes/traffic/results/d_s02_longitudinal_follow_summary.json`
- `prototypes/traffic/results/D_S02_LONGITUDINAL_FOLLOW_VISUALIZATION.svg`

Résultat courant : 90 s simulées au pas `1/120 s`, aucun contact, aucun immobilisme, gap minimal `17,50 m`, et stabilisation au gap cible `17,50 m`.

## D-S03 - Déclenchement de dépassement candidat

Le troisième jalon teste une décision statique : l'ego doit déclencher une intention de dépassement seulement s'il est bloqué par une voiture lente et si la ligne candidate est libre.

```powershell
python prototypes\traffic\tools\run_d_s03_overtake_candidate.py
python prototypes\traffic\tools\render_d_s03_visualization.py
```

Sorties attendues :

- `prototypes/traffic/results/D_S03_OVERTAKE_CANDIDATE_RESULT.md`
- `prototypes/traffic/results/d_s03_overtake_candidate_summary.json`
- `prototypes/traffic/results/D_S03_OVERTAKE_CANDIDATE_VISUALIZATION.svg`

Résultat courant : 4 cas conformes sur 4. Le dépassement est proposé uniquement dans le cas clair ; il est refusé si la ligne candidate est bloquée devant, bloquée derrière, ou si le besoin de dépasser n'est pas déclenché.

## D-S04 - Deux voitures côte à côte

Le quatrième jalon simule deux voitures côte à côte sur deux offsets latéraux imposés, avec mesure de la clearance latérale, du delta longitudinal et de la marge au bord de piste.

```powershell
python prototypes\traffic\tools\run_d_s04_side_by_side.py
python prototypes\traffic\tools\render_d_s04_visualization.py
```

Sorties attendues :

- `prototypes/traffic/results/D_S04_SIDE_BY_SIDE_RESULT.md`
- `prototypes/traffic/results/d_s04_side_by_side_summary.json`
- `prototypes/traffic/results/D_S04_SIDE_BY_SIDE_VISUALIZATION.svg`

Résultat courant : 45 s côte à côte, aucun contact, aucun hors-piste, clearance latérale minimale `0,50 m`, puis stabilisation à `1,70 m`.

## D-S05 - Réinsertion après écart

Le cinquième jalon simule une voiture ego déjà décalée latéralement qui revient dans le corridor cible entre deux voitures, uniquement quand les gaps avant et arrière respectent les seuils de sécurité.

```powershell
python prototypes\traffic\tools\run_d_s05_rejoin.py
python prototypes\traffic\tools\render_d_s05_visualization.py
```

Sorties attendues :

- `prototypes/traffic/results/D_S05_REJOIN_RESULT.md`
- `prototypes/traffic/results/d_s05_rejoin_summary.json`
- `prototypes/traffic/results/D_S05_REJOIN_VISUALIZATION.svg`

Résultat courant : réinsertion lancée à `0,49 s`, terminée à `3,47 s`, aucun contact, aucun hors-piste, gap avant minimal `32,15 m`, gap arrière minimal `29,24 m`, et stabilité dans le corridor cible `100 %` après completion.

## D-S06 - Synthèse statistique trafic

Le sixième jalon consolide les résultats D-S01 à D-S05 pour conclure l'expérience D.

```powershell
python prototypes\traffic\tools\run_d_s06_traffic_summary.py
python prototypes\traffic\tools\render_d_s06_visualization.py
```

Sorties attendues :

- `prototypes/traffic/results/D_S06_TRAFFIC_SUMMARY_RESULT.md`
- `prototypes/traffic/results/d_s06_traffic_summary.json`
- `prototypes/traffic/results/D_S06_TRAFFIC_SUMMARY_VISUALIZATION.svg`

Résultat courant : 5 scénarios conformes sur 5, 190 s dynamiques simulées, 0 contact consolidé, 0 hors-piste consolidé, 4 décisions conformes sur 4. L'expérience D est validée avec réserves.
