# Rapport consolidé de faisabilité

- **Statut :** conclusion de faisabilité prête
- **Version :** 0.3
- **Phase :** Phase 1
- **Ticket directeur :** #2
- **Date d’ouverture :** 25 juillet 2026

Ce document est le livrable final de la Phase 1. Il doit rester synthétique : les protocoles, journaux, données et mesures détaillées appartiennent aux rapports d’expérience.

## 1. Résumé exécutif

La Phase 1 confirme la faisabilité du projet sous forme de `Go avec réserves`. Les huit expériences réduisent les risques majeurs : les données Automation sont exportables, un modèle dynamique 2D candidat existe, le contrôleur autonome peut boucler sans script par virage, les interactions de trafic sont réglables, le replay hybride est navigable, la cible de charge est plausible, et UR2D2 peut fournir un circuit exploitable via ses fichiers de piste.

La validation H-S06 est le point de fermeture du Proof of Concept : une QFC55 issue des exports Automation roule sur un `TrackDefinition` reconstruit depuis un vrai dossier de track UR2D2, avec rendu de replay aligné sur le fond runtime.

### Décision générale

- **Décision :** Go avec réserves
- **Niveau de confiance :** bon pour lancer le vertical slice
- **Recommandation :** passer au vertical slice en gardant les prototypes comme références de validation. Les réserves doivent être traitées comme travaux intégrés : calibration physique, robustesse multi-circuits UR2D2, intégration Unity, et format de replay/import production.

## 2. Tableau des décisions

| Expérience | Question | Conclusion | Niveau de confiance | Risque résiduel principal |
|---|---|---|---|---|
| A — Extraction Automation | Les données nécessaires sont-elles exportables et stables ? | Validée avec réserves | Moyen | Unités Automation encore partielles |
| B — Dynamique d’une voiture | Un modèle 2D commun produit-il des différences plausibles ? | Validée avec réserves | Moyen | Direction encore calibrable, unités latérales inconnues |
| C — Tour autonome et circuit minimal | Le contrôleur peut-il rouler sans script par virage avec un contrat de circuit minimal ? | Validée avec réserves | Moyen à bon | Contrat validé sur piste canonique, import réel et surfaces détaillées non prouvés |
| D — Trafic et dépassement | Les interactions peuvent-elles être crédibles et réglables ? | Validée avec réserves | Moyen | Interactions longues, denses ou contestées non prouvées |
| E — Replay minimal | Le replay hybride est-il autonome et navigable ? | Validée avec réserves | Moyen à bon | Format JSON non optimisé, coût à l'échelle à mesurer dans F |
| F — Charge et accélération | La cible de voitures et l’exécution accélérée sont-elles viables ? | Validée avec réserves | Moyen | Harnais Python hors Unity ; profilage runtime réel à faire pendant le vertical slice |
| G — Import UR2D2 editor `.sav` | Les sauvegardes éditeur UR2D2 peuvent-elles reconstruire le modèle minimal validé en C ? | Validée avec réserves | Moyen | Format opaque, calibration et robustesse multi-tracés encore à renforcer |
| H — Import UR2D2 vrais tracks | Les fichiers runtime/export final UR2D2 peuvent-ils reconstruire le même modèle minimal ? | Validée avec réserves | Bon | Chemin validé sur une piste ; généralisation multi-circuits et contraintes murs/pitlane à produire |

Conclusions autorisées : `validée`, `validée avec réserves`, `à modifier`, `non viable`.

## 3. Paramètres candidats retenus

