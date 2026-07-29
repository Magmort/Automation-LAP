# Expérience E - Replay minimal

- **Statut :** validée avec réserves
- **Ticket :** #7
- **Responsable :** à renseigner
- **Date de début :** 2026-07-27
- **Date de conclusion :** 2026-07-28
- **Version du protocole :** 0.1
- **Dépendance d'entrée :** états dynamiques B, `TrackDefinition` C-S06, scénarios D utiles pour interactions
- **Dépendance produite :** contrat candidat de replay autonome pour analyse, debugging et F

## 1. Question testée

Une course enregistrée peut-elle être chargée, parcourue dans les deux sens et affichée sans recalculer toutes les décisions ?

## 2. Hypothèse

Un fichier replay autonome peut contenir :

- un en-tête versionné ;
- les unités et conventions ;
- un snapshot de piste ;
- la liste des véhicules ;
- une timeline de frames échantillonnées ;
- des événements ;
- un index de navigation.

L'hypothèse est que ce format suffit pour charger un replay, se déplacer vers un instant arbitraire, inspecter l'état d'une voiture et reconstruire un affichage simple sans relancer la simulation.

## 3. Hors périmètre

- rendu Unity ;
- compression finale ou format binaire définitif ;
- streaming réseau ;
- caméra de diffusion ;
- synchronisation audio ;
- rollback de simulation ;
- recalcul des décisions IA depuis le replay.

## 4. Environnement

| Élément | Version ou valeur |
|---|---|
| Système d'exploitation | Windows, machine locale |
| Matériel pertinent | non significatif pour E-S01 à E-S06 |
| Runtime / SDK | Python embarqué Codex pour prototype hors Unity |
| Version du prototype | `prototypes/replay/` |
| Entrées utilisées | `D-S05` traffic summary, `TrackDefinition` C-S06, replay E-S01, scripts E-S02 à E-S06 |
| Graine aléatoire | aucune |

## 5. Protocole reproductible

1. Charger un résultat dynamique existant.
2. Créer un fichier replay autonome versionné.
3. Valider la structure et les unités.
4. Charger le replay sans relire la source.
5. Chercher plusieurs timestamps arbitraires.
6. Vérifier les événements et la cohérence temporelle.
7. Mesurer la taille du fichier.
8. Générer des variantes à plusieurs fréquences d'échantillonnage.
9. Générer des cas de compatibilité valides et invalides.
10. Consolider la décision de faisabilité.
11. Produire un rapport JSON, un rapport Markdown et une visualisation SVG.

## 6. Scénarios

| Identifiant | Description | Entrées | Répétitions |
|---|---|---|---:|
| E-S01 | Contrat replay autonome | résultat D-S05, piste C | 1, validé avec réserves |
| E-S02 | Navigation temporelle avant/arrière | replay E-S01 | validé avec réserves |
| E-S03 | Événements et saut vers événement | replay E-S01 | validé avec réserves |
| E-S04 | Taille et fréquence d'échantillonnage | replay E-S01 variants | validé avec réserves |
| E-S05 | Compatibilité de version | replays valides/invalides | validé avec réserves |
| E-S06 | Synthèse replay minimal | résultats E-S01 à E-S05 | validé avec réserves |

## 7. Métriques

| Métrique | Unité | Méthode de collecte | Seuil ou attente |
|---|---|---|---|
| Taille fichier | octets | `stat()` du replay JSON | mesurée |
| Frames | nombre | timeline replay | > 0 |
| Véhicules | nombre | liste replay | conforme source |
| Événements | nombre | liste replay | >= 2 sur D-S05 |
| Erreurs de structure | nombre | validation schema v0.1 | 0 |
| Checks de seek | nombre | interpolation/lookup | tous conformes |
| Commandes navigation | nombre | script E-S02 | toutes exécutées |
| Échecs monotonicité | nombre | lecture avant/arrière E-S02 | 0 |
| Clamps aux bornes | nombre | seeks hors durée E-S02 | détectés |
| Sauts événementiels | nombre | index événement E-S03 | tous conformes |
| Contextes événementiels | nombre | pré/post-roll E-S03 | valides |
| Durée couverte | s | timeline | égale source |
| Fréquence d'échantillonnage | Hz | variantes E-S04 | mesurée |
| Débit replay brut | octets/s | taille / durée E-S04 | mesuré |
| Écart événement-frame | s | distance événement vers frame la plus proche | <= demi-intervalle |
| Compatibilité version | booléen | lecteur replay | détectée |
| Cas incompatibles refusés | nombre | lecteur E-S05 | tous conformes |
| Scénarios E validés | nombre | synthèse E-S06 | tous conformes |

## 8. Critères de réussite et d'échec

### Réussite

