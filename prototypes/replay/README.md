# Prototype Replay

- **Expérience :** E - Replay minimal
- **Statut :** E-S06 validé avec réserves
- **Ticket :** #7
- **Protocole :** [../../docs/feasibility/experiments/E-REPLAY-MINIMAL.md](../../docs/feasibility/experiments/E-REPLAY-MINIMAL.md)

Ce prototype vérifie progressivement qu'une course enregistrée peut être relue, inspectée et parcourue sans relancer la simulation.

## Entrées prévues

- `prototypes/traffic/results/d_s05_rejoin_summary.json`
- `prototypes/autonomous-lap/fixtures/canonical_track.json`

## E-S01 - Contrat replay autonome

Le premier jalon génère un fichier replay JSON autonome depuis le scénario D-S05. Le fichier contient un en-tête versionné, les unités, un snapshot de piste, les véhicules, les frames, les événements et un index de navigation.

```powershell
python prototypes\replay\tools\run_e_s01_replay_contract.py
python prototypes\replay\tools\render_e_s01_visualization.py
```

Sorties attendues :

- `prototypes/replay/results/e_s01_minimal_replay.replay.json`
- `prototypes/replay/results/E_S01_REPLAY_CONTRACT_RESULT.md`
- `prototypes/replay/results/e_s01_replay_contract_summary.json`
- `prototypes/replay/results/E_S01_REPLAY_CONTRACT_VISUALIZATION.svg`

Résultat courant : replay autonome de `148756` octets, `55 s`, `221` frames, `3` véhicules, `3` événements, `0` erreur de structure, et `5` checks de seek exact/interpolé.

## E-S02 - Navigation temporelle avant/arrière

Le second jalon charge le replay autonome E-S01 et exécute un script de navigation couvrant seek, lecture avant, pause, seek arbitraire, lecture arrière et clamps aux bornes.

```powershell
python prototypes\replay\tools\run_e_s02_navigation.py
python prototypes\replay\tools\render_e_s02_visualization.py
```

Sorties attendues :

- `prototypes/replay/results/E_S02_NAVIGATION_RESULT.md`
- `prototypes/replay/results/e_s02_navigation_summary.json`
- `prototypes/replay/results/E_S02_NAVIGATION_VISUALIZATION.svg`

Résultat courant : `9` commandes exécutées, `36` samples de navigation, `2` lectures avant, `1` lecture arrière, `5` seeks, `1` pause, `14` samples interpolés, `3` clamps aux bornes, et `0` échec de monotonicité.

## E-S03 - Événements et saut vers événement

Le troisième jalon charge le replay autonome E-S01, vérifie l'index d'événements et saute sur chaque événement requis avec un contexte pré/post-roll.

```powershell
python prototypes\replay\tools\run_e_s03_event_jump.py
python prototypes\replay\tools\render_e_s03_visualization.py
```

Sorties attendues :

- `prototypes/replay/results/E_S03_EVENT_JUMP_RESULT.md`
- `prototypes/replay/results/e_s03_event_jump_summary.json`
- `prototypes/replay/results/E_S03_EVENT_JUMP_VISUALIZATION.svg`

Résultat courant : `3` événements requis trouvés sur `3`, `3` jumps exécutés, `2` jumps interpolés, `3` contextes pré/post-roll valides, `2` clamps attendus, et `0` erreur d'index événement.

## E-S04 - Taille et fréquence d'échantillonnage

Le quatrième jalon resample le replay autonome E-S01 avec plusieurs fréquences afin de mesurer le coût brut du format JSON avant compression ou format binaire.

```powershell
python prototypes\replay\tools\run_e_s04_sampling_size.py
python prototypes\replay\tools\render_e_s04_visualization.py
```

Sorties attendues :

- `prototypes/replay/results/E_S04_SAMPLING_SIZE_RESULT.md`
- `prototypes/replay/results/e_s04_sampling_size_summary.json`
- `prototypes/replay/results/E_S04_SAMPLING_SIZE_VISUALIZATION.svg`
- `prototypes/replay/results/e_s04_variants/`

Résultat courant : `5` profils mesurés de `1` à `20 Hz`, `56` à `1101` frames, `41831` à `719882` octets, `760.6` à `13088.8` octets/s, taille monotone avec la fréquence, couverture événementielle conforme et `0` erreur de validation.

## E-S05 - Compatibilité de version

Le cinquième jalon génère des replays valides et invalides depuis E-S01, puis vérifie que le lecteur accepte seulement `AutomationLapReplay` en `schemaVersion` `0.1.0` et refuse les cas incompatibles avec un code d'erreur explicite.

```powershell
python prototypes\replay\tools\run_e_s05_version_compatibility.py
python prototypes\replay\tools\render_e_s05_visualization.py
```

Sorties attendues :

- `prototypes/replay/results/E_S05_VERSION_COMPATIBILITY_RESULT.md`
- `prototypes/replay/results/e_s05_version_compatibility_summary.json`
- `prototypes/replay/results/E_S05_VERSION_COMPATIBILITY_VISUALIZATION.svg`
- `prototypes/replay/results/e_s05_compatibility_cases/`

Résultat courant : `10` cas testés, `1` replay courant accepté, `9` cas incompatibles refusés, `10 / 10` attentes respectées, et `0` mismatch de code d'erreur.

## E-S06 - Synthèse replay minimal

Le sixième jalon agrège E-S01 à E-S05 et conclut sur la viabilité du replay minimal comme contrat candidat pour les tests de charge et le futur ADR-0002.

```powershell
python prototypes\replay\tools\run_e_s06_replay_summary.py
python prototypes\replay\tools\render_e_s06_visualization.py
```

Sorties attendues :

- `prototypes/replay/results/E_S06_REPLAY_SUMMARY_RESULT.md`
- `prototypes/replay/results/e_s06_replay_summary.json`
- `prototypes/replay/results/E_S06_REPLAY_SUMMARY_VISUALIZATION.svg`

Résultat courant : `5 / 5` scénarios E validés, décision `validée avec réserves`, confiance `moyen à bon`, contrat candidat `AutomationLapReplay` JSON v0.1, télémétrie de référence `4 Hz`, images-clés `1 s`.
