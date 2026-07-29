# G-S03 - Conversion candidate vers TrackDefinition

- **Expérience :** G - Import du modèle minimal depuis les sauvegardes UR2D2
- **Scénario :** G-S03
- **Statut :** validated-with-reserves
- **Date :** 2026-07-29T17:01:13+00:00
- **TrackDefinition :** `C:\Users\jerem\Documents\UnityProject\Automation-LAP\prototypes\ur2d2-track-import\results\g_s03_track_definition_candidate.json`
- **Validation C-S01 :** succès

## Décision du jalon

G-S03 produit un `TrackDefinition` candidat qui passe les invariants C-S01.

## Politique de conversion

- Échelle : `1 m = 12.8 unités éditeur` (`grid-calibrated`).
- Raison échelle : Les deux premières clés route sont séparées par 1056 unités éditeur et 33 carreaux de grille, soit 32 unités éditeur par carreau. Avec 1 carreau = 2,5 m, l'échelle retenue est 12,8 unités éditeur par mètre.
- Largeur route : 10.000 m total (`source-file`).
- Axes : raw x increases to TrackDefinition x ; raw y is inverted so screen-down editor coordinates become negative forward coordinates (`experimental`).
- Interpolation vectorielle : cubic bezier per segment; handle A is key[i] + angleA[i]/weightA[i], handle B is key[i+1] + angleB[i]/weightB[i] (`experimental-needs-g-s04-confirmation`).
- Convention poignées : UR2D2 stores the incoming B handle on the previous segment row. Handle vectors use a global vertical inversion relative to raw point coordinates.
- Ligne centrale : 4 clés vectorielles -> 16 points échantillonnés.
- Checkpoints : 3 candidats mappés au point central le plus proche.

## Validation C-S01

- Erreurs : 0
- Points : 16
- Segments : 16
- Longueur : 272.884 m
- Largeur totale min : 10.000 m
- Courbure max absolue : 0.074087 1/m

## Réserves

- L'échelle est plausible mais pas calibrée avec une mesure connue en jeu.
- L'échelle est recalibrée depuis la grille éditeur : 33 carreaux pour 1056 unités éditeur, 1 carreau = 2,5 m.
- La largeur de route n'est plus forcée : elle provient du fichier source (`globalCandidates.float32At0`).
- L'inversion de l'axe Y est une hypothèse de convention écran -> monde.
- La ligne centrale est échantillonnée depuis des courbes de Bézier candidates ; la convention des poignées est cohérente avec le retour G-S04 mais reste à confirmer sur davantage de fixtures.
- Les murs, surfaces, lignes IA et pitlane lus par G-S02 ne sont pas encore inclus comme champs source `TrackDefinition` v0.1.
- G-S04 valide la cohérence visuelle interne, mais pas encore une superposition pixel-perfect avec une capture éditeur.
