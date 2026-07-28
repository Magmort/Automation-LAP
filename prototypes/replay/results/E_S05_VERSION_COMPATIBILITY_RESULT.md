# E-S05 - Compatibilite de version

- **Experience :** E - Replay minimal
- **Scenario :** E-S05
- **Statut :** valide avec reserves
- **Date :** 2026-07-28T14:24:40Z
- **Objectif :** verifier que le lecteur replay accepte la version supportee et refuse explicitement les versions ou structures incompatibles.
- **Reserve :** politique stricte de prototype : seule la version `0.1.0` est acceptee, sans migration automatique.

## Entrees

- Replay source : `prototypes/replay/results/e_s01_minimal_replay.replay.json`
- Cas : `prototypes/replay/fixtures/e_s05_compatibility_cases.json`

## Metriques

- Cas testes : 10
- Cas acceptes attendus : 1
- Cas refuses attendus : 9
- Attentes respectees : 10 / 10
- Versions supportees : 0.1.0
- Mismatches : 0

## Cas

| Cas | Attendu | Obtenu | Code attendu | Code obtenu | OK |
| --- | --- | --- | --- | --- | --- |
| valid_current | oui | oui | OK | OK | oui |
| unsupported_patch | non | non | UNSUPPORTED_SCHEMA_VERSION | UNSUPPORTED_SCHEMA_VERSION | oui |
| unsupported_future_major | non | non | UNSUPPORTED_SCHEMA_VERSION | UNSUPPORTED_SCHEMA_VERSION | oui |
| missing_schema | non | non | MISSING_FIELD | MISSING_FIELD | oui |
| invalid_kind | non | non | INVALID_KIND | INVALID_KIND | oui |
| missing_units | non | non | MISSING_FIELD | MISSING_FIELD | oui |
| missing_timeline | non | non | MISSING_FIELD | MISSING_FIELD | oui |
| frame_count_mismatch | non | non | FRAME_COUNT_MISMATCH | FRAME_COUNT_MISMATCH | oui |
| non_monotonic_frame_time | non | non | NON_MONOTONIC_FRAME_TIME | NON_MONOTONIC_FRAME_TIME | oui |
| malformed_json | non | non | INVALID_JSON | INVALID_JSON | oui |

## Decision

E-S05 est valide avec reserves. La detection des versions et structures incompatibles est explicite ; le prototype peut passer a E-S06 pour la synthese.
