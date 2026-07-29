# Prototype Performance

- **Expérience :** F - Charge et accélération
- **Statut :** Expérience F validée avec réserves
- **Ticket :** #8
- **Protocole :** [../../docs/feasibility/experiments/F-PERFORMANCE-LOAD.md](../../docs/feasibility/experiments/F-PERFORMANCE-LOAD.md)

Ce prototype mesure progressivement la capacité de la boucle représentative B à E à fonctionner en temps réel et en accéléré, hors rendu Unity.

## Entrées prévues

- `prototypes/replay/results/e_s01_minimal_replay.replay.json`
- `prototypes/performance/fixtures/f_s01_benchmark_profiles.json`
- `prototypes/performance/fixtures/f_s02_realtime_profiles.json`
- `prototypes/performance/fixtures/f_s03_accelerated_profiles.json`
- `prototypes/performance/fixtures/f_s04_replay_cost_profiles.json`

## F-S01 - Harnais de benchmark sans rendu

Le premier jalon crée un banc de mesure reproductible. Il duplique déterministiquement les états du replay E-S01 pour `1`, `12`, `20` et `40` voitures, puis mesure une boucle sans rendu incluant expansion d'états, perception simple, décision légère et sérialisation replay.

```powershell
python prototypes\performance\tools\run_f_s01_benchmark_harness.py
python prototypes\performance\tools\render_f_s01_visualization.py
```

Sorties attendues :

- `prototypes/performance/results/F_S01_BENCHMARK_HARNESS_RESULT.md`
- `prototypes/performance/results/f_s01_benchmark_harness_summary.json`
- `prototypes/performance/results/F_S01_BENCHMARK_HARNESS_VISUALIZATION.svg`

Résultat courant : harnais opérationnel, `4` profils mesurés, `5` répétitions par profil, `0` erreur de benchmark. Le profil `40` voitures traite `55 s` simulées en `180,00 ms` de temps mural moyen, soit `307,2x` le temps réel dans cette charge hors rendu simplifiée.

## F-S02 - Charge cible temps réel

Le second jalon exécute une boucle représentative à `60 Hz` avec un budget de `16,667 ms` par tick. Les profils requis sont `12` et `20` voitures ; le profil `40` voitures sert de stress test non bloquant. La boucle mesure les temps par système, les deadline misses, le débit véhicules-ticks et le débit replay compact.

```powershell
python prototypes\performance\tools\run_f_s02_realtime_load.py
python prototypes\performance\tools\render_f_s02_visualization.py
```

Sorties attendues :

- `prototypes/performance/results/F_S02_REALTIME_LOAD_RESULT.md`
- `prototypes/performance/results/f_s02_realtime_load_summary.json`
- `prototypes/performance/results/F_S02_REALTIME_LOAD_VISUALIZATION.svg`

Résultat courant : profils requis validés avec `0` deadline miss sur `3` répétitions. Le profil `20` voitures atteint un tick p95 moyen de `0,3744 ms`, soit `2,25 %` du budget 60 Hz, avec un facteur temps réel moyen de `73,4x`.

## F-S03 - Simulation accélérée sans rendu

Le troisième jalon mesure le débit soutenu sans rendu sur `180 s` simulées. Il conserve le tick logique `60 Hz`, mais juge le résultat sur le facteur d'accélération moyen et la stabilité du p95 plutôt que sur une deadline stricte par tick.

```powershell
python prototypes\performance\tools\run_f_s03_accelerated_no_render.py
python prototypes\performance\tools\render_f_s03_visualization.py
```

Sorties attendues :

- `prototypes/performance/results/F_S03_ACCELERATED_NO_RENDER_RESULT.md`
- `prototypes/performance/results/f_s03_accelerated_no_render_summary.json`
- `prototypes/performance/results/F_S03_ACCELERATED_NO_RENDER_VISUALIZATION.svg`

Résultat courant : profils requis validés. Le profil `20` voitures simule `180 s` en `4955,77 ms` de temps mural moyen, soit `36,3x` le temps réel, avec un tick p95 moyen de `0,7666 ms`.

## F-S04 - Coût replay détaillé

Le quatrième jalon isole la capture replay compacte en mémoire. Il compare un baseline sans replay aux fréquences `1`, `2`, `4`, `10` et `20 Hz` sur `20` voitures, puis ajoute un stress `40` voitures sur `off`, `4 Hz` et `20 Hz`.

```powershell
python prototypes\performance\tools\run_f_s04_replay_cost.py
python prototypes\performance\tools\render_f_s04_visualization.py
```

Sorties attendues :

- `prototypes/performance/results/F_S04_REPLAY_COST_RESULT.md`
- `prototypes/performance/results/f_s04_replay_cost_summary.json`
- `prototypes/performance/results/F_S04_REPLAY_COST_VISUALIZATION.svg`

Résultat courant : référence `20` voitures à `4 Hz` validée avec une part replay de `6,0 %` du tick moyen, `0,0284 ms` de replay moyen et `5021` octets/s. Le `20 Hz` monte à `23,1 %`, ce qui confirme que `4 Hz` reste le meilleur candidat compact pour la suite.

## F-S05 - Synthèse charge et accélération

Le cinquième jalon consolide les sorties F-S01 à F-S04 et produit la décision de clôture.

```powershell
python prototypes\performance\tools\run_f_s05_performance_summary.py
python prototypes\performance\tools\render_f_s05_visualization.py
```

Sorties attendues :

- `prototypes/performance/results/F_S05_PERFORMANCE_SUMMARY_RESULT.md`
- `prototypes/performance/results/f_s05_performance_summary.json`
- `prototypes/performance/results/F_S05_PERFORMANCE_SUMMARY_VISUALIZATION.svg`

Résultat courant : expérience F validée avec réserves. Paramètres candidats : `12` à `20` voitures, tick `60 Hz`, replay compact `4 Hz`, stress suivi `40` voitures.