| Domaine | Paramètre | Valeur candidate | Origine | Statut |
|---|---|---:|---|---|
| Simulation | Pas de temps physique | `1/60 s` candidat, `1/120 s` référence de mesure | Expérience B-S05 | Candidat |
| Circuit | Schéma minimal `TrackDefinition` | v0.1 candidat | Expérience C-S01 | Candidat |
| Circuit | Tolérances de fermeture et continuité | boucle fermée implicite, polyligne validée | Expérience C-S01 | Candidat |
| Circuit | Transformation UR2D2 `.sav` vers unités SI | `1 m = 12,8 unités éditeur` sur la piste runtime validée, Y inversé pour la simulation | Expériences G/H | Candidat avec réserves |
| Circuit | Transformation UR2D2 runtime vers PNG | `track.png` 4096 x 2048 vers `track_preview.png` 768 x 384, échelle uniforme `0,1875` | Expérience H-S04/H-S06 | Candidat validé visuellement |
| Contrôle IA | Fréquence de commande | `1/60 s` candidate, `1/120 s` référence | Expérience C-S02/C-S03 | Candidat |
| Contrôle IA | Adaptation de vitesse | cible par courbure anticipée, QFC55 A9 | Expérience C-S03 | Candidat avec réserves |
| Contrôle IA | Récupération latérale | retour sous 0,75 m en moins de 7 s après perturbation | Expérience C-S04 | Candidat avec réserves |
| Contrôle IA | Profils pilote | prudent, équilibré, agressif | Expérience C-S05 | Candidat avec réserves |
| Contrôle IA | Saturation du grip | yaw demandé plafonné par limite latérale véhicule | Expérience C-S05 | Garde-fou candidat |
| Perception | Fréquence de mise à jour | À mesurer | Expérience D | En attente |
| Replay | Fréquence des images-clés | 1 s | Expérience E-S04 | Candidat avec réserves |
| Replay | Fréquence de télémétrie | 4 Hz référence, plage 1 à 20 Hz mesurée | Expériences E-S04 et F-S04 | Candidat avec réserves |
| Performance | Nombre cible de voitures | 12 à 20 | F-S05 | Candidat avec réserves |
| Performance | Stress de suivi | 40 voitures | F-S01 à F-S05 | Candidat de mesure |

## 4. Résultats par expérience

### A — Extraction Automation

- **Ticket :** #3
- **Conclusion :** validée avec réserves pour l'entrée de B
- **Preuves principales :** exports trois voitures, validation de répétabilité, inventaire des graphes, séries brutes A7, contrat unifié A8 `AutomationRawVehicleData` v0.1
- **Données manquantes :** unités exactes de certaines courbes Automation, usage physique final des graphes de freinage et de grip
- **Impact sur ADR-0003 :** le format brut versionné devient l'entrée candidate de l'adaptateur Automation

### B — Dynamique d’une voiture

- **Ticket :** #4
- **Conclusion :** validée avec réserves
- **Modèle testé :** état 2D minimal vitesse / position / cap, alimenté par les courbes Automation A9
- **Écarts mesurés :** B-S05 stable aux pas `1/30 s`, `1/60 s` et `1/120 s` ; B-S06 conserve les différences inter-voitures sur toutes les métriques consolidées
- **Paramètres dérivés nécessaires :** normalisation de direction, loi latérale calibrable, unités finales des graphes `LowSpeedSteering` et `HighSpeedSteering`

### C — Tour autonome et modèle minimal de circuit

- **Ticket :** #5
- **Conclusion :** validée avec réserves
- **Contrôleur testé :** pure pursuit à vitesse contrainte en C-S02, adaptation de vitesse par courbure avec QFC55 en C-S03, récupération d'écarts latéraux en C-S04, puis profils pilote différenciés en C-S05
- **Schéma minimal retenu :** `TrackDefinition` v0.1 candidat, indépendant de Unity et d'UR2D2
- **Invariants et tolérances :** C-S01 valide une boucle fermée implicite de 381,92 m, 24 segments, largeur minimale 10 m, courbure finie
- **Régularité :** C-S02 référence `1/120 s` : tours d'environ 30,45 s, erreur latérale moyenne 0,173 m, max 0,693 m
- **Adaptation de vitesse :** C-S03 référence `1/120 s` : trois tours en 83,33 s, vitesse moyenne 49,31 km/h, vitesse max 62,79 km/h, erreur latérale moyenne 0,231 m, max 0,807 m, aucune sortie
- **Récupération latérale :** C-S04 référence `1/120 s` : offsets `+2,75 m`, `-3,25 m` et `+3,00 m` récupérés en 1,433 s, 1,800 s et 2,467 s, aucune sortie
- **Différenciation des pilotes :** C-S05 référence `1/120 s` : prudent 115,28 s, équilibré 83,33 s, agressif 56,84 s sur trois tours, aucune sortie ; erreur latérale moyenne `0,126 m`, `0,231 m`, `0,302 m`
- **Témoin négatif C-S05 :** sur-vitesse volontaire : saturation grip `84,11 %`, ratio maximal `5,87x`, erreur latérale maximale `24,197 m`, sortie de piste attendue
- **Contrat C-S06 pour G :** `TrackDefinition` v0.1 consolidé ; champs source, invariants et valeurs dérivées listés dans `C_S06_CONTRACT_CONSOLIDATION_RESULT.md`
- **Réserve C-S03 à C-S05 :** la limite latérale utilise encore le proxy B-S04 `FrontGripG + RearGripG`, la perturbation C-S04 reste cinématique, les profils C-S05 sont heuristiques, et la saturation latérale ne distingue pas encore sous-virage et survirage
- **Données obligatoires pour un importeur :** identité, version, unités SI, axes et orientation, boucle et sens, surface principale, ligne centrale ordonnée, largeurs gauche/droite, départ, checkpoints