- [x] un replay autonome est généré ;
- [x] le replay contient piste, véhicules, frames, événements et index ;
- [x] le replay se charge sans relire le résultat D source ;
- [x] plusieurs timestamps peuvent être résolus ;
- [x] les événements restent dans la durée de la timeline ;
- [x] la taille est mesurée.
- [x] le replay peut être parcouru en avant et en arrière ;
- [x] les pauses et seeks arbitraires conservent un état cohérent ;
- [x] les bornes temporelles sont clampées.
- [x] les événements peuvent être indexés et rejoints ;
- [x] le contexte pré/post-roll autour des événements est lisible.
- [x] plusieurs fréquences d'échantillonnage peuvent être générées depuis le même replay ;
- [x] la taille brute et le débit par seconde sont mesurés par fréquence ;
- [x] les événements restent couverts par la frame la plus proche ou par interpolation.
- [x] la version supportée `0.1.0` est acceptée explicitement ;
- [x] les versions incompatibles sont refusées explicitement ;
- [x] les structures corrompues produisent un code d'erreur déterministe.
- [x] la synthèse E-S06 produit une décision exploitable pour F et ADR-0002.

### Échec ou révision obligatoire

- [ ] le replay dépend du recalcul de simulation pour être lu ;
- [ ] le format n'est pas versionné ;
- [ ] le seek produit des états incohérents ou hors durée ;
- [ ] la taille ne peut pas être mesurée ;
- [ ] un changement de version incompatible n'est pas détectable.

## 9. Résultats

### Données brutes

- `prototypes/replay/results/e_s01_minimal_replay.replay.json`
- `prototypes/replay/results/E_S01_REPLAY_CONTRACT_RESULT.md`
- `prototypes/replay/results/e_s01_replay_contract_summary.json`
- `prototypes/replay/results/E_S01_REPLAY_CONTRACT_VISUALIZATION.svg`
- `prototypes/replay/results/E_S02_NAVIGATION_RESULT.md`
- `prototypes/replay/results/e_s02_navigation_summary.json`
- `prototypes/replay/results/E_S02_NAVIGATION_VISUALIZATION.svg`
- `prototypes/replay/results/E_S03_EVENT_JUMP_RESULT.md`
- `prototypes/replay/results/e_s03_event_jump_summary.json`
- `prototypes/replay/results/E_S03_EVENT_JUMP_VISUALIZATION.svg`
- `prototypes/replay/results/E_S04_SAMPLING_SIZE_RESULT.md`
- `prototypes/replay/results/e_s04_sampling_size_summary.json`
- `prototypes/replay/results/E_S04_SAMPLING_SIZE_VISUALIZATION.svg`
- `prototypes/replay/results/e_s04_variants/`
- `prototypes/replay/results/E_S05_VERSION_COMPATIBILITY_RESULT.md`
- `prototypes/replay/results/e_s05_version_compatibility_summary.json`
- `prototypes/replay/results/E_S05_VERSION_COMPATIBILITY_VISUALIZATION.svg`
- `prototypes/replay/results/e_s05_compatibility_cases/`
- `prototypes/replay/results/E_S06_REPLAY_SUMMARY_RESULT.md`
- `prototypes/replay/results/e_s06_replay_summary.json`
- `prototypes/replay/results/E_S06_REPLAY_SUMMARY_VISUALIZATION.svg`

### Synthèse

| Scénario | Résultat | Variance | Observation |
|---|---:|---:|---|
| E-S01 | replay autonome `148756` octets | aucune | 221 frames, 3 véhicules, 3 événements, seek exact et interpolé |
| E-S02 | 9 commandes exécutées | aucune | avant, arrière, pause, 5 seeks, 3 clamps, 0 échec de monotonicité |
| E-S03 | 3 jumps événementiels | aucune | 3 événements requis trouvés, 2 jumps interpolés, 3 contextes pré/post-roll valides |
| E-S04 | 5 profils d'échantillonnage | aucune | 1 à 20 Hz, 41831 à 719882 octets, 0 erreur de validation |
| E-S05 | 10 cas de compatibilité | aucune | 1 accepté, 9 refusés, 10 attentes respectées, 0 mismatch |
| E-S06 | décision consolidée | aucune | 5 scénarios validés / 5, décision validée avec réserves, confiance moyen à bon |

## 10. Analyse

E-S01 génère un fichier `AutomationLapReplay` JSON v0.1 depuis D-S05. Le replay embarque le snapshot de piste C, les définitions de véhicules, `221` frames sur `55 s`, `3` événements et un index de keyframes. La validation recharge uniquement le replay généré, vérifie la structure, confirme la version supportée et résout `5` timestamps, dont des timestamps interpolés entre deux frames.

La taille mesurée est `148756` octets pour ce scénario court à `3` véhicules. Ce chiffre est volontairement brut : il donne un premier ordre de grandeur avant compression, échantillonnage variable ou format binaire.

