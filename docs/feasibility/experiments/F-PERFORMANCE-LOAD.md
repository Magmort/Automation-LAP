# Expérience F - Charge et accélération

- **Statut :** validée avec réserves
- **Ticket :** #8
- **Responsable :** à renseigner
- **Date de début :** 2026-07-28
- **Date de conclusion :** 2026-07-28
- **Version du protocole :** 0.1
- **Dépendance d'entrée :** expériences B à E validées avec réserves, replay E-S06 disponible
- **Dépendance produite :** enveloppe de performance candidate pour le vertical slice

## 1. Question testée

Le modèle envisagé permet-il de simuler le nombre cible de voitures en temps réel, puis plus vite que le temps réel sans rendu, tout en enregistrant un replay exploitable ?

## 2. Hypothèse

Les expériences B à E ont produit une boucle représentative : dynamique 2D simplifiée, piste canonique, trafic nominal et replay autonome.

L'hypothèse est qu'une boucle sans rendu peut :

- tenir au moins `12` à `20` voitures en temps réel ;
- dépasser significativement le temps réel sans rendu ;
- identifier le coût relatif de la simulation, de la perception et de l'écriture replay ;
- mesurer la mémoire et les allocations du prototype ;
- fournir une base avant toute optimisation.

## 3. Hors périmètre

- performance Unity avec rendu réel ;
- profilage GPU ;
- optimisation de production ;
- multithreading définitif ;
- réseau, audio, caméra et UI ;
- format binaire replay définitif.

## 4. Environnement

| Élément | Version ou valeur |
|---|---|
| Système d'exploitation | Windows, machine locale |
| Matériel pertinent | mesuré par F-S01 |
| Runtime / SDK | Python embarqué Codex pour prototype hors Unity |
| Version du prototype | `prototypes/performance/` |
| Entrées utilisées | replay E-S01, synthèse E-S06 |
| Graine aléatoire | aucune pour F-S01 à F-S04 |

## 5. Protocole reproductible

1. Charger le replay autonome E-S01.
2. Charger les profils de charge F.
3. Dupliquer déterministiquement les états véhicules pour `1`, `12`, `20` et `40` voitures.
4. Exécuter une boucle sans rendu : expansion d'états, perception simple, décision légère, sérialisation replay.
5. Mesurer temps mural, temps CPU, facteur temps réel, débit de frames, mémoire allouée et taille sérialisée.
6. Produire un rapport JSON, un rapport Markdown et une visualisation SVG.

## 6. Scénarios

| Identifiant | Description | Entrées | Répétitions |
|---|---|---|---:|
| F-S01 | Harnais de benchmark sans rendu | replay E-S01, profils 1/12/20/40 voitures | 5 répétitions, validé avec réserves |
| F-S02 | Charge cible temps réel | F-S01, boucle représentative 60 Hz | 3 répétitions, validé avec réserves |
| F-S03 | Simulation accélérée sans rendu | F-S02, profils 12/20/40 voitures | 3 répétitions, validé avec réserves |
| F-S04 | Coût replay détaillé | replay E, fréquences E-S04 | 3 répétitions, validé avec réserves |
| F-S05 | Synthèse charge et accélération | F-S01 à F-S04 | validé avec réserves |

## 7. Métriques

| Métrique | Unité | Méthode de collecte | Seuil ou attente |
|---|---|---|---|
| Voitures | nombre | profil F | 1, 12, 20, 40 |
| Durée simulée | s | timeline replay | 55 s pour F-S01 et F-S02, 180 s pour F-S03 |
| Temps mural | ms | `perf_counter()` | mesuré |
| Temps CPU | ms | `process_time()` | mesuré |
| Facteur temps réel | x | durée simulée / temps mural | > 1 en prototype sans rendu |
| Budget par tick | ms | `1000 / 60 Hz` | 16,667 ms pour F-S02 |
| Tick p95 | ms | distribution des ticks F-S02 | <= 50 % du budget pour les profils requis |
| Deadline miss | nombre | tick > budget 60 Hz | 0 pour les profils requis |
| Facteur d'accélération | x | durée simulée / temps mural sans rendu | >= 20x pour les profils requis F-S03 |
| Coût par système | part du tick moyen | timings instrumentés | systèmes dominants identifiés |
| Part replay | part du tick moyen | timing `replay` / timing `tick` | <= 12 % pour la référence 20 voitures à 4 Hz |
| Débit replay | octets/s | sérialisation compacte en mémoire | mesuré par fréquence |
| Frames traitées | nombre | boucle F-S01 | conforme replay source |
| Voitures-frames | nombre | frames x voitures | augmente avec la charge |
| Débit | frames/s et voitures-frames/s | mesures F-S01 | mesuré |
| Pic mémoire tracé | octets | `tracemalloc` | mesuré |
| Taille replay sérialisée | octets | sérialisation JSON compacte | mesurée |
| Erreurs de benchmark | nombre | validation F-S01 | 0 |

