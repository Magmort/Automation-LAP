# Expérience D - Trafic et dépassement

- **Statut :** validée avec réserves
- **Ticket :** #6
- **Responsable :** à renseigner
- **Date de début :** 2026-07-27
- **Date de conclusion :** 2026-07-27
- **Version du protocole :** 0.1
- **Dépendance d'entrée :** expériences B et C validées avec réserves, `TrackDefinition` v0.1 consolidé
- **Dépendance utile mais non bloquante :** expérience E pour l'analyse replay des interactions longues
- **Dépendance produite :** scénarios statistiques de trafic pour F et pour la future IA de course

## 1. Question testée

Plusieurs voitures peuvent-elles partager la piste et produire des interactions crédibles, réglables et mesurables sans collisions constantes, immobilisme collectif ou scripts de résultat ?

## 2. Hypothèse

L'expérience C fournit un repère curviligne stable sur la piste : progression, latéralité, largeur disponible, sorties de piste et suivi de trajectoire.

L'hypothèse est qu'un prototype peut :

- représenter plusieurs voitures sur le même `TrackDefinition` ;
- détecter les voisins avant/arrière et adjacents à partir de la progression et du décalage latéral ;
- calculer des écarts, vitesses relatives et temps de rattrapage ;
- simuler un suivi longitudinal simple derrière une voiture plus lente ;
- déclencher des décisions candidates de dépassement sans script par virage ;
- mesurer contacts, blocages, dépassements et retours en ligne.

## 3. Hors périmètre

- replay complet, traité par E ;
- performance à grande échelle, traitée par F ;
- collisions physiques détaillées ;
- stratégie de course complète ;
- règles sportives, drapeaux, stands et pénalités ;
- modèle pneu détaillé ou vraie séparation sous-virage/survirage.

## 4. Environnement

| Élément | Version ou valeur |
|---|---|
| Système d'exploitation | Windows, machine locale |
| Matériel pertinent | non significatif pour D-S01 à D-S05 |
| Runtime / SDK | Python embarqué Codex pour prototype hors Unity |
| Version du prototype | `prototypes/traffic/` |
| Entrées utilisées | `TrackDefinition` C-S06, fixtures D-S01 à D-S05 |
| Graine aléatoire | aucune pour D-S01 à D-S05 |

## 5. Protocole reproductible

1. Charger la piste canonique `TrackDefinition` v0.1.
2. Charger une scène multi-voitures déterministe.
3. Projeter chaque voiture sur la distance curviligne de la piste.
4. Calculer les voisins avant/arrière dans un corridor latéral paramétré.
5. Mesurer gaps, vitesses relatives, temps de rattrapage, hors-piste et incohérences.
6. Produire un rapport JSON, un rapport Markdown et une visualisation SVG.

## 6. Scénarios

| Identifiant | Description | Entrées | Répétitions |
|---|---|---|---:|
| D-S01 | Perception des voisins sur piste | piste C, 6 voitures statiques | 1, validée |
| D-S02 | Suivi longitudinal derrière voiture lente | piste C, 2 voitures | 90 s, validée avec réserves |
| D-S03 | Déclenchement de dépassement candidat | piste C, 2 à 3 voitures | 4 cas, validée avec réserves |
| D-S04 | Deux voitures côte à côte | piste C, 2 voitures | 45 s, validée avec réserves |
| D-S05 | Réinsertion après écart | piste C, 3 voitures | 55 s, validée avec réserves |
| D-S06 | Synthèse statistique trafic | résultats D-S01 à D-S05 | validée |

## 7. Métriques

| Métrique | Unité | Méthode de collecte | Seuil ou attente |
|---|---|---|---|
| Erreurs de projection | m | projection sur `TrackDefinition` | proche de 0 sur fixtures |
| Voisins détectés | nombre | perception avant/arrière | conforme aux attendus |
| Gap longitudinal | m | delta curviligne modulo longueur piste | positif et documenté |
| Séparation latérale | m | différence d'offset projeté | corridor paramétrable |
| Temps de rattrapage | s | gap / vitesse relative positive | fini quand fermeture |
| Décision de dépassement | booléen | D-S03 | conforme aux attendus |
| Blockers de ligne candidate | nombre | D-S03 | détectés avant/arrière |
| Clearance latérale | m | D-S04 | positive, stabilisée |
| Clearance bord de piste | m | D-S04 | marge minimale conservée |
| Gap de réinsertion | m | D-S05 | avant/arrière au-dessus des seuils |
| Temps de réinsertion | s | D-S05 | fini et documenté |
| Hors-piste | nombre | limite latérale C | 0 en scènes nominales |
| Contacts | nombre | à partir de D-S02+ | mesuré |
| Immobilisme | s ou ticks | vitesse sous seuil | mesuré |
| Dépassements | nombre | inversion d'ordre curviligne | mesuré |

## 8. Critères de réussite et d'échec

### Réussite