### D — Trafic et dépassement

- **Ticket :** #6
- **Conclusion :** validée avec réserves
- **Protocole :** `docs/feasibility/experiments/D-TRAFFIC-OVERTAKING.md`
- **Socle D-S01 :** 6 voitures projetées sur `TrackDefinition`, 6 liens de voisinage détectés, aucun hors-piste, wrap de départ validé
- **Suivi D-S02 :** 90 s derrière voiture lente, aucun contact, aucun immobilisme, gap minimal `17,50 m`, stabilisation au gap cible
- **Décision D-S03 :** 4 cas conformes / 4, dépassement candidat déclenché uniquement quand la ligne candidate est libre
- **Côte à côte D-S04 :** 45 s, aucun contact, aucun hors-piste, clearance latérale stabilisée `1,70 m`
- **Réinsertion D-S05 :** 55 s, retour dans le corridor cible en `2,98 s`, aucun contact, aucun hors-piste, gaps minimaux `32,15 m` devant et `29,24 m` derrière
- **Synthèse D-S06 :** 5 scénarios conformes / 5, 190 s dynamiques simulées, 0 contact consolidé, 0 hors-piste consolidé, 4 décisions conformes / 4
- **Réserve :** scénarios déterministes et peu nombreux ; interactions longues, denses, contestées et performance restent à couvrir

### E — Replay minimal

- **Ticket :** #7
- **Conclusion :** validée avec réserves
- **Protocole :** `docs/feasibility/experiments/E-REPLAY-MINIMAL.md`
- **Format testé :** E-S01 `AutomationLapReplay` JSON v0.1 autonome, avec piste embarquée, véhicules, frames, événements et index
- **Taille et débit :** E-S01 D-S05 replay : `148756` octets pour `55 s`, `221` frames, `3` véhicules, `3` événements
- **Navigation E-S02 :** `9` commandes, `36` samples, `2` lectures avant, `1` lecture arrière, `5` seeks, `3` clamps aux bornes, `0` échec de monotonicité
- **Événements E-S03 :** `3` événements requis trouvés / `3`, `3` jumps, `2` jumps interpolés, `3` contextes pré/post-roll valides, `0` erreur d'index
- **Échantillonnage E-S04 :** `5` profils de `1` à `20 Hz`, `56` à `1101` frames, `41831` à `719882` octets, `760.6` à `13088.8` octets/s, `0` erreur de validation
- **Compatibilité E-S05 :** `10` cas testés, `1` replay courant accepté, `9` cas incompatibles refusés, `0` mismatch ; seule la version `0.1.0` est supportée par le prototype
- **Synthèse E-S06 :** `5` scénarios validés / `5`, décision `validée avec réserves`, confiance `moyen à bon`, contrat candidat pour F et ADR-0002

### F — Charge et accélération

- **Ticket :** #8
- **Conclusion :** validée avec réserves
- **Protocole :** `docs/feasibility/experiments/F-PERFORMANCE-LOAD.md`
- **Machine de référence F-S01 :** Windows 11, Python `3.12.13`, `32` CPU logiques
- **Harnais F-S01 :** `4` profils (`1`, `12`, `20`, `40` voitures), `5` répétitions, `55 s` simulées, `0` erreur de benchmark
- **Profil 40 voitures F-S01 :** `180,00 ms` de temps mural moyen, facteur temps réel moyen `307,2x`, `49374` véhicules-frames/s, replay compact `12077` octets/s
- **Charge cible F-S02 :** boucle représentative `60 Hz`, budget `16,667 ms`, profils requis `12` et `20` voitures, `3` répétitions, `0` deadline miss
- **Profil 20 voitures F-S02 :** tick p95 moyen `0,3744 ms`, ratio p95/budget `0,0225`, facteur temps réel moyen `73,4x`, replay compact `5021` octets/s
- **Stress 40 voitures F-S02 :** tick p95 moyen `0,7124 ms`, ratio p95/budget `0,0427`, facteur temps réel moyen `38,6x`, non bloquant
- **Accélération F-S03 :** `180 s` simulées, profils requis `12` et `20` voitures, `3` répétitions, seuil requis `20x`, validation avec facteur minimal moyen `36,3x`
- **Profil 20 voitures F-S03 :** temps mural moyen `4955,77 ms`, tick p95 moyen `0,7666 ms`, `43598` véhicules-ticks/s, système dominant `input` à `38,5 %`
- **Stress 40 voitures F-S03 :** facteur moyen `19,7x`, tick p95 moyen `1,4452 ms`, non bloquant
- **Coût replay F-S04 :** `9` profils, `3` répétitions, référence `20` voitures à `4 Hz`, part replay `6,0 %` du tick moyen, replay moyen `0,0284 ms`, débit `5021` octets/s
- **Fréquence haute F-S04 :** `20` voitures à `20 Hz`, part replay `23,1 %`, débit `25104` octets/s ; `40` voitures à `20 Hz`, part replay `23,4 %`, débit `49879` octets/s
- **Synthèse F-S05 :** décision `validée avec réserves`, `0` blocage, paramètres candidats `12` à `20` voitures, tick `60 Hz`, replay compact `4 Hz`, stress suivi `40` voitures
- **Réserve :** benchmark Python hors Unity, avec voitures dupliquées depuis E-S01 ; F mesure une sérialisation compacte en mémoire, pas une écriture disque continue ni le format binaire final

