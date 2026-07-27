# C-S06 - Consolidation du contrat minimal TrackDefinition

- **Experience :** C - Tour autonome et modele minimal de circuit
- **Scenario :** C-S06
- **Statut :** valide avec reserves
- **Date :** 2026-07-27T17:11:29Z
- **Objectif :** figer le contrat minimal candidat que G devra reconstruire depuis UR2D2.
- **Reserve :** le contrat est valide pour un controle centre-ligne ; il ne couvre pas encore elevation, surfaces detaillees, racing line ou pneus detailles.

## Decision

- Pret pour l'experience G : oui
- Niveau de confiance : moyen a bon
- Reserve principale : TrackDefinition v0.1 is validated for centerline-based autonomous control, but not yet for real imported tracks, detailed surfaces, elevation, racing lines, or a full understeer/oversteer tyre model.

## Champs source TrackDefinition v0.1

| Champ | Type | Contrainte | Raison |
| --- | --- | --- | --- |
| `kind` | string | must be TrackDefinition | contract identity |
| `schemaVersion` | semver string | 0.1.0 candidate | versioned importer target |
| `trackId` | string | stable unique id | persistence and replay references |
| `name` | string | human readable | debug and authoring |
| `coordinateSystem.units.distance` | enum | m | SI distance contract |
| `coordinateSystem.units.angle` | enum | rad | SI angle contract |
| `coordinateSystem.units.time` | enum | s | SI time contract |
| `coordinateSystem.axis.x` | enum | right | 2D coordinate convention |
| `coordinateSystem.axis.y` | enum | forward | 2D coordinate convention |
| `coordinateSystem.orientation` | enum | clockwise or counter-clockwise | authoring convention |
| `closedLoop` | bool | true for current scope | lap counting and implicit closure |
| `direction` | enum | clockwise or counter-clockwise | progression direction |
| `surface.type` | string | asphalt in fixture | future surface model |
| `surface.grip` | number | finite positive scalar | future surface grip multiplier |
| `centerline[].id` | string | unique and stable | references from start/checkpoints |
| `centerline[].x` | number | finite metres | track geometry |
| `centerline[].y` | number | finite metres | track geometry |
| `centerline[].leftWidth` | number | finite metres | left track limit |
| `centerline[].rightWidth` | number | finite metres | right track limit |
| `startLine.centerlinePointId` | string | references centerline[].id | lap origin |
| `startLine.width` | number | finite metres | start line drawing/import hint |
| `checkpoints[].id` | string | unique and stable | checkpoint identity |
| `checkpoints[].centerlinePointId` | string | references centerline[].id | progress validation |

## Valeurs derivees a ne pas stocker comme verite source

- segment list and segment length
- cumulative distance / curvilinear coordinate
- total track length
- sampled x/y positions along the centerline
- tangent and normal vectors
- local left/right width interpolation
- curvature and lookahead curvature
- projection of vehicle position onto centerline
- lateral error and off-track test
- lap count from wrapped progress

## Invariants valides

- kind == TrackDefinition
- schemaVersion == 0.1.0
- units are metres, radians and seconds
- closed loop is implicit from last centerline point to first point
- direction is explicit and finite
- centerline has at least 8 points
- centerline ids are unique
- coordinates and widths are finite
- total width is at least 4 m everywhere
- start line references a centerline point
- checkpoints are present and reference centerline points
- loop length is finite and above 100 m
- preprocessed curvature is finite

## Preuves C-S01 a C-S05

| Scenario | Preuve retenue |
| --- | --- |
| C-S01 | 24 points, 381.92 m, largeur min 10.00 m, courbure max 0.03578 1/m |
| C-S02 | 3 tours, erreur laterale moyenne 0.173 m, max 0.693 m, sorties 0 |
| C-S03 | 3 tours en 83.33 s, vitesse moyenne 49.31 km/h, G lateral max 0.446 g |
| C-S04 | 3 / 3 perturbations recuperees, recuperation max 2.467 s, sorties 0 |
| C-S05 | profils differencies ; temoin sur-vitesse sat. grip 84.11 %, ratio 5.87x, sorties 4011 |

## Contrat attendu pour G

- Produce a TrackDefinition JSON with the source fields listed by C-S06.
- Do not store derived runtime geometry as source truth when it can be reconstructed deterministically.
- Preserve SI units or document a deterministic conversion to metres/radians/seconds.
- Preserve the ordered centerline and the driving direction.
- Provide left/right drivable widths or a deterministic fallback width policy.
- Provide a start line and at least one checkpoint reference.
- Pass the C-S01 validator without hidden repair.
- Run at least the C-S02 path-following smoke test after conversion.

## Limites reportees

- Les largeurs restent scalaires gauche/droite ; pas encore de polygones de bord de piste.
- La piste canonique est synthetique ; G devra verifier un vrai import.
- La courbure est derivee d'une polyligne ; un lissage pourra etre necessaire.
- La limite laterale vehicule reste un proxy issu de B-S04/A9.
- C-S05 valide la detection de saturation du grip, pas un modele detaille sous-virage/survirage.

## Conclusion

C-S06 valide avec reserves `TrackDefinition` v0.1 comme contrat d'entree de G.
