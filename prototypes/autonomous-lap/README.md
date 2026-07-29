# Prototype Autonomous Lap

- **Expérience :** C — Tour autonome et modèle minimal de circuit
- **Statut :** C-S06 validé avec réserves
- **Ticket :** #5
- **Protocole :** [../../docs/feasibility/experiments/C-AUTONOMOUS-LAP.md](../../docs/feasibility/experiments/C-AUTONOMOUS-LAP.md)

Ce prototype vérifie qu'un `TrackDefinition` minimal peut alimenter un contrôleur de tour autonome sans dépendre de Unity ni d'un éditeur externe.

## Entrées prévues

- `prototypes/autonomous-lap/fixtures/canonical_track.json`
- export A9 QFC55 dans `outputs/a9-raw-vehicle-data/QFC55 - Magmort Carcharhini RCZ/`
- résultats B dans `prototypes/vehicle-dynamics/results/`

## Résultats prévus

- validation du contrat de circuit ;
- prétraitement de la ligne centrale ;
- suivi de trajectoire ;
- adaptation de vitesse ;
- récupération après perturbation ;
- consolidation du contrat minimal pour l'expérience G.

Les résultats sont placés dans `prototypes/autonomous-lap/results/`.

## C-S01 - Contrat TrackDefinition

Le premier jalon valide une piste canonique créée directement dans le contrat interne candidat.

```powershell
python prototypes\autonomous-lap\tools\run_c_s01_track_contract.py
```

Sorties attendues :

- `prototypes/autonomous-lap/results/C_S01_TRACK_CONTRACT_RESULT.md`
- `prototypes/autonomous-lap/results/c_s01_track_contract_summary.json`

Résultat courant : la piste canonique est valide, fermée implicitement et prétraitée en distance curviligne, tangentes, normales, largeurs et courbure.

## C-S02 - Suivi de trajectoire à vitesse contrainte

Le second jalon teste un contrôleur pure pursuit sur trois tours à vitesse contrainte.

```powershell
python prototypes\autonomous-lap\tools\run_c_s02_path_following.py
```

Sorties attendues :

- `prototypes/autonomous-lap/results/C_S02_PATH_FOLLOWING_RESULT.md`
- `prototypes/autonomous-lap/results/c_s02_path_following_summary.json`

Résultat courant : trois tours terminés aux pas `1/60 s` et `1/120 s`, sans sortie de piste. L'erreur latérale moyenne de référence est d'environ 0,17 m.

## C-S03 - Adaptation de vitesse par courbure

Le troisième jalon utilise la QFC55 et remplace la vitesse constante par une cible issue de la courbure anticipée.

```powershell
python prototypes\autonomous-lap\tools\run_c_s03_curvature_speed.py
```

Sorties attendues :

- `prototypes/autonomous-lap/results/C_S03_CURVATURE_SPEED_RESULT.md`
- `prototypes/autonomous-lap/results/c_s03_curvature_speed_summary.json`
- `prototypes/autonomous-lap/results/C_S03_CURVATURE_SPEED_VISUALIZATION.svg`

Résultat courant : trois tours terminés aux pas `1/60 s` et `1/120 s`, sans sortie de piste. La référence `1/120 s` atteint 83,33 s sur trois tours, 49,31 km/h de vitesse moyenne et 0,231 m d'erreur latérale moyenne.

Réserve : la limite latérale est encore dérivée du proxy B-S04 `FrontGripG + RearGripG` avec facteur de sécurité.

Visualisation de contrôle :

```powershell
python prototypes\autonomous-lap\tools\render_c_s03_visualization.py
```

Elle produit un SVG autonome avec la piste, la ligne centrale et la trajectoire colorée par vitesse.

## C-S04 - Récupération après perturbation latérale

Le quatrième jalon conserve la QFC55 et la logique de vitesse C-S03, puis applique trois écarts latéraux instantanés.

```powershell
python prototypes\autonomous-lap\tools\run_c_s04_lateral_recovery.py
```

Sorties attendues :

- `prototypes/autonomous-lap/results/C_S04_LATERAL_RECOVERY_RESULT.md`
- `prototypes/autonomous-lap/results/c_s04_lateral_recovery_summary.json`
- `prototypes/autonomous-lap/results/C_S04_LATERAL_RECOVERY_VISUALIZATION.svg`

Résultat courant : trois perturbations récupérées aux pas `1/60 s` et `1/120 s`, sans sortie de piste. La référence `1/120 s` récupère les offsets `+2,75 m`, `-3,25 m` et `+3,00 m` en 1,433 s, 1,800 s et 2,467 s.

Réserve : la perturbation est un déplacement cinématique instantané, pas encore une perte d'adhérence ou un contact physique.

Visualisation de contrôle :

```powershell
python prototypes\autonomous-lap\tools\render_c_s04_visualization.py
```

Elle produit un SVG autonome avec la trajectoire colorée par erreur latérale absolue, les perturbations et les points de récupération.

## C-S05 - Différences de compétence pilote

Le cinquième jalon conserve la QFC55, le circuit et la logique C-S03, puis compare trois profils de contrôle.

```powershell
python prototypes\autonomous-lap\tools\run_c_s05_driver_profiles.py
```

Sorties attendues :

- `prototypes/autonomous-lap/results/C_S05_DRIVER_PROFILES_RESULT.md`
- `prototypes/autonomous-lap/results/c_s05_driver_profiles_summary.json`
- `prototypes/autonomous-lap/results/C_S05_DRIVER_PROFILES_VISUALIZATION.svg`

Résultat courant : les profils prudent, équilibré et agressif terminent trois tours sans sortie de piste. La référence `1/120 s` les différencie nettement : 115,28 s, 83,33 s et 56,84 s sur trois tours. Le prudent reste le plus propre en moyenne (`0,126 m`), l'équilibré conserve une marge (`0,231 m`), et l'agressif accepte davantage d'écart (`0,302 m`) en montant jusqu'à `1,002 g` latéral. Un témoin négatif de sur-vitesse est aussi exécuté : il sature le grip sur `84,11 %` des ticks, atteint un ratio de saturation maximal de `5,87x` et sort de piste, ce qui vérifie que le modèle ne tourne plus sans limite physique.

Réserve : les profils sont des réglages de contrôle heuristiques, pas encore des pilotes IA complets. La limite latérale est une saturation minimale du yaw demandé ; elle ne modélise pas encore séparément le sous-virage et le survirage.

Visualisation de contrôle :

```powershell
python prototypes\autonomous-lap\tools\render_c_s05_visualization.py
```

Elle produit un SVG autonome avec les trajectoires, le témoin de sur-vitesse et trois graphes de télémétrie par progression : vitesse, G latéral demandé et erreur latérale absolue. Les trajectoires nominales peuvent se superposer ; la lecture utile de C-S05 se fait donc surtout sur ces graphes.

## C-S06 - Consolidation du contrat minimal pour G

Le sixième jalon relit les résultats C-S01 à C-S05 et fige le contrat `TrackDefinition` v0.1 comme cible candidate de l'expérience G.

```powershell
python prototypes\autonomous-lap\tools\run_c_s06_contract_consolidation.py
```

Sorties attendues :

- `prototypes/autonomous-lap/results/C_S06_CONTRACT_CONSOLIDATION_RESULT.md`
- `prototypes/autonomous-lap/results/c_s06_contract_consolidation_summary.json`

Résultat courant : `TrackDefinition` v0.1 est prêt pour G avec réserves. Les champs source sont listés, les valeurs dérivées restent reconstruites au runtime, et G devra produire un JSON qui passe au minimum C-S01 puis C-S02 sans réparation cachée.