### G — Import du modèle minimal depuis UR2D2

- **Ticket :** #10
- **Conclusion :** validée avec réserves
- **Source :** sauvegardes `.sav` directement issues du Track Editor
- **Préparation G-S00/G-S01 :** inventaire et analyse différentielle créés ; huit sauvegardes observées
- **Lecteur brut G-S02 :** validé avec réserves ; `UR2D2RawTrackData` v0.1.0 extrait une région stable de 17 tableaux `float32` comptés, 4 segments de route, 3 lignes IA, 3 checkpoints, 1 mur multi-segments, 1 zone de sable et 1 zone d'arbres ; les tracés sont exposés comme clés vectorielles candidates ; pitlane, entrée et sortie détectées avec attribution encore en confiance basse
- **Conversion G-S03 :** validée avec réserves ; `g_s03_track_definition_candidate.json` passe C-S01 avec 16 points échantillonnés depuis 4 clés vectorielles, 16 segments, 109,154 m de boucle, largeur totale minimale recalibrée à 5,000 m et 0 erreur de contrat
- **Validation visuelle G-S04 :** validée avec réserves ; `G_S04_VISUAL_VALIDATION.svg` superpose route, clés, poignées, lignes IA, checkpoints, mur, pit1 entrée, pit2 sortie, pitlane droite, sable et arbres ; les deux segments droits ont 0,000 m d'écart d'alignement et les 3 checkpoints se projettent sur les points attendus ; `G_S04_HANDLE_INTERPRETATION.svg` expose la convention corrigée `A[i]` sortante et `B[i-1]` entrante ; `G_S04_SAND_HANDLE_HYPOTHESES.svg` valide l'inversion verticale globale des vecteurs pour le sable
- **Synthèse G-S05 :** la représentation est validée après correction de l'échelle, de la fermeture de piste, des poignées vectorielles et des voies de pitlane
- **Fichiers et structures identifiés :** route principale, lignes IA, checkpoints, pitlane, entrée/sortie pitlane, mur, sable et arbres
- **Champs du contrat reconstruits :** identité, unités SI, axes, boucle, sens, surface principale, centerline, largeurs, ligne de départ et checkpoints
- **Transformation de coordonnées :** `1 m = 32 unités éditeur`, Y inversé, origine au centroïde des clés de route ; formule de Bézier candidate `key[i] + angleA[i]/weightA[i]` vers `key[i+1] + angleB[i]/weightB[i]`, avec inversion verticale globale des vecteurs de poignées ; encore à confirmer visuellement sur toutes les familles de tracés
- **Interventions manuelles nécessaires :** calibration et validation visuelle encore recommandées pour un nouveau type de tracé
- **Décision sur le chemin `.sav` :** viable avec réserves comme référence d'analyse ; le chemin H est préféré pour le vertical slice lorsqu'un dossier runtime complet est disponible

### H — Import du modèle minimal depuis les vrais fichiers de tracks UR2D2