E-S02 charge le replay autonome E-S01 et exécute un script de navigation de `9` commandes : seek début, lecture avant, pause, seek arbitraire au milieu, lecture arrière accélérée, seek proche fin, lecture jusqu'à la borne, puis deux seeks hors durée. La validation produit `36` samples de navigation, dont `22` exacts et `14` interpolés. Les `3` clamps aux bornes sont détectés, et aucun échec de monotonicité n'est observé pendant la lecture avant/arrière.

E-S03 vérifie l'index d'événements du replay E-S01. Les `3` événements requis sont trouvés dans l'ordre attendu : `gap_safe_start`, `rejoin_started`, `rejoin_completed`. Les `3` jumps sont exécutés, dont `2` interpolés car les événements ne tombent pas exactement sur une frame. Les `3` contextes pré/post-roll sont valides ; `2` clamps sont attendus car les premiers pré-rolls sortent du début de timeline.

E-S04 resample le replay E-S01 en `5` variantes : `1 Hz`, `2 Hz`, `4 Hz`, `10 Hz` et `20 Hz`. La taille brute JSON passe de `41831` octets à `1 Hz` à `719882` octets à `20 Hz`. Le profil `4 Hz` de référence produit `221` frames et `148964` octets, cohérent avec les `148756` octets du fichier E-S01 initial. Le débit mesuré va de `760.6` à `13088.8` octets/s sur ce scénario court à `3` véhicules. Les tailles augmentent de façon monotone avec la fréquence et les `5` variantes ont `0` erreur de validation.

E-S05 fixe une politique de compatibilité stricte pour le prototype : seule la version `0.1.0` est supportée. Le lecteur accepte `1` cas valide et refuse `9` cas invalides : version patch non migrée, version majeure future, version absente, kind invalide, unités absentes, timeline absente, nombre de frames incohérent, temps non monotone et JSON malformé. Les `10` attentes sont respectées avec `0` mismatch de code d'erreur.

E-S06 consolide les cinq preuves précédentes. Les `5` scénarios sont validés. Le contrat candidat retenu est `AutomationLapReplay` JSON v0.1 avec unités SI, télémétrie de référence `4 Hz`, images-clés toutes les `1 s`, et politique de version stricte par liste de versions supportées. La conclusion est `validée avec réserves`, avec un niveau de confiance `moyen à bon`.

## 11. Limites

- E-S01 utilise un JSON lisible, pas un format optimisé.
- La source initiale vient de D-S05 et reste déterministe.
- Le replay stocke des frames échantillonnées, pas tous les ticks physiques.
- L'interpolation n'est pas encore validée visuellement dans Unity.
- E-S03 ne teste pas encore les catégories d'événements plus riches ou les bookmarks utilisateur.
- E-S04 mesure un scénario court à `3` véhicules ; il ne remplace pas le test de charge F.
- E-S05 ne fournit pas encore de migration de schéma ; il prouve seulement le refus explicite et déterministe.
- E-S06 ne transforme pas le format JSON prototype en format de production ; il fixe une base candidate à mesurer dans F.

## 12. Conclusion

### Décision

> Validée avec réserves. E-S01 à E-S06 sont conformes.

### Niveau de confiance

> Moyen à bon. Le replay autonome, la navigation avant/arrière, les sauts événementiels, les tailles par fréquence, les refus de compatibilité et la synthèse de décision sont prouvés hors Unity.

## 13. Conséquences

### Paramètres retenus

- format replay candidat : `AutomationLapReplay` JSON v0.1 ;
- unités embarquées : `s`, `m`, `m/s`, `rad` ;
- replay E-S01 : `55 s`, `221` frames, `3` véhicules, `3` événements ;
- taille brute E-S01 : `148756` octets.
- navigation E-S02 : `9` commandes, `36` samples, `0` échec de monotonicité, `3` clamps détectés.
- événements E-S03 : `3` événements requis, `3` jumps, `2` jumps interpolés, `3` contextes valides.
- échantillonnage E-S04 : `1`, `2`, `4`, `10` et `20 Hz` mesurés ; référence `4 Hz` à `148964` octets pour `55 s`.
- débit replay E-S04 : `760.6` à `13088.8` octets/s avant compression.
- compatibilité E-S05 : `schemaVersion` supportée `0.1.0` uniquement ; `10` cas testés, `0` mismatch.
- synthèse E-S06 : `5` scénarios validés / `5`, décision `validée avec réserves`, confiance `moyen à bon`.

### Risques résiduels

- format JSON non optimisé ;
- source déterministe D-S05 ;
- catégories d'événements avancées non encore testées ;
- migrations de schéma non encore conçues.

### Documents affectés

- plan de faisabilité ;
- tableau de bord Phase 1 ;
- rapport consolidé ;
- README des prototypes.

### Travaux suivants

- utiliser le contrat E comme entrée candidate pour les tests de charge F ;
- conserver E-S04 comme base de comparaison avant compression ou format binaire ;
- confirmer ADR-0002 lorsque F aura mesuré le coût à l'échelle cible.