## 8. Critères de réussite et d'échec

### Réussite

- [x] le harnais F-S01 mesure les profils `1`, `12`, `20` et `40` voitures ;
- [x] la boucle F-S02 tient les profils requis `12` et `20` voitures à `60 Hz` ;
- [x] la boucle F-S03 dépasse significativement le temps réel sans rendu sur `12` et `20` voitures ;
- [x] F-S04 isole le coût replay sur les fréquences `1`, `2`, `4`, `10` et `20 Hz` ;
- [x] F-S05 consolide les paramètres candidats et les risques résiduels ;
- [x] les métriques temps, débit, mémoire et sérialisation sont produites ;
- [x] les résultats sont reproductibles sans rendu ;
- [x] un rendu visuel complète la validation.

### Échec ou révision obligatoire

- [ ] le harnais ne peut pas charger les résultats E ;
- [ ] les profils ne couvrent pas la cible 12 à 20 voitures ;
- [ ] les mesures ne distinguent pas temps simulé, temps mural et débit ;
- [ ] la sérialisation replay n'est pas mesurée.

## 9. Résultats

### Données brutes

- `prototypes/performance/results/F_S01_BENCHMARK_HARNESS_RESULT.md`
- `prototypes/performance/results/f_s01_benchmark_harness_summary.json`
- `prototypes/performance/results/F_S01_BENCHMARK_HARNESS_VISUALIZATION.svg`
- `prototypes/performance/results/F_S02_REALTIME_LOAD_RESULT.md`
- `prototypes/performance/results/f_s02_realtime_load_summary.json`
- `prototypes/performance/results/F_S02_REALTIME_LOAD_VISUALIZATION.svg`
- `prototypes/performance/results/F_S03_ACCELERATED_NO_RENDER_RESULT.md`
- `prototypes/performance/results/f_s03_accelerated_no_render_summary.json`
- `prototypes/performance/results/F_S03_ACCELERATED_NO_RENDER_VISUALIZATION.svg`
- `prototypes/performance/results/F_S04_REPLAY_COST_RESULT.md`
- `prototypes/performance/results/f_s04_replay_cost_summary.json`
- `prototypes/performance/results/F_S04_REPLAY_COST_VISUALIZATION.svg`
- `prototypes/performance/results/F_S05_PERFORMANCE_SUMMARY_RESULT.md`
- `prototypes/performance/results/f_s05_performance_summary.json`
- `prototypes/performance/results/F_S05_PERFORMANCE_SUMMARY_VISUALIZATION.svg`

### Synthèse

| Scénario | Résultat | Variance | Observation |
|---|---:|---:|---|
| F-S01 | 4 profils mesurés | 5 répétitions | 1, 12, 20 et 40 voitures, 0 erreur, facteur temps réel moyen min 307,2x |
| F-S02 | profils requis validés | 3 répétitions | 12 et 20 voitures à 60 Hz, 0 deadline miss, p95 max requis 0,3744 ms |
| F-S03 | accélération sans rendu validée | 3 répétitions | 180 s simulées, facteur requis min 36,3x, tick p95 max requis 0,7666 ms |
| F-S04 | coût replay détaillé validé | 3 répétitions | référence 20 voitures à 4 Hz : 6,0 % du tick, 5021 octets/s |
| F-S05 | synthèse validée avec réserves | F-S01 à F-S04 | cible 12-20 voitures, tick 60 Hz, replay compact 4 Hz |

## 10. Analyse

F-S01 pose un banc de mesure et non un verdict final. Le prototype duplique les états du replay E-S01 pour produire des charges de `1`, `12`, `20` et `40` voitures, puis exécute une boucle déterministe sans rendu.