- **Ticket :** #11
- **Conclusion :** validée avec réserves
- **Source :** dossier runtime/export final UR2D2 contenant `track_editor.sav`, `track_info.data`, `track_preview.png` et les PNG de couches
- **H-S00/H-S01 :** inventaire et comparaison G/H réalisés ; `track.data` contient des signaux corrélables mais n'est pas retenu comme source critique
- **H-S02 :** lecteur `.sav` runtime validé ; piste principale, pitlane, murs et checkpoints extraits depuis `track_editor.sav`
- **H-S03 :** `TrackDefinition` v0.1 reconstruit et validé C-S01 : 64 points, 275,352 m, largeur 10,000 m, courbure maximale 0,241360 1/m
- **H-S04 :** superposition sur `track_preview.png` validée visuellement ; piste, pitlane, murs et checkpoints alignés, largeur piste/pitlane correcte
- **H-S05 :** paquet `UR2D2ImportedTrackPackage` produit : `TrackDefinition`, extras simulation, mapping runtime PNG et provenance sans dépendance à `track.data`
- **H-S06 :** replay fonctionnel validé ; QFC55 sur 3 tours, 62,658 s, 0 sortie, trajectoire colorée par vitesse sur fond runtime
- **Champs du contrat reconstruits :** identité, unités SI, axes, boucle, sens, surface principale, centerline, largeurs, départ et checkpoints
- **Décision sur le chemin runtime :** chemin H recommandé comme base d'import UR2D2 pour le vertical slice, avec validation multi-circuits à prévoir

## 5. Risques résiduels

| Risque | Probabilité | Impact | Preuve disponible | Réponse proposée |
|---|---|---|---|---|
| Données Automation insuffisantes | Moyenne | Élevé | Expérience A8 | Paramètres dérivés, usage des courbes Automation et calibration documentée pendant B |
| Modèle physique trop coûteux | Moyenne | Élevé | Expériences B et F | Profilage Unity réel puis simplification guidée par mesure |
| Modèle de circuit inadapté au contrôle | À évaluer | Élevé | Expérience C | Définition pilotée par les usages et invariants testés |
| IA peu crédible en trafic | À évaluer | Élevé | Expériences C et D | Architecture en couches et scénarios statistiques |
| Replay trop volumineux | Moyenne | Moyen | Expériences E-S04 et F-S04 | Garder `4 Hz` compact, mesurer format binaire et écriture disque plus tard |
| Import UR2D2 incomplet ou fragile | Moyenne | Moyen | Expériences G et H, validation H-S06 | Retenir le chemin H, garder un adaptateur versionné, ajouter une campagne multi-circuits et conserver une solution de repli indépendante |
| Dépendance excessive à Unity | Faible par conception | Élevé | ADR-0001 | Tests sans rendu et frontières de dépendance |

## 6. Changements requis

### Plan général

- Aucun changement de périmètre produit identifié à ce jour.
- La Phase 1 contient désormais deux expériences dédiées à l’import UR2D2 : G pour les sauvegardes éditeur, H pour les vrais fichiers de tracks.

### Architecture

- Confirmer après C la séparation `TrackDefinition` / données runtime dérivées.
- Prévoir après G/H une frontière `UR2D2RawTrackData` ou `UR2D2RuntimeTrackData` → convertisseur → `TrackDefinition` si l’un des imports est viable.

### ADR

- ADR-0001 : à confirmer après B et F.
- ADR-0002 : candidat confirmé par E, à figer après mesure de charge F.
- ADR-0003 : à confirmer après A.
- ADR relatif au format de circuit et aux importeurs externes : à envisager après C, G et H.

## 7. Décision de sortie

La décision finale doit sélectionner une option :

- **Go** : les risques majeurs sont suffisamment réduits pour développer le vertical slice ;
- **Go avec réserves** : développement autorisé avec contraintes et travaux de réduction de risque intégrés ;
- **Rework** : une ou plusieurs expériences doivent être reprises avant le code de production ;
- **No-Go** : le concept ou l’architecture doit être profondément revu.

La décision générale de passage au vertical slice peut être distincte de la décision d’utiliser UR2D2. Un résultat négatif de G ou H peut conduire à un `Go` pour le projet avec une autre chaîne de création de circuits, ou avec seulement l’autre chemin UR2D2 s’il est viable.

### Décision

Go avec réserves.

### Conditions éventuelles

- Ne pas transformer directement les prototypes en code de production sans frontière d'adaptation et tests de non-régression.
- Valider l'import UR2D2 sur plusieurs circuits, notamment avec pitlane, murs, surfaces et géométries plus complexes.
- Reprendre la calibration physique dans le vertical slice : grip latéral, direction, freinage, sous-virage/survirage.
- Confirmer les coûts dans Unity avec rendu, écriture replay et charge cible réelle.