- [x] plusieurs voitures peuvent être placées sur `TrackDefinition` ;
- [x] les voisins avant/arrière sont détectés de manière déterministe ;
- [x] les gaps et temps de rattrapage sont mesurables ;
- [x] une voiture peut suivre une voiture plus lente sans contact constant ;
- [x] un dépassement candidat peut être déclenché sans script de résultat ;
- [x] les contacts et blocages sont mesurés.

### Échec ou révision obligatoire

- [ ] la perception dépend de coordonnées monde ambiguës plutôt que de la progression piste ;
- [ ] le wrap de ligne de départ produit des voisins incohérents ;
- [ ] les changements de ligne nécessitent des scripts par virage ;
- [ ] les voitures se bloquent ou se percutent sans métrique exploitable.

## 9. Résultats

### Données brutes

- `prototypes/traffic/results/D_S01_NEIGHBOR_PERCEPTION_RESULT.md`
- `prototypes/traffic/results/d_s01_neighbor_perception_summary.json`
- `prototypes/traffic/results/D_S01_NEIGHBOR_PERCEPTION_VISUALIZATION.svg`
- `prototypes/traffic/results/D_S02_LONGITUDINAL_FOLLOW_RESULT.md`
- `prototypes/traffic/results/d_s02_longitudinal_follow_summary.json`
- `prototypes/traffic/results/D_S02_LONGITUDINAL_FOLLOW_VISUALIZATION.svg`
- `prototypes/traffic/results/D_S03_OVERTAKE_CANDIDATE_RESULT.md`
- `prototypes/traffic/results/d_s03_overtake_candidate_summary.json`
- `prototypes/traffic/results/D_S03_OVERTAKE_CANDIDATE_VISUALIZATION.svg`
- `prototypes/traffic/results/D_S04_SIDE_BY_SIDE_RESULT.md`
- `prototypes/traffic/results/d_s04_side_by_side_summary.json`
- `prototypes/traffic/results/D_S04_SIDE_BY_SIDE_VISUALIZATION.svg`
- `prototypes/traffic/results/D_S05_REJOIN_RESULT.md`
- `prototypes/traffic/results/d_s05_rejoin_summary.json`
- `prototypes/traffic/results/D_S05_REJOIN_VISUALIZATION.svg`
- `prototypes/traffic/results/D_S06_TRAFFIC_SUMMARY_RESULT.md`
- `prototypes/traffic/results/d_s06_traffic_summary.json`
- `prototypes/traffic/results/D_S06_TRAFFIC_SUMMARY_VISUALIZATION.svg`

### Synthèse

| Scénario | Résultat | Variance | Observation |
|---|---:|---:|---|
| D-S01 | 6 voitures projetées / 6 | aucune | voisins avant/arrière conformes, wrap de départ validé |
| D-S02 | 90 s sans contact | aucune | le suiveur se stabilise au gap cible derrière le leader lent |
| D-S03 | 4 cas conformes / 4 | aucune | dépassement déclenché seulement quand la ligne candidate est libre |
| D-S04 | 45 s côte à côte | aucune | séparation latérale stabilisée sans contact ni hors-piste |
| D-S05 | 55 s avec réinsertion | aucune | retour dans le corridor cible entre deux voitures sans contact ni hors-piste |
| D-S06 | 5 scénarios conformes / 5 | aucune | conclusion D validée avec réserves |

## 10. Analyse

D-S01 utilise la piste canonique de C et une scène statique de six voitures. Chaque voiture est définie par une progression curviligne, un offset latéral, une vitesse et un gabarit.

Au résultat, les six voitures sont projetées sans erreur, aucune n'est hors piste et les six liens de voisinage attendus sont détectés. Le cas `yellow -> red` valide explicitement le wrap autour de la ligne de départ. Le cas `green` reste isolé car son offset latéral le place hors du corridor de perception, ce qui confirme que la perception n'est pas seulement un tri longitudinal.

D-S02 utilise deux voitures dans le même corridor. Le leader roule à `42 km/h`, tandis que le suiveur démarre plus vite et vise `70 km/h` librement. La loi de suivi réduit la cible du suiveur quand le gap mesuré devient inférieur au gap dynamique attendu (`7 m + 0,9 s` de headway).

Sur `90 s` au pas `1/120 s`, le suiveur rattrape puis se stabilise sans contact : gap minimal `17,50 m`, détection avant `100 %`, décélération maximale `2,57 m/s²`, aucun tick de contact et aucun immobilisme. Sur les 20 dernières secondes, le gap moyen et le gap cible moyen sont tous deux `17,50 m`, avec un delta de vitesse moyen nul. D-S02 valide donc le suivi longitudinal nominal, avec réserve car il n'y a pas encore de changement de ligne ni de choix de dépassement.

D-S03 ajoute une décision statique de dépassement candidat. L'ego doit avoir une voiture lente devant lui dans son corridor courant, avec un `time-to-catch` inférieur à `18 s` et un delta de vitesse supérieur à `8 km/h`. La ligne candidate est placée à `-3,0 m` latéral et doit être dans la piste, sans blocker avant à moins de `35 m` ni blocker arrière à moins de `20 m`.