La charge inclut une perception de voisinage simple, une décision longitudinale légère et une sérialisation JSON compacte. Cette mesure donne une première enveloppe, complétée par F-S02 et F-S03 ; F-S04 isole ensuite plus finement le coût replay compact.

Sur la machine locale Windows 11 avec Python `3.12.13` et `32` CPU logiques, les `5` répétitions par profil donnent :

| Voitures | Wall moyen | Facteur temps réel moyen | Véhicules-frames/s moyen | Replay bytes/s |
|---:|---:|---:|---:|---:|
| 1 | `7,96 ms` | `6916,3x` | `27791` | `413` |
| 12 | `56,95 ms` | `970,7x` | `46803` | `3730` |
| 20 | `80,86 ms` | `681,4x` | `54763` | `6105` |
| 40 | `180,00 ms` | `307,2x` | `49374` | `12077` |

La baisse du facteur temps réel avec la charge est attendue. Le débit véhicules-frames reste du même ordre entre `12`, `20` et `40` voitures, ce qui indique que le harnais mesure bien une charge croissante mais encore très légère comparée au futur runtime.

F-S02 transforme ce harnais en boucle à budget fixe `60 Hz`. Chaque tick a un budget de `16,667 ms`; les profils requis `12` et `20` voitures sont exécutés trois fois sur `55 s` simulées. Le profil `40` voitures reste un stress test non bloquant.

| Profil | Voitures | Wall moyen | Facteur temps réel moyen | Tick p95 moyen | Ratio p95/budget | Deadline misses | Replay bytes/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| target_12 | 12 | `507,13 ms` | `108,6x` | `0,2433 ms` | `0,0146` | `0` | `3042` |
| target_20 | 20 | `749,78 ms` | `73,4x` | `0,3744 ms` | `0,0225` | `0` | `5021` |
| stress_40 | 40 | `1423,43 ms` | `38,6x` | `0,7124 ms` | `0,0427` | `0` | `9976` |

La charge cible `12` à `20` voitures est donc tenue avec une marge confortable dans cette boucle représentative hors rendu. Les temps par système montrent que la décision et l'entrée/interpolation dominent encore le coût mesuré, mais restent très loin du budget de tick.

F-S03 allonge l'horizon à `180 s` simulées et retire toute contrainte de rendu. Le seuil de validation demande au moins `20x` le temps réel pour les profils requis, un tick p95 moyen inférieur à `4 ms` et une variance de tick moyen inférieure à `1 ms`.

| Profil | Voitures | Wall moyen | Facteur d'accélération moyen | Tick moyen | Tick p95 moyen | Véhicules-ticks/s | Système dominant |
|---|---:|---:|---:|---:|---:|---:|---|
| target_12_accel | 12 | `2632,14 ms` | `75,0x` | `0,2413 ms` | `0,4538 ms` | `53981` | input `39,9 %` |
| target_20_accel | 20 | `4955,77 ms` | `36,3x` | `0,4556 ms` | `0,7666 ms` | `43598` | input `38,5 %` |
| stress_40_accel | 40 | `9157,25 ms` | `19,7x` | `0,8447 ms` | `1,4452 ms` | `47224` | input `38,7 %` |

Les profils requis dépassent donc largement le temps réel dans ce prototype hors rendu. Les pics maximum isolés restent visibles sur certaines répétitions, surtout sur les runs longs sous Windows/Python, mais ils ne changent pas le verdict F-S03 car l'objectif porte sur le débit accéléré soutenu et non sur une deadline stricte par tick.

F-S04 isole la capture replay en comparant un baseline sans replay aux fréquences `1`, `2`, `4`, `10` et `20 Hz` sur `20` voitures, puis un stress `40` voitures sur `off`, `4 Hz` et `20 Hz`. Le profil de référence reste `20` voitures à `4 Hz`, cohérent avec la fréquence candidate E-S04.

| Voitures | Hz | Tick moyen | Replay moyen | Part replay | Débit replay | Octets/sample |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | off | `0,2135 ms` | `0,0006 ms` | `0,3 %` | `0` | `0` |
| 20 | 1 | `0,4076 ms` | `0,0078 ms` | `1,9 %` | `1254` | `1254` |
| 20 | 2 | `0,4564 ms` | `0,0153 ms` | `3,4 %` | `2509` | `1255` |
| 20 | 4 | `0,4746 ms` | `0,0284 ms` | `6,0 %` | `5021` | `1255` |
| 20 | 10 | `0,5053 ms` | `0,0664 ms` | `13,1 %` | `12547` | `1255` |
| 20 | 20 | `0,5808 ms` | `0,1342 ms` | `23,1 %` | `25104` | `1255` |
| 40 | 4 | `0,8715 ms` | `0,0517 ms` | `5,9 %` | `9976` | `2494` |
| 40 | 20 | `1,0687 ms` | `0,2504 ms` | `23,4 %` | `49879` | `2494` |

La référence `4 Hz` reste sous le seuil de `12 %` du tick moyen. Le débit sérialisé augmente linéairement avec la fréquence et le nombre de voitures ; l'overhead mural est conservé comme indicateur mais n'est pas utilisé comme critère, car il est fortement perturbé par l'ordre d'exécution et le scheduling Python/Windows.

F-S05 consolide les jalons précédents et clôt l'expérience. Les quatre preuves techniques sont positives : la charge cible tient le temps réel, la boucle sans rendu dépasse nettement le temps réel, le replay compact `4 Hz` reste peu coûteux, et les stress `40` voitures donnent une marge indicative utile pour le vertical slice.

Les paramètres candidats retenus sont donc :

- cible de course : `12` à `20` voitures ;
- stress de suivi : `40` voitures ;
- tick logique : `60 Hz` ;
- replay compact : `4 Hz` ;
- `20 Hz` conservé comme option détaillée coûteuse, mesurée à `23,1 %` du tick sur `20` voitures.

## 11. Limites

- F-S01 à F-S05 sont des benchmarks Python hors Unity, pas le runtime final.
- Les voitures supplémentaires sont dupliquées depuis E-S01, pas simulées avec des comportements indépendants.
- La boucle mesure une charge représentative volontairement simple.
- Les allocations mesurées par `tracemalloc` ne couvrent pas toute la mémoire native.
- Le résultat dépend de la machine locale et doit être conservé comme point de référence, pas comme garantie produit.
- Le temps CPU Windows est peu précis sur des répétitions courtes ; le temps mural et les distributions de tick restent les métriques principales.
- F-S04 mesure une sérialisation compacte en mémoire, pas une écriture disque continue ni un format binaire final.

## 12. Conclusion

### Décision

> Validée avec réserves.

### Niveau de confiance

> Moyen pour la charge, l'accélération hors rendu et le coût replay compact ; faible à moyen pour la performance finale dans Unity.

## 13. Conséquences

### Paramètres retenus

- profils de charge initiaux : `1`, `12`, `20`, `40` voitures ;
- durée F-S01 : `55 s` simulées ;
- répétitions F-S01 : `5` ;
- entrée de référence : replay E-S01 `AutomationLapReplay` JSON v0.1 ;
- profil 40 voitures F-S01 : `180,00 ms` de temps mural moyen, facteur temps réel moyen `307,2x` ;
- fréquence F-S02 : `60 Hz`, budget de tick `16,667 ms` ;
- profils requis F-S02 : `12` et `20` voitures, `3` répétitions, `0` deadline miss ;
- profil 20 voitures F-S02 : tick p95 moyen `0,3744 ms`, facteur temps réel moyen `73,4x` ;
- durée F-S03 : `180 s` simulées ;
- profils requis F-S03 : `12` et `20` voitures, facteur d'accélération moyen minimal `36,3x` ;
- profil 40 voitures F-S03 : facteur d'accélération moyen `19,7x`, non bloquant ;
- fréquence replay candidate : `4 Hz` ;
- profil replay de référence F-S04 : `20` voitures à `4 Hz`, part replay `6,0 %`, débit `5021` octets/s ;
- profil replay haut F-S04 : `20` voitures à `20 Hz`, part replay `23,1 %`, débit `25104` octets/s.

### Risques résiduels

- coût Unity/rendu non mesuré ;
- coût de simulation finale non mesuré ;
- scénarios denses non encore réalistes ;
- optimisation replay binaire et écriture disque continue non traitées.

### Documents affectés

- plan de faisabilité ;
- tableau de bord Phase 1 ;
- rapport consolidé ;
- README des prototypes.

### Travaux suivants

- conserver les profils `1`, `12`, `20`, `40` comme base commune ;
- confirmer ces mesures dans le runtime Unity réel pendant le vertical slice ;
- traiter ultérieurement le format replay binaire et l'écriture disque continue.