Quatre cas sont testés : dépassement clair, ligne candidate bloquée devant, ligne candidate bloquée derrière, et absence de besoin de dépassement. Les 4 décisions correspondent aux attendus : 1 positive et 3 négatives. D-S03 valide donc le déclenchement d'une intention de dépassement sans script de résultat, avec réserve car l'action de changement de ligne n'est pas encore simulée.

D-S04 simule deux voitures côte à côte pendant `45 s`. Les deux voitures commencent avec une clearance latérale serrée de `0,50 m`, puis rejoignent des offsets cibles séparés. Le scénario reste côte à côte `100 %` du temps, sans contact et sans sortie de piste. La clearance latérale moyenne sur les 15 dernières secondes atteint `1,70 m`, avec une clearance minimale au bord de piste de `2,25 m`. D-S04 valide donc la mesure et le maintien d'une situation côte à côte, avec réserve car les offsets latéraux sont encore imposés.

D-S05 simule une voiture ego déjà décalée latéralement à `+1,8 m`. Elle revient vers le corridor cible `0,0 m` entre une voiture avant et une voiture arrière, après maintien d'un trou sûr pendant `0,5 s`. La réinsertion commence à `0,49 s`, se termine à `3,47 s`, et dure `2,98 s`. Aucun contact ni hors-piste n'est détecté. Les gaps minimaux pendant la réinsertion restent très supérieurs aux seuils : `32,15 m` devant pour un seuil de `18 m`, et `29,24 m` derrière pour un seuil de `16 m`. D-S05 valide donc la mesure et l'exécution nominale d'une réinsertion, avec réserve car le scénario reste déterministe et non contesté.

D-S06 consolide les cinq jalons précédents. Les 5 scénarios sont conformes, les 3 scénarios dynamiques totalisent `190 s`, et les compteurs consolidés restent à `0` contact et `0` hors-piste. Les 4 cas de décision D-S03 sont conformes. D-S06 conclut donc l'expérience D en `validée avec réserves`.

## 11. Limites

- D-S01 est statique : aucune décision ni dynamique de dépassement.
- D-S02 est longitudinal : le suiveur ralentit derrière le leader, mais ne choisit pas encore de dépasser.
- D-S03 choisit une ligne candidate, mais ne déplace pas encore la voiture vers cette ligne.
- D-S04 maintient des offsets latéraux imposés ; il ne prouve pas encore une manoeuvre autonome complète.
- D-S05 valide une réinsertion nominale, mais pas encore une réinsertion contestée avec défense, erreur pilote ou gap qui se referme.
- Le corridor latéral est scalaire et devra être relié aux largeurs de voiture et de piste.
- Les contacts ne sont pas encore simulés.
- Le replay E reste souhaitable pour analyser les scénarios D longs.

## 12. Conclusion

### Décision

> Validée avec réserves.

### Niveau de confiance

> Moyen pour D global, bon pour la perception D-S01, le suivi longitudinal D-S02, la décision candidate D-S03, le maintien côte à côte D-S04 et la réinsertion nominale D-S05.

## 13. Conséquences

### Paramètres retenus

- perception en distance curviligne modulo longueur de piste ;
- corridor latéral initial D-S01 : `2,20 m` ;
- lookahead avant initial : `80 m` ;
- lookahead arrière initial : `55 m` ;
- gap dynamique D-S02 : `7 m + 0,9 s` de headway ;
- lookahead avant D-S02 : `120 m` ;
- déclenchement D-S03 : TTC <= `18 s`, delta vitesse >= `8 km/h` ;
- sécurité ligne candidate D-S03 : `35 m` devant, `20 m` derrière ;
- offsets D-S04 : `-1,8 m` et `+1,8 m` ;
- clearance latérale D-S04 stabilisée : `1,70 m`.
- seuils D-S05 : `18 m` devant, `16 m` derrière, `0,5 s` de dwell ;
- réinsertion D-S05 : `2,98 s`, offset final `0,00 m`.
- conclusion D-S06 : 5 scénarios conformes sur 5, `190 s` dynamiques, `0` contact, `0` hors-piste.

### Risques résiduels

- le corridor latéral devra évoluer vers une notion de voie ou de ligne candidate ;
- le suivi longitudinal peut encore créer de l'oscillation ou des contacts dans des cas plus denses ;
- le dépassement complet reste à consolider sur des scénarios plus longs et moins déterministes ;
- les réinsertions contestées ne sont pas encore prouvées.

### Documents affectés

- plan de faisabilité ;
- tableau de bord Phase 1 ;
- rapport consolidé ;
- README des prototypes.

### Travaux suivants

- traiter E pour disposer d'un replay exploitable des interactions longues ;
- conserver une visualisation temporelle pour chaque scénario dynamique ;
- garder le replay E comme outil d'analyse dès que les interactions dépassent quelques secondes.
